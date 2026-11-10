#!/usr/bin/env python3
"""Master page: every grind session and run on this computer, by project, with links to reports and sessions.

build:   grind_index.py build [--scan DIR ...] [--no-transcripts] [--include-temp] [--out page.html] [--open]
add:     grind_index.py add --state <folder> --run <logs/run-ID.json>

Two sources. Runs: the registry (~/.grindwright/runs.jsonl, or $GRINDWRIGHT_HOME/runs.jsonl), which
grind_report.py build appends to whenever it writes a run report, plus state folders found under --scan
(ai-docs/grind/logs/run-*.json up to six levels down; found runs join the registry, so one scan is enough).
Sessions: Claude Code transcripts (~/.claude/projects/*/*.jsonl) that ran `grw.py session start`, cached by
size and time in the registry folder; sessions in temp folders (eval sandboxes) are left out unless
--include-temp. The project is the grind profile's "project" found from the session's folder.
The page: totals, sessions and cost per project, sessions per day, every session with a resume command,
and every run with its report. Standard library only.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import webbrowser
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grind_report import PAGE, fmt_s, open_asks, read_json, span_seconds, steerwright_link, svg_bars  # noqa: E402

SKIP = {"node_modules", ".git", "Library", "Temp", "obj", "bin", "venv", ".venv", "__pycache__", "Logs", "Packages"}
START = re.compile(r"grw\.py.*\bsession\s+start\b")
TEMP = re.compile(r"[\\/](Temp|tmp)[\\/]", re.I)
PALETTE = ["var(--t)", "var(--m)", "var(--ok)", "var(--wait)", "var(--bad)", "var(--add)"]


def home():
    return Path(os.environ.get("GRINDWRIGHT_HOME") or Path.home() / ".grindwright")


def claude_projects():
    return Path(os.environ.get("GRINDWRIGHT_CLAUDE_PROJECTS") or Path.home() / ".claude" / "projects")


def registry():
    return home() / "runs.jsonl"


def norm(p):
    return os.path.normcase(str(Path(p).resolve())) if p else ""


def load_registry():
    rows, seen = [], set()
    if registry().exists():
        for line in registry().read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if norm(row.get("run", "")) not in seen:
                seen.add(norm(row.get("run", "")))
                rows.append(row)
    return rows


def add(state, run):
    """Record a run in the registry once; returns True when it was new."""
    if any(norm(r.get("run", "")) == norm(run) for r in load_registry()):
        return False
    home().mkdir(parents=True, exist_ok=True)
    with open(registry(), "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"state": str(Path(state).resolve()), "run": str(Path(run).resolve())}) + "\n")
    return True


def scan(root, depth=6):
    found, stack = [], [(Path(root), 0)]
    while stack:
        folder, d = stack.pop()
        try:
            entries = list(os.scandir(folder))
        except OSError:
            continue
        for e in entries:
            if not e.is_dir(follow_symlinks=False) or e.name in SKIP:
                continue
            p = Path(e.path)
            if e.name == "grind" and p.parent.name == "ai-docs":
                found += [(p, r) for r in sorted((p / "logs").glob("run-*.json")) if not r.name.endswith(".chain.json")]
            elif d < depth:
                stack.append((p, d + 1))
    return found


def transcript_session(path):
    """The grind facts of one Claude transcript, or None when it never ran `grw.py session start`."""
    first = last = cwd = sid = where = None
    starts = 0
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"timestamp"' not in line:
                    continue
                hit = "session start" in line and "grw" in line and "tool_use" in line
                if first and cwd and not hit:
                    m = re.search(r'"timestamp":\s*"([^"]+)"', line)
                    last = m.group(1) if m else last
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                first = first or rec.get("timestamp")
                last = rec.get("timestamp") or last
                cwd = cwd or rec.get("cwd")
                sid = sid or rec.get("sessionId")
                if hit:
                    for c in (rec.get("message") or {}).get("content") or []:
                        command = str((c.get("input") or {}).get("command", "")) if isinstance(c, dict) and c.get("type") == "tool_use" else ""
                        if invokes_start(command):
                            starts += 1
                            where = where or where_of(command)
    except OSError:
        return None
    if not starts or not cwd:
        return None
    return {"id": sid or Path(path).stem, "cwd": where or cwd, "started": first or "", "ended": last or "", "starts": starts}


Q = r'(?:"[^"]*"|\'[^\']*\'|[^\s;|&]+)'
CALL = re.compile(r'(?:grw\.py["\']?|\$\{?\w+\}?["\']?)(?:\s+--state\s+' + Q + r')?\s+session\s+start\b')


def invokes_start(command):
    """True when a shell command runs `grw.py session start` (directly or through a variable holding grw.py),
    not when it only greps for the words or carries them in a heredoc."""
    if "grw.py" not in command or "<<" in command:
        return False
    command = re.sub(r'"[^"]*session\s+start[^"]*"|\'[^\']*session\s+start[^\']*\'', '""', command)  # search patterns
    for seg in re.split(r"&&|\|\||[;|\n]", command):
        seg = seg.strip().lstrip("(").strip()
        if CALL.search(seg) and not re.match(r"(?:time\s+)?\(?\s*(?:grep|rg|egrep|findstr|Select-String|echo|printf|cat|sed|awk)\b", seg, re.I):
            return True
    return False


def plugin_repo(folder):
    """True inside a clone of grindwright itself: sessions there are the plugin's own evals, not a project."""
    p = Path(folder)
    return any((d / "skills" / "grindwright" / "scripts" / "grw.py").exists() for d in [p, *p.parents][:4])


