#!/usr/bin/env python3
"""Live status page for a grind run: a read-only local server that shows what a running crew is doing.

grw.py --state <folder> status            print the status as JSON once
grw.py --state <folder> status --serve    serve http://127.0.0.1:<port>/ (refreshes itself) and open it

Reads only: BOARD.md, WAITING.md, events.jsonl, ledger.jsonl, timing.md, sessions/, logs/, and the process list
(which grind_loop members and agent sessions are alive for this state folder). Writes nothing, takes no lock,
so it is safe beside a running crew. Standard library only.
"""
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grind_report import FAVICON_LINK, open_asks  # noqa: E402

ENDS = {"done", "released", "skip", "dropped", "rejected", "drafted", "asked", "detached", "resolved"}


def _jsonl(path, tail=None):
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if tail:
        lines = lines[-tail:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def _section(text, heading):
    m = re.search(r"^## " + re.escape(heading) + r"\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    return [line[2:].strip() for line in m.group(1).splitlines() if line.startswith("- ")]


def _processes(state):
    """Live grind_loop members and agent sessions whose command line names this state folder."""
    key = Path(state).resolve().as_posix().lower()
    rows = []
    try:
        if os.name == "nt":
            cmd = ["powershell", "-NoProfile", "-Command",
                   "Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'grind_loop|grind_crew|claude' } | "
                   "select ProcessId,ParentProcessId,CommandLine,@{n='Start';e={$_.CreationDate.ToString('s')}} | ConvertTo-Json -Compress"]
            raw = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=20).stdout.strip()
            data = json.loads(raw) if raw else []
            rows = data if isinstance(data, list) else [data]
        else:
            raw = subprocess.run(["ps", "-eo", "pid=,ppid=,lstart=,args="], capture_output=True, text=True, timeout=10).stdout
            for line in raw.splitlines():
                parts = line.split(None, 7)
                if len(parts) == 8:
                    rows.append({"ProcessId": int(parts[0]), "ParentProcessId": int(parts[1]), "Start": " ".join(parts[2:7]), "CommandLine": parts[7]})
    except Exception as error:  # status must still render without a process list
        return {"error": str(error), "members": [], "agents": [], "crew": []}
    members, agents, crew = [], [], []
    for row in rows:
        line = (row.get("CommandLine") or "")
        flat = line.replace("\\", "/").lower()
        if "get-ciminstance" in flat:  # this status query itself
            continue
        if "grind_crew" in flat and "nohup" not in flat:  # crew lines name the crew file, not the state folder
            crew.append({"pid": row["ProcessId"], "since": row.get("Start"), "file": (re.search(r"--go\s+(\S+)", line) or [None, ""])[1]})
            continue
        if key not in flat:
            continue
        if "grind_loop" in flat:
            m = re.search(r"--session-id\s+(\S+)", line)
            members.append({"pid": row["ProcessId"], "member": m.group(1) if m else "solo", "since": row.get("Start")})
        elif "claude" in flat and "-p" in line and not line.lower().startswith(("c:\\windows\\system32\\cmd", "cmd")):
            agents.append({"pid": row["ProcessId"], "parent": row.get("ParentProcessId"), "since": row.get("Start")})
    # attach agents to members through the cmd.exe parent chain when possible
    return {"members": members, "agents": agents, "crew": crew}


def _log_stats(logs, since):
    """Agent results in today's member logs: sessions finished, cost, last result line."""
    stats = {}
    if not logs.exists():
        return stats
    for path in sorted(logs.glob("*.log")):
        member = path.stem.rsplit("-", 3)[0] if re.search(r"-\d{4}-\d{2}-\d{2}$", path.stem) else path.stem
        if dt.datetime.fromtimestamp(path.stat().st_mtime) < since:
            continue
        done = cost = 0
        last = ""
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("{"):
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("type") == "result":
                done += 1
                cost += float(record.get("total_cost_usd") or 0)
                last = (record.get("result") or "")[-400:]
        row = stats.setdefault(member, {"sessions": 0, "cost": 0.0, "last": "", "log": path.name})
        row["sessions"] += done
        row["cost"] = round(row["cost"] + cost, 2)
        row["last"] = last or row["last"]
        row["log"] = path.name
    return stats


def collect(state, since=None):
    root = Path(state)
    now = dt.datetime.now()
    procs = _processes(root)
    starts = [p.get("since") for p in procs.get("crew", []) + procs.get("members", []) if p.get("since")]
    if since is None:
        try:
            since = min(dt.datetime.fromisoformat(s[:19]) for s in starts) if starts else now.replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    items = {}
    for record in _jsonl(root / "ledger.jsonl"):
        if record.get("id"):
            items[record["id"]] = record
    events = _jsonl(root / "events.jsonl")
    open_claims = {}
    counts = {}
    timeline = []
    for event in events:
        kind, item = event.get("type"), event.get("id")
        if kind == "claim":
            open_claims[item] = event
        elif kind in ENDS:
            open_claims.pop(item, None)
        try:
            when = dt.datetime.fromisoformat(event.get("ts", "")[:19])
        except ValueError:
            continue
        if when >= since:
            counts[kind] = counts.get(kind, 0) + 1
            timeline.append(event)
    working = []
    for item, event in open_claims.items():
        rec = items.get(item, {})
        if rec.get("state") in ("done", "dropped"):
            continue
        try:
            age = int((now - dt.datetime.fromisoformat(event["ts"][:19])).total_seconds() // 60)
        except (KeyError, ValueError):
            age = None
        working.append({"id": item, "member": event.get("session"), "lane": event.get("lane") or rec.get("lane"),
                        "title": rec.get("title") or item, "minutes": age, "cost": rec.get("cost")})
    working.sort(key=lambda w: (w["minutes"] is None, w["minutes"] or 0))
    for event in timeline:
        rec = items.get(event.get("id"), {})
        event["title"] = rec.get("title", "")
        event["lane"] = event.get("lane") or rec.get("lane", "")
    board = (root / "BOARD.md").read_text(encoding="utf-8", errors="replace") if (root / "BOARD.md").exists() else ""
    waiting = (root / "WAITING.md").read_text(encoding="utf-8", errors="replace") if (root / "WAITING.md").exists() else ""
    timing_rows = []
    if (root / "timing.md").exists():
        for line in (root / "timing.md").read_text(encoding="utf-8", errors="replace").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 7 and re.match(r"\d{4}-\d{2}-\d{2}$", cells[0]):
                timing_rows.append(dict(zip(["date", "member", "id", "title", "estimate", "actual", "why"], cells)))
    project = re.search(r"Project: ([^.\n]+)", board)
    return {
        "project": project.group(1) if project else root.name,
        "state": str(root.resolve()),
        "now": now.isoformat(timespec="seconds"),
        "since": since.isoformat(timespec="seconds"),
        "running": bool(procs.get("members") or procs.get("crew")),
        "processes": procs,
        "counts": counts,
        "working": working,
        "timeline": list(reversed(timeline[-80:])),
        "notes": _section(board, "Notes")[-8:],
        "asks": [dict(a, since=a["since"][:16]) for a in open_asks(root)],
        "waiting": [line[2:] for line in waiting.splitlines() if line.startswith("- ")],
        "timing": timing_rows[-10:],
        "logs": _log_stats(root / "logs", since),
    }


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
""" + FAVICON_LINK + r"""
<title>Grind status</title><style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2330;--mute:#6b7280;--line:#e3e6ec;--ok:#15803d;--warn:#b45309;--bad:#b91c1c;--acc:#2563eb}
@media (prefers-color-scheme:dark){:root{--bg:#12151b;--card:#1b2029;--ink:#e6e9ef;--mute:#9aa3b2;--line:#2a313d;--ok:#4ade80;--warn:#fbbf24;--bad:#f87171;--acc:#60a5fa}}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,Segoe UI,sans-serif}
main{max-width:1200px;margin:0 auto;padding:16px}h1{font-size:20px;margin:0}h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);margin:0 0 8px}
header{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin-bottom:14px}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-weight:600;font-size:12px}
.on{background:color-mix(in srgb,var(--ok) 18%,transparent);color:var(--ok)}.off{background:color-mix(in srgb,var(--mute) 18%,transparent);color:var(--mute)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;min-width:0}
.wide{grid-column:1/-1}.stats{display:flex;flex-wrap:wrap;gap:18px}.stat b{display:block;font-size:24px}.stat span{color:var(--mute);font-size:12px}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:4px 6px;border-top:1px solid var(--line);vertical-align:top}th{color:var(--mute);font-weight:500;font-size:12px;border-top:0}
.mute{color:var(--mute)}.t{white-space:nowrap;color:var(--mute);font-variant-numeric:tabular-nums}code{font-size:12px}
.k-done{color:var(--ok)}.k-skip,.k-dropped,.k-rejected,.k-released{color:var(--warn)}.k-asked{color:var(--acc)}
ul{margin:0;padding-left:18px}li{margin:3px 0;overflow-wrap:anywhere}.scroll{max-height:420px;overflow:auto}pre{white-space:pre-wrap;margin:0;font-size:12px;color:var(--mute)}
</style></head><body><main>
<header><div><h1 id="proj">Grind status</h1><div class="mute" id="sub"></div></div><div><span id="run" class="pill off">...</span> <span class="mute" id="upd"></span></div></header>
<div class="grid">
<section class="card wide"><div class="stats" id="stats"></div></section>
<section class="card"><h2>Members</h2><div id="members"></div></section>
<section class="card"><h2>Working now</h2><div id="working"></div></section>
<section class="card wide"><h2>Timeline (this run)</h2><div class="scroll" id="timeline"></div></section>
<section class="card"><h2>Askwright pages waiting</h2><div id="asks"></div></section>
<section class="card"><h2>Waiting on you</h2><div id="waiting"></div></section>
<section class="card"><h2>Notes between members</h2><div id="notes"></div></section>
<section class="card wide"><h2>Estimate vs actual (minutes)</h2><div id="timing"></div></section>
</div></main><script>
const e=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const hm=s=>s?s.slice(11,16):'';const ago=m=>m==null?'':m<60?m+' min':Math.floor(m/60)+' h '+(m%60)+' min';
const link=s=>e(s).replace(/(https?:\/\/[^\s,]+)/g,'<a href="$1" target="_blank">$1</a>');
async function tick(){let d;try{d=await (await fetch('api',{cache:'no-store'})).json()}catch(x){document.getElementById('upd').textContent='server not answering';return}
document.title=(d.running?'● ':'')+d.project+' grind';proj.textContent=d.project;sub.textContent='run since '+d.since.replace('T',' ')+'  ·  '+d.state;
run.textContent=d.running?'RUNNING':'NOT RUNNING';run.className='pill '+(d.running?'on':'off');upd.textContent='updated '+hm(d.now)+':'+d.now.slice(17,19);
const c=d.counts,cost=Object.values(d.logs).reduce((a,l)=>a+l.cost,0),ses=Object.values(d.logs).reduce((a,l)=>a+l.sessions,0);
stats.innerHTML=[['done',c.done],['claimed',c.claim],['added',c.add],['asked',c.asked],['skipped',(c.skip||0)+(c.released||0)+(c.dropped||0)],['agent sessions finished',ses],['agent cost',cost?'$'+cost.toFixed(2):'-'],['live agents',d.processes.agents.length]]
 .map(([k,v])=>`<div class="stat"><b>${e(v??0)}</b><span>${k}</span></div>`).join('');
const p=d.processes;members.innerHTML=(p.error?`<p class="mute">process list failed: ${e(p.error)}</p>`:'')+(p.crew.length?`<p class="mute">crew ${e(p.crew[0].file)} since ${e(hm(p.crew[0].since))}</p>`:'')+
 '<table><tr><th>member</th><th>since</th><th>sessions</th><th>cost</th><th>log</th></tr>'+
 [...new Set([...p.members.map(m=>m.member),...Object.keys(d.logs)])].map(n=>{const m=p.members.find(x=>x.member==n),l=d.logs[n]||{};
 return `<tr><td>${m?'🟢':'⚪'} ${e(n)}</td><td class="t">${e(m?hm(m.since):'')}</td><td>${e(l.sessions??'')}</td><td>${l.cost?'$'+l.cost.toFixed(2):''}</td><td class="mute"><code>${e(l.log||'')}</code></td></tr>`}).join('')+'</table>'+
 (Object.values(d.logs).some(l=>l.last)?'<h2 style="margin-top:10px">Last agent result</h2>'+Object.entries(d.logs).filter(([,l])=>l.last).map(([n,l])=>`<pre><b>${e(n)}</b>: ${e(l.last.slice(-300))}</pre>`).join(''):'');
working.innerHTML=d.working.length?'<table><tr><th>member</th><th>item</th><th>for</th></tr>'+d.working.map(w=>`<tr><td>${e(w.member)}</td><td>${e(w.title)} <span class="mute">${e(w.lane||'')} · <code>${e(w.id)}</code></span></td><td class="t">${ago(w.minutes)}</td></tr>`).join('')+'</table>':'<p class="mute">nothing claimed</p>';
timeline.innerHTML=d.timeline.length?'<table>'+d.timeline.map(v=>`<tr><td class="t">${hm(v.ts)}</td><td class="k-${e(v.type)}"><b>${e(v.type)}</b></td><td>${e(v.session||'')}</td><td>${e(v.title||v.text||v.source||'')} <span class="mute">${e(v.lane||'')} ${v.id?'<code>'+e(v.id)+'</code>':''}</span>${v.evidence?'<div class="mute">'+e(v.evidence)+'</div>':''}${v.why?'<div class="mute">'+e(v.why)+'</div>':''}</td></tr>`).join('')+'</table>':'<p class="mute">no events since the run started</p>';
asks.innerHTML=d.asks.length?'<ul>'+d.asks.map(a=>'<li><code>'+e(a.set)+'</code> ('+e(a.people.join(', ')||'anyone')+'): '+a.items.map(i=>e(i.id+' '+i.title)).join('; ')+'</li>').join('')+'</ul>':'<p class="mute">none open</p>';
waiting.innerHTML=d.waiting.length?'<ul>'+d.waiting.map(w=>'<li>'+link(w)+'</li>').join('')+'</ul>':'<p class="mute">nothing</p>';
notes.innerHTML=d.notes.length?'<ul>'+d.notes.slice().reverse().map(n=>'<li>'+e(n)+'</li>').join('')+'</ul>':'<p class="mute">none</p>';
timing.innerHTML=d.timing.length?'<table><tr><th>date</th><th>member</th><th>item</th><th>est</th><th>actual</th><th>why</th></tr>'+d.timing.slice().reverse().map(t=>`<tr><td class="t">${e(t.date)}</td><td>${e(t.member)}</td><td>${e(t.title)}</td><td>${e(t.estimate)}</td><td>${e(t.actual)}</td><td class="mute">${e(t.why)}</td></tr>`).join('')+'</table>':'<p class="mute">none</p>';}
tick();setInterval(tick,15000);
</script></body></html>"""


def make_server(state, port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path.startswith("/api"):
                body = json.dumps(collect(state), ensure_ascii=False).encode("utf-8")
                kind = "application/json"
            elif self.path in ("/", "/index.html"):
                body, kind = PAGE.encode("utf-8"), "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(state, port=0, open_browser=True):
    server = make_server(state, port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(json.dumps({"ok": True, "url": url, "state": str(Path(state).resolve())}), flush=True)
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def cmd_status(store, args):
    if args.serve:
        sys.exit(serve(store.root, args.port, not args.no_open))
    return collect(store.root)


def add_parsers(add):
    p = add("status", cmd_status, "live run status; --serve for a self-refreshing local page")
    p.add_argument("--serve", action="store_true")
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--no-open", action="store_true")
