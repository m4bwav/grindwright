import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "grindwright" / "scripts"))
import grw_work  # noqa: E402

SHA = "a" * 40


class FakeGh:
    """repos/o/r is private; art/a.png exists on main only."""

    def __call__(self, *args, stdin=None):
        path = args[1] if args[0] == "api" else ""
        if path == "repos/o/r":
            return json.dumps({"private": True, "default_branch": "main"})
        if path.startswith("repos/o/r/contents/"):
            if path.endswith("art/a.png?ref=main"):
                return "{}"
            raise grw_work.Refused(["404"])
        if path.startswith("repos/o/r/commits/"):
            return json.dumps({"sha": SHA})
        raise AssertionError(args)


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.old, grw_work.gh = grw_work.gh, FakeGh()

    def tearDown(self):
        grw_work.gh = self.old

    def test_urls_from_markdown_and_img_tags(self):
        body = '![x](https://a/1.png) text <img width="3" src="https://a/2.gif">'
        self.assertEqual(grw_work.image_urls(body), ["https://a/1.png", "https://a/2.gif"])

    def test_raw_link_on_private_repo_is_relinked_to_a_pinned_blob(self):
        got = grw_work.check_image("https://raw.githubusercontent.com/o/r/main/art/a.png", ["feat"], {})
        self.assertEqual(got["new"], f"https://github.com/o/r/blob/{SHA}/art/a.png?raw=true")

    def test_deleted_branch_falls_back_to_a_ref_that_has_the_file(self):
        got = grw_work.check_image("https://github.com/o/r/blob/gone/art/a.png?raw=true", ["gone", "main"], {})
        self.assertEqual(got["new"], f"https://github.com/o/r/blob/{SHA}/art/a.png?raw=true")

    def test_missing_everywhere_has_no_new_link(self):
        self.assertIsNone(grw_work.check_image("https://github.com/o/r/blob/x/none.png?raw=true", ["main"], {})["new"])

    def test_good_blob_link_and_uploads_left_alone(self):
        self.assertIsNone(grw_work.check_image("https://github.com/o/r/blob/main/art/a.png?raw=true", [], {}))
        self.assertIsNone(grw_work.check_image("https://github.com/user-attachments/assets/1", [], {}))


if __name__ == "__main__":
    unittest.main()
