#!/usr/bin/env python3
"""Run several bounded grind_loop drivers at once, across projects and on one project, from a crew file.

Each project has its own state folder, so knowledge and logs never mix. Members of one project share that folder and
coordinate through its ledger, so it must live outside the worktrees. A member starts only if work is left for it.
Default is a dry run; --go runs. It installs nothing and schedules nothing. Standard library only.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRW = HERE / "grw.py"
LOOP = HERE / "grind_loop.py"
sys.path.insert(0, str(HERE))
import grind_report  # noqa: E402


def problems(crew):
    found, states = [], {}
    if not crew.get("max_hours") or not crew.get("max_sessions_each"):
        found.append("the crew file must set max_hours and max_sessions_each: the bounds are the owner's call")
    for project in crew.get("projects", []):
        name = project.get("name", "?")
        for key in ("name", "repo", "state", "prompt"):
            if not project.get(key):
                found.append(f"{name}: missing {key}")
        if not project.get("state") or not project.get("repo"):
            continue
        state, repo = Path(project["state"]).resolve(), Path(project["repo"]).resolve()
        if str(state) in states:
            found.append(f"{name}: shares its state folder with {states[str(state)]}; each project keeps its own")
        states[str(state)] = name
        count = project.get("sessions", 1)
        if count > 1 and (state == repo or repo in state.parents):
            found.append(f"{name}: state is inside the repo, so each worktree would get its own ledger copy; move it outside and pass the new path")
        if count > 1 and project.get("worktrees") is False:
            found.append(f"{name}: {count} sessions without worktrees would share one working tree")
    return found


def rank(project, member):
    env = dict(os.environ, GRINDWRIGHT_SESSION=member)
    done = subprocess.run([sys.executable, str(GRW), "--state", project["state"], "session", "check", "--no-probe"], capture_output=True, text=True, encoding="utf-8", env=env)
    try:
        return json.loads(done.stdout)
    except ValueError:
        return {"may_stop": True, "why": ["grw.py failed: " + (done.stderr or done.stdout)[:200]]}


def worktree(project, member, today):
    """One tree and one branch per member. A project can opt out; Unity projects with a live Editor may need to."""
    if project.get("worktrees") is False:
        return project["repo"]
    repo = Path(project["repo"]).resolve()
    root = Path(project["worktree_root"]) if project.get("worktree_root") else repo.parent / f"{repo.name}-grind"
    path = root / member
    branch = f"grind/{member}-{today}"
    base = project.get("base", "origin/HEAD")
    subprocess.run(["git", "-C", str(repo), "fetch", "-q", "origin"], check=False)
    if path.exists():
        current = git_out(path, "rev-parse", "--abbrev-ref", "HEAD")
        if current == branch or not current:  # today's tree, or a folder set up by hand
            return str(path)
        # A tree left by an earlier run: move it to a fresh branch only when nothing in it would be lost.
        clean = not git_out(path, "status", "--porcelain")
        if clean and git_out(path, "rev-parse", "--verify", base) and not git_out(path, "rev-list", f"{base}..HEAD"):
            subprocess.run(["git", "-C", str(path), "checkout", "-q", "-B", branch, base], check=True)
            return str(path)
        path = root / f"{member}-{today}"
        if path.exists():
            return str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "-B", branch, str(path), base], check=True)
    return str(path)


def git_out(path, *argv):
    done = subprocess.run(["git", "-C", str(path), *argv], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def plan(crew):
    rows = []
    for project in crew["projects"]:
        for number in range(1, project.get("sessions", 1) + 1):
            rows.append((project, f"{project['name']}-{number}"))
    return rows


def discover_first(crew, project, member):
    """First member of a project whose crew file sets discover_first runs once even on an empty ledger."""
    return bool(project.get("discover_first", crew.get("discover_first"))) and member == f"{project['name']}-1"


def loop_command(crew, project, member, cwd, log):
    command = [sys.executable, str(LOOP), project["prompt"], "--state", project["state"], "--cwd", cwd, "--session-id", member,
               "--max-sessions", str(crew["max_sessions_each"]), "--max-hours", str(crew["max_hours"]), "--log", str(log), "--no-report", "--go"]
    if crew.get("session_minutes"):
        command += ["--session-minutes", str(crew["session_minutes"])]
    if crew.get("require_text"):
        command += ["--require-text", crew["require_text"]]
    if discover_first(crew, project, member):
        command += ["--discover-first"]
    if crew.get("agent"):
        command += ["--", *crew["agent"]]
    return command


def run(crew, sleep=time.sleep):
    today = dt.date.today().isoformat()
    started = grind_report.stamp()
    running, skipped = [], []
    for index, (project, member) in enumerate(plan(crew)):
        if index:
            sleep(crew.get("stagger_seconds", 120))
        check = rank(project, member)
        if check.get("may_stop") and not discover_first(crew, project, member):
            skipped.append({"member": member, "why": check.get("why"), "waiting_on": check.get("waiting_on", [])})
            continue
        logs = Path(project["state"]) / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        log = logs / f"{member}-{today}.log"
        cwd = worktree(project, member, today)
        env = dict(os.environ, GRINDWRIGHT_STATE=str(Path(project["state"]).resolve()), GRINDWRIGHT_SESSION=member)
        process = subprocess.Popen(loop_command(crew, project, member, cwd, log), env=env, stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        running.append((member, project, process, cwd))
    results = []
    for member, project, process, cwd in running:
        out, _ = process.communicate()
        try:
            results.append(dict(json.loads(out), member=member, project=project["name"], cwd=cwd))
        except ValueError:
            results.append({"member": member, "project": project["name"], "cwd": cwd, "ok": False, "stopped": "driver-output", "tail": (out or "")[-300:]})
    summary = {"ok": True, "started": len(running), "skipped": skipped, "results": results}
    for project in crew["projects"]:
        logs = Path(project["state"]) / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / f"crew-{today}.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    summary["reports"] = reports(crew, started, results, skipped)
    return summary


def reports(crew, started, results, skipped):
    """One run file and run report per project, shown once every member has ended, unless switched off."""
    made = {}
    ended = grind_report.stamp()
    run_id = "run-" + started.replace(":", "").replace("T", "-")[:15]
    for project in crew["projects"]:
        members = [{"member": r["member"], "cwd": r.get("cwd"), "passes": r.get("passes", []),
                    "result": {k: v for k, v in r.items() if k not in ("passes", "member", "project", "cwd")}}
                   for r in results if r.get("project") == project["name"]]
        members += [{"member": x["member"], "passes": [], "result": {"ok": True, "stopped": "skipped", "why": x.get("why"), "waiting_on": x.get("waiting_on")}}
                    for x in skipped if x["member"].startswith(project["name"] + "-")]
        profile = grind_report.read_json(Path(project["state"]) / "profile.json", {}) or {}
        run = {"id": run_id, "project": profile.get("project") or project["name"], "prompt": project.get("prompt"), "crew": True,
               "started": started, "ended": ended, "members": members}
        path = Path(project["state"]) / "logs" / f"{run_id}.json"
        grind_report.write_run(path, run)
        made[project["name"]] = grind_report.finish(project["state"], path, crew)
    return made


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("crew", help="crew JSON file")
    parser.add_argument("--go", action="store_true", help="really run; without it, print what would run")
    args = parser.parse_args(argv)
    crew = json.loads(Path(args.crew).read_text(encoding="utf-8"))
    found = problems(crew)
    if found:
        print(json.dumps({"ok": False, "refused": found}, indent=1, ensure_ascii=False))
        return 2
    if not args.go:
        rows = [{"member": member, "project": project["name"], "state": project["state"], "now": rank(project, member)} for project, member in plan(crew)]
        print(json.dumps({"ok": True, "dry_run": True, "members": rows, "max_hours": crew["max_hours"], "max_sessions_each": crew["max_sessions_each"]}, indent=1, ensure_ascii=False))
        return 0
    print(json.dumps(run(crew), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
