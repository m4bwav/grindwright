"""Tiny Colony: a small invented game for evals."""
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
