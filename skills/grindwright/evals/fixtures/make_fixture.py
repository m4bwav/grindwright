"""Build an invented game's grindwright state in ai-docs/grind for one eval case."""
import json
import subprocess
import sys
from pathlib import Path

GRW = Path(__file__).resolve().parents[2] / "scripts" / "grw.py"
STATE = Path("ai-docs/grind")


def grw(*argv):
    done = subprocess.run([sys.executable, str(GRW), "--state", str(STATE), *argv], capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(done.stdout + done.stderr)
    return json.loads(done.stdout)


def add(title, lane, value, human=0, *more):
    return grw("add", title, "--lane", lane, "--source", "fixture", "--value", str(value), "--human-min", str(human), *more)["id"]


def question_set(name):
    folder = Path("ask") / name
    folder.mkdir(parents=True, exist_ok=True)
    guess = {"option": "a", "why": "the silhouette reads best at card size", "confidence": "low"}
    (folder / "questions.json").write_text(json.dumps({"askwright": 1, "id": name, "title": "Card takes", "project": "Tiny Colony", "questions": [
        {"id": "q1", "kind": "choice", "title": "Card take", "why": "The pick gets wired into the game.", "look_for": ["The silhouette at card size."], "question": "Which take?", "options": [{"id": "a", "label": "Take A"}, {"id": "b", "label": "Take B"}], "guess": guess}]}))
    return str(folder)


def main(case):
    grw("init", "--project", "Tiny Colony", "--repo", ".", "--force")
    profile = json.loads((STATE / "profile.json").read_text())
    profile["people"] = {"owner": {"review_cap": 2}, "pat": {"review_cap": 1}}
    profile["lanes"] = {"cards": {"kind": "art", "needs": []}, "balance": {"kind": "code"}, "code": {"kind": "code"}, "sound": {"kind": "code"}, "music": {"kind": "music"}}
    profile["guards"] = {"merge": "allow: after checks", "touch_main": "deny: branch", "stack_on_pending": "allow"}
    if case == "other":
        profile["guards"] = {"merge": "deny: this is Pat's game; Pat merges", "touch_main": "deny: worktree only", "stack_on_pending": "deny"}
    (STATE / "profile.json").write_text(json.dumps(profile, indent=1))
    grw("session", "start")
    if case == "blocked":
        grw("wait-human", add("Card batch 3", "cards", 4, 15, "--person", "owner"), "--set", question_set("b3"))
        add("Balance the energy curve", "balance", 4)
    elif case == "easy":
        add("Rename a helper variable", "code", 2)
        add("Finish the ending", "code", 5, 30, "--person", "owner")
    elif case == "small":
        add("Create the new sound folder and pick its name", "sound", 3)
    elif case == "other":
        grw("wait-human", add("Building batch PR 12", "cards", 4, 20, "--person", "pat"), "--why", "PR review", "--pr", "12")
    elif case == "music":
        add("Colony music loop", "music", 4)
        add("Fix the save bug", "code", 3)
    elif case == "running":
        grw("claim", add("Render 48 card candidates", "cards", 4))
    elif case == "answered":
        item = add("Card batch 4", "cards", 3, 15, "--person", "owner")
        folder = question_set("b4")
        grw("wait-human", item, "--set", folder)
        grw("relay", item, "--person", "owner", "--note", "take b; never put people on fire cards")
        add("Big new feature", "code", 5)
    elif case == "cap":
        for n in range(2):
            grw("wait-human", add(f"Batch {n}", "cards", 4, 15, "--person", "owner"), "--set", question_set(f"c{n}"))
        add("Card batch ready to ask about", "cards", 5, 15, "--person", "owner")
        add("Add a save test", "code", 2)
    elif case == "devlog":
        Path("ai-docs/devlog.md").write_text("# Devlog 7. The colony now survives its first winter.")
    elif case != "empty":
        raise SystemExit(f"unknown case {case}")


if __name__ == "__main__":
    main(sys.argv[1])
