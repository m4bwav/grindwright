"""Every page grindwright writes or serves carries the inline tab icon."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "grindwright" / "scripts"))
import grind_index  # noqa: E402
import grind_report  # noqa: E402
import grw_status  # noqa: E402


class FaviconTest(unittest.TestCase):
    def test_link_is_inline_svg(self):
        link = grind_report.FAVICON_LINK
        self.assertTrue(link.startswith('<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,'))
        href = link.split('href="', 1)[1]
        for bad in ('"', "#", "<", ">"):
            self.assertNotIn(bad, href[:-2])

    def test_every_page_has_icon(self):
        pages = {
            "report and index template": grind_report.PAGE,
            "status page": grw_status.PAGE,
            "index page": grind_index.PAGE,
        }
        for name, page in pages.items():
            head = page.split("</head>", 1)[0] if "</head>" in page else page.split("<style>", 1)[0]
            self.assertIn(grind_report.FAVICON_LINK, head, name)


if __name__ == "__main__":
    unittest.main()
