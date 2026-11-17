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


class WhoIsRunning(unittest.TestCase):
    """The who-is-running card: askwright's collector when found, the grindwright claims alone when not."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.project = Path(self.dir.name) / "colony"
        self.state = self.project / "ai-docs" / "grind"
        with contextlib.redirect_stdout(io.StringIO()):
            grw.main(["--state", str(self.state), "init", "--project", "Tiny Colony", "--repo", str(self.project)])
            grw.main(["--state", str(self.state), "add", "Paint the mill", "--lane", "art", "--source", "t", "--value", "4"])
            grw.main(["--state", str(self.state), "add", "Fix the save", "--lane", "bugs", "--source", "t", "--value", "3"])
        rows = grw_status._jsonl(self.state / "ledger.jsonl")
        now = dt.datetime.now()
        for row in rows:  # mill: fresh lease; save: lease ran out 3 h ago (a dead session's claim)
            hours = 5 if row["title"] == "Paint the mill" else -3
            row.update(state="running", session="m-" + row["lane"], branch="grind/" + row["lane"],
                       lease_until=(now + dt.timedelta(hours=hours)).isoformat(timespec="seconds"))
        with open(self.state / "ledger.jsonl", "a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        grw_status._WHO_CACHE.clear()

    def test_project_dir_is_above_ai_docs(self):
        self.assertEqual(grw_status.project_dir(self.state), self.project.resolve())

    def test_claims_only_without_askwright_says_so(self):
        with mock.patch.object(grw_status, "askwright_scripts", return_value=None):
            data = grw_status.who(self.state, now=dt.datetime.now())
        self.assertEqual(data["source"], "grindwright claims")
        status = {r["claims"][0]["title"]: r["status"] for r in data["rows"]}
        self.assertEqual(status, {"Paint the mill": "claimed, no session seen", "Fix the save": "possibly stale"})
        self.assertIn("lease ran out", [r for r in data["rows"] if r["status"] == "possibly stale"][0]["evidence"][0])
        self.assertTrue(any("claimed nothing" in p for p in data["problems"]))

    def test_uses_askwright_collector_when_found(self):
        scripts = Path(self.dir.name) / "askwright-scripts"
        scripts.mkdir()
        (scripts / "agents.py").write_text(
            "def collect(dirs):\n    return {'rows': [{'session': 's1', 'status': 'live', 'cwd': dirs[0]}], 'problems': []}\n",
            encoding="utf-8")
        with mock.patch.object(grw_status, "askwright_scripts", return_value=scripts):
            data = grw_status.who(self.state, now=dt.datetime.now())
        self.assertEqual(data["source"], "askwright")
        self.assertEqual(Path(data["rows"][0]["cwd"]), self.project.resolve())

    def test_broken_collector_falls_back_and_says_why(self):
        scripts = Path(self.dir.name) / "askwright-scripts"
        scripts.mkdir()
        (scripts / "agents.py").write_text("def collect(dirs):\n    raise OSError('drive gone')\n", encoding="utf-8")
        with mock.patch.object(grw_status, "askwright_scripts", return_value=scripts):
            data = grw_status.who(self.state, now=dt.datetime.now())
        self.assertEqual(len(data["rows"]), 2)
        self.assertIn("drive gone", data["problems"][0])

    def test_askwright_link_only_when_project_known_and_hub_up(self):
        home = Path(self.dir.name) / "askhome"
        (home / "projects").mkdir(parents=True)
        (home / "projects" / "colony.json").write_text(json.dumps({"slug": "colony", "dirs": [str(self.project)]}), encoding="utf-8")
        import socket
        hub = socket.socket()
        hub.bind(("127.0.0.1", 0))
        hub.listen()
        self.addCleanup(hub.close)
        env = {"ASKWRIGHT_HOME": str(home), "ASKWRIGHT_PORT": str(hub.getsockname()[1])}
        with mock.patch.dict("os.environ", env):
            self.assertEqual(grw_status.askwright_link(self.state), f"http://127.0.0.1:{env['ASKWRIGHT_PORT']}/projects/colony")
            hub.close()
            self.assertIsNone(grw_status.askwright_link(self.state))
        with mock.patch.dict("os.environ", {"ASKWRIGHT_HOME": str(Path(self.dir.name) / "none")}):
            self.assertIsNone(grw_status.askwright_link(self.state))

    def test_steerwright_link_only_when_project_known_and_hub_up(self):
        home = Path(self.dir.name) / "steerhome"
        home.mkdir()
        (home / "projects.json").write_text(json.dumps({"projects": {
            "other": {"paths": [str(Path(self.dir.name) / "elsewhere")]},
            "colony": {"paths": [], "sources": {"grindwright": [str(self.state)]}}}}), encoding="utf-8")
        import socket
        hub = socket.socket()
        hub.bind(("127.0.0.1", 0))
        hub.listen()
        self.addCleanup(hub.close)
        env = {"STEERWRIGHT_HOME": str(home), "ASKWRIGHT_PORT": str(hub.getsockname()[1])}
        with mock.patch.dict("os.environ", env):
            self.assertEqual(grw_status.steerwright_link(self.state), f"http://127.0.0.1:{env['ASKWRIGHT_PORT']}/steer/p/colony")
            hub.close()
            self.assertIsNone(grw_status.steerwright_link(self.state))
        with mock.patch.dict("os.environ", {"STEERWRIGHT_HOME": str(Path(self.dir.name) / "none")}):
            self.assertIsNone(grw_status.steerwright_link(self.state))

    def test_page_inline_needs_no_fetch(self):
        page = grw_status.page({"project": "</script><b>x", "who": {"rows": []}})
        self.assertNotIn("fetch('api'", page)
        self.assertIn("grind-data", page)
        self.assertNotIn("</script><b>", page.split("id='grind-data'>", 1)[1].split("</script></body>")[0])
        self.assertIn("fetch('api'", grw_status.page())
        self.assertIn('id="who"', grw_status.page())


if __name__ == "__main__":
    unittest.main()
