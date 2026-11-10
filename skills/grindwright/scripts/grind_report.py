#!/usr/bin/env python3
"""Run report: one HTML page, shown when a grind run ends, saying what the run did and why it stopped.

build:   grind_report.py build --state <folder> --run <logs/run-ID.json> [--out page.html] [--open] [--force] [--no-github]
enabled: grind_report.py enabled --state <folder> [--crew crew.json]     exit 0 on, 1 off.

The run file is written by grind_loop.py and grind_crew.py: when it ran, which members, each member's stop
result and the sessions it ran (Claude session id, time, cost, tokens). The report adds, for the run's window:
the ledger events (what was finished, drafted, asked, added, per lane and road milestone), the pull requests
and issues GitHub shows as created, updated or commented on, and a chainwright tier page when chainwright is
installed. Switches, most specific first: --no-report on the driver, GRINDWRIGHT_REPORT=off, the crew file's
"report", the profile's "report"; default on. "open_report": false in either file builds without opening.
Standard library only; GitHub needs the gh CLI and is skipped quietly without it.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent

STOPS = {
    "ledger": "the ledger had nothing left this member could do; the rest waits on people or other members",
    "max-sessions": "it used every session the run allowed",
    "max-hours": "it reached the run's time limit",
    "no-progress": "two sessions in a row changed nothing in the ledger",
    "usage-limit": "the usage limit lasted longer than the run could wait",
    "session-failed": "an agent session exited with an error",
    "session-timeout": "a session ran past its time limit and was ended",
    "plugin-missing": "two sessions in a row ran without the plugin loaded",
    "command-not-found": "the agent command was not found",
    "driver-output": "the member's driver printed something unreadable",
    "crashed": "the driver crashed",
    "skipped": "it never started: nothing was selectable for it",
}
WORK = ("done", "drafted", "asked", "add", "claim")
LABEL = {"done": "finished", "drafted": "drafted", "asked": "asked a person", "add": "added", "claim": "started"}


def steerwright_link():
    """A header link to the steerwright hub when ~/.steerwright/server.json has a url, else ''."""
    home = os.environ.get("STEERWRIGHT_HOME") or os.path.join(os.path.expanduser("~"), ".steerwright")
    try:
        with open(os.path.join(home, "server.json"), encoding="utf-8") as f:
            url = json.load(f).get("url")
    except (OSError, ValueError, AttributeError):
        return ""
    if not isinstance(url, str) or not re.match(r"https?://", url):
        return ""
    return (f'<nav style="float:right;font-size:13px"><a href="{html.escape(url, quote=True)}" '
            'title="all projects">steerwright</a></nav>')


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def jsonl(path):
    rows = []
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return rows
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def open_asks(state):
    """Askwright sets still waiting on a person for this state folder: one row per set, its items and people."""
    sets = {}
    for i in jsonl(Path(state) / "ledger.jsonl"):
        if i.get("state") == "waiting-on-human" and i.get("set"):
            row = sets.setdefault(str(i["set"]), {"set": str(i["set"]), "items": [], "people": set(), "since": ""})
            row["items"].append({"id": i.get("id"), "title": i.get("title", "")})
            if i.get("person"):
                row["people"].add(str(i["person"]))
            row["since"] = max(row["since"], str(i.get("updated") or i.get("ts") or ""))
    # Sets on disk (the project's ask/ folder) with questions nobody has answered yet.
    root = Path(state).resolve()
    for base in {root.parent.parent / "ask", root / "ask"}:
        for qf in sorted(base.glob("*/questions.json")) if base.is_dir() else []:
            q = read_json(qf, {}) or {}
            qs = q.get("questions", []) if isinstance(q, dict) else []
            ans = read_json(qf.parent / "answers.json", {}) or {}
            ans = ans.get("answers", ans) if isinstance(ans, dict) else {}
            open_q = [x for x in qs if isinstance(x, dict) and x.get("id") not in ans]
            if open_q:
                row = sets.setdefault(qf.parent.name, {"set": qf.parent.name, "items": [], "people": set(), "since": ""})
                row["open_questions"] = len(open_q)
                row["title"] = q.get("title", "")
                if not row["items"]:
                    row["items"] = [{"id": x.get("id"), "title": x.get("title") or x.get("question", "")} for x in open_q]
    return [dict(r, people=sorted(r["people"])) for r in sorted(sets.values(), key=lambda r: r["set"])]


def enabled(state, crew=None):
    """Return (build, open)."""
    if (os.environ.get("GRINDWRIGHT_REPORT") or "").lower() in ("off", "0", "false", "no"):
        return False, False
    profile = read_json(Path(state) / "profile.json", {}) or {}
    for source in (crew or {}, profile):
        if source.get("report") is not None:
            return bool(source["report"]), bool(source.get("open_report", True)) and bool(source["report"])
    return True, bool((crew or {}).get("open_report", profile.get("open_report", True)))


def stamp():
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def usage_of(stdout):
    """The claude -p --output-format json result line: session id, cost, time, tokens, turns."""
    for line in reversed((stdout or "").strip().splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            found = json.loads(line)
        except ValueError:
            continue
        if isinstance(found, dict) and ("total_cost_usd" in found or "session_id" in found):
            usage = found.get("usage") or {}
            tokens = sum(v for k, v in usage.items() if k.endswith("tokens") and isinstance(v, int)) or None
            model = next(iter(found.get("modelUsage") or {}), None)
            return {"session_id": found.get("session_id"), "usd": found.get("total_cost_usd"), "tokens": tokens,
                    "seconds": round((found.get("duration_ms") or 0) / 1000) or None, "turns": found.get("num_turns"), "model": model}
    return {}


def write_run(path, run):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes((json.dumps(run, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))


def chain_ledger(run, path):
    """The run as a chainwright ledger (one chain per member), so chain_report.py can draw it."""
    chains = []
    for m in run.get("members", []):
        history = [{"at": p.get("started"), "outcome": p.get("outcome", ""), "seconds": p.get("seconds"), "tokens": p.get("tokens"),
                    "usd": p.get("usd"), "model": p.get("model")} for p in m.get("passes", [])]
        chains.append({"name": m["member"], "prompt": run.get("prompt") or "", "sessions": len(history), "history": history,
                       "state": (m.get("result") or {}).get("stopped", "")})
    ledger = {"name": run.get("id", "grind run"), "project": run.get("project"), "report": True, "managers": [], "chains": chains}
    if len(chains) == 1:
        ledger["headless"] = True
    write_run(path, ledger)
    return path


def find_chain_report():
    """chainwright's chain_report.py: $CHAINWRIGHT_REPORT, the newest plugin cache copy, or a clone beside this plugin."""
    if os.environ.get("CHAINWRIGHT_REPORT") and Path(os.environ["CHAINWRIGHT_REPORT"]).exists():
        return Path(os.environ["CHAINWRIGHT_REPORT"])
    cache = Path.home() / ".claude" / "plugins" / "cache"
    found = sorted(cache.glob("*/chainwright/*/skills/chainwright/scripts/chain_report.py"), key=lambda p: p.stat().st_mtime)
    if found:
        return found[-1]
    sibling = HERE.parents[3] / "chainwright" / "skills" / "chainwright" / "scripts" / "chain_report.py"
    return sibling if sibling.exists() else None


