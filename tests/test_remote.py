"""Two computers, two state folders, one repository host: claims made through host refs. gh is faked."""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_crew import Base  # noqa: E402

import grw_work  # noqa: E402


class FakeHost:
    """Just enough of the git refs API: creating an existing ref fails with 422, a non-fast-forward PATCH too."""

    def __init__(self):
        self.refs, self.commits, self.calls, self.n = {}, {"base": {"tree": {"sha": "t0"}, "message": "", "parents": []}}, [], 0

    def run(self, *argv, stdin=None):
        self.calls.append(argv)
        if argv[0] != "api":
            return ""
        method, path = argv[2], argv[3]
        body = json.loads(stdin) if stdin else None
        tail = path.split("/git/", 1)[-1] if "/git/" in path else path
        if method == "GET" and path == "repos/o/r":
            return json.dumps({"default_branch": "main"})
        if method == "GET" and path.endswith("/commits/main"):
            return json.dumps({"sha": "base", "commit": {"tree": {"sha": "t0"}}})
        if method == "POST" and tail == "commits":
            self.n += 1
            sha = f"c{self.n}"
            self.commits[sha] = {"tree": {"sha": body["tree"]}, "message": body["message"], "parents": body["parents"]}
            return json.dumps({"sha": sha})
        if method == "GET" and tail.startswith("commits/"):
            return json.dumps(self.commits[tail.split("/", 1)[1]])
        if method == "POST" and tail == "refs":
            name = body["ref"][len("refs/heads/"):]
            if name in self.refs:
                raise grw_work.Refused(["gh api failed: Reference already exists (HTTP 422)"])
            self.refs[name] = body["sha"]
            return json.dumps({"ref": body["ref"]})
        if tail.startswith("ref/heads/") or tail.startswith("refs/heads/"):
            name = tail.split("heads/", 1)[1]
            if name not in self.refs:
                raise grw_work.Refused(["gh api failed: Not Found (HTTP 404)"])
            if method == "GET":
                return json.dumps({"object": {"sha": self.refs[name]}})
            if method == "DELETE":
                del self.refs[name]
                return ""
            if method == "PATCH":
                if self.refs[name] not in self.commits[body["sha"]]["parents"]:
                    raise grw_work.Refused(["gh api failed: Update is not a fast forward (HTTP 422)"])
                self.refs[name] = body["sha"]
                return "{}"
        if method == "GET" and tail.startswith("matching-refs/heads/"):
            prefix = tail.split("heads/", 1)[1]
            return json.dumps([{"ref": "refs/heads/" + k, "object": {"sha": v}} for k, v in self.refs.items() if k.startswith(prefix)])
        raise AssertionError(f"unexpected call {argv}")


class TwoComputers(Base):
    profile_extra = {"work": {"remote": {"repo": "o/r", "lease_hours": 6}}}

    def setUp(self):
        super().setUp()
        self.host = FakeHost()
        saved = {n: getattr(grw_work, n) for n in ("gh", "gh_json")}
        self.addCleanup(lambda: [setattr(grw_work, n, f) for n, f in saved.items()])
        grw_work.gh = self.host.run
        grw_work.gh_json = lambda *a: json.loads(self.host.run("api", "-X", "GET", *a) or "[]")
        os.environ["GRINDWRIGHT_NOW"] = "2026-11-08T12:00:00"
        self.addCleanup(os.environ.pop, "GRINDWRIGHT_NOW", None)
        self.addCleanup(os.environ.pop, "GRINDWRIGHT_MACHINE", None)
        # the second computer: its own state folder, same project, same host
        self.home = self.state
        self.title = "alpha engine rewrite"
        self.mine = self.add(self.title)
        self.state = self.root / "grind-b"
        self.run_grw("init", "--project", "T", "--repo", str(self.root))
        for name in ("profile.json", "road.json"):
            (self.state / name).write_text((self.home / name).read_text(encoding="utf-8"), encoding="utf-8")
        self.theirs = self.add(self.title)
        self.away = self.state
        self.state = self.home

    def on(self, computer, *argv):
        os.environ["GRINDWRIGHT_MACHINE"] = computer
        self.state = self.home if computer == "pc-a" else self.away
        return self.run_grw(*argv)

    def test_second_computer_is_refused_and_skips_it(self):
        code, got = self.on("pc-a", "claim", self.mine)
        self.assertEqual(code, 0, got)
        self.assertEqual(got["remote"]["machine"], "pc-a")
        code, got = self.on("pc-b", "claim", self.theirs)
        self.assertNotEqual(code, 0)
        self.assertIn("pc-a", json.dumps(got))
        _, nxt = self.on("pc-b", "next", "--no-probe")
        self.assertIn("another computer is on it", json.dumps(nxt))

    def test_sync_marks_the_item_and_done_releases_it(self):
        self.on("pc-a", "claim", self.mine)
        _, synced = self.on("pc-b", "sync")
        self.assertEqual(synced["remote"]["others"][0]["machine"], "pc-a")
        self.on("pc-a", "done", self.mine, "--evidence", "tests pass", "--oracle", "tests")
        self.assertEqual(self.host.refs, {})
        _, synced = self.on("pc-b", "sync")
        self.assertEqual(synced["remote"]["others"], [])
        code, got = self.on("pc-b", "claim", self.theirs)
        self.assertEqual(code, 0, got)

    def test_expired_claim_is_taken_over_with_a_fast_forward(self):
        self.on("pc-a", "claim", self.mine)
        os.environ["GRINDWRIGHT_NOW"] = "2026-11-08T19:00:00"
        code, got = self.on("pc-b", "claim", self.theirs)
        self.assertEqual(code, 0, got)
        self.assertEqual(got["remote"]["took_over"]["machine"], "pc-a")
        sha = self.host.refs["grind-claim/t-" + grw_work.key_of(self.title)]
        self.assertIn('"machine": "pc-b"', self.host.commits[sha]["message"])

    def test_remote_lists_claims_and_ticket_first_refuses_untracked(self):
        self.on("pc-a", "claim", self.mine)
        _, listed = self.on("pc-b", "remote")
        self.assertEqual([c["machine"] for c in listed["claims"]], ["pc-a"])
        profile = json.loads((self.away / "profile.json").read_text(encoding="utf-8"))
        profile["work"]["remote"]["ticket_first"] = True
        (self.away / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
        other = self.add("beta shop screen")
        code, got = self.on("pc-b", "claim", other)
        self.assertIn("ticket_first", json.dumps(got))


if __name__ == "__main__":
    unittest.main()
