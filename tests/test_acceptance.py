"""Ready-for-acceptance labels: open issues whose referencing PRs all merged. gh is faked."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "grindwright" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grw  # noqa: E402
import grw_work  # noqa: E402
from test_crew import Base, FakeGh, issue  # noqa: E402


class AcceptanceGh(FakeGh):
    def __init__(self):
        super().__init__()
        self.closed_prs, self.timeline = [], {}

    def api(self, *argv):
        path = argv[0]
        if "/pulls?state=closed" in path:
            return self.closed_prs
        if "/timeline" in path:
            return self.timeline.get(int(path.split("/issues/")[1].split("/")[0]), [])
        return super().api(*argv)

    def edits(self):
        return [c for c in self.calls if c[:2] == ("issue", "edit")]

    def comments_posted(self):
        return [c for c in self.calls if c[:2] == ("issue", "comment")]


def pr(number, body, merged=True):
    return {"number": number, "title": f"Change {number}", "body": body, "merged_at": "2026-01-02T00:00:00Z" if merged else None}


def cross_ref(number, state, merged=False, repo="o/r"):
    return {"event": "cross-referenced", "source": {"type": "issue", "issue": {
        "number": number, "state": state, "repository": {"full_name": repo},
        "pull_request": {"merged_at": "2026-01-02T00:00:00Z" if merged else None}}}}


class Acceptance(Base):
    profile_extra = {"work": {"issues": {"repo": "o/r", "lane_bug": "bugs", "lane_feature": "features",
                                         "acceptance": {"enabled": True}}}}

    def setUp(self):
        super().setUp()
        self.fake = AcceptanceGh()
        for name, fn in (("gh", self.fake.run), ("gh_json", self.fake.api)):
            self.addCleanup(setattr, grw_work, name, getattr(grw_work, name))
            setattr(grw_work, name, fn)

    def set_acceptance(self, **block):
        path = self.state / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["work"]["issues"]["acceptance"] = block
        path.write_text(json.dumps(profile), encoding="utf-8")

    def accept(self, *flags):
        code, out = self.run_grw("issue-acceptance", *flags)
        self.assertEqual(code, 0, out)
        return out

    def test_default_is_off(self):
        self.assertFalse(grw_work.acceptance({})["enabled"])
        self.assertFalse(grw_work.acceptance({"repo": "o/r"})["enabled"])
        self.set_acceptance()
        self.fake.issues = [issue(1, "Crash")]
        self.fake.closed_prs = [pr(5, "Refs #1")]
        self.assertNotIn("acceptance", self.run_grw("issue-sync")[1])
        self.assertEqual(self.run_grw("issue-acceptance")[0], 2)
        self.assertEqual(self.fake.edits(), [])

    def test_merged_and_nothing_open_is_labelled_with_one_comment(self):
        self.fake.issues = [issue(1, "Crash")]
        self.fake.closed_prs = [pr(5, "Refs #1"), pr(6, "Part two of #1")]
        out = self.accept()
        self.assertEqual(out["ready"], [{"issue": 1, "merged": ["#5", "#6"]}])
        self.assertEqual(out["labelled"], [1])
        self.assertIn(("label", "create", "ready for acceptance"), [c[:3] for c in self.fake.calls])
        self.assertNotIn("--force", next(c for c in self.fake.calls if c[:2] == ("label", "create")))
        self.assertEqual(self.fake.edits(), [("issue", "edit", "1", "-R", "o/r", "--add-label", "ready for acceptance")])
        self.assertEqual(len(self.fake.comments_posted()), 1)
        self.assertIn("#5, #6", self.fake.stdin[-1])
        self.assertFalse(any(c[:2] == ("issue", "close") or "--remove-label" in c for c in self.fake.calls))

    def test_label_name_and_comment_come_from_the_profile(self):
        self.set_acceptance(enabled=True, label="to verify", comment=False)
        self.fake.issues = [issue(1, "Crash")]
        self.fake.closed_prs = [pr(5, "Closes #1")]
        self.assertEqual(self.accept()["labelled"], [1])
        self.assertEqual(self.fake.edits()[0][-1], "to verify")
        self.assertEqual(self.fake.comments_posted(), [])

    def test_any_open_pr_disqualifies(self):
        self.fake.issues = [issue(1, "Crash"), issue(2, "Hang")]
        self.fake.closed_prs = [pr(5, "Refs #1"), pr(6, "Refs #2")]
        self.fake.open_prs = [{"number": 7, "title": "Rest of #1", "body": ""}]
        self.fake.timeline = {2: [cross_ref(8, "open")]}  # named only in a comment, so only the timeline knows
        out = self.accept()
        self.assertEqual((out["ready"], out["labelled"]), ([], []))
        self.assertEqual(out["open_pr"], [{"issue": 1, "open": ["#7"]}, {"issue": 2, "open": ["#8"]}])
        self.assertEqual(self.fake.edits(), [])

    def test_no_merged_pr_disqualifies(self):
        self.fake.issues = [issue(1, "Crash"), issue(2, "Hang")]
        self.fake.closed_prs = [pr(5, "Refs #1", merged=False), pr(6, "Refs #21")]
        out = self.accept()
        self.assertEqual((out["ready"], out["labelled"], out["open_pr"]), ([], [], []))
        self.assertEqual(self.fake.calls, [])

    def test_timeline_adds_other_repositories_and_never_relabels_an_open_one(self):
        self.fake.issues = [issue(1, "Crash")]
        self.fake.closed_prs = [pr(5, "Refs #1")]
        self.fake.timeline = {1: [cross_ref(5, "open"), cross_ref(3, "closed", merged=True, repo="o/tools")]}
        self.assertEqual(self.accept()["open_pr"], [{"issue": 1, "open": ["#5"]}])
        self.fake.timeline = {1: [cross_ref(3, "closed", merged=True, repo="o/tools")]}
        self.assertEqual(self.accept()["ready"], [{"issue": 1, "merged": ["#5", "o/tools#3"]}])

    def test_human_only_and_skip_labels_are_left_alone(self):
        self.fake.issues = [issue(1, "Crash", ("bug", "needs-human")), issue(2, "Hang", ("bug", "wontfix"))]
        self.fake.closed_prs = [pr(5, "Refs #1"), pr(6, "Refs #2")]
        self.assertEqual(self.accept()["ready"], [])
        self.assertEqual(self.fake.calls, [])

    def test_already_labelled_gets_nothing(self):
        self.fake.issues = [issue(1, "Crash", ("bug", "Ready for acceptance"))]
        self.fake.closed_prs = [pr(5, "Refs #1")]
        self.assertEqual(self.accept()["ready"], [])
        self.assertEqual(self.fake.calls, [])

    def test_dry_run_changes_nothing_even_when_off(self):
        self.set_acceptance()
        self.fake.issues = [issue(1, "Crash")]
        self.run_grw("issue-sync")
        before = (self.state / "ledger.jsonl").read_bytes()
        self.fake.closed_prs = [pr(5, "Refs #1")]
        out = self.accept("--dry-run")
        self.assertEqual((out["ready"], out["labelled"], out["dry_run"]), ([{"issue": 1, "merged": ["#5"]}], [], True))
        self.assertEqual(self.fake.calls, [])
        self.assertEqual((self.state / "ledger.jsonl").read_bytes(), before)

    def test_sync_labels_and_records_a_ledger_event(self):
        self.fake.issues = [issue(1, "Crash")]
        item = self.run_grw("issue-sync")[1]["new"][0]
        self.fake.closed_prs = [pr(5, "Closes #1")]
        self.assertEqual(self.run_grw("issue-sync")[1]["acceptance"]["labelled"], [1])
        row = grw_work.find_item(grw.Store(self.state).items(), item)
        self.assertEqual((row["acceptance"]["label"], row["acceptance"]["prs"]), ("ready for acceptance", ["#5"]))
        events = [e for e in grw.Store(self.state).events() if e["type"] == "acceptance"]
        self.assertEqual([(e["id"], e["issue"]) for e in events], [(item, 1)])
        self.fake.issues = [issue(1, "Crash", ("bug", "ready for acceptance"))]
        self.assertEqual(self.run_grw("issue-sync")[1]["acceptance"]["labelled"], [])
        self.assertEqual(len(self.fake.comments_posted()), 1)

    def test_issue_close_labels_instead_of_closing(self):
        self.fake.issues = [issue(1, "Crash")]
        item = self.run_grw("issue-sync")[1]["new"][0]
        self.run_grw("issue-accept", item)
        self.run_grw("claim", item)
        self.run_grw("issue-pr", item, "--branch", "b", "--title", "Fix crash", "--why", "g", "--why-not", "r", "--evidence", "t")
        self.fake.pulls[9] = {"merged_at": "2026-01-02T00:00:00Z"}
        self.fake.issues = [issue(1, "Crash", ("bug", "ready for acceptance"))]  # sync's own pass is tested above
        self.assertEqual(self.run_grw("issue-sync")[1]["closeout"], [item])
        code, out = self.run_grw("issue-close", item, "--evidence", "all three steps play")
        self.assertEqual((code, out["labelled"]), (0, 1))
        self.assertFalse(any(c[:2] == ("issue", "close") for c in self.fake.calls))
        self.assertEqual(grw_work.find_item(grw.Store(self.state).items(), item)["state"], "done")


if __name__ == "__main__":
    unittest.main()
