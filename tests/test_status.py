"""Tests for grw_status.py: the live run status the status page serves."""
import contextlib
import datetime as dt
import io
import json
import sys
import tempfile
import unittest
import urllib.request
import threading
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "grindwright" / "scripts"))
import grw  # noqa: E402
import grw_status  # noqa: E402

NO_PROCS = {"members": [], "agents": [], "crew": []}


class Status(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.state = Path(self.dir.name) / "grind"
        with contextlib.redirect_stdout(io.StringIO()):
            grw.main(["--state", str(self.state), "init", "--project", "Tiny Colony", "--repo", self.dir.name])
            grw.main(["--state", str(self.state), "add", "Paint the mill", "--lane", "art", "--source", "t", "--value", "4"])
            grw.main(["--state", str(self.state), "add", "Fix the save", "--lane", "bugs", "--source", "t", "--value", "3"])
        self.ids = {r["title"]: r["id"] for r in grw_status._jsonl(self.state / "ledger.jsonl")}

    def event(self, **fields):
        fields.setdefault("ts", dt.datetime.now().isoformat(timespec="seconds"))
        with open(self.state / "events.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps(fields) + "\n")

    def collect(self):
        with mock.patch.object(grw_status, "_processes", return_value=NO_PROCS):
            return grw_status.collect(self.state, since=dt.datetime.now() - dt.timedelta(hours=1))

    def test_open_claims_and_counts(self):
        mill, save = self.ids["Paint the mill"], self.ids["Fix the save"]
        self.event(type="claim", id=mill, session="a")
        self.event(type="claim", id=save, session="b")
        self.event(type="done", id=save, session="b")
        data = self.collect()
        self.assertEqual([w["title"] for w in data["working"]], ["Paint the mill"])
        self.assertEqual(data["working"][0]["member"], "a")
        self.assertEqual(data["counts"]["claim"], 2)
        self.assertEqual(data["counts"]["done"], 1)
        self.assertEqual(data["timeline"][0]["title"], "Fix the save")
        self.assertEqual(data["project"], "Tiny Colony")
        self.assertFalse(data["running"])

    def test_log_cost_and_sessions(self):
        logs = self.state / "logs"
        logs.mkdir(exist_ok=True)
        result = json.dumps({"type": "result", "total_cost_usd": 1.5, "result": "GRINDWRIGHT-LOADED"})
        (logs / f"m1-{dt.date.today().isoformat()}.log").write_text("noise\n" + result + "\n" + result + "\n", encoding="utf-8")
        row = self.collect()["logs"]["m1"]
        self.assertEqual((row["sessions"], row["cost"]), (2, 3.0))

    def test_status_command_is_read_only(self):
        before = (self.state / "events.jsonl").read_bytes() if (self.state / "events.jsonl").exists() else b""
        out = io.StringIO()
        with mock.patch.object(grw_status, "_processes", return_value=NO_PROCS), contextlib.redirect_stdout(out):
            self.assertEqual(grw.main(["--state", str(self.state), "status"]), 0)
        self.assertTrue(json.loads(out.getvalue())["ok"])
        after = (self.state / "events.jsonl").read_bytes() if (self.state / "events.jsonl").exists() else b""
        self.assertEqual(before, after)

    def test_server_serves_page_and_api(self):
        server = grw_status.make_server(self.state, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}/"
        try:
            with mock.patch.object(grw_status, "_processes", return_value=NO_PROCS):
                with urllib.request.urlopen(base, timeout=10) as page:
                    self.assertIn("Grind status", page.read().decode("utf-8"))
                with urllib.request.urlopen(base + "api", timeout=10) as api:
                    self.assertEqual(json.loads(api.read())["project"], "Tiny Colony")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
