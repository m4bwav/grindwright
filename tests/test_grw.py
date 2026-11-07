"""Unit tests for grw.py. Run from the repository root: python -m unittest discover -s tests"""
import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "grindwright" / "scripts"))
import grw  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.state = Path(self.dir.name) / "grind"
        self.saved = {k: os.environ.get(k) for k in ("GRINDWRIGHT_NOW", "GRINDWRIGHT_ASK", "GRINDWRIGHT_PLUGIN_DIRS", "GRINDWRIGHT_STATE")}
        self.addCleanup(self.restore)
        os.environ["GRINDWRIGHT_NOW"] = "2026-11-03T12:00:00"
        os.environ["GRINDWRIGHT_PLUGIN_DIRS"] = str(Path(self.dir.name) / "plugins")
        os.environ.pop("GRINDWRIGHT_ASK", None)
        self.grw("init", "--project", "Tiny", "--repo", self.dir.name)
        self.profile({})

    def restore(self):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def profile(self, extra):
        data = json.loads((self.state / "profile.json").read_text(encoding="utf-8"))
        data["people"] = {"alex": {"review_cap": 2}, "sam": {"review_cap": 1}}
        data["lanes"] = {"art": {"kind": "art", "host": "gpu", "needs": []}, "maint": {"kind": "maintenance"}, "code": {"kind": "code"}}
        data.update(extra)
        (self.state / "profile.json").write_text(json.dumps(data), encoding="utf-8")

    def grw(self, *argv, expect=0):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = grw.main(["--state", str(self.state), *argv])
        self.assertEqual(code, expect, out.getvalue())
        text = out.getvalue()
        return json.loads(text) if text.lstrip().startswith("{") else text

    def add(self, title, value=3, human=0, lane="code", *more):
        return self.grw("add", title, "--lane", lane, "--source", "test", "--value", str(value), "--human-min", str(human), *more)["id"]

    def next_id(self):
        return self.grw("next", "--no-probe")["next"].get("id")

    def make_set(self, name="s", guess=None):
        folder = Path(self.dir.name) / name
        folder.mkdir()
        q = {"id": "q1", "question": "Which?", "options": []}
        if guess is not None:
            q["guess"] = guess
        (folder / "questions.json").write_text(json.dumps({"questions": [q]}), encoding="utf-8")
        return str(folder)


