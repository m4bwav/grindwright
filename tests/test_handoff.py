"""Stale takeover and deliberate handoff. Real git in temp folders; gh is faked."""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_crew import Base  # noqa: E402
from test_remote import TwoComputers  # noqa: E402

import grw_work  # noqa: E402

T0 = "2026-11-08T12:00:00"


def git(cwd, *argv, when=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@example.invalid")
    if when:
        env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    return subprocess.run(["git", "-C", str(cwd), *argv], check=True, capture_output=True, text=True, env=env).stdout.strip()


class Handoff(Base):
    def setUp(self):
        super().setUp()
        self.at(T0)
        self.addCleanup(os.environ.pop, "GRINDWRIGHT_NOW", None)
        self.addCleanup(os.environ.pop, "GRINDWRIGHT_MACHINE", None)
        os.environ["GRINDWRIGHT_MACHINE"] = "pc-a"
        git(self.root, "init", "-q", "-b", "main")
        (self.root / "a.txt").write_text("a\n", encoding="utf-8")
        git(self.root, "add", "a.txt")
        git(self.root, "commit", "-q", "-m", "base", when="2026-11-01T00:00:00")
        self.item = self.add("alpha engine rewrite")
        self.comments = []
        saved = grw_work.gh
        self.addCleanup(setattr, grw_work, "gh", saved)
        grw_work.gh = lambda *argv, stdin=None: self.comments.append((argv, stdin)) or "https://example.invalid/c/1"

    def at(self, when):
        os.environ["GRINDWRIGHT_NOW"] = when

    def branch_commit(self, when, name="feat/alpha"):
        git(self.root, "checkout", "-q", "-B", name)
        (self.root / "b.txt").write_text(when + "\n", encoding="utf-8")
        git(self.root, "add", "b.txt")
        git(self.root, "commit", "-q", "-m", "work", when=when)
        git(self.root, "checkout", "-q", "main")

    def pause(self, branch="feat/alpha"):
        self.assertEqual(self.run_grw("claim", self.item, "--branch", branch, sid="a")[0], 0)
        self.assertEqual(self.run_grw("session", "release", sid="a")[0], 0)

    def next_for(self, sid):
        return json.dumps(self.run_grw("rank", "--no-probe", sid=sid)[1])

    def test_ambiguous_branch_not_seen_is_not_stale(self):
        self.pause()
        self.at("2026-11-10T12:00:00")
        self.assertIn("unsure, so not stale", self.next_for("b"))
        code, got = self.run_grw("claim", self.item, sid="b")
        self.assertEqual(code, 2, got)

    def test_fresh_owner_is_left_alone(self):
        self.branch_commit("2026-11-08T11:00:00")
        self.pause()
        self.at("2026-11-08T15:00:00")
        self.assertIn("under the 12h threshold", self.next_for("b"))
        self.assertEqual(self.run_grw("claim", self.item, sid="b")[0], 2)

    def test_live_owner_refuses_even_take_over(self):
        self.pause()
        self.branch_commit("2026-11-08T12:30:00")
        self.at("2026-11-08T13:00:00")
        code, got = self.run_grw("claim", self.item, "--take-over", sid="b")
        self.assertEqual(code, 2)
        self.assertIn("who is live", json.dumps(got))

    def test_stale_item_is_offered_and_continues_from_its_branch(self):
        self.branch_commit("2026-11-08T11:00:00")
        self.pause()
        self.at("2026-11-09T06:00:00")
        ranked = self.run_grw("rank", "--no-probe", sid="b")[1]["ranked"]
        self.assertEqual(ranked[0]["action"], "continue-stale")
        code, got = self.run_grw("claim", self.item, sid="b")
        self.assertEqual(code, 0, got)
        self.assertEqual(got["took_over"]["from"], "a")
        self.assertEqual(got["took_over"]["kind"], "stale")
        self.assertEqual(got["continue"]["from_branch"], "feat/alpha")
        self.assertIn("origin/feat/alpha", got["continue"]["commands"][1])
        item = self.run_grw("show", self.item)[1]["item"]
        self.assertEqual(item["branch"], "feat/alpha-b")
        self.assertEqual(item["continued_from"], "feat/alpha")
        board = (self.state / "BOARD.md").read_text(encoding="utf-8")
        self.assertIn("b took it over from a", board)
        events = [json.loads(line) for line in (self.state / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertTrue(any(e["type"] == "takeover" and e["from"] == "a" for e in events))

    def test_threshold_is_set_per_project(self):
        path = self.state / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["takeover"] = {"stale_hours": 48}
        path.write_text(json.dumps(profile), encoding="utf-8")
        self.branch_commit("2026-11-08T11:00:00")
        self.pause()
        self.at("2026-11-09T06:00:00")
        self.assertIn("under the 48h threshold", self.next_for("b"))

    def test_expired_lease_with_a_branch_stays_with_its_owner_until_stale(self):
        self.branch_commit("2026-11-08T11:00:00")
        self.run_grw("claim", self.item, "--branch", "feat/alpha", sid="a")
        self.at("2026-11-08T19:00:00")
        self.run_grw("sync", sid="b")
        self.assertEqual(self.run_grw("show", self.item)[1]["item"]["paused_by"], "a")
        self.assertEqual(self.run_grw("claim", self.item, sid="b")[0], 2)
        self.at("2026-11-09T12:00:00")
        self.assertEqual(self.run_grw("claim", self.item, sid="b")[0], 0)

    def test_takeover_leaves_a_note_on_the_pr(self):
        path = self.state / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["work"] = {"issues": {"repo": "o/r"}}
        path.write_text(json.dumps(profile), encoding="utf-8")
        self.run_grw("set", self.item, "pr=7")
        self.branch_commit("2026-11-08T11:00:00")
        self.pause()
        self.at("2026-11-09T06:00:00")
        self.assertEqual(self.run_grw("claim", self.item, sid="b")[0], 0)
        argv, body = self.comments[-1]
        self.assertEqual(argv[:3], ("pr", "comment", "7"))
        self.assertIn("Taking over this from `a`", body)

    def test_handoff_inside_the_session_pushes_and_marks(self):
        origin = self.root / "origin.git"
        git(self.root, "init", "-q", "--bare", str(origin))
        work = self.root / "wt"
        git(self.root, "clone", "-q", str(origin), str(work))
        git(work, "checkout", "-q", "-b", "feat/alpha")
        git(work, "commit", "-q", "--allow-empty", "-m", "base")
        (work / "c.txt").write_text("half\n", encoding="utf-8")
        self.run_grw("claim", self.item, "--branch", "feat/alpha", sid="a")
        wrong = self.run_grw("handoff", self.item, "--to", "jennifer", "--left", "x", "--next", "y", "--worktree", str(self.root), sid="a")
        self.assertIn("is on main", json.dumps(wrong[1]))
        code, got = self.run_grw("handoff", self.item, "--to", "jennifer", "--done", "parser", "--left", "the writer",
                                 "--next", "write the writer", "--worktree", str(work), sid="a")
        self.assertEqual(code, 0, got)
        self.assertEqual(got["pushed"], ["committed", "pushed"])
        self.assertIn("feat/alpha", git(origin, "branch", "--list"))
        item = self.run_grw("show", self.item)[1]["item"]
        self.assertEqual(item["state"], "ready")
        self.assertEqual(item["handed_off"]["to"], "jennifer")
        self.assertFalse(item["handed_off"]["from_terminal"])
        self.assertNotIn("lease_until", item)
        self.assertIn("jennifer:", (self.state / "WAITING.md").read_text(encoding="utf-8"))

    def test_handoff_from_a_terminal_never_touches_the_worktree(self):
        self.run_grw("claim", self.item, "--branch", "feat/alpha", sid="a")
        (self.root / "a.txt").write_text("dirty\n", encoding="utf-8")
        code, got = self.run_grw("handoff", self.item, "--to", "jennifer", "--left", "x", "--next", "y", sid="mark")
        self.assertEqual(code, 0, got)
        self.assertTrue(got["handed_off"]["from_terminal"])
        self.assertEqual(got["pushed"], [])
        self.assertIn("a.txt", git(self.root, "status", "--porcelain"))

    def test_selector_ranks_handoff_high_for_the_addressee_only(self):
        path = self.state / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["people"] = {"jennifer": {"sessions": ["jen-1"]}}
        path.write_text(json.dumps(profile), encoding="utf-8")
        other = self.run_grw("add", "beta big feature", "--lane", "code", "--source", "t", "--value", "5")[1]["id"]
        self.run_grw("claim", self.item, "--branch", "feat/alpha", sid="a")
        self.run_grw("handoff", self.item, "--to", "jennifer", "--left", "x", "--next", "write the writer", sid="mark")
        ranked = self.run_grw("rank", "--no-probe", sid="jen-1")[1]["ranked"]
        self.assertEqual([r["id"] for r in ranked][:2], [self.item, other])
        self.assertEqual(ranked[0]["action"], "continue-handoff")
        self.assertIn("handed off to jennifer", self.next_for("c"))
        self.assertEqual(self.run_grw("claim", self.item, sid="c")[0], 2)
        code, got = self.run_grw("claim", self.item, sid="jen-1")
        self.assertEqual(code, 0, got)
        self.assertEqual(got["handoff_note"]["next"], "write the writer")
        self.assertEqual(got["continue"]["from_branch"], "feat/alpha")
        self.assertNotIn("handed_off", self.run_grw("show", self.item)[1]["item"])

    def test_handoff_to_anyone(self):
        self.run_grw("claim", self.item, sid="a")
        code, got = self.run_grw("handoff", self.item, "--to", "anyone", "--left", "x", "--next", "y", sid="a")
        self.assertEqual(code, 2)  # no branch: it will not guess which worktree to commit
        self.assertIn("names no branch", json.dumps(got))
        self.assertEqual(self.run_grw("handoff", self.item, "--to", "anyone", "--left", "x", "--next", "y", "--no-push", sid="a")[0], 0)
        self.assertEqual(self.run_grw("claim", self.item, sid="z")[0], 0)


class RemoteHandoff(TwoComputers):
    def test_terminal_handoff_ends_the_lease_and_the_other_computer_continues(self):
        self.assertEqual(self.on("pc-a", "claim", self.mine)[0], 0)
        self.on("pc-b", "sync")
        self.assertEqual(self.on("pc-b", "claim", self.theirs)[0], 2)
        code, got = self.on("pc-b", "handoff", self.theirs, "--to", "anyone", "--left", "x", "--next", "y")
        self.assertEqual(code, 0, got)
        self.assertEqual(got["remote"], "lease ended")
        code, got = self.on("pc-b", "claim", self.theirs)
        self.assertEqual(code, 0, got)
        self.assertEqual(got["remote"]["took_over"]["machine"], "pc-a")
        self.assertEqual(len(self.host.refs), 1)  # the record was updated, never deleted

    def test_fresh_host_claim_blocks_a_stale_takeover(self):
        self.on("pc-a", "claim", self.mine)
        self.on("pc-b", "sync")
        code, got = self.on("pc-b", "claim", self.theirs, "--take-over")
        self.assertNotEqual(code, 0)
        self.assertIn("pc-a", json.dumps(got))
