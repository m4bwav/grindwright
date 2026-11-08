#!/usr/bin/env python3
"""Bounded outer driver: run fresh agent sessions on a continue prompt until the ledger says stop.

Each pass starts a new session, so nothing depends on one session's memory. It stops at the first of:
--max-sessions, --max-hours, the ledger allowing a stop, two sessions in a row that changed nothing,
or a failure it cannot wait out. A run that looks like a usage limit sleeps and tries again.

It installs nothing and schedules nothing. Default is a dry run; --go runs. How long it may run is the
owner's call, so both bounds are required. After --: the agent command (default claude -p). Standard library only.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

GRW = Path(__file__).with_name("grw.py")
LIMIT = re.compile(r"usage limit|rate limit|limit reached|hit your limit|overloaded|\b429\b", re.I)
DEFAULT_COMMAND = ["claude", "-p", "--permission-mode", "auto", "--output-format", "json"]


PROGRESS = ("done", "asked", "detached", "resolved", "redo", "drafted")


def records(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return [r for r in rows if isinstance(r, dict)]


def fingerprint(state, sid=None):
    """What counts as progress. Bookkeeping does not: opening, closing, discovering, or a checkpoint on idle work."""
    digest = hashlib.sha1()
    for item in records(Path(state) / "ledger.jsonl"):
        if sid and item.get("session") != sid:
            continue  # another member's progress is not this member's
        running = item.get("state") == "running"
        working = len(item.get("checkpoints", [])) if running else 0
        shown = "ready" if running else item.get("state")  # a claim or release alone is not progress
        digest.update(repr((item.get("id"), shown,bool(item.get("answered")), working)).encode())
    for event in records(Path(state) / "events.jsonl"):
        if event.get("type") in PROGRESS and (not sid or event.get("session") == sid):
            digest.update(repr((event.get("type"), event.get("id"), event.get("ts"))).encode())
    return digest.hexdigest()


def verdict(state, sid=None):
    done = subprocess.run([sys.executable, str(GRW), "--state", str(state), *(["--session", sid] if sid else []), "session", "check"],
                          capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(done.stdout)
    except ValueError:
        return {"may_stop": True, "why": ["grw.py failed: " + (done.stderr or done.stdout)[:200]]}


def resolve(command):
    """Windows installs claude as a .cmd wrapper, which CreateProcess cannot find by its bare name."""
    found = shutil.which(command[0])
    return [found, *command[1:]] if found else None


def kill_tree(process):
    """Killing only a wrapper leaves the real agent running and holding the pipes."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
    else:
        os.killpg(process.pid, signal.SIGKILL)


def session(command, cwd, timeout):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                               cwd=cwd, start_new_session=sys.platform != "win32")
    try:
        out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(process)
        process.communicate()
        raise
    return subprocess.CompletedProcess(command, process.returncode, out, err)


def plugins_loaded(stdout, need):
    """A headless session that silently lost the plugin must not be trusted."""
    if not need:
        return True
    return need in stdout


def note(args, text):
    if args.log:
        with open(args.log, "a", encoding="utf-8") as log:
            print(f"=== {text}", file=log)


def run(args, sleep=time.sleep, clock=time.monotonic):
    """A crew member gives back what it held however it stops, so its areas do not stay locked for the lease.
    Its stop reason goes to its own log at once: the crew prints results only when every member has ended."""
    result = {"ok": False, "stopped": "crashed"}
    try:
        result = drive(args, sleep, clock)
        return result
    finally:
        if args.go:
            note(args, "stopped: " + json.dumps(result, ensure_ascii=False))
        if args.session_id and args.go:
            subprocess.run([sys.executable, str(GRW), "--state", str(args.state), "--session", args.session_id, "session", "release", "--reason", "driver stopped"], capture_output=True)


def drive(args, sleep, clock):
    wanted = args.command or DEFAULT_COMMAND
    command = resolve(wanted)
    if not command:
        return {"ok": False, "stopped": "command-not-found", "command": wanted[0], "sessions": 0}
    prompt = f"Execute {Path(args.prompt).resolve().as_posix()}"  # the session runs in --cwd, so a relative path would miss
    if not args.go:
        return {"ok": True, "dry_run": True, "would_run": command + [prompt], "max_sessions": args.max_sessions,
                "max_hours": args.max_hours, "now": verdict(args.state, args.session_id)}
    deadline = clock() + args.max_hours * 3600
    sessions, idle, waits, missing = 0, 0, 0, 0
    while True:
        check = verdict(args.state, args.session_id)
        if check.get("may_stop") and not (args.discover_first and sessions == 0):
            return {"ok": True, "stopped": "ledger", "why": check.get("why"), "waiting_on": check.get("waiting_on", []), "sessions": sessions}
        if sessions >= args.max_sessions:
            return {"ok": True, "stopped": "max-sessions", "sessions": sessions}
        if clock() >= deadline:
            return {"ok": True, "stopped": "max-hours", "sessions": sessions}
        before = fingerprint(args.state, args.session_id)
        allowed = deadline - clock()
        if args.session_minutes:
            allowed = min(allowed, args.session_minutes * 60)
        try:
            done = session(command + [prompt], args.cwd, allowed)
        except subprocess.TimeoutExpired:
            return {"ok": False, "stopped": "session-timeout", "seconds": round(allowed), "sessions": sessions}
        output = (done.stdout or "") + (done.stderr or "")
        if args.log:
            with open(args.log, "a", encoding="utf-8") as log:
                print(f"=== pass {sessions + 1}, exit {done.returncode}", output, sep=chr(10), file=log)
        if done.returncode != 0 and LIMIT.search(output):
            waits += 1
            if waits > args.max_waits or clock() + args.limit_wait >= deadline:
                return {"ok": False, "stopped": "usage-limit", "sessions": sessions}
            sleep(args.limit_wait)
            continue
        if done.returncode != 0:
            return {"ok": False, "stopped": "session-failed", "code": done.returncode, "tail": output[-500:], "sessions": sessions}
        sessions += 1
        if not plugins_loaded(output, args.require_text):
            missing += 1  # one miss is often a session that ended its turn mid-wait; two in a row is a lost plugin
            if missing >= 2:
                return {"ok": False, "stopped": "plugin-missing", "sessions": sessions}
            note(args, f"marker {args.require_text!r} missing from pass {sessions}; one more miss stops this member")
        else:
            missing = 0
        idle = idle + 1 if fingerprint(args.state, args.session_id) == before else 0
        if idle >= 2:
            return {"ok": False, "stopped": "no-progress", "sessions": sessions}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("prompt", help="the continue prompt file")
    parser.add_argument("--state", default="ai-docs/grind")
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--max-sessions", type=int, required=True)
    parser.add_argument("--max-hours", type=float, required=True)
    parser.add_argument("--session-minutes", type=float, help="longest one session may run; --max-hours always applies")
    parser.add_argument("--limit-wait", type=int, default=1800, help="seconds to sleep on a usage limit")
    parser.add_argument("--max-waits", type=int, default=4)
    parser.add_argument("--require-text", help="text the session output must contain, such as the plugin's name")
    parser.add_argument("--log", help="append each session's output to this file")
    parser.add_argument("--session-id", help="this member's name when several sessions share the state")
    parser.add_argument("--discover-first", action="store_true",
                        help="run session 1 even when the ledger has nothing selectable, after a person widened the rules")
    parser.add_argument("--go", action="store_true", help="really run; without it, print what would run")
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in argv:
        split = argv.index("--")
        argv, command = argv[:split], argv[split + 1:]
    args = parser.parse_args(argv)
    args.command = command
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
