"""Tests for grind_report.py and the run records the drivers write."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["GRINDWRIGHT_HOME"] = tempfile.mkdtemp(prefix="grw-home-")  # keep the run registry out of ~/.grindwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "grindwright" / "scripts"))
import grind_loop  # noqa: E402
import grind_report  # noqa: E402
import grw  # noqa: E402

RESULT = json.dumps({"type": "result", "session_id": "abc-123", "total_cost_usd": 1.25, "duration_ms": 61000, "num_turns": 9,
                     "usage": {"input_tokens": 100, "output_tokens": 50}, "modelUsage": {"claude-x": {}}})


class Report(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name)
        self.state = self.root / "grind"
        os.environ["GRINDWRIGHT_PLUGIN_DIRS"] = str(self.root / "none")
        self.addCleanup(os.environ.pop, "GRINDWRIGHT_PLUGIN_DIRS", None)
        with contextlib.redirect_stdout(io.StringIO()):
            grw.main(["--state", str(self.state), "init", "--project", "Tiny Colony", "--repo", str(self.root)])
            grw.main(["--state", str(self.state), "add", "Paint the mill", "--lane", "art", "--source", "t", "--value", "4"])

    def test_usage_of_reads_claude_json(self):
        got = grind_report.usage_of("noise\n" + RESULT)
        self.assertEqual(got["session_id"], "abc-123")
        self.assertEqual(got["usd"], 1.25)
        self.assertEqual(got["tokens"], 150)
        self.assertEqual(got["seconds"], 61)
        self.assertEqual(got["model"], "claude-x")

    def test_switches(self):
        os.environ.pop("GRINDWRIGHT_REPORT", None)
        self.assertEqual(grind_report.enabled(self.state), (True, True))
        self.assertEqual(grind_report.enabled(self.state, {"report": False}), (False, False))
        self.assertEqual(grind_report.enabled(self.state, {"open_report": False}), (True, False))
        profile = json.loads((self.state / "profile.json").read_text(encoding="utf-8"))
        profile["report"] = False
        (self.state / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
        self.assertEqual(grind_report.enabled(self.state)[0], False)
        os.environ["GRINDWRIGHT_REPORT"] = "off"
        self.addCleanup(os.environ.pop, "GRINDWRIGHT_REPORT", None)
        self.assertEqual(grind_report.enabled(self.state, {"report": True})[0], False)

    def test_build_page(self):
        items = [json.loads(x) for x in (self.state / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        item = items[0]["id"]
        with contextlib.redirect_stdout(io.StringIO()):
            grw.main(["--state", str(self.state), "--session", "m-1", "claim", item])
        run = {"id": "run-test", "project": "Tiny Colony", "started": "2000-01-01T00:00:00", "ended": "2999-01-01T00:00:00",
               "members": [{"member": "m-1", "cwd": str(self.root), "result": {"ok": True, "stopped": "ledger", "why": ["waits on a person"]},
                            "passes": [{"n": 1, "started": "2000-01-01T00:00:00", "seconds": 61, "usd": 1.25, "tokens": 150,
                                        "outcome": "worked", "session_id": "abc-123"}]}]}
        path = self.state / "logs" / "run-test.json"
        grind_report.write_run(path, run)
        result = grind_report.build(self.state, path, use_github=False)
        self.assertTrue(result["ok"])
        page = Path(result["report"]).read_text(encoding="utf-8")
        for text in ("Tiny Colony run report", "Why it stopped", "the ledger had nothing left", "Paint the mill", "claude --resume abc-123", "$1.25", "<svg"):
            self.assertIn(text, page)
        self.assertIn("m-1: 1 sessions", result["summary"])

    def test_loop_records_passes_and_report(self):
        os.environ.pop("GRINDWRIGHT_REPORT", None)
        profile = json.loads((self.state / "profile.json").read_text(encoding="utf-8"))
        profile["open_report"] = False
        (self.state / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
        agent = self.root / "agent.py"
        agent.write_text(f"print({RESULT!r})\n", encoding="utf-8")
        prompt = self.root / "p.md"
        prompt.write_text("x", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            code = grind_loop.main([str(prompt), "--state", str(self.state), "--cwd", str(self.root), "--max-sessions", "3",
                                    "--max-hours", "1", "--go", "--", sys.executable, str(agent)])
        self.assertEqual(code, 2)  # the fake agent changes nothing, so no-progress
        runs = [p for p in (self.state / "logs").glob("run-*.json") if not p.name.endswith(".chain.json")]
        self.assertEqual(len(runs), 1)
        run = json.loads(runs[0].read_text(encoding="utf-8"))
        passes = run["members"][0]["passes"]
        self.assertEqual(len(passes), 2)
        self.assertEqual(passes[0]["session_id"], "abc-123")
        self.assertEqual(passes[0]["outcome"], "idle")
        self.assertTrue(list((self.state / "logs").glob("run-*-report.html")))

    def test_no_report_flag(self):
        agent = self.root / "agent.py"
        agent.write_text(f"print({RESULT!r})\n", encoding="utf-8")
        prompt = self.root / "p.md"
        prompt.write_text("x", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            grind_loop.main([str(prompt), "--state", str(self.state), "--cwd", str(self.root), "--max-sessions", "1",
                             "--max-hours", "1", "--no-report", "--go", "--", sys.executable, str(agent)])
        self.assertFalse(list((self.state / "logs").glob("run-*.json")))


if __name__ == "__main__":
    unittest.main()
