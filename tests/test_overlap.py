import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "grindwright" / "scripts"))
import grw_work  # noqa: E402

BASE = {"number": 10, "title": "Frost on walls, render half", "headRefName": "feat/wall-frost",
        "body": "Part of #7: the render half."}
SLIDERS = {"number": 11, "title": "Wall frost debug sliders", "headRefName": "feat/wall-frost-debug",
           "body": "Stacked on #10.\n\n**Series: wall frost (part 2)**. One change split."}
OTHER = {"number": 12, "title": "Tavern door animation", "headRefName": "art/tavern-door", "body": "Closes #9"}


class OverlapTests(unittest.TestCase):
    def test_issue_reference_matches(self):
        hits = grw_work.overlaps([BASE, OTHER], [], "Wall frost art batch", issue=7)
        self.assertEqual([h["pr"] for h in hits], [10])

    def test_stacking_on_open_pr_matches(self):
        hits = grw_work.overlaps([BASE, OTHER], [], "Something new", base="feat/wall-frost")
        self.assertIn("this PR would stack on it", hits[0]["why"])

    def test_branch_names_concept(self):
        hits = grw_work.overlaps([BASE], ["art/wall-frost-b1"], "Wall frost layers for nine buildings")
        self.assertEqual({h.get("pr") or h["branch"] for h in hits}, {10, "art/wall-frost-b1"})

    def test_unrelated_is_clean(self):
        self.assertEqual(grw_work.overlaps([BASE, OTHER], ["feat/fog"], "Mill grinding sound", issue=3), [])

    def test_issue_number_is_exact(self):
        self.assertEqual(grw_work.overlaps([BASE], [], "x", issue=70), [])

    def test_own_branch_skipped_and_series_read(self):
        hits = grw_work.overlaps([BASE, SLIDERS], [], "Wall frost", issue=7, head="feat/wall-frost")
        self.assertEqual(hits[0]["series"], "wall frost")

    def test_series_note(self):
        note = grw_work.series_note("wall frost", 3, [{"pr": 10}, {"pr": 11}])
        self.assertIn("Series: wall frost (part 3)", note)
        self.assertEqual(grw_work.series_of(note), ("wall frost", 3))

    def test_series_block_in_every_part_replaces_old(self):
        parts = [(10, "Render half"), (11, "Sliders")]
        body = grw_work.with_series("Original text", grw_work.series_block("wall frost", 11, parts))
        again = grw_work.with_series(body, grw_work.series_block("wall frost", 11, parts + [(12, "Art")]))
        self.assertEqual(again.count(grw_work.SERIES_START), 1)
        self.assertIn("| 2 | #11 | Sliders (this PR) |", again)
        self.assertIn("#12", again)
        self.assertTrue(again.endswith("Original text"))


if __name__ == "__main__":
    unittest.main()
