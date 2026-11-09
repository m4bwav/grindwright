"""Tests for sessions sharing a state folder, work sources and the crew driver. gh is faked."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
os.environ.setdefault("GRINDWRIGHT_REPORT", "off")  # tests never open a browser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "grindwright" / "scripts"))
import grind_crew  # noqa: E402
import grw  # noqa: E402
import grw_work  # noqa: E402


class Base(unittest.TestCase):
    profile_extra = {}

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name)
        self.state = self.root / "grind"
        os.environ["GRINDWRIGHT_PLUGIN_DIRS"] = str(self.root / "none")
        self.addCleanup(os.environ.pop, "GRINDWRIGHT_PLUGIN_DIRS", None)
        self.run_grw("init", "--project", "T", "--repo", str(self.root))
        path = self.state / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile.update(self.profile_extra)
        profile["lanes"] = {"code": {"kind": "code"}, "bugs": {"kind": "code"}, "features": {"kind": "code"},
                            "editor": {"kind": "code", "areas": ["resource:editor"]}}
        path.write_text(json.dumps(profile), encoding="utf-8")
        (self.state / "road.json").write_text(json.dumps({"confirmed": True, "milestones": []}), encoding="utf-8")

    def run_grw(self, *argv, sid=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = grw.main(["--state", str(self.state), *(["--session", sid] if sid else []), *argv])
        return code, json.loads(out.getvalue()) if out.getvalue().startswith("{") else out.getvalue()

    def add(self, title, *more):
        return self.run_grw("add", title, "--lane", "code", "--source", "t", "--value", "4", *more)[1]["id"]


class Sessions(Base):
    def test_second_session_gets_other_work_and_sees_the_first(self):
        first = self.add("alpha engine rewrite")
        second = self.add("beta shop screen")
        self.run_grw("session", "start", "--no-probe", sid="a")
        self.run_grw("session", "start", "--no-probe", sid="b")
        _, got_a = self.run_grw("next", "--claim", "--no-probe", sid="a")
        _, got_b = self.run_grw("next", "--claim", "--no-probe", sid="b")
        self.assertEqual({got_a["claimed"]["id"], got_b["claimed"]["id"]}, {first, second})
        self.assertEqual(got_b["others_working"][0]["session"], "a")
        self.assertIn("a:", (self.state / "BOARD.md").read_text(encoding="utf-8"))

    def test_area_clash_refused_and_deferred(self):
        first = self.add("alpha engine rewrite", "--area", "src/ui/**")
        second = self.add("beta shop screen", "--area", "src/ui/shop.py")
        self.run_grw("claim", first, sid="a")
        code, out = self.run_grw("claim", second, sid="b")
        self.assertEqual(code, 2)
        self.assertIn("held by a", out["refused"][0])
        _, ranked = self.run_grw("rank", "--no-probe", sid="b")
        self.assertEqual(ranked["ranked"], [])

    def test_lane_resource_is_exclusive(self):
        ids = [self.run_grw("add", t, "--lane", "editor", "--source", "t", "--value", "4")[1]["id"] for t in ("alpha job", "beta task")]
        self.run_grw("claim", ids[0], sid="a")
        self.assertEqual(self.run_grw("claim", ids[1], sid="b")[0], 2)

    def test_other_sessions_running_item_does_not_block_my_stop(self):
        item = self.add("alpha engine rewrite")
        self.run_grw("claim", item, sid="a")
        self.run_grw("discover", "--no-gh", sid="b")
        self.run_grw("session", "start", "--no-probe", sid="b")
        _, verdict = self.run_grw("session", "check", "--no-probe", sid="b")
        self.assertTrue(verdict["may_stop"])

    def test_release_only_frees_my_items(self):
        mine, theirs = self.add("alpha engine rewrite"), self.add("beta shop screen")
        self.run_grw("claim", mine, sid="a")
        self.run_grw("claim", theirs, sid="b")
        self.run_grw("session", "release", sid="a")
        states = {i["id"]: i["state"] for i in grw.Store(self.state).items()}
        self.assertEqual((states[mine], states[theirs]), ("ready", "running"))

    def test_zombie_session_cannot_finish_a_reclaimed_item(self):
        item = self.add("alpha engine rewrite")
        self.run_grw("claim", item, sid="a")
        store = grw.Store(self.state)
        items = store.items()
        grw.find_item(items, item)["lease_until"] = "2000-01-01T00:00:00"
        store.save_items(items)
        self.run_grw("sync", sid="b")
        self.assertEqual(self.run_grw("claim", item, sid="b")[0], 0)
        for verb in (["done", item, "--evidence", "e", "--oracle", "tests"], ["checkpoint", item, "half"], ["redo", item, "n"]):
            self.assertEqual(self.run_grw(*verb, sid="a")[0], 2, verb[0])
        self.assertEqual(grw.find_item(grw.Store(self.state).items(), item)["session"], "b")
        self.assertEqual(self.run_grw("done", item, "--evidence", "e", "--oracle", "tests", sid="b")[0], 0)

    def test_paused_item_stays_with_its_session(self):
        item = self.add("alpha engine rewrite")
        self.run_grw("claim", item, sid="a")
        self.run_grw("session", "release", sid="a")
        _, ranked = self.run_grw("rank", "--no-probe", sid="b")
        self.assertNotIn(item, [r["id"] for r in ranked["ranked"]])
        self.assertEqual(self.run_grw("claim", item, sid="b")[0], 2)
        self.assertEqual(self.run_grw("claim", item, "--take-over", sid="b")[0], 0)
        self.assertNotIn("paused_by", grw.find_item(grw.Store(self.state).items(), item))

    def test_cap_matches_people_without_case(self):
        path = self.state / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["people"] = {"jo": {"review_cap": 1}}
        path.write_text(json.dumps(profile), encoding="utf-8")
        waiting, drafted = self.add("alpha engine rewrite"), self.add("beta shop screen")
        self.run_grw("claim", waiting)
        self.run_grw("wait-human", waiting, "--person", "Jo", "--pr", "5")
        self.run_grw("claim", drafted)
        self.run_grw("hold", drafted, "--evidence", "e", "--person", "Jo")
        _, ranked = self.run_grw("rank", "--no-probe")
        self.assertIn(drafted, [d["id"] for d in ranked["deferred"]])

    def test_hold_from_ready_and_again_when_drafted(self):
        item = self.add("alpha engine rewrite")
        self.assertEqual(self.run_grw("hold", item, "--evidence", "e", "--person", "jo")[0], 0)
        _, again = self.run_grw("hold", item, "--evidence", "newer")
        self.assertEqual(again["state"], "drafted")

    def test_session_files_do_not_clobber(self):
        self.run_grw("session", "start", "--budget", "3", "--no-probe", sid="a")
        self.run_grw("session", "start", "--budget", "9", "--no-probe", sid="b")
        self.assertEqual(json.loads((self.state / "sessions" / "a.json").read_text())["budget"], 3)

    def test_duplicate_add_refused(self):
        self.add("Fishing works in winter")
        code, out = self.run_grw("add", "fishing works in winter", "--lane", "code", "--source", "t", "--value", "3")
        self.assertEqual(code, 2)
        self.assertTrue(out["duplicates"])

    def test_answers_not_handled_twice(self):
        item = self.add("alpha engine rewrite")
        store = grw.Store(self.state)
        rows = store.items()
        rows[0]["answered"] = ["q1"]
        store.save_items(rows)
        _, a = self.run_grw("next", "--claim", "--no-probe", sid="a")
        self.assertEqual(a["next"]["id"], item)
        _, b = self.run_grw("rank", "--no-probe", sid="b")
        self.assertEqual(b["ranked"], [])

    def test_stalled_run_names_the_decisions(self):
        item = self.add("alpha engine rewrite")
        self.run_grw("set", item, "state=waiting-on-human", "person=pat", "waits_for=pick")
        self.run_grw("session", "start", "--no-probe")
        self.run_grw("discover", "--no-gh")
        _, verdict = self.run_grw("session", "check", "--no-probe")
        self.assertTrue(verdict["may_stop"])
        self.assertEqual(verdict["waiting_on"][0]["person"], "pat")
        self.assertIn("pat", (self.state / "WAITING.md").read_text(encoding="utf-8"))


class WorktreeRoot(unittest.TestCase):
    def test_discover_first_reaches_only_the_first_member(self):
        crew = {"max_sessions_each": 1, "max_hours": 1, "discover_first": True}
        project = {"name": "a", "prompt": "p.md", "state": "s"}
        self.assertIn("--discover-first", grind_crew.loop_command(crew, project, "a-1", ".", "l"))
        self.assertNotIn("--discover-first", grind_crew.loop_command(crew, project, "a-2", ".", "l"))
        self.assertNotIn("--discover-first", grind_crew.loop_command({"max_sessions_each": 1, "max_hours": 1}, project, "a-1", ".", "l"))

    def test_root_replaces_the_default_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            taken = Path(folder) / "elsewhere" / "m-1"
            taken.mkdir(parents=True)
            project = {"repo": str(Path(folder) / "game"), "worktree_root": str(taken.parent)}
            self.assertEqual(grind_crew.worktree(project, "m-1", "2026-01-01"), str(taken))


class FakeGh:
    def __init__(self):
        self.calls, self.stdin, self.issues, self.events, self.comments = [], [], [], [], []

    def api(self, *argv):
        path = argv[0]
        if path.endswith("/events?per_page=100"):
            return self.events
        if path.endswith("/comments?per_page=100"):
            return self.comments
        if "/branches" in path:
            return [{"name": "main"}]
        tail = path.rsplit("/", 1)[-1]
        if tail.isdigit():
            return next(r for r in self.issues if r["number"] == int(tail))
        return self.issues

    def run(self, *argv, stdin=None):
        self.calls.append(argv)
        self.stdin.append(stdin)
        if argv[:2] == ("pr", "create"):
            return "https://github.com/o/r/pull/9\n"
        if argv[:2] == ("pr", "list"):
            return "[]"
        if argv[:2] == ("repo", "view"):
            return '{"defaultBranchRef": {"name": "main"}}'
        if argv[:2] == ("issue", "create"):
            return "https://github.com/o/r/issues/77\n"
        return "https://github.com/o/r/issues/1#c\n"


def issue(number, title, labels=("bug",), assoc="COLLABORATOR", updated="2026-01-01T00:00:00Z"):
    return {"number": number, "title": title, "html_url": f"https://github.com/o/r/issues/{number}", "labels": [{"name": l} for l in labels],
            "author_association": assoc, "updated_at": updated, "state": "open", "body": ""}


class Issues(Base):
    profile_extra = {"work": {"issues": {"repo": "o/r", "lane_bug": "bugs", "lane_feature": "features", "greenlighters": ["pat"]},
                              "tasks": {"path": "tasks.md", "person": "pat"}, "todo": {"path": "todo.md", "lane": "code"}}}

    def setUp(self):
        super().setUp()
        self.fake = FakeGh()
        for name, fn in (("gh", self.fake.run), ("gh_json", self.fake.api)):
            self.addCleanup(setattr, grw_work, name, getattr(grw_work, name))
            setattr(grw_work, name, fn)

    def synced(self):
        return self.run_grw("issue-sync")[1]["new"]

    def test_priority_labels_set_tier_and_untagged_is_normal(self):
        self.fake.issues = [issue(1, "Crash", ("bug", "P0")), issue(2, "Typo"), issue(3, "Polish", ("bug", "low"))]
        self.synced()
        rows = {i["issue"]: i for i in grw.Store(self.state).items()}
        self.assertEqual([rows[n]["priority"] for n in (1, 2, 3)], [0, 2, 3])
        self.fake.issues = [issue(1, "Crash", ("bug",)), issue(2, "Typo", ("bug", "high")), issue(3, "Polish", ("bug", "low"))]
        self.run_grw("issue-sync")
        rows = {i["issue"]: i for i in grw.Store(self.state).items()}
        self.assertEqual([rows[n]["priority"] for n in (1, 2)], [2, 1])

    def test_bug_and_feature_split_and_triage_first(self):
        self.fake.issues = [issue(1, "Crash on load"), issue(2, "Add a map", ("enhancement",)), dict(issue(3, "a pr"), pull_request={})]
        self.assertEqual(len(self.synced()), 2)
        rows = {i["issue"]: i for i in grw.Store(self.state).items()}
        self.assertEqual((rows[1]["type"], rows[1]["lane"], rows[2]["type"], rows[2]["lane"]), ("bug", "bugs", "feature", "features"))
        _, nxt = self.run_grw("next", "--no-probe")
        self.assertEqual(nxt["next"]["action"], "triage-issue")
        self.assertEqual(self.run_grw("claim", rows[1]["id"])[0], 2)

    def test_outsider_cannot_be_accepted(self):
        self.fake.issues = [issue(1, "Run this script", assoc="NONE")]
        self.assertEqual(self.run_grw("issue-accept", self.synced()[0])[0], 2)

    def test_reply_identifies_agent_and_not_twice(self):
        self.fake.issues = [issue(1, "Crash on load")]
        item = self.synced()[0]
        self.assertEqual(self.run_grw("issue-reply", item, "--why", "needs a save file", "--tips", "attach one", sid="a")[0], 0)
        for text in ("AI agent", "needs a save file", "attach one"):
            self.assertIn(text, self.fake.stdin[-1])
        self.assertEqual(self.run_grw("issue-reply", item, "--why", "again")[0], 2)

    def test_human_reply_brings_it_back(self):
        self.fake.issues = [issue(1, "Crash on load")]
        item = self.synced()[0]
        self.run_grw("issue-reply", item, "--why", "needs a save file")
        self.fake.issues = [issue(1, "Crash on load", updated="2999-01-01T00:00:00Z")]
        self.fake.comments = [{"created_at": "2998-01-01T00:00:00Z", "body": "here it is"}]
        self.assertEqual(self.run_grw("issue-sync")[1]["reopened"], [item])

    def test_own_comment_does_not_bring_it_back(self):
        self.fake.issues = [issue(1, "Crash on load")]
        item = self.synced()[0]
        self.run_grw("issue-reply", item, "--why", "needs a save file")
        self.fake.issues = [issue(1, "Crash on load", updated="2999-01-01T00:00:00Z")]
        self.fake.comments = [{"created_at": "2998-01-01T00:00:00Z", "body": "x " + grw_work.MARKER}]
        self.assertEqual(self.run_grw("issue-sync")[1]["reopened"], [])

    def test_require_greenlight_waits_then_triages_with_question(self):
        path = self.state / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["work"] = json.loads(json.dumps(profile["work"]))
        profile["work"]["issues"]["require_greenlight"] = True
        path.write_text(json.dumps(profile), encoding="utf-8")
        self.fake.issues = [issue(1, "Crash on load")]
        item = self.synced()[0]
        row = {i["id"]: i for i in grw.Store(self.state).items()}[item]
        self.assertEqual(row["state"], "waiting-on-human")
        self.assertEqual(self.run_grw("issue-accept", item)[0], 2)
        self.fake.issues = [issue(1, "Crash on load", labels=("bug", "agent-ready"))]
        self.fake.events = [{"event": "labeled", "label": {"name": "agent-ready"}, "actor": {"login": "pat"}}]
        self.assertEqual(self.run_grw("issue-sync")[1]["greenlit"], [item])
        _, nxt = self.run_grw("next", "--no-probe")
        self.assertEqual(nxt["next"]["action"], "triage-issue")
        self.assertEqual(self.run_grw("issue-question", item, "--question", "Which save slot?", "--person", "pat")[0], 0)
        self.assertIn("@pat", self.fake.stdin[-1])
        self.fake.issues = [issue(1, "Crash on load", labels=("bug", "agent-ready"), updated="2999-01-01T00:00:00Z")]
        self.fake.comments = [{"created_at": "2998-01-01T00:00:00Z", "body": "slot 2"}]
        self.assertEqual(self.run_grw("issue-sync")[1]["reopened"], [item])
        self.assertEqual(self.run_grw("issue-accept", item)[0], 0)

    def test_require_greenlight_holds_unapproved_drafts(self):
        self.fake.issues = [issue(1, "Crash"), issue(2, "Hang")]
        ids = self.synced()
        store = grw.Store(self.state)
        items = store.items()
        for i in items:
            i.update(state="drafted", triaged=True)
        store.save_items(items)
        path = self.state / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["work"] = json.loads(json.dumps(profile["work"]))
        profile["work"]["issues"]["require_greenlight"] = True
        path.write_text(json.dumps(profile), encoding="utf-8")
        self.fake.issues = [issue(1, "Crash", labels=("bug", "agent-ready")), issue(2, "Hang")]
        self.fake.events = [{"event": "labeled", "label": {"name": "agent-ready"}, "actor": {"login": "pat"}}]
        self.run_grw("issue-sync")
        rows = {i["issue"]: i for i in grw.Store(self.state).items()}
        self.assertEqual((rows[1]["state"], rows[1]["greenlit_by"]), ("drafted", "pat"))
        self.assertEqual((rows[2]["state"], rows[2]["held_from"]), ("waiting-on-human", "drafted"))
        self.fake.issues = [issue(1, "Crash", labels=("bug", "agent-ready")), issue(2, "Hang", labels=("bug", "agent-ready"))]
        self.run_grw("issue-sync")
        self.assertEqual({i["issue"]: i for i in grw.Store(self.state).items()}[2]["state"], "drafted")

    def test_issue_accept_takes_the_issue_number(self):
        self.fake.issues = [issue(7, "Crash on load")]
        self.synced()
        self.assertEqual(self.run_grw("issue-accept", "#7")[0], 0)

    def test_pr_links_both_ways_with_both_cases(self):
        self.fake.issues = [issue(1, "Crash on load")]
        item = self.synced()[0]
        self.run_grw("issue-accept", item)
        self.run_grw("claim", item)
        code, out = self.run_grw("issue-pr", item, "--branch", "b", "--title", "Fix crash", "--why", "good", "--why-not", "risky", "--evidence", "tests")
        self.assertEqual(code, 0)
        for text in ("Closes #1", "good", "risky", "tests"):
            self.assertIn(text, self.fake.stdin[-2])
        self.assertIn(out["pr"], self.fake.stdin[-1])
        self.assertEqual(self.fake.calls[-1][:3], ("issue", "comment", "1"))

    def test_task_ticket_needs_check_mentions_person_and_waits_for_their_label(self):
        ticket = ("ticket", "Add soil fertility", "--type", "feature", "--body", "b", "--from-task", "Add soil fertility")
        self.assertEqual(self.run_grw(*ticket)[0], 2)
        code, out = self.run_grw(*ticket, "--checked", "no code matches")
        self.assertEqual(code, 0)
        self.assertIn("@pat", self.fake.stdin[-1])
        item = out["id"]
        self.assertEqual(grw_work.find_item(grw.Store(self.state).items(), item)["state"], "waiting-on-human")
        self.fake.issues = [issue(77, "Add soil fertility", ("enhancement", "agent-ready"))]
        self.fake.events = [{"event": "labeled", "label": {"name": "agent-ready"}, "actor": {"login": "mallory"}}]
        self.assertEqual(self.run_grw("issue-sync")[1]["greenlit"], [])
        self.fake.events = [{"event": "labeled", "label": {"name": "agent-ready"}, "actor": {"login": "pat"}}]
        self.assertEqual(self.run_grw("issue-sync")[1]["greenlit"], [item])

    def test_proposal_waits_for_label_and_stops_at_limit(self):
        path = self.state / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["work"]["proposals"] = {"open": 1}
        path.write_text(json.dumps(profile), encoding="utf-8")
        code, out = self.run_grw("ticket", "Snow on roofs", "--type", "feature", "--body", "b", "--propose", "--person", "pat")
        self.assertEqual(code, 0)
        create = next(c for c in self.fake.calls if c[:2] == ("issue", "create"))
        self.assertIn("proposal", create)
        self.assertIn("@pat", self.fake.stdin[-1])
        item = grw_work.find_item(grw.Store(self.state).items(), out["id"])
        self.assertEqual((item["state"], item["proposal"]), ("waiting-on-human", True))
        self.assertEqual(self.run_grw("ticket", "Animated water tiles", "--type", "feature", "--body", "b", "--propose", "--person", "pat")[0], 2)

    def test_todo_master_list_marks_then_strikes_and_keeps_line_endings(self):
        path = self.root / "todo.md"
        line = "2026-10-01 - **Clinic sound** never auditioned."
        path.write_bytes(f"# Todos\r\n\r\n- {line}\r\n  second line stays\r\n- Other thing\r\n".encode())
        code, out = self.run_grw("ticket", "Clinic sound", "--type", "bug", "--body", "b", "--from-todo", line)
        self.assertEqual(code, 0)
        item = grw_work.find_item(grw.Store(self.state).items(), out["id"])
        self.assertEqual(item["state"], "ready")
        self.fake.issues = [issue(77, "Clinic sound")]
        self.assertEqual(self.run_grw("todo-sync")[1]["written"], False)
        self.assertNotIn(b"#77", path.read_bytes())
        self.run_grw("todo-sync", "--write")
        self.assertIn(f"- {line} (#77)\r\n  second line stays\r\n".encode(), path.read_bytes())
        shown = [r["text"] for r in self.run_grw("scan", "todo")[1]["showing"]]
        self.assertEqual(shown, ["Other thing"])
        self.fake.issues = [dict(issue(77, "Clinic sound"), state="closed")]
        out = self.run_grw("todo-sync", "--write")[1]
        self.assertEqual((out["changed"][0]["state"], out["lines_not_found"]), ("closed", []))
        self.assertIn(f"- ~~{line}~~ (closed #77)\r\n".encode(), path.read_bytes())
        self.assertEqual(self.run_grw("todo-sync", "--write")[1]["changed"], [])

    def test_banned_words_stop_tickets_and_comments(self):
        path = self.state / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["text_bans"] = ["Robin"]
        path.write_text(json.dumps(profile), encoding="utf-8")
        self.assertEqual(self.run_grw("ticket", "Winter fishing stops", "--type", "bug", "--body", "asked by robin")[0], 2)
        self.assertEqual(self.fake.calls, [])
        self.fake.issues = [issue(1, "Crash on load")]
        self.assertEqual(self.run_grw("issue-reply", self.synced()[0], "--why", "Robin said so")[0], 2)
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(self.run_grw("ticket", "Robinson crate breaks", "--type", "bug", "--body", "b")[0], 0)

    def test_todo_tickets_stop_at_the_open_limit(self):
        path = self.state / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["work"]["todo"]["open_tickets"] = 1
        path.write_text(json.dumps(profile), encoding="utf-8")
        self.assertEqual(self.run_grw("ticket", "Winter fishing stops", "--type", "bug", "--body", "b", "--from-todo", "one line")[0], 0)
        self.assertEqual(self.run_grw("ticket", "Taxes come monthly", "--type", "bug", "--body", "b", "--from-todo", "other words")[0], 2)

    def test_ticket_duplicates_refused_even_closed(self):
        self.fake.issues = [dict(issue(5, "Add soil fertility now"), state="closed")]
        code, out = self.run_grw("ticket", "add soil fertility now", "--type", "feature", "--body", "b")
        self.assertEqual(code, 2)
        self.assertEqual(out["duplicates"], [5])
        self.fake.issues = []
        self.run_grw("ticket", "Winter fishing stops", "--type", "bug", "--body", "b")
        self.assertEqual(self.run_grw("ticket", "winter fishing stops", "--type", "bug", "--body", "b")[0], 2)

    def test_scan_never_writes_and_skip_hides(self):
        path = self.root / "tasks.md"
        original = "- Add fertile tiles\n   - sub\n- ~~Old thing~~\n- Rain effect\n"
        path.write_text(original, encoding="utf-8")
        _, out = self.run_grw("scan", "tasks")
        self.assertEqual([r["text"] for r in out["showing"]], ["Add fertile tiles", "Rain effect"])
        self.assertEqual(out["showing"][0]["sub"], 1)
        self.run_grw("skip", out["showing"][0]["key"], "--why", "done in abc")
        self.assertEqual(len(self.run_grw("scan", "tasks")[1]["showing"]), 1)
        self.assertEqual(path.read_text(encoding="utf-8"), original)
        self.assertFalse(grw.guard_answer(grw.Store(self.state).profile(), "touch", "tasks.md")[0])

    def test_todo_mode_tickets_go_to_the_file(self):
        path = self.state / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["work"]["tickets"] = "todo"
        path.write_text(json.dumps(profile), encoding="utf-8")
        self.assertEqual(self.run_grw("ticket", "Winter fishing stops", "--type", "bug", "--body", "b")[0], 0)
        self.assertIn("[bug] Winter fishing stops", (self.root / "todo.md").read_text(encoding="utf-8"))
        self.assertEqual(self.fake.calls, [])

    def test_sync_survives_github_failure(self):
        def broken(*argv):
            raise grw_work.Refused(["gh api failed"])
        grw_work.gh_json = broken
        code, out = self.run_grw("sync")
        self.assertEqual(code, 0)
        self.assertIn("error", out["issues"])


class Crew(unittest.TestCase):
    def test_refuses_shared_state_state_in_repo_and_no_bounds(self):
        base = {"repo": "r", "prompt": "p"}
        found = grind_crew.problems({"projects": [dict(base, name="a", state="s"), dict(base, name="b", state="s")]})
        self.assertTrue(any("max_hours" in f for f in found))
        self.assertTrue(any("shares" in f for f in found))
        bounds = {"max_hours": 1, "max_sessions_each": 1}
        found = grind_crew.problems(dict(bounds, projects=[dict(base, name="a", state="r/ai-docs/grind", sessions=2)]))
        self.assertTrue(any("inside the repo" in f for f in found))
        found = grind_crew.problems(dict(bounds, projects=[dict(base, name="a", state="s", sessions=2, worktrees=False)]))
        self.assertTrue(any("without worktrees" in f for f in found))
        self.assertEqual(grind_crew.problems(dict(bounds, projects=[dict(base, name="a", state="s", sessions=2)])), [])


if __name__ == "__main__":
    unittest.main()


class FakePrGh:
    def __init__(self):
        self.prs, self.comments, self.inline, self.reviews = [], [], [], []
        self.detail = {}

    def api(self, path):
        if "/pulls?state=open" in path:
            return self.prs
        tail = path.rsplit("/pulls/", 1)[-1]
        if tail.isdigit():
            return self.detail.get(int(tail), {"mergeable": True, "mergeable_state": "clean"})
        if path.endswith("/reviews?per_page=100"):
            return self.reviews
        if "/pulls/" in path:
            return self.inline
        return self.comments

    def run(self, *argv, stdin=None):
        return '{"login": "agent"}' if argv[:2] == ("api", "user") else ""


def pr(number, author="agent"):
    return {"number": number, "title": f"PR {number}", "user": {"login": author}, "head": {"ref": f"branch-{number}"}}


def note(cid, assoc="OWNER", body="please rename", at="2026-01-02T00:00:00Z"):
    return {"id": cid, "user": {"login": "owner"}, "author_association": assoc, "created_at": at,
            "html_url": f"https://github.com/o/r/pull/1#c{cid}", "body": body}


class PullRequestReviews(Base):
    profile_extra = {"work": {"prs": {"repo": "o/r", "lane": "bugs"}}}

    def setUp(self):
        super().setUp()
        self.fake = FakePrGh()
        for name, fn in (("gh", self.fake.run), ("gh_json", self.fake.api)):
            self.addCleanup(setattr, grw_work, name, getattr(grw_work, name))
            setattr(grw_work, name, fn)

    def items(self):
        return [i for i in grw.Store(self.state).items() if i.get("review_of")]

    def test_owner_comment_on_agent_pr_becomes_one_ready_item(self):
        self.fake.prs = [pr(1), pr(2, author="someone")]
        self.fake.comments = [note(10)]
        self.assertEqual(len(self.run_grw("pr-sync")[1]["new"]), 1)
        (item,) = self.items()
        self.assertEqual((item["review_of"], item["pr_branch"], item["state"]), (1, "branch-1", "ready"))

    def test_non_owner_and_agent_marker_comments_are_ignored(self):
        self.fake.prs = [pr(1)]
        self.fake.comments = [note(10, assoc="NONE"), note(11, body="done <!-- grindwright -->")]
        self.assertEqual(self.run_grw("pr-sync")[1]["new"], [])

    def test_seen_comments_do_not_repeat_and_new_ones_reopen(self):
        self.fake.prs = [pr(1)]
        self.fake.comments = [note(10)]
        self.run_grw("pr-sync")
        self.assertEqual(self.run_grw("pr-sync")[1]["new"] + self.run_grw("pr-sync")[1]["updated"], [])
        self.fake.reviews = [{"id": 5, "user": {"login": "owner"}, "author_association": "OWNER", "state": "CHANGES_REQUESTED",
                              "submitted_at": "2026-01-03T00:00:00Z", "html_url": "u", "body": ""}]
        self.assertEqual(len(self.run_grw("pr-sync")[1]["updated"]), 1)
        self.assertEqual(len(self.items()), 1)

    def conflict(self, number, head="h1", base="b1"):
        self.fake.detail[number] = {"mergeable": False, "mergeable_state": "dirty", "html_url": f"u{number}",
                                    "head": {"sha": head, "ref": f"branch-{number}"}, "base": {"sha": base, "ref": "main"}}

    def test_conflicting_agent_pr_becomes_one_item_until_a_side_moves(self):
        self.fake.prs = [pr(1), pr(2)]
        self.conflict(1)
        self.assertEqual(len(self.run_grw("pr-sync")[1]["conflicts"]), 1)
        self.assertEqual(self.run_grw("pr-sync")[1]["conflicts"], [])
        items = grw.Store(self.state).items()
        (item,) = [i for i in items if i.get("conflict_of")]
        self.assertEqual((item["conflict_of"], item["pr_branch"], item["pr_base"], item["state"]), (1, "branch-1", "main", "ready"))
        item["state"] = "done"  # resolved, or explained on the PR
        grw.Store(self.state).save_items(items)
        self.assertEqual(self.run_grw("pr-sync")[1]["conflicts"], [])
        self.conflict(1, base="b2")
        self.assertEqual(len(self.run_grw("pr-sync")[1]["conflicts"]), 1)

    def test_unknown_mergeability_waits(self):
        self.fake.prs = [pr(1)]
        self.fake.detail[1] = {"mergeable": None, "mergeable_state": "unknown"}
        self.assertEqual(self.run_grw("pr-sync")[1]["conflicts"], [])