def where_of(command):
    """The folder a grind command works in: GRINDWRIGHT_STATE, else an absolute --state, else the first cd."""
    for pat in (r'GRINDWRIGHT_STATE\s*=\s*(' + Q + ')', r'--state\s+(' + Q + ')', r'(?:^|[;&\s])cd\s+(?:/d\s+)?(' + Q + ')'):
        m = re.search(pat, command)
        if m:
            p = m.group(1).strip("\"'")
            if re.match(r"^([A-Za-z]:[\\/]|/[a-z]/|/)", p) and not p.startswith("$"):
                if re.match(r"^/[a-z]/", p):
                    p = p[1].upper() + ":" + p[2:]
                return p
    return None


STATE_GLOBS = ("ai-docs/grind/profile.json", "grind/profile.json", "*/ai-docs/grind/profile.json", "*/grind/profile.json",
               "grind-state/*/profile.json")


def states_near(folders):
    """Grind state folders (those with a profile.json) in, under or beside the given folders."""
    found, looked = {}, set()
    for f in folders:
        p = Path(f)
        for d in [p, *p.parents][:3]:
            if norm(d) in looked:
                continue
            looked.add(norm(d))
            for g in STATE_GLOBS:
                for prof in d.glob(g):
                    found[norm(prof.parent)] = prof.parent
    return list(found.values())


class Projects:
    """Names the project of a session folder: its own state's profile, a profile whose repo holds it, or a
    crew member named in a state's sessions/ folder; else the folder's name."""

    def __init__(self, states):
        self.rows = []
        for s in states:
            prof = read_json(Path(s) / "profile.json") or {}
            if not prof.get("project"):
                continue
            repo = prof.get("repo")
            repo = norm(Path(s, repo) if repo and not Path(repo).is_absolute() else repo) if repo else None
            members = {f.stem for f in (Path(s) / "sessions").glob("*.json")}
            self.rows.append((norm(s), repo, members, prof["project"]))

    def of(self, cwd):
        c, name = norm(cwd), Path(cwd).name
        for state, repo, _, project in self.rows:
            root = state
            if os.path.basename(state) == "grind":
                root = os.path.dirname(state)
                if os.path.basename(root) == "ai-docs":
                    root = os.path.dirname(root)
            if c == root or c.startswith(root + os.sep):
                return project
        for _, repo, _, project in self.rows:
            if repo and (c == repo or c.startswith(repo + os.sep)):
                return project
        for _, _, members, project in self.rows:
            if any(name == m or name.startswith(m + "-") for m in members):
                return project
        return name