def transcript(cwd, session_id):
    """Where Claude Code keeps a session's transcript: ~/.claude/projects/<cwd with non-alphanumerics as ->/<id>.jsonl."""
    if not cwd or not session_id:
        return None
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(Path(cwd).resolve()))
    path = Path.home() / ".claude" / "projects" / slug / f"{session_id}.jsonl"
    return path if path.exists() else None


def gh_json(args, cwd):
    if not shutil.which("gh"):
        return None
    try:
        done = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", cwd=cwd, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode:
        return None
    try:
        return json.loads(done.stdout)
    except ValueError:
        return None


def utc(ts):
    """Local ledger time to the UTC that GitHub searches and returns."""
    try:
        return dt.datetime.fromisoformat(ts).astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def github(repo_dir, since, until):
    """PRs and issues the run's account created, updated or commented on in the window."""
    start, end = utc(since), utc(until)
    if not start or not repo_dir or not Path(repo_dir).exists():
        return None
    day = start.strftime("%Y-%m-%d")
    fields = "number,title,url,state,createdAt,updatedAt,author"

    def within(row, key):
        when = dt.datetime.fromisoformat(row[key].replace("Z", "+00:00"))
        return start <= when and (not end or when <= end + dt.timedelta(minutes=5))

    prs = gh_json(["pr", "list", "--state", "all", "--author", "@me", "--search", f"updated:>={day}", "--limit", "100", "--json", fields], repo_dir)
    if prs is None:
        return None
    out = {"prs_created": [], "prs_updated": [], "issues_created": [], "issues_commented": []}
    for pr in prs:
        if within(pr, "createdAt"):
            out["prs_created"].append(pr)
        elif within(pr, "updatedAt"):
            out["prs_updated"].append(pr)
    issues = gh_json(["issue", "list", "--state", "all", "--search", f"involves:@me updated:>={day}", "--limit", "100", "--json", fields], repo_dir) or []
    for issue in issues:
        if not within(issue, "updatedAt"):
            continue
        mine = (issue.get("author") or {}).get("login") == (prs[0]["author"]["login"] if prs else None)
        (out["issues_created"] if mine and within(issue, "createdAt") else out["issues_commented"]).append(issue)
    return out


