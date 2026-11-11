"""Tests for grw.py track: animations go stale when their start or end image changes."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_grw import Base  # noqa: E402


class Track(Base):
    def setUp(self):
        super().setUp()
        self.profile({"lanes": {"anim": {"kind": "animation", "needs": []}, "code": {"kind": "code"}}})
        self.root = Path(self.dir.name)
        (self.root / "a.png").write_bytes(b"start")
        (self.root / "b.png").write_bytes(b"end")

    def test_unchanged_is_fresh_changed_is_stale(self):
        self.grw("track", "record", "walk", "--start", "a.png", "--end", "b.png", "--output", "walk.mp4")
        self.assertEqual(self.grw("track", "check")["stale"], [])
        (self.root / "b.png").write_bytes(b"new end")
        stale = self.grw("track", "check")["stale"]
        self.assertEqual(stale[0]["animation"], "walk")
        self.assertEqual(stale[0]["changed"], [{"role": "end", "image": "b.png", "state": "changed"}])

    def test_add_files_one_redo_item_in_animation_lane(self):
        self.grw("track", "record", "walk", "--start", "a.png")
        (self.root / "a.png").unlink()
        added = self.grw("track", "check", "--add")["added"]
        self.assertEqual(len(added), 1)
        item = self.grw("show", added[0])
        self.assertEqual(item.get("lane", item.get("item", {}).get("lane")), "anim")
        self.assertEqual(self.grw("track", "check", "--add")["added"], [])

    def test_rerecord_clears_stale_and_missing_file_refused(self):
        self.grw("track", "record", "walk", "--start", "a.png")
        (self.root / "a.png").write_bytes(b"other")
        self.grw("track", "record", "walk", "--start", "a.png")
        self.assertEqual(self.grw("track", "check")["stale"], [])
        self.grw("track", "record", "run", "--start", "nope.png", expect=2)


if __name__ == "__main__":
    unittest.main()