def local(ts):
    """A transcript's UTC timestamp as local 'YYYY-MM-DDTHH:MM:SS'."""
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%dT%H:%M:%S")
    except (AttributeError, ValueError):
        return ts or ""


def scan_transcripts(include_temp=False, states=()):
    cache_path = home() / "sessions-cache.json"
    cache = read_json(cache_path) or {}
    out, fresh, root = [], {}, claude_projects()
    for path in (sorted(root.glob("*/*.jsonl")) if root.exists() else []):
        try:
            st = path.stat()
        except OSError:
            continue
        key, stamp = str(path), f"2:{st.st_size}:{int(st.st_mtime)}"  # 2: cache format version
        hit = cache.get(key)
        info = hit["info"] if hit and hit.get("stamp") == stamp else transcript_session(path)
        fresh[key] = {"stamp": stamp, "info": info}
        if info and (include_temp or not (TEMP.search(info["cwd"]) or plugin_repo(info["cwd"]))):
            out.append(dict(info, started=local(info["started"]), ended=local(info["ended"])))
    home().mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(fresh), encoding="utf-8")
    names = Projects(list(states) + states_near({s["cwd"] for s in out}))
    for s in out:
        s["project"] = names.of(s["cwd"])
    return out


def summarize(row):
    run = read_json(row["run"])
    if not run:
        return None
    members, sessions, usd, tokens, stops = [], [], 0.0, 0, []
    for m in run.get("members") or []:
        members.append(m.get("member", "?"))
        if (m.get("result") or {}).get("stopped"):
            stops.append(m["result"]["stopped"])
        for p in m.get("passes") or []:
            usd += p.get("usd") or 0
            tokens += p.get("tokens") or 0
            if p.get("session_id"):
                sessions.append({"id": p["session_id"], "usd": p.get("usd") or 0, "tokens": p.get("tokens") or 0})
    report = Path(row["run"]).with_name(Path(row["run"]).stem + "-report.html")
    state = Path(row.get("state") or Path(row["run"]).parent.parent)
    return {"id": run.get("id") or Path(row["run"]).stem, "project": run.get("project") or state.parent.parent.name,
            "state": str(state), "started": run.get("started") or "",
            "seconds": span_seconds(run.get("started"), run.get("ended")) if run.get("ended") else 0,
            "crew": bool(run.get("crew")), "members": members, "stops": stops, "usd": usd, "tokens": tokens,
            "sessions": sessions, "report": str(report) if report.exists() else None}


def esc(s):
    return html.escape(str(s))


def merge(runs, sessions):
    """Sessions from transcripts plus run sessions with no transcript; each tagged with its run and cost."""
    by_id = {s["id"]: dict(s) for s in sessions}
    for r in runs:
        for s in r["sessions"]:
            row = by_id.setdefault(s["id"], {"id": s["id"], "cwd": "", "started": r["started"], "ended": "",
                                             "project": r["project"], "starts": 1})
            row.update(run=r["id"], usd=s["usd"], tokens=s["tokens"])
    for row in by_id.values():
        row["seconds"] = span_seconds(row["started"], row["ended"]) if row.get("ended") else 0
    return sorted(by_id.values(), key=lambda s: s["started"], reverse=True)


