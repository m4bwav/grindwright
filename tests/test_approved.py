"""Tests for grw.py approve / approved --check: approved files change only with a new approval."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_grw import Base  # noqa: E402


class Approved(Base):
    def setUp(self):
        super().setUp()
        self.root = Path(self.dir.name)
        (self.root / "spec.md").write_text("v1", encoding="utf-8")
        (self.root / "art.png").write_bytes(b"png")

    def test_unchanged_passes_changed_fails(self):
        self.grw("approve", "spec.md", "art.png")
        self.assertEqual(self.grw("approved", "--check")["changed"], [])
        (self.root / "spec.md").write_text("v2", encoding="utf-8")
        out = self.grw("approved", "--check", expect=1)
        self.assertFalse(out["ok"])
        self.assertEqual(out["changed"], [{"file": "spec.md", "state": "changed"}])
        self.grw("approve", "spec.md")
        self.grw("approved", "--check")

    def test_gone_and_unapproved_named(self):
        self.grw("approve", "art.png")
        (self.root / "art.png").unlink()
        out = self.grw("approved", "--check", "spec.md", expect=1)
        self.assertEqual(out["changed"], [{"file": "art.png", "state": "gone"}])
        self.assertEqual(out["unapproved"], ["spec.md"])

    def test_listing_without_check_exits_zero_and_missing_file_refused(self):
        self.grw("approve", "spec.md")
        (self.root / "spec.md").write_text("v2", encoding="utf-8")
        self.assertEqual(len(self.grw("approved")["changed"]), 1)
        self.grw("approve", "nope.md", expect=2)


if __name__ == "__main__":
    unittest.main()
