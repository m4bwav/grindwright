"""Tests for grind_loop.py, using a fake agent command."""
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
import grind_loop  # noqa: E402
import grw  # noqa: E402


class Loop(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name)
        self.state = self.root / "grind"
        os.environ["GRINDWRIGHT_PLUGIN_DIRS"] = str(self.root / "none")
        self.addCleanup(os.environ.pop, "GRINDWRIGHT_PLUGIN_DIRS", None)
        self.grw("init", "--project", "T", "--repo", str(self.root))
        self.grw("add", "work", "--lane", "code", "--source", "t", "--value", "4")

    def grw(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()):
            return grw.main(["--state", str(self.state), *argv])

    def fake(self, body):
        path = self.root / "agent.py"
        path.write_text(body, encoding="utf-8")
        return [sys.executable, str(path)]

    def go(self, command, *more):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = grind_loop.main(["p.md", "--state", str(self.state), "--max-sessions", "3", "--max-hours", "1", *more, "--go", "--", *command])
        return code, json.loads(out.getvalue())

    def test_dry_run_is_the_default(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            grind_loop.main(["p.md", "--state", str(self.state), "--max-sessions", "1", "--max-hours", "1"])
        self.assertTrue(json.loads(out.getvalue())["dry_run"])

    def test_bounds_are_required(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            grind_loop.main(["p.md"])

    def test_no_progress_stops(self):
        code, result = self.go(self.fake("print('hi')"))
        self.assertEqual((code, result["stopped"], result["sessions"]), (2, "no-progress", 2))

    def test_bookkeeping_alone_is_no_progress(self):
        agent = self.fake(f"""
with open({str(self.state / 'events.jsonl')!r}, 'a') as f:
    f.write('{{"type": "session_start"}}' + chr(10) + '{{"type": "session_end"}}' + chr(10))
""")
        code, result = self.go(agent)
        self.assertEqual(result["stopped"], "no-progress")

    def test_hung_session_stops_at_the_session_limit(self):
        code, result = self.go(self.fake("import time; time.sleep(30)"), "--session-minutes", "0.01")
        self.assertEqual(result["stopped"], "session-timeout")
        self.assertEqual(code, 2)

    def test_missing_command_stops_even_in_a_dry_run(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = grind_loop.main(["p.md", "--state", str(self.state), "--max-sessions", "1", "--max-hours", "1", "--", "no-such-agent-here"])
        self.assertEqual(json.loads(out.getvalue())["stopped"], "command-not-found")
        self.assertEqual(code, 2)

    def test_timeout_kills_the_child_of_a_wrapper(self):
        marker = self.root / "survived"
        child = f"import time, pathlib; time.sleep(3); pathlib.Path({str(marker)!r}).write_text('x')"
        wrapper = self.fake(f"import subprocess, sys; subprocess.run([sys.executable, '-c', {child!r}])")
        code, result = self.go(wrapper, "--session-minutes", "0.01")
        self.assertEqual(result["stopped"], "session-timeout")
        time.sleep(4)
        self.assertFalse(marker.exists())

    def test_log_keeps_session_output(self):
        log = self.root / "run.log"
        self.go(self.fake("print('session said this')"), "--log", str(log))
        self.assertIn("session said this", log.read_text(encoding="utf-8"))

    def test_max_sessions_stops(self):
        body = f"open(r'{self.state / 'events.jsonl'}','a').write('{{\"ts\":\"0\",\"type\":\"x\"}}\\n')"
        code, result = self.go(self.fake(body))
        self.assertEqual((code, result["stopped"], result["sessions"]), (0, "max-sessions", 3))

    def test_failure_stops(self):
        _, result = self.go(self.fake("raise SystemExit(3)"))
        self.assertEqual(result["stopped"], "session-failed")

    def test_usage_limit_gives_up_after_waits(self):
        body = "import sys;print('You hit your limit');sys.exit(1)"
        code, result = self.go(self.fake(body), "--limit-wait", "0", "--max-waits", "1")
        self.assertEqual((code, result["stopped"]), (2, "usage-limit"))

    def test_lost_plugin_is_caught(self):
        _, result = self.go(self.fake("print('no such thing')"), "--require-text", "grindwright")
        self.assertEqual(result["stopped"], "plugin-missing")


if __name__ == "__main__":
    unittest.main()