def render(runs, sessions, asks=None):
    projects_d = defaultdict(lambda: {"sessions": 0, "hours": 0.0, "usd": 0.0, "runs": 0, "first": "9", "last": ""})
    by_day = defaultdict(lambda: defaultdict(int))
    for s in sessions:
        p = projects_d[s["project"]]
        p["sessions"] += 1
        p["hours"] += s["seconds"] / 3600
        p["usd"] += s.get("usd", 0)
        p["first"], p["last"] = min(p["first"], s["started"][:10]), max(p["last"], s["started"][:10])
        by_day[s["started"][:10]][s["project"]] += 1
    for r in runs:
        projects_d[r["project"]]["runs"] += 1
    projects = sorted(projects_d, key=lambda k: -projects_d[k]["sessions"])
    colors = {p: PALETTE[i % len(PALETTE)] for i, p in enumerate(projects)}
    hours = sum(s["seconds"] for s in sessions)
    kpis = [(len(sessions), "grind sessions"), (len(projects), "projects"), (len(runs), "driven runs"),
            (fmt_s(hours), "session time"), (f"${sum(s.get('usd', 0) for s in sessions):,.2f}", "cost known (runs only)"),
            (len(by_day), "days with grinding")]
    body = ["<h1>Grindwright</h1>",
            f"<p class='sub'>Every grind session and driven run on this computer. Built {dt.datetime.now():%Y-%m-%d %H:%M}.</p>",
            "<div class='kpis'>" + "".join(f"<div class='kpi'><b>{esc(v)}</b><span>{esc(k)}</span></div>" for v, k in kpis) + "</div>"]
    if not sessions and not runs:
        body.append("<p class='mute'>Nothing found yet. Grind sessions show here once a session runs <code>grw.py session start</code>.</p>")
        return PAGE.replace("__TITLE__", "Grindwright").replace("__BODY__", "\n".join(body)).replace("__STEER__", steerwright_link())
    body.append("<div class='grid'>")
    body.append("<div class='card'><h2>Sessions by project</h2>" + svg_bars(
        [(p, {"sessions": projects_d[p]["sessions"]}) for p in projects], ["sessions"], ["var(--t)"]) + "</div>")
    body.append("<div class='card'><h2>Session hours by project</h2>" + svg_bars(
        [(p, {"hours": round(projects_d[p]["hours"], 1)}) for p in projects], ["hours"], ["var(--m)"], unit=" h") + "</div>")
    body.append("</div>")
    body.append("<div class='card' style='margin-top:12px'><h2>Sessions per day</h2>" + svg_bars(
        [(d, dict(by_day[d])) for d in sorted(by_day)], projects, [colors[p] for p in projects]) + "</div>")
    body.append("<h2>Projects</h2><table><tr><th>Project</th><th>Sessions</th><th>Hours</th><th>Runs</th><th>First</th><th>Last</th></tr>")
    for p in projects:
        v = projects_d[p]
        body.append(f"<tr><td><i style='display:inline-block;width:10px;height:10px;border-radius:2px;background:{colors[p]}'></i> {esc(p)}</td>"
                    f"<td>{v['sessions']}</td><td>{v['hours']:.1f}</td><td>{v['runs']}</td><td>{esc(v['first'] if v['first'] != '9' else '')}</td><td>{esc(v['last'])}</td></tr>")
    body.append("</table>")
    asks = asks or {}
    if any(asks.values()):
        body.append("<h2>Askwright pages waiting</h2><p class='mute'>Every question set still open, by project.</p>"
                    "<table><tr><th>Project</th><th>Set</th><th>Person</th><th>Items</th></tr>")
        for proj in sorted(asks):
            for a in asks[proj]:
                items = "; ".join(f"{esc(i['id'])} {esc(i['title'])}" for i in a["items"])
                body.append(f"<tr><td>{esc(proj)}</td><td><code>{esc(a['set'])}</code></td>"
                            f"<td>{esc(', '.join(a['people']) or 'anyone')}</td><td>{items}</td></tr>")
        body.append("</table>")
    else:
        body.append("<h2>Askwright pages waiting</h2><p class='mute'>None open.</p>")
    if runs:
        body.append("<h2>Driven runs</h2><table><tr><th>Started</th><th>Project</th><th>Members</th><th>Stopped</th><th>Length</th><th>Cost</th><th>Report</th></tr>")
        for r in sorted(runs, key=lambda r: r["started"], reverse=True):
            rep = f"<a href='{Path(r['report']).as_uri()}'>report</a>" if r["report"] else "<span class='mute'>none</span>"
            stops = " ".join(f"<span class='chip'>{esc(s)}</span>" for s in sorted(set(r["stops"]))) or "?"
            body.append(f"<tr><td>{esc(r['started'][:16].replace('T', ' '))}</td><td>{esc(r['project'])}</td>"
                        f"<td>{esc(', '.join(r['members']))}{' (crew)' if r['crew'] else ''}</td><td>{stops}</td>"
                        f"<td>{fmt_s(r['seconds']) if r['seconds'] else '?'}</td><td>${r['usd']:,.2f}</td><td>{rep}</td></tr>")
        body.append("</table>")
    body.append("<h2>Sessions</h2><p class='mute'>Click an id to copy its resume command; run it in the session's folder.</p>"
                "<table><tr><th>Started</th><th>Project</th><th>Length</th><th class='hide-s'>Folder</th><th>Run</th><th>Session</th></tr>")
    for s in sessions:
        cmd = f"cd \"{s['cwd']}\" && claude --resume {s['id']}" if s["cwd"] else f"claude --resume {s['id']}"
        body.append(f"<tr><td>{esc(s['started'][:16].replace('T', ' '))}</td><td>{esc(s['project'])}</td>"
                    f"<td>{fmt_s(s['seconds']) if s['seconds'] else '?'}</td><td class='hide-s'><code>{esc(s['cwd'])}</code></td>"
                    f"<td>{esc(s.get('run', ''))}</td><td><code class='sid' title='{esc(cmd)}' data-cmd='{esc(cmd)}'>{esc(s['id'][:8])}</code></td></tr>")
    body.append("</table><script>document.querySelectorAll('.sid').forEach(e=>{e.style.cursor='copy';e.onclick=()=>{try{navigator.clipboard.writeText(e.dataset.cmd);e.textContent='copied'}catch(x){}}})</script>")
    return PAGE.replace("__TITLE__", "Grindwright").replace("__BODY__", "\n".join(body)).replace("__STEER__", steerwright_link())


