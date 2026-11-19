"""Tests for the work order: the profile's `order` of categories, and where the stop step looks for new tickets."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("GRINDWRIGHT_REPORT", "off")
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "grindwright" / "scripts"))
import grw  # noqa: E402
from test_grw import Base  # noqa: E402


class Order(Base):
    def setUp(self):
        super().setUp()
        self.other = self.add("Discovered gap", 5)
        self.ticket = self.add("Approved ticket", 4)
        self.answers = self.add("Answered question", 3)
        self.comments = self.add("Address owner review on PR #4", 3)
        self.conflict = self.add("Resolve merge conflicts on PR #3", 2)
        self.mark(self.ticket, issue=12, triaged=True, greenlit_by="alex")
        self.mark(self.answers, answered=True)
        self.mark(self.comments, review_of=4)
        self.mark(self.conflict, conflict_of=3)

    def mark(self, item_id, **fields):
        store = grw.Store(self.state)
        items = store.items()
        grw.find_item(items, item_id).update(fields)
        store.save_items(items)

    def ranked(self):
        return self.grw("rank", "--no-probe")["ranked"]

    def test_default_order_puts_pull_requests_before_answers_and_tickets(self):
        note = self.add("Owner asked for this", 2, 0, "code", "--owner-note")
        got = self.ranked()
        self.assertEqual([r["id"] for r in got], [note, self.conflict, self.comments, self.answers, self.ticket, self.other])
        self.assertEqual([r["category"] for r in got], ["owner-note", "pr-conflicts", "pr-comments", "answers", "tickets", "other"])

    def test_profile_order_wins_and_left_out_categories_follow_in_default_order(self):
        self.profile({"order": ["tickets", "answers"]})
        self.assertEqual([r["id"] for r in self.ranked()], [self.ticket, self.answers, self.conflict, self.comments, self.other])

    def test_value_still_ranks_inside_a_category(self):
        better = self.add("Second approved ticket", 5)
        self.mark(better, issue=13, triaged=True, greenlit_by="alex")
        ids = [r["id"] for r in self.ranked()]
        self.assertLess(ids.index(better), ids.index(self.ticket))

    def test_unknown_category_is_a_profile_conflict(self):
        found = grw.profile_conflicts({"order": ["answers", "bugs-first"]})
        self.assertEqual(len(found), 1)
        self.assertIn("bugs-first", found[0])
        self.assertEqual(grw.profile_conflicts({"order": list(grw.ORDER)}), [])


class Sources(Base):
    def stop(self):
        self.grw("session", "start")
        self.grw("discover", "--no-gh")
        return self.grw("next", "--no-probe")["next"]

    def test_stop_names_the_task_list_todo_file_and_plans(self):
        self.profile({"work": {"tasks": {"path": "tasks.md"}, "todo": {"path": "Docs/Agent Todos.md"},
                               "plans": ["Docs/Design/"]}})
        got = self.stop()
        self.assertEqual(got["action"], "stop")
        self.assertEqual(got["ticket_sources"], ["tasks.md", "Docs/Agent Todos.md", "Docs/Design/", "open issues"])
        self.assertIn("ticket --propose", " ".join(got["why"]))

    def test_stop_without_work_sources_falls_back_to_design_docs(self):
        self.assertEqual(self.stop()["ticket_sources"], ["unbuilt design-doc sections", "open issues"])


if __name__ == "__main__":
    unittest.main()
