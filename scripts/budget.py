"""Size budget for grindwright. Run from the repository root: python scripts/budget.py

The always-loaded footprint (the skill description, read in every session) and the installed size must stay
small enough that nobody thinks twice about installing the plugin. Exit 2 at red, 0 otherwise; a yellow is
reported so the maintainer can be told. Tokens are estimated as bytes / 4.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "grindwright"

# measure, green <=, yellow <= (above yellow is red)
BUDGETS = [
    ("description characters (always loaded; harness cuts at 1,536)", 1100, 1400),
    ("SKILL.md tokens (loaded on every use)", 2500, 3500),
    
    ("largest reference file tokens (loaded on demand)", 5500, 7000),
    ("installed skill folder KB", 300, 600),
    ("tracked repository KB", 1024, 3072),
]


def measure():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r'^description:\s*"(.*)"\s*$', text, re.M)
    desc = len(m.group(1)) if m else 0
    skill_tokens = len(text.encode("utf-8")) // 4
    docs = list((SKILL / "references").glob("*.md"))
    biggest = max(docs, key=lambda p: p.stat().st_size)
    files = [p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    folder_kb = sum(p.stat().st_size for p in files) // 1024
    try:
        tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout.split(b"\0")
        repo_kb = sum((ROOT / t.decode()).stat().st_size for t in tracked if t and (ROOT / t.decode()).exists()) // 1024
    except (OSError, subprocess.CalledProcessError):
        repo_kb = folder_kb
    return [(desc, ""), (skill_tokens, ""), (biggest.stat().st_size // 4, biggest.name), (folder_kb, ""), (repo_kb, "")]


def main():
    rows = []
    for (label, g, y), (v, where) in zip(BUDGETS, measure()):
        status = "green" if v <= g else ("yellow" if v <= y else "red")
        rows.append({"measure": label, "value": v, "green": g, "yellow": y, "status": status, "worst": where})
    overall = "red" if any(r["status"] == "red" for r in rows) else ("yellow" if any(r["status"] == "yellow" for r in rows) else "green")
    if "--json" in sys.argv:
        print(json.dumps({"overall": overall, "rows": rows}, indent=2))
    else:
        for r in rows:
            print("%-64s %6s  green<=%-5s yellow<=%-5s %-6s %s" % (r["measure"], r["value"], r["green"], r["yellow"], r["status"], r["worst"]))
        print("budget: %s" % overall.upper())
    return 2 if overall == "red" else 0


if __name__ == "__main__":
    sys.exit(main())