def build(scan_roots=(), out=None, open_page=False, transcripts=True, include_temp=False):
    added = 0
    states = []
    for root in scan_roots:
        for state, run in scan(root):
            added += add(state, run)
        states += states_near([root])
    rows = load_registry()
    runs = [s for s in (summarize(r) for r in rows) if s]
    states += [Path(r["state"]) for r in rows if r.get("state")]
    sessions = merge(runs, scan_transcripts(include_temp, states) if transcripts else [])
    out = Path(out) if out else home() / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    asks = defaultdict(list)
    named = Projects(states)
    for st in {norm(x): Path(x) for x in states}.values():
        prof = read_json(st / "profile.json") or {}
        asks[prof.get("project") or named.of(str(st))].extend(open_asks(st))
    out.write_bytes(render(runs, sessions, asks).encode("utf-8"))
    if open_page:
        webbrowser.open(out.resolve().as_uri())
    return {"ok": True, "page": str(out), "runs": len(runs), "sessions": len(sessions), "added": added,
            "projects": sorted({s["project"] for s in sessions} | {r["project"] for r in runs})}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--scan", action="append", default=[], help="folder to search for state folders (repeatable)")
    b.add_argument("--no-transcripts", action="store_true", help="skip the Claude transcript scan")
    b.add_argument("--include-temp", action="store_true", help="keep sessions run in temp folders (eval sandboxes)")
    b.add_argument("--out")
    b.add_argument("--open", action="store_true")
    a_ = sub.add_parser("add")
    a_.add_argument("--state", required=True)
    a_.add_argument("--run", required=True)
    a = p.parse_args(argv)
    if a.command == "add":
        print(json.dumps({"ok": True, "added": add(a.state, a.run)}))
        return 0
    print(json.dumps(build(a.scan, a.out, a.open, not a.no_transcripts, a.include_temp), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
