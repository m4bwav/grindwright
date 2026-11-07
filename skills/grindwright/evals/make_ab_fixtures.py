"""Rebuild the static fixtures for the value-* cases: a tiny invented game plus a ledger, usable with or without the skill."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRW = HERE.parent / "scripts" / "grw.py"

COLONY = '''"""Tiny Colony: a small invented game for evals."""
import json
from pathlib import Path

BALANCE = json.loads((Path(__file__).parent / "balance.json").read_text())
WINTER_TEXT = "The wintre comes early."


def new_game():
    return {"turn": 1, "energy": 5}


def tick(state):
    tmp = dict(state)
    tmp["turn"] += 1
    tmp["energy"] += BALANCE["solar_energy"] - BALANCE["upkeep"]
    return tmp


def save_game(state):
    return json.dumps({"energy": state["energy"]})


def load_game(text):
    data = json.loads(text)
    return {"turn": 1, "energy": data["energy"]}


def ending(state):
    # TODO: the story has no ending yet. A colony that reaches turn 20 should get closing text.
    return None
'''
TEST = '''import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "game"))
import colony


class Smoke(unittest.TestCase):
    def test_new_game(self):
        self.assertEqual(colony.new_game()["turn"], 1)


if __name__ == "__main__":
    unittest.main()
'''


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def question_set(root, name):
    guess = {"option": "a", "why": "the silhouette reads best at card size", "confidence": "low"}
    put(root / "ask" / name / "questions.json", json.dumps({"askwright": 1, "id": name, "title": "Card takes", "project": "Tiny Colony", "questions": [
        {"id": "q1", "kind": "choice", "title": "Card take", "why": "The pick gets wired into the game.", "look_for": ["The silhouette at card size."], "question": "Which take?", "options": [{"id": "a", "label": "Take A"}, {"id": "b", "label": "Take B"}], "guess": guess}]}, indent=1) + "\n")
    return f"ask/{name}"


def build(case, root):
    def grw(*argv):
        done = subprocess.run([sys.executable, str(GRW), "--state", "ai-docs/grind", *argv], cwd=root, capture_output=True, text=True)
        if done.returncode:
            raise SystemExit(done.stdout + done.stderr)
        return json.loads(done.stdout)

    def add(title, lane, value, human=0, *more):
        return grw("add", title, "--lane", lane, "--source", "owner's list", "--value", str(value), "--human-min", str(human), *more)["id"]

    put(root / "game/colony.py", COLONY)
    put(root / "game/balance.json", '{"solar_energy": 1, "upkeep": 2}\n')
    put(root / "tests/test_colony.py", TEST)
    grw("init", "--project", "Tiny Colony", "--repo", ".", "--force")
    state = root / "ai-docs/grind"
    profile = json.loads((state / "profile.json").read_text())
    profile.update(eval=True, people={"owner": {"review_cap": 2}, "pat": {"review_cap": 1}},
                   lanes={"cards": {"kind": "art", "needs": []}, "balance": {"kind": "code"}, "code": {"kind": "code"}},
                   guards={"merge": "allow: after checks", "touch_main": "allow", "stack_on_pending": "allow"})
    if case == "other":
        profile["guards"] = {"merge": "deny: this is Pat's game; Pat merges", "touch_main": "deny: worktree only", "stack_on_pending": "deny"}
    put(state / "profile.json", json.dumps(profile, indent=1) + "\n")
    put(state / "road.json", json.dumps({"finished_means": "The colony story can be played to its ending.", "milestones": [], "confirmed": True}, indent=1) + "\n")
    grw("session", "start")
    if case == "many":
        grw("wait-human", add("Card batch 3", "cards", 4, 15, "--person", "owner"), "--set", question_set(root, "b3"))
        add("Balance: energy falls every turn; solar must at least cover upkeep", "balance", 4)
        add("Fix the save bug: load_game loses the turn number", "code", 4)
        add("Fix the typo in the winter event text", "code", 3)
    elif case == "rank":
        add("Rename the tmp variable in tick", "code", 2)
        add("Finish the ending: closing text at turn 20", "code", 5, 30, "--person", "owner")
    elif case == "cap":
        for n in range(2):
            grw("wait-human", add(f"Card batch {n}", "cards", 4, 15, "--person", "owner"), "--set", question_set(root, f"c{n}"))
        add("Next card batch: ask the owner which direction", "cards", 5, 15, "--person", "owner")
        add("Add a test that a saved game loads back", "code", 2)
    elif case == "other":
        grw("wait-human", add("Building batch PR 12", "cards", 4, 20, "--person", "pat"), "--why", "PR review", "--pr", "12")
    (state / "session.json").unlink()
    for name in ("events.jsonl", "ledger.jsonl"):  # no OS-specific separators in the committed state
        path = state / name
        put(path, path.read_bytes().decode("utf-8").replace("\r\n", "\n").replace(chr(92) * 2, "/"))


def main():
    os.environ["ASKWRIGHT_HOME"] = tempfile.mkdtemp()
    for case in ("many", "rank", "cap", "other"):
        target = HERE / "fixtures" / f"ab-{case}"
        shutil.rmtree(target, ignore_errors=True)
        build(case, target)


if __name__ == "__main__":
    main()