def collect(state, run, use_github=True):
    state = Path(state)
    since, until = run.get("started"), run.get("ended") or stamp()
    members = {m["member"] for m in run.get("members", [])}
    events = [e for e in jsonl(state / "events.jsonl") if since <= (e.get("ts") or "") <= until
              and (not members or e.get("session") in members or e.get("session") is None)]
    items = {i["id"]: i for i in jsonl(state / "ledger.jsonl") if "id" in i}
    road = read_json(state / "road.json", {}) or {}
    lanes, touched, ends = {}, {}, []
    for e in events:
        kind = e.get("type")
        if kind == "session_end":
            ends.append(e)
        if kind not in WORK or not e.get("id"):
            continue
        item = items.get(e["id"], {})
        lane = e.get("lane") or item.get("lane") or "?"
        lanes.setdefault(lane, dict.fromkeys(WORK, 0))[kind] += 1
        row = touched.setdefault(e["id"], {"id": e["id"], "title": item.get("title") or e.get("id"), "lane": lane, "road": item.get("road"),
                                           "now": item.get("state", "?"), "pr": item.get("pr"), "issue": item.get("issue"),
                                           "source": item.get("source"), "evidence": item.get("evidence"), "did": [], "by": set(),
                                           "shots": item.get("shots", []), "no_shots": item.get("no_shots")})
        if kind not in row["did"]:
            row["did"].append(kind)
        row["by"].add(e.get("session") or "")
    left = {}
    for item in items.values():
        if item.get("state") in ("done", "dropped", "rejected"):
            continue
        left.setdefault(item.get("lane") or "?", {}).setdefault(item.get("state", "?"), 0)
        left[item.get("lane") or "?"][item.get("state", "?")] += 1
    stones = []
    for stone in road.get("milestones", []):
        mine = [i for i in items.values() if i.get("road") == stone.get("id")]
        stones.append({"id": stone.get("id"), "title": stone.get("title"), "status": stone.get("status", ""),
                       "done": sum(i.get("state") == "done" for i in mine), "total": len(mine),
                       "this_run": sum(1 for t in touched.values() if t["road"] == stone.get("id") and "done" in t["did"])})
    profile = read_json(state / "profile.json", {}) or {}
    repo = profile.get("repo")
    if repo and not Path(repo).is_absolute():
        repo = str((state.parent / repo).resolve())
    gh = github(repo, since, until) if use_github else None
    roots = [Path(repo)] if repo else []
    roots += [Path(m["cwd"]) for m in run.get("members", []) if m.get("cwd")]
    for row in touched.values():
        row["pictures"] = [picture(shot, roots) for shot in row["shots"]]
    return {"events": events, "lanes": lanes, "touched": list(touched.values()), "left": left, "stones": stones,
            "ends": ends, "github": gh, "road": road, "since": since, "until": until}


IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
MAX_EMBED = 1_500_000


def picture(shot, roots):
    """(src, href) for one screenshot: a URL as is; a local file embedded when small, so the page travels alone."""
    if shot.startswith("http"):
        return shot, shot
    for root in roots:
        path = (root / shot) if not Path(shot).is_absolute() else Path(shot)
        if path.exists():
            kind = IMAGE_TYPES.get(path.suffix.lower())
            href = path.resolve().as_uri()
            if kind and path.stat().st_size <= MAX_EMBED:
                import base64
                return f"data:{kind};base64," + base64.b64encode(path.read_bytes()).decode(), href
            return (href if kind else None), href
    return None, None


def fmt_s(s):
    s = int(s or 0)
    return f"{s // 3600}h {s % 3600 // 60}m" if s >= 3600 else f"{s // 60}m {s % 60}s" if s >= 60 else f"{s}s"


def span_seconds(a, b):
    try:
        return (dt.datetime.fromisoformat(b) - dt.datetime.fromisoformat(a)).total_seconds()
    except (TypeError, ValueError):
        return 0


def svg_bars(rows, series, colors, width=640, unit=""):
    """Horizontal stacked bars: rows = [(label, {series: value})]."""
    if not rows:
        return "<p class='mute'>nothing to chart</p>"
    top = max(sum(v.get(s, 0) or 0 for s in series) for _, v in rows) or 1
    h, left, out = 22, 120, []
    for n, (label, values) in enumerate(rows):
        y, x = n * (h + 6), left
        out.append(f'<text x="{left - 8}" y="{y + 15}" text-anchor="end" class="lbl">{html.escape(str(label))[:18]}</text>')
        total = 0
        for s, color in zip(series, colors):
            v = values.get(s, 0) or 0
            w = (width - left - 60) * v / top
            if w:
                out.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w, 1.5):.1f}" height="{h}" rx="3" fill="{color}"><title>{html.escape(str(label))}: {html.escape(LABEL.get(s, s))} {v:g}{unit}</title></rect>')
            x += w
            total += v
        out.append(f'<text x="{x + 6:.1f}" y="{y + 15}" class="lbl">{total:g}{unit}</text>')
    legend = "".join(f'<span><i style="background:{c}"></i>{html.escape(LABEL.get(s, s))}</span>' for s, c in zip(series, colors))
    return f'<svg viewBox="0 0 {width} {len(rows) * (h + 6)}" width="100%" role="img">{"".join(out)}</svg><div class="legend">{legend}</div>'


def svg_timeline(run, width=640):
    start = run.get("started")
    total = span_seconds(start, run.get("ended") or stamp()) or 1
    members = run.get("members", [])
    if not members:
        return ""
    h, left, out = 22, 120, []
    for n, m in enumerate(members):
        y = n * (h + 6)
        out.append(f'<text x="{left - 8}" y="{y + 15}" text-anchor="end" class="lbl">{html.escape(m["member"])}</text>')
        out.append(f'<rect x="{left}" y="{y + h / 2 - 1}" width="{width - left - 10}" height="2" fill="var(--line)"/>')
        for p in m.get("passes", []):
            x0 = left + (width - left - 10) * max(0, span_seconds(start, p.get("started"))) / total
            w = max(2, (width - left - 10) * (p.get("seconds") or span_seconds(p.get("started"), p.get("ended"))) / total)
            color = {"worked": "var(--ok)", "idle": "var(--wait)", "failed": "var(--bad)"}.get(p.get("outcome"), "var(--mute)")
            tip = f'pass {p.get("n")}: {p.get("outcome")}, {fmt_s(p.get("seconds"))}, ${p.get("usd") or 0:.2f}'
            out.append(f'<rect x="{x0:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="3" fill="{color}"><title>{html.escape(tip)}</title></rect>')
    axis = f'<text x="{left}" y="{len(members) * (h + 6) + 12}" class="lbl">{html.escape(start or "")[11:16]}</text>' \
           f'<text x="{width - 10}" y="{len(members) * (h + 6) + 12}" text-anchor="end" class="lbl">{html.escape((run.get("ended") or "")[11:16])}</text>'
    return (f'<svg viewBox="0 0 {width} {len(members) * (h + 6) + 16}" width="100%" role="img">{"".join(out)}{axis}</svg>'
            '<div class="legend"><span><i style="background:var(--ok)"></i>worked</span><span><i style="background:var(--wait)"></i>idle</span>'
            '<span><i style="background:var(--bad)"></i>failed</span></div>')


