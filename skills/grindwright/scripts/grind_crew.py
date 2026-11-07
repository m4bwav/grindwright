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
    path = repo.parent / f"{repo.name}-grind" / member
    if path.exists():
        return str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(repo), "fetch", "-q", "origin"], check=False)
    base = project.get("base", "origin/HEAD")
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "-b", f"grind/{member}-{today}", str(path), base], check=True)
    return str(path)


def plan(crew):
    rows = []
    for project in crew["projects"]:
        for number in range(1, project.get("sessions", 1) + 1):
            rows.append((project, f"{project['name']}-{number}"))
    return rows


def loop_command(crew, project, member, cwd, log):
    command = [sys.executable, str(LOOP), project["prompt"], "--state", project["state"], "--cwd", cwd, "--session-id", member,
               "--max-sessions", str(crew["max_sessions_each"]), "--max-hours", str(crew["max_hours"]), "--log", str(log), "--go"]
    if crew.get("session_minutes"):
        command += ["--session-minutes", str(crew["session_minutes"])]
    if crew.get("require_text"):
        command += ["--require-text", crew["require_text"]]
    if crew.get("agent"):
        command += ["--", *crew["agent"]]
    return command


def run(crew, sleep=time.sleep):
    today = dt.date.today().isoformat()
    running, skipped = [], []
    for index, (project, member) in enumerate(plan(crew)):
        if index:
            sleep(crew.get("stagger_seconds", 120))
        check = rank(project, member)
        if check.get("may_stop"):
            skipped.append({"member": member, "why": check.get("why"), "waiting_on": check.get("waiting_on", [])})
            continue
        logs = Path(project["state"]) / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        log = logs / f"{member}-{today}.log"
        cwd = worktree(project, member, today)
        env = dict(os.environ, GRINDWRIGHT_STATE=str(Path(project["state"]).resolve()), GRINDWRIGHT_SESSION=member)
        process = subprocess.Popen(loop_command(crew, project, member, cwd, log), env=env, stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        running.append((member, project, process))
    results = []
    for member, project, process in running:
        out, _ = process.communicate()
        try:
            results.append(dict(json.loads(out), member=member))
        except ValueError:
            results.append({"member": member, "ok": False, "stopped": "driver-output", "tail": (out or "")[-300:]})
    summary = {"ok": True, "started": len(running), "skipped": skipped, "results": results}
    for project in crew["projects"]:
        logs = Path(project["state"]) / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / f"crew-{today}.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


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
