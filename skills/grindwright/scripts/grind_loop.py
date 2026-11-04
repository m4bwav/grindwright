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


def fingerprint(state):
    digest = hashlib.sha1()
    ledger, events = Path(state) / "ledger.jsonl", Path(state) / "events.jsonl"
    if ledger.exists():
        digest.update(ledger.read_bytes())
    if events.exists():
        for line in events.read_bytes().splitlines():
            if b'"session_start"' not in line and b'"session_end"' not in line:  # opening and closing is not progress
                digest.update(line)
    return digest.hexdigest()


def verdict(state):
    done = subprocess.run([sys.executable, str(GRW), "--state", str(state), "session", "check"],
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


def run(args, sleep=time.sleep, clock=time.monotonic):
    wanted = args.command or DEFAULT_COMMAND
    command = resolve(wanted)
    if not command:
        return {"ok": False, "stopped": "command-not-found", "command": wanted[0], "sessions": 0}
    prompt = f"Execute {args.prompt}"
    if not args.go:
        return {"ok": True, "dry_run": True, "would_run": command + [prompt], "max_sessions": args.max_sessions,
                "max_hours": args.max_hours, "now": verdict(args.state)}
    deadline = clock() + args.max_hours * 3600
    sessions, idle, waits = 0, 0, 0
    while True:
        check = verdict(args.state)
        if check.get("may_stop"):
            return {"ok": True, "stopped": "ledger", "why": check.get("why"), "sessions": sessions}
        if sessions >= args.max_sessions:
            return {"ok": True, "stopped": "max-sessions", "sessions": sessions}
        if clock() >= deadline:
            return {"ok": True, "stopped": "max-hours", "sessions": sessions}
        before = fingerprint(args.state)
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
            return {"ok": False, "stopped": "plugin-missing", "sessions": sessions}
        idle = idle + 1 if fingerprint(args.state) == before else 0
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
