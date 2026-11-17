"""Tests for the product tracks: grw.py product-scan and product-due."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_grw import Base  # noqa: E402
import grw_product  # noqa: E402


class Product(Base):
    def setUp(self):
        super().setUp()
        repo = Path(self.dir.name)
        (repo / "package.json").write_text(json.dumps({"devDependencies": {"jest": "29"}}), encoding="utf-8")
        for page in ("pages/index.tsx", "pages/pricing.tsx", "pages/checkout.tsx", "pages/_app.tsx"):
            (repo / page).parent.mkdir(exist_ok=True)
            (repo / page).write_text("x", encoding="utf-8")
        (repo / "e2e").mkdir()
        (repo / "e2e" / "buy.spec.ts").write_text("await page.goto('/checkout')", encoding="utf-8")
        self.calls = []
        real = grw_product.run_cmd

        def fake(argv, cwd, timeout=180):
            self.calls.append(argv)
            joined = " ".join(argv) if isinstance(argv, list) else argv
            if "outdated" in joined:
                return 1, json.dumps({"react": {"current": "17.0.2", "wanted": "17.0.2", "latest": "19.1.0"},
                                      "lodash": {"current": "4.17.20", "latest": "4.17.21"}}), ""
            if "audit" in joined:
                return 1, json.dumps({"vulnerabilities": {"minimist": {"severity": "high"}}}), ""
            if " ls " in f" {joined} ":
                return 0, json.dumps({"dependencies": {"request": {"version": "2.88.2"}, "react": {"version": "17.0.2"}}}), ""
            if "view request@" in joined:
                return 0, "request has been deprecated\n", ""
            if joined == "build":
                return 0, "warn: punycode module is deprecated\nok\n", ""
            return 0, "", ""
        grw_product.run_cmd = fake
        self.addCleanup(setattr, grw_product, "run_cmd", real)
        self.profile({"product": {"deprecation_cmds": ["build"]}})

    def test_deps_ranks_major_and_audit(self):
        new = self.grw("product-scan", "--track", "deps")["tracks"]["deps"]["new"]
        titles = [f["title"] for f in new]
        self.assertEqual(new[0]["value"], 4)
        self.assertIn("Update react 17.0.2 to 19.1.0 (major)", titles)
        self.assertTrue(any("lodash" in t and "patch" in t for t in titles))

    def test_tests_track_finds_untested_route_and_missing_approval(self):
        out = self.grw("product-scan", "--track", "tests")["tracks"]["tests"]
        keys = {f["key"] for f in out["new"]}
        self.assertIn("route:pricing", keys)
        self.assertNotIn("route:checkout", keys)
        self.assertNotIn("route:_app", keys)
        self.assertIn("no-approval", keys)
        self.assertNotIn("no-e2e", keys)

    def test_deprecations_package_and_warning(self):
        out = self.grw("product-scan", "--track", "deprecations")["tracks"]["deprecations"]["new"]
        titles = " ".join(f["title"] for f in out)
        self.assertIn("request@2.88.2", titles)
        self.assertIn("punycode", titles)

    def test_added_or_skipped_findings_drop_out(self):
        first = self.grw("product-scan", "--track", "tests")["tracks"]["tests"]["new"]
        pick = next(f for f in first if f["key"] == "route:pricing")
        self.grw("add", pick["title"], "--lane", "code", "--source", f"product:{pick['key']}", "--value", "3")
        self.grw("skip", "product:no-approval", "--why", "not worth it")
        again = {f["key"] for f in self.grw("product-scan", "--track", "tests")["tracks"]["tests"]["new"]}
        self.assertNotIn("route:pricing", again)
        self.assertNotIn("no-approval", again)

    def test_due_follows_schedule(self):
        self.assertIn("deps", self.grw("product-due")["due"])
        self.grw("product-scan", "--track", "deps")
        due = self.grw("product-due")
        self.assertNotIn("deps", due["due"])
        self.assertIn("tests", due["due"])
