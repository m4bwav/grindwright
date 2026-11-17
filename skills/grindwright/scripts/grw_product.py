"""grindwright product tracks: commercial products and websites.

Read-only scans that turn a product repo into candidate work: test gaps (end-to-end, approval), dependencies
(npm outdated and audit), deprecations (deprecated packages and deprecation warnings from the project's own
commands) and a features track the agent works by hand. Scans never add items: they list findings with a
ready `add` line, and the agent decides. `product-due` says which tracks are due by the profile's schedule.
"""
import json
import re
import subprocess
from pathlib import Path

TRACKS = ("tests", "deps", "deprecations", "features")
EVERY_DAYS = {"deps": 7, "deprecations": 30, "tests": 14, "features": 30}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "out", "coverage", "vendor", ".venv", "bin", "obj"}
E2E_DEPS = ("@playwright/test", "playwright", "cypress", "puppeteer", "webdriverio", "@wdio/cli", "testcafe", "nightwatch")
UNIT_DEPS = ("jest", "vitest", "mocha", "ava", "jasmine", "@testing-library/react", "@testing-library/dom")
APPROVAL_DEPS = ("approvaltests", "jest-image-snapshot", "verify", "@storybook/test-runner", "chromatic", "backstopjs", "loki")
E2E_DIRS = ("e2e", "cypress", "playwright", "tests/e2e", "test/e2e", "integration", "tests/integration")
ROUTE_DIRS = ("pages", "app", "src/pages", "src/app", "src/routes", "routes", "src/views", "views")
PAGE_EXT = (".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte", ".astro", ".html", ".md", ".mdx", ".cshtml", ".razor")
SEVERITY_VALUE = {"critical": 5, "high": 4, "moderate": 3, "low": 2, "info": 1}
FEATURE_PROMPTS = [
    "read the README, landing page and pricing: what does a paying customer come for, and what stops them",
    "read open issues, support mail summaries and reviews the repo already holds: repeated asks are minor features",
    "compare two or three competitors' public feature lists: gaps that customers would pay for are major features",
    "look at analytics or logs the project exposes (no new tracking): drop-off pages and slow pages",
    "write each idea as a question to the owner with your guess of value and size; never build a major feature unasked",
]


def run_cmd(argv, cwd, timeout=180):
    """Run a command; returns (code, stdout, stderr). Tests replace this."""
    try:
        done = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, shell=isinstance(argv, str))
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)
    return done.returncode, done.stdout, done.stderr


def npm():
    import os
    return "npm.cmd" if os.name == "nt" else "npm"