class Selector(Base):
    def test_helper_ranks_with_the_item_waiting_on_it(self):
        other = self.add("middle", 4, 0, "code")
        helper = self.add("helper", 2, 0, "code")
        self.add("big feature", 5, 0, "code", "--blocked-by", helper)
        self.assertEqual(self.next_id(), helper)
        self.assertNotEqual(helper, other)

    def test_low_value_helper_clears_the_floor_when_needed(self):
        helper = self.add("helper", 1, 0, "code")
        self.assertNotEqual(self.next_id(), helper)
        self.add("big feature", 5, 0, "code", "--blocked-by", helper)
        self.assertEqual(self.next_id(), helper)

    def test_log_records_finished_work_and_reject_shows_in_discover(self):
        made = self.grw("log", "fixed a crash", "--lane", "code", "--source", "playtest", "--evidence", "boots", "--oracle", "boot")
        self.assertEqual(made["state"], "done")
        self.grw("log", "new card art", "--lane", "art", "--source", "t", "--evidence", "e", "--oracle", "none", expect=2)
        self.grw("reject", "old TODO in menu", "--why", "menu is going away")
        self.assertEqual(self.grw("discover", "--no-gh", "--dry-run")["rejected"][0]["finding"], "old TODO in menu")

    def test_high_value_hard_beats_easy_low_value(self):
        easy = self.add("rename a variable", 2, 0, "code")
        hard = self.add("finish the tutorial", 5, 60, "code")
        self.assertEqual(self.next_id(), hard, easy)

    def test_human_minutes_discount_between_equal_values(self):
        needy = self.add("needs review", 4, 60)
        free = self.add("needs nobody", 4, 0)
        self.assertEqual(self.next_id(), free, needy)

    def test_value_under_floor_is_not_selected(self):
        self.add("busywork", 1, 0)
        self.assertEqual(self.next_id(), None)
        self.assertEqual(self.grw("next", "--no-probe")["next"]["action"], "discover")

    def test_empty_queue_discovers_then_stops(self):
        self.grw("session", "start")
        self.assertEqual(self.grw("next", "--no-probe")["next"]["action"], "discover")
        self.grw("discover", "--no-gh")
        self.assertEqual(self.grw("next", "--no-probe")["next"]["action"], "stop")

    def test_add_requires_a_source(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.grw("add", "invented", "--lane", "code", "--value", "3")

    def test_maintenance_cap_holds_until_nothing_else(self):
        for n in range(3):
            done = self.add(f"bump {n}", 3, 0, "maint")
            self.grw("claim", done)
            self.grw("done", done, "--evidence", "ok", "--oracle", "tests")
        maint = self.add("bump again", 4, 0, "maint")
        other = self.add("polish", 3, 0, "code")
        self.assertEqual(self.next_id(), other)
        self.grw("drop", other, "--why", "test")
        self.assertEqual(self.grw("next", "--no-probe")["next"]["action"], "discover")
        self.grw("session", "start")
        self.grw("discover", "--no-gh")
        self.assertEqual(self.next_id(), maint)

    def test_worst_class_gets_analysis_not_work(self):
        worst = self.add("rewrite options copy with owner", 2, 60)
        self.assertEqual(self.grw("next", "--no-probe")["next"]["action"], "analyse")
        self.grw("claim", worst, expect=2)
        result = self.grw("analyse", worst, "--verdict", "shave", "--note", "only one line needs him", "--shave-title", "fix the one line")
        self.assertEqual(self.next_id(), result["created"])
        self.grw("claim", result["created"])

    def test_cut_verdict_drops(self):
        worst = self.add("bad", 2, 45)
        self.grw("analyse", worst, "--verdict", "cut", "--note", "not needed")
        self.assertEqual(grw.find_item(grw.Store(self.state).items(), worst)["state"], "dropped")

    def test_blocked_item_deferred_and_blocker_bonus(self):
        first = self.add("blocker", 3, 0)
        self.add("later", 5, 0, "code", "--blocked-by", first)
        rank = self.grw("rank", "--no-probe")
        self.assertEqual(rank["ranked"][0]["id"], first)
        self.assertTrue(any("unblocks" in w for w in rank["ranked"][0]["why"]))
        self.assertEqual(len(rank["deferred"]), 1)

    def test_machine_down_defers_gpu_lane(self):
        gpu = self.add("render cards", 5, 0, "art")
        code = self.add("wire", 2, 0, "code")
        down = json.dumps({"alive": [], "idle": [], "report": {}})
        self.assertEqual(self.grw("next", "--hosts-json", down)["next"]["id"], code, gpu)

    def test_idle_machine_lifts_score(self):
        gpu = self.add("render", 3, 0, "art")
        plain = self.grw("rank", "--hosts-json", json.dumps({"alive": [["gpu"]], "idle": []}))
        idle = self.grw("rank", "--hosts-json", json.dumps({"alive": [["gpu"]], "idle": [["gpu"]]}))
        self.assertGreater(idle["ranked"][0]["score"], plain["ranked"][0]["score"], gpu)

    def test_budget_defers_large_items_then_allows_stop(self):
        self.add("big", 5, 0, "code", "--cost", "L")
        self.grw("session", "start", "--budget", "2")
        rank = self.grw("rank", "--no-probe")
        self.assertEqual(rank["ranked"], [])
        self.assertTrue(self.grw("session", "check", "--no-probe")["may_stop"])


class HumanQueue(Base):
    def test_only_blocked_lane_switches_to_other_work(self):
        art = self.add("card batch", 5, 20, "code", "--person", "alex")
        other = self.add("balance pass", 3, 0)
        self.grw("claim", art)
        self.grw("wait-human", art, "--set", self.make_set(guess={"option": "a", "why": "cleanest read"}), "--batch", "4")
        self.assertEqual(self.next_id(), other)
        verdict = self.grw("session", "check", "--no-probe")
        self.assertFalse(verdict["may_stop"])

    def test_eval_profile_needs_isolated_inbox(self):
        self.profile({"eval": True})
        saved = os.environ.pop("ASKWRIGHT_HOME", None)
        self.addCleanup(lambda: os.environ.__setitem__("ASKWRIGHT_HOME", saved) if saved else os.environ.pop("ASKWRIGHT_HOME", None))
        self.assertIn("ASKWRIGHT_HOME", json.dumps(self.grw("session", "start", expect=2)))
        os.environ["ASKWRIGHT_HOME"] = str(Path(self.dir.name) / "inbox")
        self.grw("session", "start")

    def test_placeholder_guess_refused(self):
        item = self.add("cards", 4, 20, "code", "--person", "alex")
        out = self.grw("wait-human", item, "--set", self.make_set(guess={"option": "a", "why": "no guess made"}), expect=2)
        self.assertIn("no real guess", " ".join(out["refused"]))

    def test_missing_guess_refused(self):
        item = self.add("cards", 4, 20, "code", "--person", "alex")
        self.grw("wait-human", item, "--set", self.make_set(), expect=2)

    def test_add_question_needs_guess(self):
        self.grw("add", "q", "--lane", "code", "--source", "t", "--value", "3", "--question", "Which?", expect=2)

    def test_cap_defers_more_asks(self):
        guess = {"option": "a", "why": "reads best"}
        for n in range(2):
            item = self.add(f"batch {n}", 4, 20, "code", "--person", "alex")
            self.grw("wait-human", item, "--set", self.make_set(f"s{n}", guess))
        more = self.add("batch 3", 5, 20, "code", "--person", "alex")
        refused = self.grw("wait-human", more, "--set", self.make_set("s9", guess), expect=2)
        self.assertIn("cap", " ".join(refused["refused"]))

    def fill_queue(self):
        guess = {"option": "a", "why": "reads best"}
        for n in range(2):
            item = self.add(f"batch {n}", 4, 20, "code", "--person", "alex")
            self.grw("wait-human", item, "--set", self.make_set(f"s{n}", guess))
            yield item

    def test_past_the_cap_drafts_then_asks_when_room_opens(self):
        waiting = list(self.fill_queue())
        draft = self.add("batch 3", 5, 20, "code", "--person", "alex")
        top = self.grw("next", "--no-probe")["next"]
        self.assertEqual((top["id"], top["action"]), (draft, "draft"))
        self.grw("claim", draft)
        self.grw("hold", draft, "--evidence", "draft on branch")
        self.assertIn(draft, [d["id"] for d in self.grw("rank", "--no-probe")["deferred"]])
        self.grw("drop", waiting[0], "--why", "test")
        top = self.grw("next", "--no-probe")["next"]
        self.assertEqual((top["id"], top["action"]), (draft, "ask-drafted"))
        self.grw("wait-human", draft, "--why", "PR")

    def test_drafts_stop_at_the_cap(self):
        list(self.fill_queue())
        for n in range(2):
            draft = self.add(f"draft {n}", 5, 20, "code", "--person", "alex")
            self.grw("claim", draft)
            self.grw("hold", draft, "--evidence", "made")
        extra = self.add("draft 3", 5, 20, "code", "--person", "alex")
        self.assertIn(extra, [d["id"] for d in self.grw("rank", "--no-probe")["deferred"]])

    def test_a_question_is_not_drafted_past_the_cap(self):
        list(self.fill_queue())
        ask = self.add("which style", 5, 20, "code", "--person", "alex", "--question", "Which?", "--guess", "the first reads best")
        self.assertIn(ask, [d["id"] for d in self.grw("rank", "--no-probe")["deferred"]])

    def test_text_and_order_guesses_pass_the_gate(self):
        for n, guess in enumerate(({"text": "ten", "why": "fits"}, {"order": ["a", "b"], "why": "fits"})):
            self.assertEqual(grw.question_failures(self.make_set(f"g{n}", guess)), [])

    def test_batch_minimum_per_person(self):
        self.profile({"lanes": {"bld": {"kind": "art", "batch_min": {"sam": 5}}}})
        item = self.add("buildings", 4, 20, "bld", "--person", "sam")
        out = self.grw("wait-human", item, "--why", "PR", "--batch", "3", expect=2)
        self.assertIn("minimum of 5", " ".join(out["refused"]))
        self.grw("wait-human", item, "--why", "PR", "--batch", "5", "--pr", "30")

    def test_no_stack_lane_waits_on_pending_review(self):
        self.profile({"lanes": {"bld": {"kind": "art", "stack_on_pending": False}}})
        one = self.add("batch 1", 4, 20, "bld", "--person", "sam")
        two = self.add("batch 2", 4, 20, "bld", "--person", "alex")
        self.grw("wait-human", one, "--why", "PR", "--pr", "30")
        rank = self.grw("rank", "--no-probe")
        self.assertEqual([d["id"] for d in rank["deferred"]], [two])

    def test_answers_are_acted_on_before_new_work_and_before_new_asks(self):
        fake = Path(self.dir.name) / "ask.py"
        fake.write_text("import json;print(json.dumps({'ok':True,'answered':['q1'],'open':2}))", encoding="utf-8")
        os.environ["GRINDWRIGHT_ASK"] = str(fake)
        guess = {"option": "a", "why": "reads best"}
        item = self.add("cards", 2, 20, "code", "--person", "alex")
        self.grw("wait-human", item, "--set", self.make_set("a", guess))
        big = self.add("big feature", 5, 0)
        new_ask = self.add("another ask", 4, 10, "code", "--person", "alex")
        self.assertEqual(self.grw("sync")["answers"][0]["new"], 1)
        top = self.grw("next", "--no-probe")["next"]
        self.assertEqual((top["id"], top["action"]), (item, "act-on-answers"), big)
        self.grw("wait-human", new_ask, "--set", self.make_set("b", guess), expect=2)
        self.grw("resolve", item, "--accepted", "1", expect=2)
        self.grw("resolve", item, "--accepted", "1", "--rule", "no figures on fire cards")
        self.assertEqual(json.loads((self.state / "rules.jsonl").read_text(encoding="utf-8"))["rule"], "no figures on fire cards")
        self.assertEqual(grw.find_item(grw.Store(self.state).items(), item)["state"], "waiting-on-human")
        self.assertEqual(self.grw("sync")["answers"], [])
        metric = self.grw("metrics")["lanes"]["code"]
        self.assertEqual(metric["questions_per_accepted"], 1.0)


class Gates(Base):
    def test_derived_artifact_must_be_rebuilt_then_seen(self):
        root = Path(self.dir.name)
        strip, gif = root / "strip.png", root / "pr.gif"
        strip.write_text("a")
        gif.write_text("b")
        item = self.add("anim", 4, 20, "code", "--person", "sam")
        self.grw("derived", item, str(gif), "--source", str(strip))
        os.utime(strip, (time.time() + 50, time.time() + 50))
        refused = self.grw("wait-human", item, "--why", "PR", expect=2)
        self.assertIn("rebuild", " ".join(refused["refused"]))
        os.utime(gif, (time.time() + 100, time.time() + 100))
        refused = self.grw("wait-human", item, "--why", "PR", expect=2)
        self.assertIn("not looked at", " ".join(refused["refused"]))
        item_list = grw.Store(self.state).items()
        grw.find_item(item_list, item).setdefault("looked", {})[str(gif)] = time.time() + 200
        grw.Store(self.state).save_items(item_list)
        self.grw("wait-human", item, "--why", "PR")

    def test_repeated_redo_forces_a_route_change(self):
        item = self.add("observatory", 4, 0)
        self.grw("redo", item, "roof wrong")
        self.assertEqual(self.grw("next", "--no-probe")["next"]["action"], "work")
        self.assertTrue(self.grw("redo", item, "roof still wrong")["route_change_required"])
        self.assertEqual(self.grw("next", "--no-probe")["next"]["action"], "change-route")
        self.grw("claim", item, expect=2)
        self.grw("claim", item, "--new-route", "Blender blockout as a reference")

    def test_done_requires_evidence(self):
        item = self.add("x")
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.grw("done", item)

    def test_guards_for_someone_elses_project(self):
        self.profile({"guards": {"merge": "deny: Sam merges", "touch_main": "deny: worktree only", "stack_on_pending": "deny"},
                      "read_only_paths": ["tasks.md"], "text_bans": ["Alex", "spouse"]})
        self.assertIn("Sam merges", self.grw("guard", "merge", expect=2)["refused"][0])
        self.grw("guard", "touch_main", expect=2)
        self.grw("guard", "touch", "repo/tasks.md", expect=2)
        self.grw("guard", "touch", "repo/Docs/Agent Todos.md")
        text = Path(self.dir.name) / "pr.txt"
        text.write_text("Asked by Alex", encoding="utf-8")
        self.assertEqual(self.grw("lint-text", str(text), expect=2)["hits"], ["Alex"])
        text.write_text("Remark on marking sprites", encoding="utf-8")
        self.grw("lint-text", str(text))

    def test_outward_actions_refused_even_if_profile_allows(self):
        self.profile({"guards": {"post": "allow"}})
        for action in ("post", "publish", "deploy", "store-page", "outreach", "install-hooks"):
            self.grw("guard", action, expect=2)


class Proof(Base):
    def test_machine_done_is_not_human_proven(self):
        one = self.add("a")
        two = self.add("b")
        self.assertFalse(self.grw("done", one, "--evidence", "green", "--oracle", "tests")["human_proven"])
        self.assertTrue(self.grw("done", two, "--evidence", "kept", "--oracle", "human")["human_proven"])
        metrics = self.grw("metrics")
        self.assertEqual((metrics["machine_done"], metrics["human_unproven"]), (2, [one]))

    def test_asset_needs_provenance(self):
        item = self.add("card", 3, 0, "art")
        self.grw("done", item, "--evidence", "wired", "--oracle", "human", expect=2)
        self.grw("done", item, "--evidence", "wired", "--oracle", "human", "--provenance", "Klein, seed 22")

    def test_low_confidence_lowers_score(self):
        self.add("sure", 4, 0)
        unsure = self.add("unsure", 4, 0, "code", "--confidence", "low")
        self.assertEqual(self.grw("rank", "--no-probe")["ranked"][1]["id"], unsure)

    def test_meta_work_is_capped(self):
        self.profile({"lanes": {"meta": {"kind": "meta"}, "code": {"kind": "code"}}})
        first = self.add("tune the plugin", 5, 0, "meta")
        self.grw("claim", first)
        self.grw("done", first, "--evidence", "x", "--oracle", "tests")
        tinker = self.add("tune it more", 5, 0, "meta")
        game = self.add("finish level", 3, 0)
        self.assertEqual(self.next_id(), game, tinker)


class Mining(Base):
    def test_lane_not_on_allowlist_is_refused(self):
        self.grw("add", "balance her game", "--lane", "balance", "--source", "t", "--value", "5", expect=2)

    def test_no_discover_lanes_means_stop_is_correct(self):
        self.profile({"discover": []})
        self.grw("session", "start")
        self.assertEqual(self.grw("next", "--no-probe")["next"]["action"], "stop")
        self.assertTrue(self.grw("session", "check", "--no-probe")["may_stop"])

    def test_owner_note_outranks_everything(self):
        self.add("big", 5, 0)
        note = self.add("small thing he asked for", 1, 0, "code", "--owner-note")
        top = self.grw("next", "--no-probe")["next"]
        self.assertEqual((top["id"], top["action"]), (note, "act-on-owner-note"))

    def test_relayed_feedback_counts_as_answer(self):
        item = self.add("batch", 4, 20, "code", "--person", "sam")
        self.grw("wait-human", item, "--why", "PR", "--pr", "30")
        self.grw("relay", item, "--person", "sam", "--note", "roof should be stone")
        self.assertEqual(self.grw("next", "--no-probe")["next"]["action"], "act-on-answers")
        self.grw("resolve", item, "--accepted", "4", "--rule", "stone buildings get stone roofs")

    def test_batch_tail_exception(self):
        self.profile({"lanes": {"bld": {"kind": "art", "batch_min": {"sam": 5}}}})
        item = self.add("last 3", 4, 20, "bld", "--person", "sam")
        self.grw("wait-human", item, "--why", "PR", "--batch", "3", "--tail")

    def test_long_set_is_refused(self):
        item = self.add("cards", 4, 20, "code", "--person", "alex")
        folder = Path(self.make_set("big", {"option": "a", "why": "best read"}))
        data = json.loads((folder / "questions.json").read_text(encoding="utf-8"))
        data["questions"] = [dict(data["questions"][0], id=f"q{n}") for n in range(13)]
        (folder / "questions.json").write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("split the set", " ".join(self.grw("wait-human", item, "--set", str(folder), expect=2)["refused"]))


class Plugins(Base):
    def test_missing_plugin_closes_only_its_lane(self):
        root = Path(self.dir.name) / "plugins" / "musicwright" / "skills"
        root.mkdir(parents=True)
        self.profile({"lanes": {"music": {"kind": "music"}, "art": {"kind": "art"}, "bugs": {"kind": "code"}}})
        doctor = self.grw("doctor", "--no-probe")
        self.assertEqual(doctor["closed_lanes"], {"art": ["comfyui-gen"]})
        self.assertEqual(doctor["open_lanes"], ["bugs", "music"])
        self.assertFalse(doctor["plugins"]["artwright"])


class ClosedLane(Base):
    def test_selector_routes_around_a_closed_lane(self):
        self.profile({"lanes": {"music": {"kind": "music"}, "code": {"kind": "code"}}})
        closed = self.add("music loop", 5, 0, "music")
        open_item = self.add("save bug", 3, 0)
        self.assertEqual(self.next_id(), open_item)
        rank = self.grw("rank", "--no-probe")
        self.assertEqual(rank["deferred"][0]["id"], closed)
        self.assertIn("lane closed", rank["deferred"][0]["why"][0])


class Crash(Base):
    def test_usage_limit_pauses_and_nothing_is_lost(self):
        item = self.add("batch", 4)
        self.grw("claim", item)
        self.grw("session", "check", "--no-probe")
        self.assertFalse(self.grw("session", "check", "--no-probe")["may_stop"])
        self.grw("checkpoint", item, "12 of 48 rendered")
        self.grw("session", "pause", "--reason", "usage limit", "--until", "2026-11-03T18:00:00")
        self.assertTrue(self.grw("session", "check", "--no-probe")["may_stop"])
        saved = grw.find_item(grw.Store(self.state).items(), item)
        self.assertEqual(saved["state"], "ready")
        self.assertEqual(saved["checkpoints"][0]["note"], "12 of 48 rendered")

    def test_dead_session_lease_recovers(self):
        item = self.add("batch", 4)
        self.grw("claim", item)
        self.assertEqual(self.grw("sync")["recovered"], [])
        os.environ["GRINDWRIGHT_NOW"] = "2026-11-03T23:00:00"
        self.assertEqual(self.grw("sync")["recovered"], [item])

    def test_detached_render_comes_back_on_sync(self):
        item = self.add("render", 4)
        flag = Path(self.dir.name) / "render.done"
        self.grw("claim", item)
        self.grw("wait-machine", item, "--done-file", str(flag), "--why", "48 renders on the Mac")
        self.assertEqual(self.grw("sync")["machines"], [])
        flag.write_text("x")
        self.assertEqual(self.grw("sync")["machines"], [item])

    def test_session_cannot_end_while_work_is_selectable(self):
        self.add("work", 4)
        self.grw("session", "start")
        self.grw("session", "end", "--no-probe", expect=2)
        ended = self.grw("session", "end", "--no-probe", "--force", "owner said stop")
        self.assertTrue(ended["nothing_made"])
        self.assertEqual(self.grw("metrics")["nothing_made"], 1)


class Plan(Base):
    def test_plan_is_read_only_and_shows_questions(self):
        self.grw("add", "style call", "--lane", "code", "--source", "t", "--value", "4", "--person", "alex",
                 "--question", "Painted or flat?", "--guess", "painted, the cards already are")
        before = (self.state / "ledger.jsonl").read_bytes(), (self.state / "events.jsonl").read_bytes()
        text = self.grw("plan", "--no-probe")
        self.assertIn("Painted or flat?", text)
        self.assertIn("NOT confirmed", text)
        self.assertEqual(before, ((self.state / "ledger.jsonl").read_bytes(), (self.state / "events.jsonl").read_bytes()))

    def test_relative_repo_resolves_against_the_project(self):
        project = Path(self.dir.name) / "game"
        state = project / "ai-docs" / "grind"
        state.mkdir(parents=True)
        store = grw.Store(str(state))
        self.assertEqual(grw.project_repo(store, ".").resolve(), project.resolve())
        self.assertEqual(grw.project_repo(store, str(project)), project)

    def test_next_warns_while_road_unconfirmed(self):
        self.grw("add", "A feature", "--lane", "code", "--value", "4", "--source", "test")
        self.assertIn("road_warning", self.grw("next"))
        road = json.loads((self.state / "road.json").read_text(encoding="utf-8"))
        road["confirmed"] = True
        (self.state / "road.json").write_text(json.dumps(road), encoding="utf-8")
        self.assertNotIn("road_warning", self.grw("next"))

    def test_discover_dry_run_records_nothing(self):
        (Path(self.dir.name) / "juice-report.md").write_text("### S-01 Silent card\n### S-02 Pitch\n", encoding="utf-8")
        result = self.grw("discover", "--no-gh", "--dry-run")
        juice = [s for s in result["signals"] if s["lane"] == "juice"][0]
        self.assertEqual(juice["count"], 2)
        self.assertEqual([e for e in grw.Store(self.state).events() if e["type"] == "discover"], [])

    def test_ledger_stays_sorted_one_line_per_item(self):
        self.add("b")
        self.add("a")
        lines = (self.state / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        ids = [json.loads(line)["id"] for line in lines]
        self.assertEqual(ids, sorted(ids))


class Show(unittest.TestCase):
    def test_show_returns_one_item(self):
        with tempfile.TemporaryDirectory() as folder:
            def call(*argv):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    grw.main(["--state", folder, *argv])
                return json.loads(out.getvalue())
            call("init", "--project", "T", "--repo", folder)
            made = call("add", "work", "--lane", "code", "--source", "t", "--value", "4")["id"]
            self.assertEqual(call("show", made)["item"]["title"], "work")


if __name__ == "__main__":
    unittest.main()