def link(url, text):
    return f'<a href="{html.escape(url)}">{html.escape(text)}</a>' if url else html.escape(text)


def gh_rows(rows):
    if not rows:
        return "<p class='mute'>none</p>"
    return "<ul>" + "".join(f'<li>{link(r["url"], "#" + str(r["number"]))} {html.escape(r["title"])} <span class="chip">{html.escape(r["state"].lower())}</span></li>' for r in rows) + "</ul>"


# Tab icon, inline so it works from file:// and served: a white gear on an amber tile (askwright's tile style).
FAVICON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect x="1" y="1" width="30" height="30" rx="8" fill="#c9821f"/>'
               '<circle cx="16" cy="16" r="9" fill="none" stroke="#fff" stroke-width="4" stroke-dasharray="3.53 3.53"/>'
               '<circle cx="16" cy="16" r="5.5" fill="none" stroke="#fff" stroke-width="3.5"/></svg>')
FAVICON_LINK = '<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,' + FAVICON_SVG.replace('"', "'").replace("#", "%23").replace("<", "%3C").replace(">", "%3E") + '">'


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
""" + FAVICON_LINK + """
<title>__TITLE__</title><style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--mute:#6b6b66;--line:#e2e1dc;--t:#3b6fd8;--m:#c9821f;--ok:#2f9e5a;--bad:#d04848;--wait:#8a6fd1;--add:#9aa3ad}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#17181a;--card:#212226;--ink:#ecebe6;--mute:#9a9a94;--line:#34353a;--t:#6c9bff;--m:#e7a64a;--add:#6b737c}}
:root[data-theme=dark]{--bg:#17181a;--card:#212226;--ink:#ecebe6;--mute:#9a9a94;--line:#34353a;--t:#6c9bff;--m:#e7a64a;--add:#6b737c}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif;padding:24px 16px}main{max-width:1000px;margin:auto}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:22px 0 8px}.sub,.mute{color:var(--mute)}a{color:var(--t)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:14px 0}
.kpi,.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}.kpi b{display:block;font-size:20px}.kpi span{color:var(--mute);font-size:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
td,th{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{color:var(--mute);font-weight:600;font-size:12px}
.chip{border:1px solid var(--line);border-radius:999px;padding:0 8px;font-size:11px;color:var(--mute);white-space:nowrap}
.lbl{fill:var(--mute);font-size:12px}.legend{color:var(--mute);font-size:12px;display:flex;flex-wrap:wrap;gap:12px;margin-top:4px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:middle}
.stop{border-left:4px solid var(--wait)}.stop.bad{border-left-color:var(--bad)}code{font-size:12px}
details summary{cursor:pointer;color:var(--mute)}.shots img{height:96px;max-width:100%;border:1px solid var(--line);border-radius:6px;margin:2px 6px 2px 0;object-fit:contain;background:var(--bg)}ul{margin:4px 0;padding-left:20px}
@media (max-width:600px){td,th{padding:5px 6px}.hide-s{display:none}}
</style></head><body><main>__STEER__
__BODY__
</main></body></html>"""


def render(run, data, chain_page=None):
    e = html.escape
    members = run.get("members", [])
    passes = [p for m in members for p in m.get("passes", [])]
    usd = sum(p.get("usd") or 0 for p in passes)
    tokens = sum(p.get("tokens") or 0 for p in passes)
    agent_s = sum(p.get("seconds") or 0 for p in passes)
    wall = span_seconds(run.get("started"), run.get("ended") or stamp())
    finished = sum(v["done"] for v in data["lanes"].values())
    drafted = sum(v["drafted"] for v in data["lanes"].values())
    gh = data["github"] or {}
    kpis = [("wall time", fmt_s(wall)), ("agent time", fmt_s(agent_s)), ("sessions", len(passes)), ("cost", f"${usd:,.2f}"),
            ("tokens", f"{tokens:,}"), ("finished", finished), ("drafted", drafted),
            ("PRs opened", len(gh.get("prs_created", [])) if data["github"] is not None else "?")]
    body = [f'<h1>{e(run.get("project") or "Grind")} run report</h1>',
            f'<div class="sub">{e(run.get("id", ""))} · {e(run.get("started", ""))} to {e(run.get("ended") or "still running")} · '
            f'{len(members)} member{"s" * (len(members) != 1)}{" · " + link(Path(chain_page).resolve().as_uri(), "chainwright tier report") if chain_page else ""}</div>',
            '<div class="kpis">' + "".join(f'<div class="kpi"><b>{e(str(v))}</b><span>{k}</span></div>' for k, v in kpis) + "</div>"]

    body.append("<h2>Why it stopped</h2>")
    for m in members:
        r = m.get("result") or {}
        why = STOPS.get(r.get("stopped"), r.get("stopped") or "still running")
        bad = not r.get("ok", True)
        extra = ""
        if r.get("why"):
            extra += "<ul>" + "".join(f"<li>{e(str(w))}</li>" for w in (r["why"] if isinstance(r["why"], list) else [r["why"]])) + "</ul>"
        if r.get("waiting_on"):
            extra += "<div class='mute'>waiting on: " + e(", ".join(str(w) for w in r["waiting_on"])) + "</div>"
        last = next((x for x in reversed(data["ends"]) if x.get("session") == m["member"] and x.get("reason")), None)
        if last:
            extra += f"<div class='mute'>its last session said: {e(last['reason'])}</div>"
        body.append(f'<div class="card stop{" bad" if bad else ""}"><b>{e(m["member"])}</b> · {len(m.get("passes", []))} session(s) · '
                    f'<code>{e(r.get("stopped", "?"))}</code>: {e(why)}{extra}</div>')

    body.append('<h2>Charts</h2><div class="grid">')
    lane_rows = sorted(data["lanes"].items(), key=lambda kv: -sum(kv[1].values()))
    body.append('<div class="card"><b>Work by lane</b>' + svg_bars(lane_rows, ["done", "drafted", "asked", "add"], ["var(--ok)", "var(--t)", "var(--wait)", "var(--add)"]) + "</div>")
    mem_rows = [(m["member"], {"usd": round(sum(p.get("usd") or 0 for p in m.get("passes", [])), 2)}) for m in members]
    body.append('<div class="card"><b>Cost by member ($)</b>' + svg_bars(mem_rows, ["usd"], ["var(--m)"]) + "</div>")
    min_rows = [(m["member"], {"minutes": round(sum(p.get("seconds") or 0 for p in m.get("passes", [])) / 60, 1)}) for m in members]
    body.append('<div class="card"><b>Agent minutes by member</b>' + svg_bars(min_rows, ["minutes"], ["var(--t)"]) + "</div>")
    body.append('<div class="card"><b>Sessions over the run</b>' + svg_timeline(run) + "</div></div>")

    body.append("<h2>How far each front got</h2>")
    if data["stones"]:
        body.append("<table><tr><th>Road milestone</th><th>Items done</th><th>This run</th><th class='hide-s'>Status</th></tr>" + "".join(
            f"<tr><td>{e(s['title'] or s['id'])}</td><td>{s['done']} of {s['total']}</td><td>{s['this_run']}</td><td class='hide-s'>{e(s['status'])}</td></tr>"
            for s in data["stones"]) + "</table><br>")
    lanes = sorted(set(data["lanes"]) | set(data["left"]))
    body.append("<table><tr><th>Lane</th><th>This run</th><th>Still open</th></tr>" + "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            e(lane),
            e(", ".join(f"{v} {LABEL[k]}" for k, v in data["lanes"].get(lane, {}).items() if v and k != "claim") or "nothing"),
            e(", ".join(f"{v} {k}" for k, v in sorted(data["left"].get(lane, {}).items())) or "none"))
        for lane in lanes) + "</table>")

    body.append("<h2>Pull requests and issues</h2>")
    if data["github"] is None:
        body.append("<p class='mute'>GitHub not read (no gh, no repo, or --no-github); the items below come from the ledger.</p>")
    else:
        body.append('<div class="grid">' + "".join(f'<div class="card"><b>{t}</b>{gh_rows(gh.get(k, []))}</div>' for t, k in (
            ("PRs opened", "prs_created"), ("PRs updated", "prs_updated"), ("Issues opened", "issues_created"),
            ("Issues commented on or touched", "issues_commented"))) + "</div>")

    body.append("<h2>Items worked</h2>")
    if data["touched"]:
        rows = []
        for t in sorted(data["touched"], key=lambda t: (t["lane"], t["id"])):
            refs = []
            if t["pr"]:
                refs.append(f"PR #{t['pr']}")
            if t["issue"]:
                refs.append(f"issue #{t['issue']}")
            src = link(t["source"], "source") if (t["source"] or "").startswith("http") else ""
            rows.append(f"<tr><td><code>{e(t['id'])}</code></td><td>{e(t['title'])}<div class='mute'>{e((t['evidence'] or '')[:220])}</div></td>"
                        f"<td>{e(t['lane'])}</td><td>{e(', '.join(LABEL[d] for d in t['did']))}</td><td>{e(t['now'])}</td>"
                        f"<td class='hide-s'>{e(', '.join(refs))} {src}</td></tr>")
            thumbs = "".join(f'<a href="{e(href or shot)}"><img src="{e(src)}" alt="{e(shot)}" loading="lazy"></a>' if src else
                             f'<span class="chip">{e(shot)} (not found)</span>' for shot, (src, href) in zip(t["shots"], t["pictures"]))
            if t["no_shots"]:
                thumbs += f"<span class='mute'>no screenshot: {e(t['no_shots'])}</span>"
            if thumbs:
                rows.append(f"<tr><td></td><td colspan='5' class='shots'>{thumbs}</td></tr>")
        body.append("<table><tr><th>Item</th><th>What</th><th>Lane</th><th>This run</th><th>Now</th><th class='hide-s'>Links</th></tr>" + "".join(rows) + "</table>")
    else:
        body.append("<p class='mute'>No item was started, finished, drafted or asked about in this run.</p>")

    body.append("<h2>Sessions</h2><table><tr><th>Member</th><th>#</th><th>Outcome</th><th>Time</th><th>Cost</th><th class='hide-s'>Tokens</th><th>Session</th></tr>")
    for m in members:
        for p in m.get("passes", []):
            path = transcript(m.get("cwd"), p.get("session_id"))
            sid = p.get("session_id") or ""
            ref = link(path.as_uri(), sid[:8]) if path else e(sid[:8])
            resume = f"<div class='mute'><code>claude --resume {e(sid)}</code></div>" if sid else ""
            body.append(f"<tr><td>{e(m['member'])}</td><td>{p.get('n')}</td><td>{e(p.get('outcome', ''))}</td><td>{fmt_s(p.get('seconds'))}</td>"
                        f"<td>${p.get('usd') or 0:.2f}</td><td class='hide-s'>{(p.get('tokens') or 0):,}</td><td>{ref}{resume}</td></tr>")
    body.append("</table>")
    title = f"{run.get('project') or 'Grind'} Run Report"
    return PAGE.replace("__TITLE__", e(title)).replace("__BODY__", "".join(body)).replace("__STEER__", steerwright_link())


def summary_md(run, data):
    members = run.get("members", [])
    passes = [p for m in members for p in m.get("passes", [])]
    lines = [f"Run {run.get('id')}: {len(passes)} sessions, ${sum(p.get('usd') or 0 for p in passes):.2f}, "
             f"{fmt_s(span_seconds(run.get('started'), run.get('ended') or stamp()))} wall time."]
    for m in members:
        r = m.get("result") or {}
        lines.append(f"- {m['member']}: {len(m.get('passes', []))} sessions, stopped `{r.get('stopped', '?')}` ({STOPS.get(r.get('stopped'), '')})")
    for lane, v in sorted(data["lanes"].items()):
        lines.append(f"- lane {lane}: " + ", ".join(f"{n} {LABEL[k]}" for k, n in v.items() if n and k != "claim"))
    gh = data["github"]
    if gh:
        for key, label in (("prs_created", "PRs opened"), ("prs_updated", "PRs updated"), ("issues_created", "issues opened"), ("issues_commented", "issues touched")):
            if gh.get(key):
                lines.append(f"- {label}: " + ", ".join(f"#{r['number']}" for r in gh[key]))
    return "\n".join(lines)


def build(state, run_path, out=None, open_page=False, use_github=True):
    run = read_json(run_path)
    if not run:
        return {"ok": False, "error": f"no run file at {run_path}"}
    data = collect(state, run, use_github)
    chain_page = None
    script = find_chain_report()
    if script and run.get("members"):
        ledger = chain_ledger(run, Path(run_path).with_suffix(".chain.json"))
        chain_page = Path(run_path).with_name(Path(run_path).stem + "-tiers.html")
        subprocess.run([sys.executable, str(script), "build", str(ledger), "--out", str(chain_page), "--force"], capture_output=True)
        if not chain_page.exists():
            chain_page = None
    out = Path(out) if out else Path(run_path).with_name(Path(run_path).stem + "-report.html")
    out.write_bytes(render(run, data, chain_page).encode("utf-8"))
    md = summary_md(run, data)
    out.with_suffix(".md").write_bytes((md + "\n").encode("utf-8"))
    if open_page:
        webbrowser.open(out.resolve().as_uri())
    index = None
    try:  # the master page of every run (grind_index.py); a failure here never fails the run report
        import grind_index
        grind_index.add(state, run_path)
        index = grind_index.build()["page"]
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "report": str(out), "summary": md, "chain_report": str(chain_page) if chain_page else None,
            "github": data["github"] is not None, "index": index}


def finish(state, run_path, crew=None, forced_off=False):
    """Called by the drivers when a run ends: build and show unless switched off. Never raises."""
    try:
        on, show = enabled(state, crew)
        if forced_off or not on:
            return {"report": "off"}
        return build(state, run_path, open_page=show)
    except Exception as error:  # a report must never turn a finished run into a failed one
        return {"ok": False, "report_error": repr(error)[:300]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--state", required=True)
    b.add_argument("--run", help="logs/run-ID.json; default the newest in the state's logs")
    b.add_argument("--out")
    b.add_argument("--open", action="store_true")
    b.add_argument("--force", action="store_true", help="build even when switched off")
    b.add_argument("--no-github", action="store_true")
    en = sub.add_parser("enabled")
    en.add_argument("--state", required=True)
    en.add_argument("--crew")
    a = p.parse_args(argv)
    crew = read_json(a.crew) if getattr(a, "crew", None) else None
    if a.command == "enabled":
        on, show = enabled(a.state, crew)
        print(json.dumps({"on": on, "open": show}))
        return 0 if on else 1
    run = a.run
    if not run:
        found = sorted((Path(a.state) / "logs").glob("run-*.json"), key=lambda p: p.stat().st_mtime)
        found = [f for f in found if not f.name.endswith(".chain.json")]
        if not found:
            print(json.dumps({"ok": False, "error": "no run file in logs/"}))
            return 2
        run = found[-1]
    if not a.force and not enabled(a.state)[0]:
        print(json.dumps({"ok": True, "skipped": "report is off (profile or GRINDWRIGHT_REPORT); --force builds anyway"}))
        return 1
    result = build(a.state, run, a.out, a.open, not a.no_github)
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
