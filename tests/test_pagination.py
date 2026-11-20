import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "grindwright" / "scripts"))
import grw_work  # noqa: E402


class FakePages:
    def __init__(self, total, per_page):
        self.rows = [{"number": n} for n in range(1, total + 1)]
        self.per_page = per_page
        self.paths = []

    def api(self, path):
        self.paths.append(path)
        page = int(path.rsplit("page=", 1)[-1])
        start = (page - 1) * self.per_page
        return self.rows[start:start + self.per_page]


class GhListTests(unittest.TestCase):
    def setUp(self):
        self.old = grw_work.gh_json

    def tearDown(self):
        grw_work.gh_json = self.old

    def run_list(self, total):
        fake = FakePages(total, 100)
        grw_work.gh_json = fake.api
        return grw_work.gh_list("repos/o/r/issues?state=open"), fake

    def test_reads_past_the_first_hundred(self):
        rows, fake = self.run_list(161)
        self.assertEqual(len(rows), 161)
        self.assertEqual(fake.paths[0], "repos/o/r/issues?state=open&per_page=100&page=1")
        self.assertEqual(len(fake.paths), 2)

    def test_full_last_page_asks_once_more(self):
        rows, fake = self.run_list(200)
        self.assertEqual(len(rows), 200)
        self.assertEqual(len(fake.paths), 3)

    def test_path_without_query(self):
        fake = FakePages(3, 100)
        grw_work.gh_json = fake.api
        grw_work.gh_list("repos/o/r/branches")
        self.assertEqual(fake.paths, ["repos/o/r/branches?per_page=100&page=1"])


if __name__ == "__main__":
    unittest.main()
