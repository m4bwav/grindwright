"""Tests for the "no new work" mode: grw.py new-work, the selector filter, refusing verbs, driver and crew stops."""
import contextlib
import io
import json
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("GRINDWRIGHT_REPORT", "off")
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "grindwright" / "scripts"))
import grind_crew  # noqa: E402
import grind_loop  # noqa: E402
import grind_report  # noqa: E402
import grw  # noqa: E402
import grw_work  # noqa: E402
import test_grind_loop  # noqa: E402
from test_grw import Base  # noqa: E402


class Mode(Base):
    def setUp(self):
        super().setUp()
        os.environ.pop(grw_work.MODE_ENV, None)
        self.fresh = self.add("Fresh backlog item", 5)
        self.review = self.add("Address owner review on PR #7", 3)
        self.mark(self.review, review_of=7)

    def mark(self, item_id, **fields):
        store = grw.Store(self.state)
        items = store.items()
        grw.find_item(items, item_id).update(fields)
        store.save_items(items)

    def ranked(self):
        return [r["id"] for r in self.grw("rank", "--no-probe")["ranked"]]

    def test_off_ranks_only_owner_driven_and_survives_between_runs(self):
        self.assertEqual(self.ranked(), [self.review, self.fresh])  # PR comments come before new work (grw.ORDER)
        shown = self.grw("new-work", "off", "--why", "catching up")
        self.assertEqual((shown["new_work"], shown["held"], shown["owner_driven"]), ("off", [self.fresh], [self.review]))
        self.assertEqual(json.loads((self.state / "mode.json").read_text(encoding="utf-8"))["new_work"], "off")
        self.assertEqual(self.ranked(), [self.review])  # a new process reads the stored mode
        self.assertEqual(self.grw("new-work", "show")["new_work"], "off")
        held = {d["id"]: d for d in self.grw("rank", "--no-probe")["deferred"]}
        self.assertEqual(held[self.fresh]["held"], "new-work-off")

    def test_each_owner_kind_counts(self):
        cases = {"owner_note": True, "answered": True, "review_of": 3, "conflict_of": 4, "images_of": 5, "repair_of": 6,
                 "closeout": True, "greenlit_by": "pat"}
        for key, value in cases.items():
            self.assertTrue(grw_work.owner_driven({key: value}), key)
        self.assertFalse(grw_work.owner_driven({"issue": 9, "triaged": False}))  # a brand-new issue is new work
        self.assertTrue(grw_work.owner_driven({"issue": 9, "triaged": False, "issue_seen": "x", "replied": False}))
        self.assertFalse(grw_work.owner_driven({"proposal": True, "state": "waiting-on-human"}))

    def test_on_restores_the_same_pick_order(self):
        third = self.add("Another", 4)
        before = self.ranked()
        self.grw("new-work", "off")
        self.grw("new-work", "on")
        self.assertEqual(self.ranked(), before)
        self.assertIn(third, before)

    def test_refusing_verbs(self):
        self.grw("new-work", "off")
        refused = self.grw("discover", "--no-gh", expect=2)
        self.assertIn("new work is off", json.dumps(refused))
        self.grw("claim", self.fresh, expect=2)
        self.grw("wait-human", self.fresh, "--set", "s", "--person", "alex", expect=2)
        (self.state / "road.json").write_text(json.dumps({"confirmed": True, "milestones": [{"id": "m1", "title": "M"}]}), encoding="utf-8")
        self.grw("surveyed", "m1", "--why", "x", expect=2)
        with self.assertRaises(grw.Refused):
            grw_work.refuse_new_work(grw.Store(self.state), "ticket")
        self.grw("claim", self.review)  # owner-driven work still runs

    def test_add_is_recorded_but_held(self):
        self.grw("new-work", "off")
        out = self.grw("add", "Bug found while fixing", "--lane", "code", "--source", "t", "--value", "4")
        self.assertIn("held", out)
        self.assertNotIn(out["id"], self.ranked())
        repair = self.grw("add", "Fix failing checks on PR #8", "--lane", "code", "--source", "t", "--value", "3", "--repair-of", "8")
        self.assertNotIn("held", repair)
        self.assertIn(repair["id"], self.ranked())

    def test_nothing_owner_driven_stops_cleanly_without_discovery(self):
        self.mark(self.review, state="done")
        self.grw("new-work", "off")
        nxt = self.grw("next", "--no-probe")["next"]
        self.assertEqual((nxt["action"], nxt["stopped"]), ("stop", "no-new-work"))
        verdict = self.grw("session", "check", "--no-probe")
        self.assertTrue(verdict["may_stop"])
        self.assertEqual(verdict["stopped"], "no-new-work")
        self.assertNotIn("drained", json.dumps(verdict).replace("not a drained", ""))

    def test_one_shot_environment_flag_leaves_the_file_alone(self):
        os.environ[grw_work.MODE_ENV] = "1"
        self.addCleanup(os.environ.pop, grw_work.MODE_ENV, None)
        self.assertEqual(self.ranked(), [self.review])
        self.assertFalse((self.state / "mode.json").exists())
        os.environ.pop(grw_work.MODE_ENV)
        self.assertEqual(self.ranked(), [self.review, self.fresh])  # PR comments come before new work (grw.ORDER)


class Driver(unittest.TestCase):
    setUp, grw, fake, go = (test_grind_loop.Loop.setUp, test_grind_loop.Loop.grw, test_grind_loop.Loop.fake, test_grind_loop.Loop.go)

    def test_no_new_work_flag_stops_with_its_own_reason(self):
        code, result = self.go(self.fake("print('hi')"), "--no-new-work")
        self.assertEqual((code, result["stopped"], result["sessions"]), (0, "no-new-work", 0))
        self.assertFalse((self.state / "mode.json").exists())

    def test_stored_mode_stops_after_owner_work_without_no_progress(self):
        self.grw("new-work", "off")
        store = grw.Store(self.state)
        items = store.items()
        items[0]["answered"] = True
        store.save_items(items)
        ledger = str(self.state / "ledger.jsonl")
        agent = self.fake(f"""
import json
rows = [json.loads(l) for l in open({ledger!r})]
for r in rows:
    r.pop('answered', None)
open({ledger!r}, 'w').write(''.join(json.dumps(r) + chr(10) for r in rows))
""")
        code, result = self.go(agent)
        self.assertEqual((code, result["stopped"]), (0, "no-new-work"))
        self.assertIn("no-new-work", grind_report.STOPS)


class Crew(unittest.TestCase):
    def test_crew_passes_the_flag_and_not_discover_first(self):
        crew = {"max_sessions_each": 1, "max_hours": 1, "discover_first": True, "no_new_work": True}
        command = grind_crew.loop_command(crew, {"name": "a", "prompt": "p.md", "state": "s"}, "a-1", ".", "l")
        self.assertIn("--no-new-work", command)
        self.assertNotIn("--discover-first", command)
        one = {"name": "b", "prompt": "p.md", "state": "s", "no_new_work": True}
        self.assertIn("--no-new-work", grind_crew.loop_command({"max_sessions_each": 1, "max_hours": 1}, one, "b-1", ".", "l"))


if __name__ == "__main__":
    unittest.main()
