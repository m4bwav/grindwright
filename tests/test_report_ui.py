"""Tests for report_ui.py and the data UI on the run report and the live status page."""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

os.environ["GRINDWRIGHT_HOME"] = tempfile.mkdtemp(prefix="grw-home-")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "grindwright" / "scripts"))
import grind_report  # noqa: E402
import grw_status  # noqa: E402
import report_ui  # noqa: E402

DATA = {"lanes": {}, "left": {}, "stones": [], "touched": [], "github": None, "ends": []}


def run(passes):
    return {"id": "r", "project": "Tiny", "started": "2000-01-01T00:00:00", "ended": "2000-01-01T01:00:00",
            "members": [{"member": "m-1", "result": {"ok": True, "stopped": "ledger"}, "passes": passes}]}


class Helpers(unittest.TestCase):
    def test_stamp_relative_and_absolute(self):
        t = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
        s = report_ui.stamp(t)
        self.assertIn('datetime="2026-01-02T03:04:00+00:00"', s)
        self.assertIn('title="2026-01-02 03:04"', s)
        self.assertIn("data-rel=", s)

    def test_clip_expands_long_text_only(self):
        self.assertEqual(report_ui.clip("short <b>"), "short &lt;b&gt;")
        long = report_ui.clip("x" * 300, 220)
        self.assertIn("<details", long)
        self.assertIn("more", long)

    def test_empty_escapes(self):
        self.assertIn("&lt;i&gt;", report_ui.empty("<i>", "next"))

    def test_js_pages_sorts_and_keeps_state(self):
        for want in ("aria-sort", "Showing ", "history.replaceState", "No rows match", "RUI={enhance"):
            self.assertIn(want, report_ui.JS)


class ReportPage(unittest.TestCase):
    def test_empty_run_says_what_next(self):
        page = grind_report.render(run([]), DATA)
        for want in ("No item was started", "No session has finished yet.", "No lane had work", 'class="gen"'):
            self.assertIn(want, page)

    def test_sessions_table_pages_and_sorts(self):
        passes = [{"n": i, "seconds": 60, "usd": 0.5, "tokens": 10, "outcome": "worked", "session_id": ""} for i in range(60)]
        page = grind_report.render(run(passes), DATA)
        for want in ("id='sessions' data-ui data-page='25'", "data-sort='num'", "<thead>", "class='n'", "prefers-reduced-motion",
                     ":focus-visible", "position:sticky"):
            self.assertIn(want, page)
        self.assertEqual(page.count("<tr><td>m-1</td>"), 60)  # every row in the HTML, readable without JS


class StatusPage(unittest.TestCase):
    def test_loading_error_retry_and_paging(self):
        page = grw_status.page()
        for want in ('aria-busy="true"', 'role="status"', "Loading status", "Retry", "RUI.enhance()", 'id="tl" data-ui',
                     'id="timing-t" data-ui', 'lang="en"'):
            self.assertIn(want, page)
        self.assertLess(page.index("window.RUI="), page.index("async function tick"))

    def test_inline_page_still_has_ui(self):
        page = grw_status.page({"now": "2026-01-01T00:00:00"})
        self.assertIn("grind-data", page)
        self.assertIn("RUI.enhance()", page)


if __name__ == "__main__":
    unittest.main()
