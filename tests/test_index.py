"""Tests for grind_index.py: the run registry, the scans and the master page."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "grindwright" / "scripts"))
import grind_index  # noqa: E402


def make_run(root, project, rid, usd=1.5, sessions=2):
    logs = Path(root) / project / "ai-docs" / "grind" / "logs"
    logs.mkdir(parents=True)
    passes = [{"n": i, "session_id": f"{rid}-s{i}", "usd": usd, "tokens": 1000, "seconds": 60,
               "outcome": "worked", "started": "2026-11-08T10:00:00"} for i in range(sessions)]
    run = {"id": rid, "project": project, "started": "2026-11-08T10:00:00", "ended": "2026-11-08T12:00:00",
           "members": [{"member": "m1", "passes": passes, "result": {"stopped": "ledger"}}]}
    path = logs / f"{rid}.json"
    path.write_text(json.dumps(run), encoding="utf-8")
    (logs / f"{rid}.chain.json").write_text("{}", encoding="utf-8")
    (logs / f"{rid}-report.html").write_text("<html></html>", encoding="utf-8")
    return path


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["GRINDWRIGHT_HOME"] = os.path.join(self.tmp, "home")
        self.cp = Path(self.tmp) / "claude-projects"
        os.environ["GRINDWRIGHT_CLAUDE_PROJECTS"] = str(self.cp)
        os.environ["STEERWRIGHT_HOME"] = os.path.join(self.tmp, "steer")

    def transcript(self, name, cwd, command):
        folder = self.cp / "proj"
        folder.mkdir(parents=True, exist_ok=True)
        lines = [{"type": "user", "timestamp": "2026-11-08T10:00:00Z", "cwd": cwd, "sessionId": name},
                 {"type": "assistant", "timestamp": "2026-11-08T10:05:00Z", "cwd": cwd, "sessionId": name,
                  "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": command}}]}},
                 {"type": "assistant", "timestamp": "2026-11-08T11:00:00Z", "cwd": cwd, "sessionId": name}]
        (folder / f"{name}.jsonl").write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")

    def test_scan_registers_once_and_page_links_runs(self):
        make_run(self.tmp, "GameA", "run-1", usd=2.0)
        make_run(self.tmp, "GameB", "run-2", usd=1.0, sessions=1)
        r = grind_index.build([self.tmp])
        self.assertEqual((r["runs"], r["sessions"], r["added"]), (2, 3, 2))
        self.assertEqual(grind_index.build([self.tmp])["added"], 0)
        page = Path(r["page"]).read_text(encoding="utf-8")
        for text in ("GameA", "GameB", "claude --resume run-1-s0", "run-1-report.html", "$5.00", "Sessions per day"):
            self.assertIn(text, page)
        self.assertNotIn(".chain.json", page)

    def test_steerwright_link_only_when_installed(self):
        self.assertNotIn("steerwright", Path(grind_index.build()["page"]).read_text(encoding="utf-8"))
        steer = Path(self.tmp) / "steer"
        steer.mkdir()
        (steer / "server.json").write_text('{"url": "http://127.0.0.1:47630/"}', encoding="utf-8")
        page = Path(grind_index.build()["page"]).read_text(encoding="utf-8")
        self.assertIn('href="http://127.0.0.1:47630/" title="all projects">steerwright</a>', page)

    def test_empty_page(self):
        r = grind_index.build()
        self.assertEqual((r["runs"], r["sessions"]), (0, 0))
        self.assertIn("Nothing found yet", Path(r["page"]).read_text(encoding="utf-8"))

    def test_missing_run_file_is_skipped(self):
        path = make_run(self.tmp, "GameA", "run-1")
        grind_index.add(path.parent.parent, path)
        path.unlink()
        self.assertEqual(grind_index.build()["runs"], 0)

    def test_transcripts_find_grind_sessions(self):
        game = Path(self.tmp) / "Game"
        (game / "ai-docs" / "grind").mkdir(parents=True)
        (game / "ai-docs" / "grind" / "profile.json").write_text(json.dumps({"project": "Star Game"}), encoding="utf-8")
        self.transcript("aaaa1111", str(game / "sub"), "python grw.py --state ai-docs/grind session start --budget 3")
        self.transcript("cccc3333", str(game), "python other.py session start")
        self.transcript("eeee5555", str(game), 'cd x; grep -l "grw.py session start" */*.jsonl | wc -l')
        self.transcript("ffff6666", "C:/elsewhere", f'G="python grw.py"; $G --state "{game}/ai-docs/grind" session start')
        self.transcript("dddd4444", os.path.join(self.tmp, "Temp", "eval"), "python grw.py session start")
        old, grind_index.TEMP = grind_index.TEMP, grind_index.re.compile(r"[\\/]Temp[\\/]eval")  # the test folder itself is in Temp
        self.addCleanup(setattr, grind_index, "TEMP", old)
        r = grind_index.build()
        self.assertEqual(r["sessions"], 2)
        self.assertEqual(r["projects"], ["Star Game"])
        page = Path(r["page"]).read_text(encoding="utf-8")
        self.assertIn("claude --resume aaaa1111", page)
        self.assertIn("claude --resume ffff6666", page)  # project found from --state, not from the session's folder
        self.assertNotIn("eeee5555", page)
        self.assertNotIn("cccc3333", page)
        self.assertNotIn("dddd4444", page)
        self.assertEqual(grind_index.build(include_temp=True)["sessions"], 3)


if __name__ == "__main__":
    unittest.main()