def walk(root, depth=4):
    root = Path(root)
    stack = [(root, 0)]
    while stack:
        here, level = stack.pop()
        try:
            entries = sorted(here.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name not in SKIP_DIRS and not entry.name.startswith(".") and level < depth:
                    stack.append((entry, level + 1))
            else:
                yield entry


def package_dirs(repo):
    return sorted({p.parent for p in walk(repo, 3) if p.name == "package.json"})


def read_pkg(folder):
    try:
        data = json.loads((Path(folder) / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    deps = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        deps.update(data.get(key) or {})
    return deps


def bump(current, latest):
    def parts(v):
        return [int(x) for x in re.findall(r"\d+", str(v))[:3]] + [0, 0, 0]
    a, b = parts(current), parts(latest)
    if a[0] != b[0]:
        return "major"
    if a[1] != b[1]:
        return "minor"
    return "patch" if a[2] != b[2] else "none"


def rel(repo, folder):
    text = str(Path(folder).relative_to(repo)).replace("\\", "/")
    return "" if text == "." else text


def finding(track, key, title, value, why, lane, human_min=0):
    source = f"product:{key}"
    line = f'add "{title}" --lane {lane} --source "{source}" --value {value}'
    if human_min:
        line += f" --human-min {human_min}"
    return {"track": track, "key": key, "title": title, "value": value, "why": why, "add": line}


# ---------------------------------------------------------------- tracks

def scan_deps(repo, lanes):
    lane = lanes.get("deps", "deps")
    found, problems = [], []
    for folder in package_dirs(repo):
        where = rel(repo, folder)
        label = f" in {where}" if where else ""
        code, out, err = run_cmd([npm(), "outdated", "--json"], folder)
        if code not in (0, 1) and not out.strip():
            problems.append(f"npm outdated failed{label}: {(err or out).strip()[:200]}")
        else:
            try:
                rows = json.loads(out or "{}")
            except ValueError:
                rows, _ = {}, problems.append(f"npm outdated gave no JSON{label}")
            for name, row in sorted(rows.items()):
                if isinstance(row, list):
                    row = row[0] if row else {}
                current, latest = row.get("current") or row.get("wanted"), row.get("latest")
                kind = bump(current, latest)
                if kind == "none" or not latest:
                    continue
                value = {"major": 3, "minor": 2, "patch": 1}[kind]
                found.append(finding("deps", f"npm:{where}:{name}@{latest}", f"Update {name} {current} to {latest}{label} ({kind})",
                                     value, f"{kind} update; major ones need a changelog read and a test run", lane))
        code, out, err = run_cmd([npm(), "audit", "--json"], folder)
        try:
            vulns = (json.loads(out or "{}").get("vulnerabilities") or {})
        except ValueError:
            vulns = {}
            problems.append(f"npm audit gave no JSON{label}")
        for name, row in sorted(vulns.items()):
            sev = row.get("severity", "low")
            found.append(finding("deps", f"audit:{where}:{name}:{sev}", f"Fix {sev} vulnerability in {name}{label}",
                                 SEVERITY_VALUE.get(sev, 2), "npm audit; prefer a version bump over audit fix --force", lane))
    if not package_dirs(repo):
        problems.append("no package.json found: the deps track reads npm only for now")
    return found, problems


def scan_deprecations(repo, lanes, profile, limit):
    lane = lanes.get("deprecations", "deprecations")
    found, problems, checked = [], [], 0
    for folder in package_dirs(repo):
        where = rel(repo, folder)
        label = f" in {where}" if where else ""
        code, out, _ = run_cmd([npm(), "ls", "--depth=0", "--json"], folder)
        try:
            installed = json.loads(out or "{}").get("dependencies") or {}
        except ValueError:
            installed = {}
        for name, row in sorted(installed.items()):
            if checked >= limit:
                problems.append(f"stopped after {limit} deprecated-package lookups; raise --limit")
                break
            version = row.get("version")
            if not version:
                continue
            checked += 1
            _, msg, _ = run_cmd([npm(), "view", f"{name}@{version}", "deprecated"], folder, timeout=60)
            if msg.strip():
                found.append(finding("deprecations", f"npm-deprecated:{where}:{name}@{version}",
                                     f"Replace deprecated {name}@{version}{label}", 3, msg.strip()[:200], lane))
    for cmd in (profile.get("product") or {}).get("deprecation_cmds", []):
        code, out, err = run_cmd(cmd, repo, timeout=900)
        seen = set()
        for raw in (out + "\n" + err).splitlines():
            line = raw.strip()
            if not re.search(r"deprecat", line, re.I):
                continue
            norm = re.sub(r"\d+|\s+", " ", re.sub(r"[A-Za-z]:?[\\/][^\s:]+", "<path>", line))[:120].strip()
            if norm in seen:
                continue
            seen.add(norm)
            key = "warn:" + re.sub(r"[^a-z0-9]+", "-", norm.lower())[:80]
            found.append(finding("deprecations", key, f"Deprecation warning: {line[:90]}", 2, f"seen running {cmd}", lane))
    return found, problems


def scan_tests(repo, lanes):
    lane = lanes.get("tests", "tests")
    found, problems = [], []
    deps = {}
    for folder in package_dirs(repo):
        deps.update(read_pkg(folder))
    files = list(walk(repo, 6))
    names = [str(p.relative_to(repo)).replace("\\", "/") for p in files]
    e2e = [d for d in E2E_DEPS if d in deps] or [d for d in E2E_DIRS if any(n.startswith(d + "/") for n in names)]
    unit = [d for d in UNIT_DEPS if d in deps]
    approval = [d for d in APPROVAL_DEPS if d in deps] + (["approved files"] if any(".approved." in n or ".verified." in n for n in names) else [])
    if not e2e:
        found.append(finding("tests", "no-e2e", "Add end-to-end tests for the main user journeys", 4,
                             "no Playwright, Cypress or e2e folder found; start with sign-up, checkout or the main task", lane))
    if not approval:
        found.append(finding("tests", "no-approval", "Add approval or snapshot tests for key outputs", 2,
                             "no approval or visual snapshot tests found (ApprovalTests, Verify, jest-image-snapshot, Storybook test runner)", lane))
    if not unit and not any(re.search(r"(^|/)(tests?|__tests__)/|\.(test|spec)\.", n) for n in names):
        found.append(finding("tests", "no-unit", "Add unit tests", 3, "no unit test framework or test files found", lane))
    spec_text = ""
    for p, n in zip(files, names):
        if re.search(r"(^|/)(e2e|cypress|playwright|integration)/|\.(e2e|cy|spec)\.", n) and p.stat().st_size < 400_000:
            try:
                spec_text += p.read_text(encoding="utf-8", errors="replace").lower() + "\n"
            except OSError:
                pass
    routes = set()
    for n in names:
        for base in ROUTE_DIRS:
            if n.startswith(base + "/") and n.endswith(PAGE_EXT) and "/api/" not in "/" + n and not re.search(r"(^|/)_|\.(test|spec)\.", n):
                stem = re.sub(r"\.[^.]+$", "", n[len(base) + 1:])
                stem = re.sub(r"(^|/)(page|index|\+page|route)$", "", stem)
                stem = re.sub(r"\(.*?\)/?", "", stem).strip("/")
                if stem and not stem.startswith("layout") and not stem.endswith("layout"):
                    routes.add(stem)
    for route in sorted(routes):
        words = [w for w in re.split(r"[/\[\]{}:.]+", route.lower()) if w and not w.startswith("$")]
        if words and not any(w in spec_text for w in words[-1:]):
            found.append(finding("tests", f"route:{route}", f"Add an end-to-end test for /{route}", 3,
                                 "no e2e or integration spec mentions this page", lane))
    summary = {"e2e": e2e, "unit": unit, "approval": approval, "routes": len(routes)}
    return found, problems, summary


# ---------------------------------------------------------------- commands

def used_keys(store):
    used = {str(i.get("source", "")) for i in store.items()}
    for e in store.events():
        if e.get("type") == "skip":
            key = str(e.get("key"))
            used |= {key, "product:" + key}
    return used


def cmd_product_scan(store, args):
    profile = store.profile()
    repo = store.repo_path()
    conf = profile.get("product") or {}
    lanes = conf.get("lanes", {})
    tracks = TRACKS if args.track == "all" else (args.track,)
    used = used_keys(store)
    result = {"repo": str(repo), "tracks": {}, "rule": (
        "each finding is a candidate, not work: check it against the code first, then run its add line "
        "(lanes must be open in the profile; see references/products.md), or skip product:<key> --why W")}
    for track in tracks:
        problems, extra = [], {}
        if track == "deps":
            found, problems = scan_deps(repo, lanes)
        elif track == "deprecations":
            found, problems = scan_deprecations(repo, lanes, profile, args.limit)
        elif track == "tests":
            found, problems, extra = scan_tests(repo, lanes)
        else:
            found = []
            extra = {"by_hand": FEATURE_PROMPTS, "lane": lanes.get("features", "features"),
                     "how": "add ideas with --question and --guess for the owner; value by revenue or retention, not by fun to build"}
        fresh = [f for f in found if f"product:{f['key']}" not in used]
        fresh.sort(key=lambda f: -f["value"])
        result["tracks"][track] = {"found": len(found), "new": fresh[:args.limit], "already_tracked": len(found) - len(fresh),
                                   "problems": problems, **extra}
        store.event("product_scan", track=track, found=len(found), new=len(fresh))
    return result


def cmd_product_due(store, args):
    from grw import now, parse_time
    conf = store.profile().get("product") or {}
    every = dict(EVERY_DAYS, **(conf.get("every_days") or {}))
    last = {}
    for e in store.events():
        if e.get("type") == "product_scan":
            last[e.get("track")] = e.get("ts")
    rows = {}
    for track in TRACKS:
        if track not in every or every[track] in (None, 0):
            continue
        ts = last.get(track)
        age = (now() - parse_time(ts)).total_seconds() / 86400 if ts else None
        rows[track] = {"every_days": every[track], "last": ts, "due": age is None or age >= every[track],
                       "age_days": None if age is None else round(age, 1)}
    due = [t for t, r in rows.items() if r["due"]]
    return {"tracks": rows, "due": due,
            "next": f"grw.py product-scan --track {due[0]}" if due else "no product track is due"}


def add_parsers(add):
    p = add("product-scan", cmd_product_scan, "products and websites: list test gaps, outdated or vulnerable npm packages, deprecations, feature prompts")
    p.add_argument("--track", choices=TRACKS + ("all",), default="all")
    p.add_argument("--limit", type=int, default=25, help="findings shown per track, and deprecated-package lookups")
    add("product-due", cmd_product_due, "which product tracks are due by the profile's product.every_days")
