#!/usr/bin/env python3
"""Live status page for a grind run: a read-only local server that shows what a running crew is doing.

grw.py --state <folder> status            print the status as JSON once
grw.py --state <folder> status --serve    serve http://127.0.0.1:<port>/ (refreshes itself) and open it

Reads only: BOARD.md, mode.json, WAITING.md, events.jsonl, ledger.jsonl, timing.md, sessions/, logs/, and the process list
(which grind_loop members and agent sessions are alive for this state folder). Writes nothing, takes no lock,
so it is safe beside a running crew. Standard library only.
"""
import datetime as dt
import html
import json
import os
import importlib.util
import re
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grind_report import FAVICON_LINK, open_asks  # noqa: E402
import report_ui  # noqa: E402

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


def _mode(root):
    try:
        return json.loads((root / "mode.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ---- who is running in this project, and the way back to askwright (both optional: the page works without askwright)

def project_dir(state):
    """The project folder: <project>/ai-docs/grind -> <project>."""
    root = Path(state).resolve()
    return root.parent.parent if root.parent.name == "ai-docs" else root


def askwright_scripts():
    """askwright's scripts folder: ASKWRIGHT_SCRIPTS, the installed plugin, or a clone beside this one. None when absent."""
    cands = [os.environ.get("ASKWRIGHT_SCRIPTS")]
    try:
        inst = json.loads((Path.home() / ".claude" / "plugins" / "installed_plugins.json").read_text("utf-8"))
        cands += [str(Path(r["installPath"], "skills", "askwright", "scripts"))
                  for k, recs in inst["plugins"].items() if k.startswith("askwright@") for r in recs]
    except Exception:
        pass
    cands.append(str(Path(__file__).resolve().parents[4] / "askwright" / "skills" / "askwright" / "scripts"))
    return next((Path(c) for c in cands if c and (Path(c) / "agents.py").is_file()), None)


def _claims_only(root, now):
    """Without askwright: the ledger's running claims, each with its lease. Sessions that claimed nothing stay unseen."""
    latest = {}
    for record in _jsonl(root / "ledger.jsonl"):
        if record.get("id"):
            latest[record["id"]] = record
    claim_ts = {e.get("id"): e.get("ts") for e in _jsonl(root / "events.jsonl") if e.get("type") == "claim"}
    rows = []
    for item in latest.values():
        if item.get("state") != "running":
            continue
        try:
            lease = dt.datetime.fromisoformat(str(item.get("lease_until"))[:19])
        except ValueError:
            lease = None
        expired = lease is not None and lease < now
        claim = {"id": item["id"], "title": str(item.get("title") or "")[:120]}
        for k in ("handed_off", "paused_by"):
            if item.get(k):
                claim[k] = item[k]
        how = f", lease ran out at {item.get('lease_until')}" if expired else f", lease until {item.get('lease_until')}"
        rows.append({"session": item.get("session") or "solo", "status": "possibly stale" if expired else "claimed, no session seen",
                     "claims": [claim], "branch": item.get("branch") or "", "started": claim_ts.get(item["id"]),
                     "subagents": [], "evidence": ["grindwright claim" + how]})
    return rows


_WHO_CACHE = {}


def who(state, now=None):
    """Every agent session seen in this project (askwright's agents.py), or the grindwright claims alone, with problems
    said in words so an unreadable source never looks like an empty list. Cached 10 s for the page's refresh."""
    key = str(Path(state).resolve())
    hit = _WHO_CACHE.get(key)
    if hit and now is None and time.time() - hit[0] < 10:
        return hit[1]
    stamp = now or dt.datetime.now()
    scripts = askwright_scripts()
    data = None
    if scripts:
        try:
            spec = importlib.util.spec_from_file_location("askwright_agents_for_grind", scripts / "agents.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            data = mod.collect([str(project_dir(state))])
            data["source"] = "askwright"
        except Exception as error:
            data = {"problems": [f"askwright's session collector failed ({error}): only grindwright claims show"]}
    if data is None or data.get("source") != "askwright":
        problems = (data or {}).get("problems") or [
            "askwright is not installed, so only grindwright claims show: a session that claimed nothing is not listed"]
        data = {"rows": _claims_only(Path(state), stamp), "problems": problems, "source": "grindwright claims",
                "note": "claims only"}
    data.setdefault("built", stamp.isoformat(timespec="seconds"))
    if now is None:
        _WHO_CACHE[key] = (time.time(), data)
    return data


def askwright_link(state):
    """The askwright project page for this folder, only when its hub answers. None otherwise."""
    home = Path(os.environ.get("ASKWRIGHT_HOME") or Path.home() / ".askwright")
    here = project_dir(state).as_posix().lower()
    slug = None
    for f in sorted((home / "projects").glob("*.json")):
        try:
            rec = json.loads(f.read_text("utf-8"))
            dirs = [Path(d).resolve().as_posix().lower() for d in rec.get("dirs") or []]
        except (OSError, ValueError, TypeError):
            continue
        if here in dirs:
            slug = rec.get("slug") or f.stem
            break
    if not slug:
        return None
    try:
        port = int(os.environ.get("ASKWRIGHT_PORT") or 47631)
        socket.create_connection(("127.0.0.1", port), 0.3).close()
    except (OSError, ValueError):
        return None
    return f"http://127.0.0.1:{port}/projects/{slug}"


def steerwright_link(state):
    """The steerwright project page (mounted at /steer/ on askwright's hub) for this folder, only when steerwright
    has a project naming this folder or grind state and the hub answers. None otherwise."""
    reg = Path(os.environ.get("STEERWRIGHT_HOME") or Path.home() / ".steerwright") / "projects.json"
    try:
        projects = json.loads(reg.read_text("utf-8")).get("projects") or {}
    except (OSError, ValueError, AttributeError):
        return None
    norm = lambda p: Path(p).resolve().as_posix().lower()
    here, st = norm(project_dir(state)), norm(state)
    key = next((k for k, rec in projects.items() if isinstance(rec, dict) and (
        here in {norm(p) for p in rec.get("paths") or []}
        or st in {norm(p) for p in (rec.get("sources") or {}).get("grindwright") or []})), None)
    if not key:
        return None
    try:
        port = int(os.environ.get("ASKWRIGHT_PORT") or 47631)
        socket.create_connection(("127.0.0.1", port), 0.3).close()
    except (OSError, ValueError):
        return None
    return f"http://127.0.0.1:{port}/steer/p/{key}"


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
        "new_work": (_mode(root)).get("new_work", "on"),
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
        "who": who(root),
        "links": {k: v for k, v in {"askwright": askwright_link(root), "steerwright": steerwright_link(root)}.items() if v},
    }


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
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
</style></head><body><main aria-busy="true">
<header><div><h1 id="proj">Grind status</h1><div class="mute" id="sub"></div></div><div><span id="run" class="pill off">...</span> <span id="mode" class="pill off" style="display:none" title="only owner-driven items: grw.py new-work on restarts new work"></span> <span class="mute loading" id="upd" role="status" aria-live="polite">Loading status</span></div></header>
<nav id="links" class="mute" style="margin:-6px 0 10px"></nav>
<div class="grid">
<section class="card wide"><div class="stats" id="stats"></div></section>
<section class="card wide" id="who-card"><h2 id="who-h">Who is running in this project</h2><div id="who"></div></section>
<section class="card"><h2>Members</h2><div id="members"></div></section>
<section class="card"><h2>Working now</h2><div id="working"></div></section>
<section class="card wide"><h2>Timeline (this run)</h2><div class="scroll" id="timeline"></div></section>
<section class="card"><h2>Askwright pages waiting</h2><div id="asks"></div></section>
<section class="card"><h2>Waiting on you</h2><div id="waiting"></div></section>
<section class="card"><h2>Notes between members</h2><div id="notes"></div></section>
<section class="card wide"><h2>Estimate vs actual (minutes)</h2><div id="timing"></div></section>
</div></main>__RUI__<script>
function retry(){const u=document.getElementById('upd');u.className='mute loading';u.textContent='Retrying';tick()}
const e=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const hm=s=>s?s.slice(11,16):'';const ago=m=>m==null?'':m<60?m+' min':Math.floor(m/60)+' h '+(m%60)+' min';
const link=s=>e(s).replace(/(https?:\/\/[^\s,]+)/g,'<a href="$1" target="_blank">$1</a>');
const dur=m=>m==null||isNaN(m)||m<0?'':m<60?Math.round(m)+' min':Math.floor(m/60)+' h '+Math.round(m%60)+' min';
const since=(t,now)=>t?(Date.parse(now)-Date.parse(t))/60000:null;
function drawWho(d){const w=d.who||{rows:[],problems:['no session data']};
links.innerHTML=Object.entries(d.links||{}).map(([k,u])=>`<a href="${e(u)}">${k==='askwright'?'&larr; askwright project page':k==='steerwright'?'steerwright project page':e(k)}</a>`).join(' &middot; ');
document.getElementById('who-h').textContent='Who is running in this project'+(w.built?' (checked '+hm(w.built)+(w.note?', '+w.note:'')+')':'');
const rows=(w.rows||[]).map(r=>{const what=(r.claims||[]).map(c=>e(c.id+' '+c.title)).join('; ')||e(r.title||r.name||'(no claimed task)');
 const subs=(r.subagents||[]).map(a=>e(a.description)+' <span class="mute">('+e(a.status)+')</span>').join(', ');
 const run=dur(since(r.started,d.now)),quiet=r.minutes_quiet!=null?dur(r.minutes_quiet):dur(since(r.last_activity,d.now));
 const cls=r.status==='live'?'k-done':r.status==='recent'?'k-asked':'k-skip';
 return `<tr><td class="${cls}"><b>${e(r.status)}</b>${r.stale_reason?'<div class="mute">'+e(r.stale_reason)+'</div>':''}</td><td>${what}${subs?'<div class="mute">subagents: '+subs+'</div>':''}</td>`+
 `<td><code>${e(r.branch||'')}</code><div class="mute">${e(r.worktree||r.cwd||'')}${r.machine?' · '+e(r.machine):''}</div></td>`+
 `<td class="t">${r.started?'started '+e(String(r.started).slice(5,16).replace('T',' ')):''}${run?'<div>working '+run+'</div>':''}${quiet?'<div>quiet '+quiet+'</div>':''}</td>`+
 `<td class="mute">${e((r.evidence||[]).join('; '))}</td></tr>`}).join('');
document.getElementById('who').innerHTML=(rows?'<div class="scroll"><table id="who-t" data-ui data-page="25"><thead><tr><th data-sort="text">status</th><th data-sort="text">working on</th><th>where</th><th>time</th><th>how it is known</th></tr></thead><tbody>'+rows+'</tbody></table></div>':'<p class="empty">No agent session seen in this project'+(w.source==='askwright'?' on this machine':'')+'. Start one with grind_loop.py or a continue prompt; it shows here within a minute.</p>')+
 (w.problems||[]).map(p=>'<p class="k-skip">'+e(p)+'</p>').join('');}
async function tick(){let d;const u=document.getElementById('upd');try{d=await (await fetch('api',{cache:'no-store'})).json()}catch(x){
u.className='err';u.innerHTML='Server not answering; the page keeps the last data. <button type="button" class="retry" onclick="retry()">Retry</button>';return}
u.className='mute';document.querySelector('main').removeAttribute('aria-busy');
drawWho(d);document.title=(d.running?'● ':'')+d.project+' grind';proj.textContent=d.project;sub.textContent='run since '+d.since.replace('T',' ')+'  ·  '+d.state;
run.textContent=d.running?'RUNNING':'NOT RUNNING';run.className='pill '+(d.running?'on':'off');mode.textContent=d.new_work==='off'?'NEW WORK OFF':'';mode.style.display=d.new_work==='off'?'':'none';u.innerHTML='updated <time title="'+e(d.now)+'">'+hm(d.now)+':'+d.now.slice(17,19)+'</time>, every 15 s';
const c=d.counts,cost=Object.values(d.logs).reduce((a,l)=>a+l.cost,0),ses=Object.values(d.logs).reduce((a,l)=>a+l.sessions,0);
stats.innerHTML=[['done',c.done],['claimed',c.claim],['added',c.add],['asked',c.asked],['skipped',(c.skip||0)+(c.released||0)+(c.dropped||0)],['agent sessions finished',ses],['agent cost',cost?'$'+cost.toFixed(2):'-'],['live agents',d.processes.agents.length]]
 .map(([k,v])=>`<div class="stat"><b>${e(v??0)}</b><span>${k}</span></div>`).join('');
const p=d.processes;members.innerHTML=(p.error?`<p class="mute">process list failed: ${e(p.error)}</p>`:'')+(p.crew.length?`<p class="mute">crew ${e(p.crew[0].file)} since ${e(hm(p.crew[0].since))}</p>`:'')+
 '<table><thead><tr><th>member</th><th>since</th><th class="n">sessions</th><th class="n">cost</th><th>log</th></tr></thead><tbody>'+
 [...new Set([...p.members.map(m=>m.member),...Object.keys(d.logs)])].map(n=>{const m=p.members.find(x=>x.member==n),l=d.logs[n]||{};
 return `<tr><td>${m?'🟢':'⚪'} ${e(n)}</td><td class="t">${e(m?hm(m.since):'')}</td><td class="n">${e(l.sessions??'')}</td><td class="n">${l.cost?'$'+l.cost.toFixed(2):''}</td><td class="mute"><code>${e(l.log||'')}</code></td></tr>`}).join('')+'</tbody></table>'+
 (Object.values(d.logs).some(l=>l.last)?'<h2 style="margin-top:10px">Last agent result</h2>'+Object.entries(d.logs).filter(([,l])=>l.last).map(([n,l])=>`<pre><b>${e(n)}</b>: ${e(l.last.slice(-300))}</pre>`).join(''):'');
working.innerHTML=d.working.length?'<table><tr><th>member</th><th>item</th><th>for</th></tr>'+d.working.map(w=>`<tr><td>${e(w.member)}</td><td>${e(w.title)} <span class="mute">${e(w.lane||'')} · <code>${e(w.id)}</code></span></td><td class="t">${ago(w.minutes)}</td></tr>`).join('')+'</table>':'<p class="empty">Nothing claimed. A member claims an item when its session starts work.</p>';
timeline.innerHTML=d.timeline.length?'<table id="tl" data-ui data-page="25"><tbody>'+d.timeline.map(v=>`<tr><td class="t">${hm(v.ts)}</td><td class="k-${e(v.type)}"><b>${e(v.type)}</b></td><td>${e(v.session||'')}</td><td>${e(v.title||v.text||v.source||'')} <span class="mute">${e(v.lane||'')} ${v.id?'<code>'+e(v.id)+'</code>':''}</span>${v.evidence?'<div class="mute">'+e(v.evidence)+'</div>':''}${v.why?'<div class="mute">'+e(v.why)+'</div>':''}</td></tr>`).join('')+'</tbody></table>':'<p class="empty">No events since the run started. Events appear as members claim, finish or ask.</p>';
asks.innerHTML=d.asks.length?'<ul>'+d.asks.map(a=>'<li><code>'+e(a.set)+'</code> ('+e(a.people.join(', ')||'anyone')+'): '+a.items.map(i=>e(i.id+' '+i.title)).join('; ')+'</li>').join('')+'</ul>':'<p class="mute">none open</p>';
waiting.innerHTML=d.waiting.length?'<ul>'+d.waiting.map(w=>'<li>'+link(w)+'</li>').join('')+'</ul>':'<p class="mute">nothing</p>';
notes.innerHTML=d.notes.length?'<ul>'+d.notes.slice().reverse().map(n=>'<li>'+e(n)+'</li>').join('')+'</ul>':'<p class="mute">none</p>';
timing.innerHTML=d.timing.length?'<table id="timing-t" data-ui data-page="25"><thead><tr><th data-sort="text">date</th><th data-sort="text">member</th><th data-sort="text">item</th><th class="n" data-sort="num">est</th><th class="n" data-sort="num">actual</th><th>why</th></tr></thead><tbody>'+d.timing.slice().reverse().map(t=>`<tr><td class="t">${e(t.date)}</td><td>${e(t.member)}</td><td>${e(t.title)}</td><td class="n">${e(t.estimate)}</td><td class="n">${e(t.actual)}</td><td class="mute">${e(t.why)}</td></tr>`).join('')+'</tbody></table>':'<p class="empty">No estimates recorded yet; rows come from timing.md in the state folder.</p>';
RUI.enhance();}
tick();setInterval(tick,15000);
</script></body></html>"""
PAGE = PAGE.replace("</style>", report_ui.CSS + "</style>", 1).replace("__RUI__", report_ui.JS)


FETCH = "await (await fetch('api',{cache:'no-store'})).json()"


def page(inline=None):
    """The status page. With inline (the collect() dict), the data is built in and no fetch is made: for hosts such as
    askwright's hub whose sandboxed page has no origin to fetch from. Such hosts reload the page to refresh it."""
    if inline is None:
        return PAGE
    data = json.dumps(json.loads(json.dumps(inline, default=str)), ensure_ascii=False).replace("</", "<\\/")
    return (PAGE.replace(FETCH, "JSON.parse(document.getElementById('grind-data').textContent)", 1)
            .replace("</body>", f"<script type='application/json' id='grind-data'>{data}</script></body>", 1))


def make_server(state, port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path.startswith("/api"):
                body = json.dumps(collect(state), ensure_ascii=False).encode("utf-8")
                kind = "application/json"
            elif self.path in ("/", "/index.html"):
                body, kind = page().encode("utf-8"), "text/html; charset=utf-8"
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
