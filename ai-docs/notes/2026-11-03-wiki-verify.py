#!/usr/bin/env python3
"""Runs every example on the wiki against a fresh clone of the published repository, in a scratch folder.
Usage: python 2026-11-03-wiki-verify.py [ref]. Output goes to stdout; save it beside this file."""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

REF = sys.argv[1] if len(sys.argv) > 1 else "main"
ROOT = Path(tempfile.mkdtemp(prefix="gw-wiki-"))
subprocess.run(["git", "clone", "-q", "--branch", REF, "https://github.com/m4bwav/grindwright", str(ROOT / "plugin")], check=True)
SCRIPTS = ROOT / "plugin/skills/grindwright/scripts"
GAME = ROOT / "game"
GAME.mkdir()
BS = chr(92)


def term(section, line):
    """Run line as the page shows it; grw.py and grind_loop.py stand for the published scripts."""
    print(f"=== {section} ===")
    print("$ " + line)
    real = re.sub(r"^(grw|grind_loop)\.py", lambda m: f'"{sys.executable}" "{SCRIPTS / m.group(0)}"', line)
    done = subprocess.run(real, shell=True, cwd=GAME, capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
    out = done.stdout + done.stderr
    for old in (BS + BS, BS):
        out = out.replace(str(ROOT).replace(BS, old), "<scratch>").replace(sys.executable.replace(BS, old), "python")
    out = out.replace(BS + BS, "/").replace(BS, "/").rstrip()
    print(re.sub(r"20\d\d-\d\d-\d\dT[\d:]+(-\d\d:\d\d)?", "<time>", out))
    print("$ echo $?")
    print(done.returncode)
    return out


term("version", "grw.py --version")
term("init needs project", "grw.py init")
term("init", 'grw.py init --project "Tiny Colony"')
print("=== state folder ===")
print("\n".join(sorted(p.relative_to(GAME).as_posix() for p in (GAME / "ai-docs/grind").rglob("*"))))
(GAME / "ai-docs/grind/profile.json").write_text(json.dumps({
    "project": "Tiny Colony", "repo": ".", "min_value": 2, "escalate_after": 2,
    "people": {"owner": {"review_cap": 1}},
    "lanes": {"cards": {"kind": "code", "needs": [], "person": "owner"}, "bugs": {"kind": "code", "needs": []}},
    "guards": {"merge": "allow: after checks pass", "touch_main": "deny: branch"},
    "text_bans": ["secret-codename"], "discover": []}), encoding="utf-8")
(GAME / "ai-docs/grind/road.json").write_text(json.dumps({
    "finished_means": "A full colony run a stranger can finish.", "confirmed": True,
    "milestones": [{"id": "core", "title": "Full run playable", "weight": 3, "status": "no ending"}]}), encoding="utf-8")
term("no source", 'grw.py add "Fix the save bug" --lane bugs --value 4')
term("add easy", 'grw.py add "Rename a menu label" --lane bugs --value 2 --source "menu.md line 3" --cost S')
hard = term("add valuable", 'grw.py add "Finish the ending" --lane bugs --value 5 --human-min 30 --road core --source "design.md: no ending"')
term("rank", "grw.py rank")
term("next", "grw.py next")
term("post", "grw.py guard post")
term("merge", "grw.py guard merge")
term("main", "grw.py guard touch_main")
term("unset", "grw.py guard deploy")
hard = json.loads(hard)["id"]
term("done no evidence", f"grw.py done {hard}")
term("wait no set", f"grw.py wait-human {hard} --person owner")
term("check", "grw.py session check")
(GAME / "pr.txt").write_text("Built for secret-codename", encoding="utf-8")
term("lint", "grw.py lint-text pr.txt")
term("doctor", "grw.py doctor")
term("loop bounds", "grind_loop.py prompt.md")
term("loop dry", "grind_loop.py prompt.md --state ai-docs/grind --max-sessions 5 --max-hours 4")
print("=== repository tests ===")
done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT / "plugin", capture_output=True, text=True)
lines = done.stderr.strip().splitlines()
print(lines[-3].split(" in ")[0], lines[-1])
shutil.rmtree(ROOT, ignore_errors=True)
