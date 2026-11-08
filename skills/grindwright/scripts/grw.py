#!/usr/bin/env python3
"""grindwright: the work ledger and selector for grinding on an indie game or a long creative project (film, video, story).

State lives in one folder (default ai-docs/grind in the current directory, or --state):
  profile.json  lanes, people, hosts, guards for this project
  road.json     the road to finished
  ledger.jsonl  one work item per line, sorted by id, so git merges stay small
  events.jsonl  append-only history; metrics read it
  rules.jsonl   answers turned into rules
  session.json  the running session's budget and pause state (sessions/<name>.json when named)
  BOARD.md, WAITING.md  generated for people: who works where, which decisions are waited on

Every command prints one JSON object, except plan, which prints markdown. Exit 0 ok, 1 usage or
state error, 2 a gate refused (the JSON says why). Standard library only, Python 3.9 or newer.
"""
import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import grw_work
from grw_work import Refused

VERSION = "0.3.8"
FORMAT = 1
STATES = ("ready", "running", "waiting-on-human", "waiting-on-machine", "done", "dropped")
COST_UNITS = {"S": 1, "M": 3, "L": 8}
HIGH_VALUE = 3
HIGH_HUMAN_MIN = 30
LEASE_HOURS = 6
SOLO = "solo"
DISCOVER_HOURS = 4
HANDLING_HOURS = 2
ANSWER_QUIET_MINUTES = 15
OUTWARD = ("post", "publish", "deploy", "store-page", "outreach", "install-hooks")
PLACEHOLDER_GUESS = re.compile(r"no guess|placeholder|\btbd\b|\btodo\b|not sure|unknown|n/a", re.I)
DEFAULT_PROFILE = {
    "format": FORMAT,
    "project": "",
    "repo": ".",
    "min_value": 2,
    "escalate_after": 2,
    "people": {},
    "lanes": {},
    "hosts": {},
    "guards": {"merge": "deny: no merge right set in the profile", "touch_main": "deny: use a branch", "stack_on_pending": "deny"},
    "read_only_paths": [],
    "text_bans": [],
    "discover": ["test", "missing tests", "balance", "gaps", "marketing"],
}
# Lane kinds: which plugins close a lane when missing, and the maintenance share cap.
LANE_DEFAULTS = {
    "art": ["comfyui-gen"],
    "animation": ["pixelwright"],
    "sound": [("sfxwright", "musicwright")],  # a tuple or nested list: any one is enough
    "music": ["musicwright"],
    "video": [("cinewright", "comfyui-gen")],
    "juice": ["game-juice"],
    "balance": ["ludowright"],
    "marketing": ["marketwright"],
    "model": ["polywright"],
    "writing": [("everwrite", "editwright")],
    "voice": ["voicewright"],
    "edit": [("cinewright", "comfyui-gen")],
}
MAX_SET_QUESTIONS = 12
MAINT_SHARE_CAP = 0.2
META_SHARE_CAP = 0.1
# Oracle ladder, weakest first. Only "human" proves a game is good; the rest prove it is not broken.
ORACLES = ("none", "compile", "tests", "boot", "scripted-play", "snapshot", "human")
ASSET_KINDS = ("art", "animation", "sound", "music", "video", "model", "voice")
CONFIDENCE = {"low": 0.7, "medium": 0.85, "high": 1.0}
SHARE_WINDOW = 10


def now():
    fixed = os.environ.get("GRINDWRIGHT_NOW")
    if fixed:
        return dt.datetime.fromisoformat(fixed)
    return dt.datetime.now().astimezone().replace(microsecond=0).replace(tzinfo=None)


def stamp():
    return now().isoformat(timespec="seconds")


def parse_time(text):
    return dt.datetime.fromisoformat(text).replace(tzinfo=None)


# ---------------------------------------------------------------- storage

class Store:
    def __init__(self, root, sid=SOLO):
        self.root = Path(root)
        self.sid = sid or SOLO
        self.profile_path = self.root / "profile.json"
        self.road_path = self.root / "road.json"
        self.ledger_path = self.root / "ledger.jsonl"
        self.events_path = self.root / "events.jsonl"
        self.rules_path = self.root / "rules.jsonl"
        self.session_path = self.root / "session.json" if self.sid == SOLO else self.root / "sessions" / f"{self.sid}.json"

    def require(self):
        if not self.profile_path.exists():
            raise SystemExit(f"no grindwright state at {self.root}: run grw.py init first")

    def profile(self):
        self.require()
        merged = dict(DEFAULT_PROFILE)
        merged.update(read_json(self.profile_path, {}))
        return merged

    def road(self):
        return read_json(self.road_path, {"finished_means": "", "milestones": [], "confirmed": False})

    def items(self):
        return read_jsonl(self.ledger_path)

    def save_items(self, items):
        lines = [json.dumps(i, ensure_ascii=False, sort_keys=True) for i in sorted(items, key=lambda x: x["id"])]
        write_atomic(self.ledger_path, "\n".join(lines) + ("\n" if lines else ""))

    def events(self):
        return read_jsonl(self.events_path)

    def event(self, kind, **fields):
        row = {"ts": stamp(), "type": kind}
        if self.sid != SOLO:
            row["session"] = self.sid
        row.update(fields)
        with open(self.events_path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def repo_path(self):
        return project_repo(self, self.profile().get("repo", "."))

    def session(self):
        return read_json(self.session_path, {})

    def save_session(self, session):
        write_atomic(self.session_path, json.dumps(session, indent=1, ensure_ascii=False) + "\n")


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def read_jsonl(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def write_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".grw-")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(tmp, path)


def find_item(items, item_id):
    for item in items:
        if item["id"] == item_id:
            return item
    raise SystemExit(f"no item {item_id}")


def touch(item):
    item["updated"] = stamp()


@contextlib.contextmanager
def state_lock(root, wait=120, stale=300):
    """Concurrent sessions are normal: one writer at a time, and a dead writer's lock goes stale."""
    path = Path(root) / ".lock"
    deadline = time.time() + wait
    while True:
        try:
            os.close(os.open(str(path), os.O_CREAT | os.O_EXCL))
            break
        except PermissionError as exc:
            raise SystemExit(f"state folder is not writable: {exc}")
        except OSError as exc:
            if not isinstance(exc, FileExistsError):
                raise SystemExit(f"state folder is not writable: {exc}")
            try:
                if time.time() - path.stat().st_mtime > stale:
                    path.unlink()
                    continue
            except OSError:
                continue
            if time.time() > deadline:
                raise SystemExit(f"state is locked: {path}")
            time.sleep(0.1)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            path.unlink()


# ---------------------------------------------------------------- scoring

def item_class(item):
    high_value = item["value"] >= HIGH_VALUE
    high_human = item.get("human_min", 0) >= HIGH_HUMAN_MIN
    if high_value and not high_human:
        return "best"
    if high_value:
        return "worth-the-ask"
    if not high_human:
        return "filler"
    return "worst"


def base_value(item, road):
    """Value counts squared so that it dominates; a road milestone's weight scales it."""
    weight = 1.0
    for stone in road.get("milestones", []):
        if stone.get("id") == item.get("road"):
            weight = {1: 1.0, 2: 1.25, 3: 1.5}.get(stone.get("weight", 1), 1.0)
    return item["value"] ** 2 * weight * CONFIDENCE.get(item.get("confidence", "high"), 1.0)


def human_discount(item):
    return 1.0 / (1.0 + item.get("human_min", 0) / 30.0)


def live_dependents(item, items):
    return [o for o in items if item["id"] in o.get("blocked_by", []) and o["state"] not in ("done", "dropped")]


def best_dependent(item, items, road, seen=None):
    """The best score among everything waiting on this item, however indirectly: a helper ranks with its users."""
    seen = seen if seen is not None else {item["id"]}
    best = 0.0
    for other in live_dependents(item, items):
        if other["id"] not in seen:
            seen.add(other["id"])
            best = max(best, base_value(other, road) * human_discount(other), best_dependent(other, items, road, seen))
    return best


def score_item(item, items, road, idle_hosts=()):
    """Return (score, reasons). Value first; human minutes discount; the rest only nudge."""
    value = base_value(item, road)
    discount = human_discount(item)
    score = value * discount
    why = [f"value {item['value']} -> {value:g}", f"human {item.get('human_min', 0)} min x{discount:.2f}"]
    freed = live_dependents(item, items)
    if freed:
        bonus = min(value, sum(base_value(o, road) for o in freed) * 0.25)
        score += bonus
        why.append(f"unblocks {len(freed)} +{bonus:g}")
        inherited = best_dependent(item, items, road)
        if inherited > score:
            score = inherited
            why.append(f"needed by work worth {inherited:g}")
    age = (now() - parse_time(item.get("updated", stamp()))).days
    if age > 0:
        factor = 1 + min(0.3, 0.02 * age)
        score *= factor
        why.append(f"{age} d old x{factor:.2f}")
    if idle_hosts and item.get("host"):
        if any(item["host"] in tags for tags in idle_hosts):
            score *= 1.1
            why.append("idle machine x1.10")
    return round(score, 3), why


def unfinished_blockers(item, items):
    finished = {i["id"] for i in items if i["state"] in ("done", "dropped")}
    return [b for b in item.get("blocked_by", []) if b not in finished]


def release_blocked(items):
    """A claimed item that now waits on another item is not being worked on: back to ready, deferred by select."""
    released = []
    for item in items:
        if item["state"] == "running" and unfinished_blockers(item, items):
            item["state"] = "ready"
            item.pop("lease_until", None)
            touch(item)
            released.append(item["id"])
    return released


def lane_of(profile, item):
    return profile.get("lanes", {}).get(item.get("lane"), {})


def lane_share(events, lane):
    worked = [e.get("lane") for e in events if e.get("type") in ("claim",)][-SHARE_WINDOW:]
    if not worked:
        return 0.0
    return worked.count(lane) / len(worked)


def same_person(left, right):
    """People are matched without case: a ledger saying Alex and a profile saying alex are one person."""
    return str(left or "").lower() == str(right or "").lower()


def open_for_person(items, person):
    sets = {i.get("set") or i["id"] for i in items if i["state"] == "waiting-on-human" and same_person(i.get("person"), person)}
    return len(sets)


def review_cap(profile, person):
    people = {str(k).lower(): v for k, v in profile.get("people", {}).items()}
    return people.get(str(person or "").lower(), {}).get("review_cap", 3)


def area_key(area):
    return re.sub(r"[/\\*]+$", "", str(area).replace("\\", "/")).lower()


def areas_overlap(left, right):
    left, right = area_key(left), area_key(right)
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def item_areas(profile, item):
    """What an item works in: its own paths, plus its lane's. resource:editor style names work the same way."""
    return list(item.get("areas", [])) + list(lane_of(profile, item).get("areas", []))


def owner_of(item):
    return item.get("session", SOLO)


def area_clashes(profile, item, items, sid):
    mine = item_areas(profile, item)
    return [f"{a} is held by {owner_of(o)} ({o['id']})" for o in items if o["state"] == "running" and owner_of(o) != sid and o["id"] != item["id"]
            for a in mine if any(areas_overlap(a, b) for b in item_areas(profile, o))]


def handled_elsewhere(item, sid):
    held = item.get("handling")
    return bool(held) and held.get("session") != sid and parse_time(held["until"]) > now()


def select(profile, road, items, events, session, hosts_alive=None, hosts_idle=(), closed=None, sid=SOLO):
    """Rank everything. Returns dict with ranked, deferred, answers_first, redo. No side effects."""
    done_ids = {i["id"] for i in items if i["state"] in ("done", "dropped")}
    remaining = None
    if session.get("budget"):
        remaining = session["budget"] - session.get("used", 0)
    since = session.get("started", "")
    if sid != SOLO:  # one pass serves every member of the crew
        since = (now() - dt.timedelta(hours=DISCOVER_HOURS)).isoformat(timespec="seconds")
    discovered = any(e.get("type") == "discover" and e.get("ts", "") >= since for e in events)
    ranked, deferred, capped = [], [], []
    for item in items:
        if handled_elsewhere(item, sid):
            deferred.append({"id": item["id"], "title": item["title"], "why": [f"being handled by {item['handling']['session']}"]})
            continue
        if item.get("paused_by") and item["paused_by"] != sid and sid != SOLO:
            deferred.append({"id": item["id"], "title": item["title"], "why": [f"paused by {item['paused_by']}: its work is on that session's branch, so leave it to that session (claim --take-over moves it)"]})
            continue
        if item["state"] == "drafted":
            person = item.get("person")
            cap = review_cap(profile, person)
            if open_for_person(items, person) >= cap:
                deferred.append({"id": item["id"], "title": item["title"], "why": [f"drafted; {person}'s review queue is at its cap of {cap}"]})
            else:
                score, why = score_item(item, items, road, hosts_idle)
                ranked.append({"id": item["id"], "title": item["title"], "lane": item.get("lane"), "score": score,
                               "class": item_class(item), "action": "ask-drafted",
                               "why": ["drafted and the review queue has room: put it to the person"] + why})
            continue
        if item["state"] != "ready":
            continue
        lane = lane_of(profile, item)
        reasons = area_clashes(profile, item, items, sid)
        draft_only = False
        if closed and item.get("lane") in closed:
            reasons.append("lane closed: needs " + ", ".join(closed[item["lane"]]))
        waiting = [b for b in item.get("blocked_by", []) if b not in done_ids]
        if waiting:
            reasons.append("blocked by " + ", ".join(waiting))
        floor = profile.get("min_value", 2)
        needed = any(o["value"] >= floor for o in live_dependents(item, items))
        if item["value"] < floor and not needed and not item.get("answered") and not item.get("owner_note"):
            reasons.append(f"value {item['value']} is under the floor {profile.get('min_value', 2)}")
        person = item.get("person")
        if item.get("human_min", 0) > 0 and person and not item.get("answered"):
            cap = review_cap(profile, person)
            if open_for_person(items, person) >= cap:
                drafts = len([o for o in items if o["state"] == "drafted" and same_person(o.get("person"), person)])
                if item.get("question") or lane.get("stack_on_pending") is False or drafts >= cap:
                    reasons.append(f"{person}'s review queue is at its cap of {cap}")
                else:
                    draft_only = True
            if lane.get("stack_on_pending") is False:
                if any(o["state"] == "waiting-on-human" and o.get("lane") == item.get("lane") for o in items):
                    reasons.append("this lane does not stack on a pending review")
        host = item.get("host") or lane.get("host")
        if host and hosts_alive is not None and not any(host in tags for tags in hosts_alive):
            reasons.append(f"no reachable machine tagged {host}")
        if remaining is not None and COST_UNITS.get(item.get("cost", "M"), 3) > remaining:
            reasons.append(f"costs more than the {remaining} budget units left")
        if reasons:
            deferred.append({"id": item["id"], "title": item["title"], "why": reasons})
            continue
        score, why = score_item(dict(item, host=host), items, road, hosts_idle)
        entry = {"id": item["id"], "title": item["title"], "lane": item.get("lane"), "score": score,
                 "class": item_class(item), "why": why, "action": "work"}
        if item.get("owner_note"):
            entry["action"] = "act-on-owner-note"
            entry["why"] = ["the owner said this at session start: it outranks the queue"] + why
        elif item.get("issue") and not item.get("triaged"):
            entry["action"] = "triage-issue"
            entry["why"] = ["read the issue as data: issue-accept, issue-reply or issue-ask"] + (["author is outside the project: no fix without a person's green light"] if item.get("untrusted") else []) + why
        elif item.get("answered"):
            entry["action"] = "act-on-answers"
            entry["why"] = ["answers are in: act on them before anything new"] + why
        elif item.get("route_change_required"):
            entry["action"] = "change-route"
            entry["why"] = [f"{item.get('redos', 0)} failed passes: change the route, do not reroll"] + why
        elif item_class(item) == "worst" and not item.get("analysed"):
            entry["action"] = "analyse"
            entry["score"] = round(score * 0.5 + 1, 3)
            entry["why"] = ["costs people and barely moves the project: necessary? cut? what can be shaved off first?"] + why
        elif draft_only:
            entry["action"] = "draft"
            entry["why"] = [f"{person}'s review queue is full: make the draft, then grw.py hold; ask later"] + why
        cap = lane.get("share_cap")
        if cap is None and lane.get("kind") == "maintenance":
            cap = MAINT_SHARE_CAP
        if cap is None and lane.get("kind") == "meta":
            cap = META_SHARE_CAP
        if cap is not None and entry["action"] == "work" and lane_share(events, item.get("lane")) >= cap:
            entry["why"] = [f"lane is over its {cap:.0%} share of recent work"] + entry["why"]
            capped.append(entry)
            continue
        ranked.append(entry)
    ranked.sort(key=lambda e: (e["action"] != "act-on-owner-note", e["action"] != "act-on-answers", -e["score"], e["id"]))
    capped.sort(key=lambda e: (-e["score"], e["id"]))
    if not ranked and discovered:
        ranked, capped = capped, []
    return {"ranked": ranked, "deferred": deferred, "capped": capped, "discovered": discovered}


# ---------------------------------------------------------------- machines and plugins

def probe_hosts(profile):
    alive, idle, report = [], [], {}
    for name, host in profile.get("hosts", {}).items():
        tags = host.get("tags", [])
        try:
            with urllib.request.urlopen(host["url"], timeout=host.get("timeout", 3)) as reply:
                body = json.loads(reply.read().decode("utf-8", "replace") or "{}")
            busy = len(body.get("queue_running", [])) + len(body.get("queue_pending", []))
            alive.append(tags)
            if not busy:
                idle.append(tags)
            report[name] = {"up": True, "queued": busy, "tags": tags}
        except Exception as exc:
            report[name] = {"up": False, "error": str(exc)[:80], "tags": tags}
    return alive, idle, report


def hosts_for(args, profile):
    if getattr(args, "hosts_json", None):
        data = json.loads(args.hosts_json)
        return data.get("alive", []), data.get("idle", []), data.get("report", {})
    if getattr(args, "no_probe", False) or not profile.get("hosts"):
        return None, [], {}
    return probe_hosts(profile)


def skill_roots():
    env = os.environ.get("GRINDWRIGHT_PLUGIN_DIRS")
    if env:
        return [Path(p) for p in env.split(os.pathsep) if p]
    home = Path.home()
    here = Path(__file__).resolve()
    roots = [home / ".claude" / "skills", home / ".agents" / "skills", home / ".claude" / "plugins" / "cache",
             home / ".codex" / "skills", home / ".copilot" / "skills"]
    for parent in here.parents:
        if parent.name in ("cache", "marketplaces"):
            roots.append(parent)
    if len(here.parents) > 4:
        roots.append(here.parents[4])
    return roots


def find_skill(name):
    """Find a plugin or skill by name: a folder with that name holding a SKILL.md or skills/."""
    for root in skill_roots():
        if not root.is_dir():
            continue
        # The plugin cache nests <marketplace>/<plugin>/<version>, so look one level under the name as well.
        for candidate in [root / name] + list(root.glob(f"*/{name}")) + list(root.glob(f"*/{name}/*")):
            if (candidate / "SKILL.md").exists() or (candidate / "skills").is_dir():
                return str(candidate)
    return None


def find_ask():
    env = os.environ.get("GRINDWRIGHT_ASK")
    if env:
        return env
    found = find_skill("askwright")
    if not found:
        return None
    for path in Path(found).rglob("ask.py"):
        return str(path)
    return None


def still_being_answered(item, status, answered):
    """A part-answered set with no done mark waits until its answers have stopped changing for a while."""
    if not status.get("unanswered") or status.get("done"):
        return False
    seen = item.get("answers_seen") or {}
    if seen.get("count") != len(answered):
        item["answers_seen"] = {"count": len(answered), "ts": stamp()}
        return True
    return parse_time(seen["ts"]) + dt.timedelta(minutes=ANSWER_QUIET_MINUTES) > now()


def ask_call(ask, *argv):
    done = subprocess.run([sys.executable, ask, *argv], capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(done.stdout)
    except ValueError:
        return {"ok": False, "error": (done.stderr or done.stdout)[:300]}


def need_met(need):
    if isinstance(need, (list, tuple)):
        return any(find_skill(n) for n in need)
    return bool(find_skill(need))


def closed_lanes(profile):
    closed = {}
    for name, lane in profile.get("lanes", {}).items():
        needs = lane.get("needs")
        if needs is None:
            needs = LANE_DEFAULTS.get(lane.get("kind"), [])
        missing = [" or ".join(n) if isinstance(n, (list, tuple)) else n for n in needs if not need_met(n)]
        if missing:
            closed[name] = missing
    return closed


# ---------------------------------------------------------------- gates

def question_failures(set_dir):
    """A question with no real guess is never sent to a person."""
    data = read_json(Path(set_dir) / "questions.json", None)
    if data is None:
        return [f"no questions.json in {set_dir}"]
    failures = []
    for q in data.get("questions", []):
        if q.get("closed") or q.get("withdrawn"):
            continue
        guess = q.get("guess") or {}
        reason = str(guess.get("why", "")) if isinstance(guess, dict) else str(guess)
        chosen = next((guess[k] for k in ("option", "options", "value", "text", "order") if guess.get(k)), None) if isinstance(guess, dict) else guess
        if not chosen or not reason.strip() or PLACEHOLDER_GUESS.search(reason):
            failures.append(f"{q.get('id')}: no real guess")
    return failures


def derived_failures(item):
    """After a redo every derived review artifact must be rebuilt, then looked at."""
    failures = []
    looked = item.get("looked", {})
    for entry in item.get("derived", []):
        path = Path(entry["path"])
        if not path.exists():
            failures.append(f"{path}: missing")
            continue
        built = path.stat().st_mtime
        for source in entry.get("from", []):
            src = Path(source)
            if src.exists() and src.stat().st_mtime > built:
                failures.append(f"{path}: older than {source}; rebuild it")
        seen = looked.get(entry["path"])
        if seen is None or seen < built:
            failures.append(f"{path}: not looked at since it was built")
    return failures


def guard_answer(profile, action, target=None):
    if action in OUTWARD:
        return False, "outward-facing: draft it and hand it to a person, whatever the profile says"
    if action == "touch":
        tasks = profile.get("work", {}).get("tasks", {}).get("path")
        for pattern in list(profile.get("read_only_paths", [])) + ([tasks] if tasks else []):
            if target and Path(target).as_posix().endswith(pattern):
                return False, f"{pattern} is read-only in this project"
        return True, "not a protected path"
    rule = str(profile.get("guards", {}).get(action, "deny: not set in the profile"))
    if rule.startswith("allow"):
        return True, rule
    return False, rule


def text_ban_hits(profile, text):
    hits = []
    for ban in profile.get("text_bans", []):
        if re.search(r"\b" + re.escape(ban) + r"\b", text, re.I):
            hits.append(ban)
    return hits


# ---------------------------------------------------------------- commands

def cmd_init(store, args):
    if store.profile_path.exists() and not args.force:
        raise SystemExit(f"{store.profile_path} exists")
    profile = json.loads(json.dumps(DEFAULT_PROFILE))
    profile["project"] = args.project
    profile["repo"] = args.repo
    write_atomic(store.profile_path, json.dumps(profile, indent=1) + "\n")
    write_atomic(store.road_path, json.dumps({"finished_means": "", "milestones": [], "confirmed": False}, indent=1) + "\n")
    store.ledger_path.touch()
    return {"state": str(store.root), "next": "fill profile.json and road.json (references/profile.md)"}


def cmd_add(store, args):
    if args.question and not args.guess:
        raise Refused(["a question needs a real guess (--guess)"])
    if args.guess and PLACEHOLDER_GUESS.search(args.guess):
        raise Refused(["that guess is a placeholder"])
    lanes = store.profile().get("lanes", {})
    if lanes and args.lane not in lanes:
        raise Refused([f"lane {args.lane} is not open on this project; open lanes: {', '.join(sorted(lanes))}"])
    items = store.items()
    same = [i["id"] for i in items if i["state"] not in ("dropped", "done") and grw_work.similar(i["title"], args.title)]
    if same and not getattr(args, "not_duplicate", "log"):
        raise Refused(["looks like " + ", ".join(same) + ": another session may have added it; --not-duplicate says why not"], duplicates=same)
    seed = f"{args.title}|{stamp()}|{len(items)}"
    item = {
        "id": "g" + hashlib.sha1(seed.encode()).hexdigest()[:6],
        "title": args.title, "lane": args.lane, "goal": args.goal or args.title, "source": args.source,
        "value": args.value, "human_min": args.human_min, "cost": args.cost, "state": "ready",
        "created": stamp(), "updated": stamp(),
    }
    optional = {"confidence": args.confidence, "road": args.road, "person": args.person, "host": args.host, "question": args.question, "guess": args.guess}
    item.update({k: v for k, v in optional.items() if v})
    if args.blocked_by:
        unknown = [b for b in args.blocked_by if b not in {o["id"] for o in items}]
        if unknown:
            raise Refused([f"--blocked-by {', '.join(unknown)}: no such item; a milestone or outside gate needs its own item (wait-human on it)"])
        item["blocked_by"] = args.blocked_by
    if getattr(args, "area", None):
        item["areas"] = args.area
    if args.owner_note:
        item["owner_note"] = True
    items.append(item)
    store.save_items(items)
    store.event("add", id=item["id"], lane=args.lane, source=args.source)
    return {"id": item["id"], "class": item_class(item)}


def cmd_set(store, args):
    items = store.items()
    item = find_item(items, args.id)
    for pair in args.field:
        key, _, raw = pair.partition("=")
        if key in ("state",) and raw not in STATES:
            raise SystemExit(f"bad state {raw}")
        try:
            item[key] = json.loads(raw)
        except ValueError:
            item[key] = raw
    touch(item)
    store.save_items(items)
    return {"id": item["id"]}


def cmd_show(store, args):
    for item in store.items():
        if item["id"] == args.id:
            return {"item": item}
    return {"ok": False, "error": f"no item {args.id}"}


def cmd_list(store, args):
    items = store.items()
    if args.only:
        items = [i for i in items if i["state"] == args.only]
    return {"items": items}


def ranking(store, args):
    profile, road, items = store.profile(), store.road(), store.items()
    alive, idle, report = hosts_for(args, profile)
    result = select(profile, road, items, store.events(), store.session(), alive, idle, closed_lanes(profile), sid=store.sid)
    result["hosts"] = report
    result["free_gpu_hosts"] = [n for n, r in report.items() if r.get("up") and not r.get("queued")]
    return result


def cmd_rank(store, args):
    return ranking(store, args)


def cmd_next(store, args):
    result = ranking(store, args)
    if result["ranked"]:
        top = result["ranked"][0]
        answer = {"next": top, "alternatives": result["ranked"][1:4], "deferred": len(result["deferred"]),
                  "free_gpu_hosts": result["free_gpu_hosts"]}
        answer.update(crew_view(store))
        if not store.road().get("confirmed"):
            answer["road_warning"] = "road not confirmed: put it to the owner; until then only work every road includes (bugs, failing tests)"
        elif getattr(args, "claim", False) and top.get("action") in ("work", "draft"):
            answer["claimed"] = cmd_claim(store, argparse.Namespace(id=top["id"], new_route=None))
        elif getattr(args, "claim", False) and store.sid != SOLO:
            hold_for_session(store, top["id"])
        return answer
    lanes = store.profile().get("discover", [])
    if not result["discovered"] and lanes:
        return {"next": {"action": "discover", "why": ["nothing selectable: run grw.py discover, then work through look_at (" + ", ".join(lanes) + ")"],
                         "look_at": lanes}, "deferred": result["deferred"]}
    return {"next": {"action": "stop", "why": ["nothing selectable after a discovery pass; do not invent work"]},
            "deferred": result["deferred"]}


def hold_for_session(store, item_id):
    """Actions that are not claims (answers, triage, analysis) still must not run twice at once."""
    items = store.items()
    item = find_item(items, item_id)
    item["handling"] = {"session": store.sid, "until": (now() + dt.timedelta(hours=HANDLING_HOURS)).isoformat(timespec="seconds")}
    store.save_items(items)


def crew_view(store):
    """What other sessions are doing and said. Empty for a lone session, so it costs nothing there."""
    items, started = store.items(), store.session().get("started", "")
    others = [{"session": owner_of(i), "id": i["id"], "title": i["title"][:80], "areas": item_areas(store.profile(), i), "branch": i.get("branch")}
              for i in items if i["state"] == "running" and owner_of(i) != store.sid]
    events = [e for e in store.events() if e.get("session") != store.sid and e.get("ts", "") >= started and e.get("session")]
    notes = [{"from": e["session"], "text": e.get("text"), "area": e.get("area")} for e in events if e["type"] == "note"][-5:]
    done = [e.get("id") for e in events if e["type"] == "done"][-5:]
    view = {}
    if others:
        view["others_working"] = others
    if notes:
        view["notes_from_others"] = notes
    if done:
        view["done_by_others"] = done
    return view


def waiting_report(store):
    """Every decision only a person can make, most unblocking first. This is what a stalled run tells the owner."""
    items = store.items()
    rows = [{"person": i.get("person") or "anyone", "id": i["id"], "title": i["title"][:100], "waits_for": i.get("waits_for") or i.get("why"),
             "where": i.get("pr_url") or i.get("ticket") or i.get("source") if (i.get("pr") or i.get("issue")) else i.get("set"),
             "unblocks": len(live_dependents(i, items))} for i in items if i["state"] == "waiting-on-human"]
    return sorted(rows, key=lambda r: (-r["unblocks"], r["person"], r["id"]))


def write_board(store):
    """BOARD.md and WAITING.md are generated for people. Agents get the same facts from next and board."""
    items, profile = store.items(), store.profile()
    lines = ["# Board (generated, do not edit)", "", f"Project: {profile.get('project')}. Updated {stamp()}.", "", "## Working now", ""]
    running = [i for i in items if i["state"] == "running"]
    lines += [f"- {owner_of(i)}: {i['id']} {i['title']} [{', '.join(item_areas(profile, i)) or 'no area'}]" + (f" on {i['branch']}" if i.get("branch") else "") for i in running] or ["- nobody"]
    lines += ["", "## Notes", ""]
    notes = [e for e in store.events() if e.get("type") == "note"][-15:]
    lines += [f"- {e['ts']} {e.get('session', SOLO)}" + (f" [{e['area']}]" if e.get("area") else "") + f": {e.get('text')}" for e in notes] or ["- none"]
    write_atomic(store.root / "BOARD.md", "\n".join(lines) + "\n")
    waits = waiting_report(store)
    text = ["# Waiting on a person (generated)", ""] + [f"- {r['person']}: {r['title']} ({r['id']}), {r['waits_for']}, {r['where'] or 'no link'}; unblocks {r['unblocks']}" for r in waits]
    write_atomic(store.root / "WAITING.md", "\n".join(text or []) + "\n")


def cmd_board(store, args):
    return dict(crew_view(store), waiting_on=waiting_report(store), file=str(store.root / "BOARD.md"))


def cmd_note(store, args):
    store.event("note", text=args.text, area=args.area)
    return {"noted": True}


def cmd_claim(store, args):
    items = store.items()
    item = find_item(items, args.id)
    if item["state"] != "ready":
        raise Refused([f"{item['id']} is {item['state']}"])
    blockers = unfinished_blockers(item, items)
    if blockers:
        raise Refused([f"{item['id']} is blocked by {', '.join(blockers)}"])
    if item_class(item) == "worst" and not item.get("analysed"):
        raise Refused(["analyse this item first: necessary, cut, or shave a part off"])
    clashes = area_clashes(store.profile(), dict(item, areas=list(item.get("areas", [])) + list(getattr(args, "area", None) or [])), items, store.sid)
    if clashes:
        raise Refused(clashes + ["take other work, or wait"])
    if item.get("issue") and not item.get("triaged"):
        raise Refused(["triage first: issue-accept, issue-reply or issue-ask"])
    if item.get("paused_by") and item["paused_by"] != store.sid and not getattr(args, "take_over", False):
        raise Refused([f"paused by {item['paused_by']}, whose work is on its own branch: take other work, or claim --take-over and start from that branch"])
    if item.get("route_change_required") and not args.new_route:
        raise Refused([f"{item.get('redos')} failed passes on this route: name a new route with --new-route"])
    item["state"] = "running"
    item["session"] = store.sid
    item.pop("paused_by", None)
    item.pop("handling", None)
    if getattr(args, "area", None):
        item["areas"] = sorted(set(item.get("areas", [])) | set(args.area))
    if getattr(args, "branch", None):
        item["branch"] = args.branch
    item["lease_until"] = (now() + dt.timedelta(hours=LEASE_HOURS)).isoformat(timespec="seconds")
    if args.new_route:
        item["route"] = args.new_route
        item["route_change_required"] = False
    touch(item)
    store.save_items(items)
    session = store.session()
    if session.get("budget"):
        session["used"] = session.get("used", 0) + COST_UNITS.get(item.get("cost", "M"), 3)
        store.save_session(session)
    store.event("claim", id=item["id"], lane=item.get("lane"))
    return {"id": item["id"], "lease_until": item["lease_until"]}


def cmd_checkpoint(store, args):
    items = store.items()
    item = find_item(items, args.id)
    item.setdefault("checkpoints", []).append({"ts": stamp(), "note": args.note})
    if item["state"] == "running":
        item["lease_until"] = (now() + dt.timedelta(hours=LEASE_HOURS)).isoformat(timespec="seconds")
    touch(item)
    store.save_items(items)
    return {"id": item["id"], "checkpoints": len(item["checkpoints"])}


def cmd_analyse(store, args):
    items = store.items()
    item = find_item(items, args.id)
    item["analysed"] = {"ts": stamp(), "verdict": args.verdict, "note": args.note}
    created = None
    if args.verdict == "cut":
        item["state"] = "dropped"
        item["drop_why"] = args.note
    if args.verdict == "shave":
        if not args.shave_title:
            raise Refused(["name the part that can be done first (--shave-title)"])
        seed = f"{args.shave_title}|{stamp()}"
        created = "g" + hashlib.sha1(seed.encode()).hexdigest()[:6]
        items.append({"id": created, "title": args.shave_title, "lane": item.get("lane"), "goal": args.shave_title,
                      "source": f"shaved off {item['id']}", "value": max(item["value"], args.shave_value),
                      "human_min": args.shave_human_min, "cost": "S", "state": "ready", "road": item.get("road"),
                      "created": stamp(), "updated": stamp(), "person": item.get("person")})
        item["blocked_by"] = list(item.get("blocked_by", [])) + [created]
        release_blocked(items)
    touch(item)
    store.save_items(items)
    store.event("analyse", id=item["id"], verdict=args.verdict, lane=item.get("lane"))
    return {"id": item["id"], "verdict": args.verdict, "created": created}


def cmd_derived(store, args):
    items = store.items()
    item = find_item(items, args.id)
    item.setdefault("derived", [])
    item["derived"] = [e for e in item["derived"] if e["path"] != args.path]
    item["derived"].append({"path": args.path, "from": args.source})
    touch(item)
    store.save_items(items)
    return {"id": item["id"], "derived": len(item["derived"])}


def cmd_look(store, args):
    items = store.items()
    item = find_item(items, args.id)
    if not Path(args.path).exists():
        raise SystemExit(f"{args.path} does not exist")
    item.setdefault("looked", {})[args.path] = time.time()
    touch(item)
    store.save_items(items)
    return {"id": item["id"], "looked_at": args.path}


def eval_isolation_failures(profile):
    """An eval's question sets must not reach the owner's real inbox."""
    if profile.get("eval") and not os.environ.get("ASKWRIGHT_HOME"):
        return ["this is an eval fixture: set ASKWRIGHT_HOME to a throwaway folder on every command, "
                "or its question sets land in the owner's real inbox"]
    return []


def cmd_wait_human(store, args):
    profile = store.profile()
    items = store.items()
    item = find_item(items, args.id)
    person = args.person or item.get("person")
    if not person:
        raise Refused(["say who answers this (--person)"])
    failures = eval_isolation_failures(profile) + list(derived_failures(item))
    others = [i["id"] for i in items if i.get("answered") and i["id"] != item["id"]]
    if others:
        failures.append("act on the answers already in first: " + ", ".join(others))
    if item.get("answered"):
        failures.append("record what you did with this item's answers first (grw.py resolve)")
    cap = review_cap(profile, person)
    already = item.get("set") and item["state"] == "waiting-on-human"
    if not already and open_for_person(items, person) >= cap:
        failures.append(f"{person}'s review queue is at its cap of {cap}: do different work")
    minimum = lane_of(profile, item).get("batch_min", {})
    minimum = minimum.get(person, 0) if isinstance(minimum, dict) else minimum
    if args.set:
        failures += question_failures(args.set)
        data = read_json(Path(args.set) / "questions.json", {})
        count = len([q for q in data.get("questions", []) if not q.get("closed")])
        if count > MAX_SET_QUESTIONS:
            failures.append(f"{count} open questions: split the set; long pages go unanswered (limit {MAX_SET_QUESTIONS})")
        ask = find_ask()
        if ask:
            lint = ask_call(ask, "lint", args.set)
            if lint.get("ok") is False:
                failures.append("askwright lint failed: " + str(lint.get("errors") or lint.get("error"))[:200])
    else:
        count = 1
        if not args.why and not args.pr:
            failures.append("no askwright set: give --pr or --why (for a PR or a chat question)")
    if args.batch is not None and args.batch < minimum and not args.tail:
        failures.append(f"batch of {args.batch} is under {person}'s minimum of {minimum}")
    if failures:
        raise Refused(failures)
    item.update({"state": "waiting-on-human", "person": person, "waits_for": args.why or (f"review of PR {args.pr}" if args.pr else "answers on the askwright set")})
    if args.set:
        item["set"] = str(args.set)
        item.pop("guess", None)  # the page holds the guess now; a second copy drifted from it
    if args.pr:
        item["pr"] = args.pr
    item.pop("lease_until", None)
    touch(item)
    store.save_items(items)
    store.event("asked", id=item["id"], lane=item.get("lane"), person=person, questions=count)
    if args.set and ask:
        ask_call(ask, "register", str(args.set))  # a set not on the shared inbox never reaches the person
    return {"id": item["id"], "person": person, "questions": count,
            "reminder": "one inbox link per message; now select other work"}


def cmd_wait_machine(store, args):
    items = store.items()
    item = find_item(items, args.id)
    item.update({"state": "waiting-on-machine", "done_file": args.done_file, "waits_for": args.why})
    item.pop("lease_until", None)
    touch(item)
    store.save_items(items)
    store.event("detached", id=item["id"], lane=item.get("lane"))
    return {"id": item["id"], "reminder": "render is detached; select other work"}


def pr_state(number, repo=None):
    """MERGED, CLOSED or OPEN from gh; None when gh cannot tell, which leaves the item waiting."""
    gh = shutil.which("gh")
    if not gh:
        return None
    try:
        out = subprocess.run([gh, "pr", "view", str(number), *(["-R", repo] if repo else []), "--json", "state", "--jq", ".state"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def apply_pr_state(item, state):
    """A merged PR finishes the item; a closed one sends it back. True when the item changed."""
    if state == "MERGED":
        item.update({"state": "done", "evidence": f"PR {item['pr']} merged", "oracle": "human", "finished": stamp()})
    elif state == "CLOSED":
        item["state"] = "ready"
        item.setdefault("checkpoints", []).append({"ts": stamp(), "note": f"PR {item['pr']} closed without merging: read why"})
    else:
        return False
    touch(item)
    return True


def cmd_sync(store, args):
    """Bring answers, finished renders and expired leases back into the ledger."""
    items = store.items()
    ask = find_ask()
    report = {"answers": [], "machines": [], "recovered": [], "pr": [], "still_waiting": [], "closed_sets": [], "released": release_blocked(items)}
    for item in items:
        if item["state"] == "waiting-on-human" and item.get("set"):
            if not ask:
                report["still_waiting"].append({"id": item["id"], "why": "askwright not found"})
                continue
            status = ask_call(ask, "status", item["set"])
            answered = set(status.get("answered", []))
            new = sorted(answered - set(item.get("acted", [])))
            if new and still_being_answered(item, status, answered):
                touch(item)
                report["still_waiting"].append({"id": item["id"], "person": item.get("person"), "set": item["set"], "why": "still being answered: acting now would split the work"})
            elif new:
                item.pop("answers_seen", None)
                item.update({"state": "ready", "answered": new, "still_open": status.get("open", 0) - len(answered)})
                touch(item)
                report["answers"].append({"id": item["id"], "new": len(new), "set": item["set"]})
            elif status.get("open", 1) == 0:
                # Everything on the page was answered and closed: nobody is left to wait for, and it fills the review queue.
                item["state"] = "ready"
                item.setdefault("checkpoints", []).append({"ts": stamp(), "note": f"set {item.pop('set')} is fully closed: finish or drop this item"})
                touch(item)
                report["closed_sets"].append(item["id"])
            else:
                report["still_waiting"].append({"id": item["id"], "person": item.get("person"), "set": item["set"], "unsure": status.get("unsure", [])})
        elif item["state"] == "waiting-on-human" and item.get("pr") and apply_pr_state(item, pr_state(item["pr"], item["pr_repo"]) if item.get("pr_repo") else pr_state(item["pr"])):
            report["pr"].append({"id": item["id"], "pr": item["pr"], "state": item["state"]})
        elif item["state"] == "waiting-on-human":
            report["still_waiting"].append({"id": item["id"], "person": item.get("person"), "why": item.get("waits_for")})
        elif item["state"] == "waiting-on-machine":
            if item.get("done_file") and Path(item["done_file"]).exists():
                item["state"] = "ready"
                item["machine_done"] = True
                touch(item)
                report["machines"].append(item["id"])
            else:
                report["still_waiting"].append({"id": item["id"], "why": item.get("waits_for")})
        elif item["state"] == "running" and parse_time(item.get("lease_until", stamp())) <= now():
            item["state"] = "ready"
            item.setdefault("checkpoints", []).append({"ts": stamp(), "note": "lease expired: a session died mid-work; inspect the partial work"})
            item.pop("lease_until", None)
            touch(item)
            report["recovered"].append(item["id"])
    try:
        report["issues"] = grw_work.issue_sync(store, items)
    except Refused as failed:  # an outage on GitHub must not stop the other lanes
        report["issues"] = {"error": failed.reasons}
    store.save_items(items)
    store.event("sync", answers=len(report["answers"]), machines=len(report["machines"]), recovered=len(report["recovered"]))
    return report


def cmd_relay(store, args):
    """A person's feedback that arrived some other way (relayed in chat, on a PR). It counts as an answer."""
    items = store.items()
    item = find_item(items, args.id)
    item.update({"state": "ready", "answered": sorted(set(item.get("answered", [])) | {"relay:" + stamp()}), "still_open": 0})
    item.setdefault("relayed", []).append({"ts": stamp(), "from": args.person, "note": args.note})
    touch(item)
    store.save_items(items)
    store.event("relayed", id=item["id"], lane=item.get("lane"), person=args.person)
    return {"id": item["id"], "state": "ready", "next": "act on it, then grw.py resolve"}


def cmd_resolve(store, args):
    """Record what became of a batch of answers. Each answer yields a rule or a stated reason not to."""
    if not args.rule and not args.no_rule:
        raise Refused(["turn the answer into a rule (--rule) or say why it is a one-off (--no-rule)"])
    items = store.items()
    item = find_item(items, args.id)
    acted = sorted(set(item.get("acted", [])) | set(item.get("answered", [])))
    item["acted"] = acted
    item.pop("answered", None)
    item.pop("owner_note", None)
    if item.get("still_open", 0) > 0 and item.get("set"):
        item["state"] = "waiting-on-human"
    touch(item)
    store.save_items(items)
    for text in args.rule or []:
        with open(store.rules_path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"ts": stamp(), "from": item["id"], "lane": item.get("lane"), "person": item.get("person"), "rule": text}, ensure_ascii=False) + "\n")
    store.event("resolved", id=item["id"], lane=item.get("lane"), person=item.get("person"), accepted=args.accepted,
                rejected=args.rejected, rules=len(args.rule or []))
    return {"id": item["id"], "state": item["state"], "rules": len(args.rule or [])}


def cmd_redo(store, args):
    profile = store.profile()
    items = store.items()
    item = find_item(items, args.id)
    item["redos"] = item.get("redos", 0) + 1
    item.setdefault("redo_notes", []).append(args.note)
    limit = profile.get("escalate_after", 2)
    escalate = item["redos"] >= limit
    if escalate:
        item["route_change_required"] = True
    item["state"] = "ready"
    item.pop("lease_until", None)
    touch(item)
    store.save_items(items)
    store.event("redo", id=item["id"], lane=item.get("lane"), note=args.note)
    return {"id": item["id"], "redos": item["redos"], "route_change_required": escalate,
            "reminder": "rebuild every derived review artifact before asking again"}


def cmd_done(store, args):
    items = store.items()
    item = find_item(items, args.id)
    kind = lane_of(store.profile(), item).get("kind")
    if kind in ASSET_KINDS and not args.provenance:
        raise Refused(["generated assets need --provenance (tool, model, seed or source) for store disclosure"])
    item.update({"state": "done", "evidence": args.evidence, "oracle": args.oracle, "finished": stamp()})
    if args.provenance:
        item["provenance"] = args.provenance
    item.pop("lease_until", None)
    touch(item)
    store.save_items(items)
    store.event("done", id=item["id"], lane=item.get("lane"), evidence=args.evidence, oracle=args.oracle)
    return {"id": item["id"], "state": "done", "human_proven": args.oracle == "human"}


def cmd_hold(store, args):
    items = store.items()
    item = find_item(items, args.id)
    if item["state"] == "drafted":  # already held: keep the newer evidence, nothing else changes
        item["evidence"] = args.evidence
        touch(item)
        store.save_items(items)
        return {"id": item["id"], "state": "drafted", "note": "already drafted; evidence updated"}
    if item["state"] not in ("running", "ready"):
        raise Refused([f"{item['id']} is {item['state']}: only a ready, running or drafted item can be held"])
    if item["state"] == "running" and owner_of(item) != store.sid:
        raise Refused([f"{item['id']} is running in {owner_of(item)}"])
    person = args.person or item.get("person")
    if not person:
        raise Refused(["say who reviews this (--person)"])
    item.update({"state": "drafted", "evidence": args.evidence, "person": person})
    if args.provenance:
        item["provenance"] = args.provenance
    item.pop("lease_until", None)
    touch(item)
    store.save_items(items)
    store.event("drafted", id=item["id"], lane=item.get("lane"), evidence=args.evidence)
    return {"id": item["id"], "state": "drafted", "reminder": "next offers ask-drafted when the review queue has room"}


def cmd_log(store, args):
    """Record work already finished: add plus done in one call."""
    if lane_of(store.profile(), {"lane": args.lane}).get("kind") in ASSET_KINDS and not args.provenance:
        raise Refused(["generated assets need --provenance (tool, model, seed or source) for store disclosure"])
    fields = dict(title=args.title, lane=args.lane, source=args.source, value=args.value, road=args.road, goal=None,
                  human_min=0, cost="S", confidence=None, person=None, host=None, question=None, guess=None,
                  blocked_by=None, owner_note=False)
    added = cmd_add(store, argparse.Namespace(**fields))
    return cmd_done(store, argparse.Namespace(id=added["id"], evidence=args.evidence, oracle=args.oracle, provenance=args.provenance))


def cmd_reject(store, args):
    store.event("rejected", finding=args.finding, source=args.source, why=args.why)
    return {"rejected": args.finding, "reminder": "discover lists it from now on, so nobody weighs it again"}


def cmd_drop(store, args):
    items = store.items()
    item = find_item(items, args.id)
    item.update({"state": "dropped", "drop_why": args.why})
    touch(item)
    store.save_items(items)
    store.event("dropped", id=item["id"], lane=item.get("lane"), why=args.why)
    return {"id": item["id"], "state": "dropped"}


def cmd_queue(store, args):
    profile, items = store.profile(), store.items()
    people = {}
    for name, person in profile.get("people", {}).items():
        waiting = [i for i in items if i["state"] == "waiting-on-human" and i.get("person") == name]
        people[name] = {"open": open_for_person(items, name), "cap": person.get("review_cap", 3),
                        "minutes": sum(i.get("human_min", 0) for i in waiting),
                        "items": [{"id": i["id"], "title": i["title"], "set": i.get("set"), "pr": i.get("pr")} for i in waiting]}
    questions = [i for i in items if i.get("question") and i["state"] not in ("done", "dropped") and i["state"] != "waiting-on-human"]
    road = store.road()
    questions.sort(key=lambda q: -sum(base_value(o, road) for o in items if q["id"] in o.get("blocked_by", [])) - base_value(q, road))
    return {"people": people, "proposed_questions": [
        {"id": q["id"], "question": q["question"], "guess": q.get("guess"), "person": q.get("person"),
         "unblocks": [o["id"] for o in items if q["id"] in o.get("blocked_by", [])]} for q in questions]}


def cmd_guard(store, args):
    allowed, why = guard_answer(store.profile(), args.action, args.target)
    if allowed:
        return {"allowed": True, "why": why}
    raise Refused([why], allowed=False)


def cmd_lint_text(store, args):
    text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    hits = text_ban_hits(store.profile(), text)
    if hits:
        raise Refused([f"text names a banned term: {h}" for h in hits], hits=hits)
    return {"clean": True}


def cmd_doctor(store, args):
    profile = store.profile()
    _, _, report = hosts_for(args, profile)
    closed = closed_lanes(profile)
    plugins = ["askwright", "artwright", "pixelwright", "musicwright", "sfxwright", "cinewright", "voicewright", "everwrite", "editwright", "game-juice", "polywright",
               "ludowright", "marketwright", "comfyui-gen", "unity-agent", "roblox-agent", "tokenwright", "everlast", "evergreen"]
    return {"plugins": {p: bool(find_skill(p)) for p in plugins}, "ask_py": find_ask(), "hosts": report,
            "closed_lanes": closed, "open_lanes": sorted(set(profile.get("lanes", {})) - set(closed)),
            "conflicts": profile_conflicts(profile),
            "repo_found": project_repo(store, profile.get("repo", ".")).exists()}


def profile_conflicts(profile):
    """Settings that contradict each other, so a session does not find out mid-batch."""
    out = []
    guard = str(profile.get("guards", {}).get("stack_on_pending", "deny"))
    if not guard.startswith("allow"):
        for name, lane in profile.get("lanes", {}).items():
            if lane.get("stack_on_pending") is True:
                out.append(f"lane {name} sets stack_on_pending true but guards.stack_on_pending says '{guard}': "
                           "the guard wins and work goes from main; change one")
    return out


def project_repo(store, repo):
    """A relative repo means relative to the project holding ai-docs/grind, not to wherever the shell is."""
    path = Path(repo)
    state = Path(store.root).resolve()
    if path.is_absolute() or state.parent.name != "ai-docs":
        return path
    return state.parent.parent / path


SKIP_DIRS = {".git", "node_modules", "Library", "Temp", "Logs", "obj", "bin", "Builds", "__pycache__", ".venv", "venv"}
SOURCE_SUFFIXES = (".cs", ".py", ".lua", ".gd", ".ts", ".js")
MARKER = re.compile(r"\b(?:TODO|FIXME|HACK)\b")


def gap_lane(profile):
    """Gap findings need an open lane: `log` and `add` refuse any other."""
    lanes = profile.get("lanes", {})
    if not lanes:
        return "features"
    for name in ("features", "bugs", "gaps"):
        if name in lanes:
            return name
    for kind in ("code", "maintenance"):
        for name, lane in lanes.items():
            if lane.get("kind") == kind:
                return name
    return sorted(lanes)[0]


def scan_repo(repo, limit=5000):
    """One pruned walk: rglob through an engine's cache folders took minutes."""
    markers, sources, sample, marketing = 0, 0, [], []
    for folder, dirs, files in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in dirs + files:
            if "marketing" in name.lower() and len(marketing) < 5:
                marketing.append(str(Path(folder) / name))
        for name in sorted(files):
            if sources >= limit or not name.endswith(SOURCE_SUFFIXES):
                continue
            sources += 1
            path = Path(folder) / name
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, 1):
                if MARKER.search(line):
                    markers += 1
                    if len(sample) < 15:
                        sample.append(f"{path.relative_to(repo).as_posix()}:{number}: {line.strip()[:80]}")
    return {"code_markers": markers, "files_scanned": sources, "sample": sample}, marketing


def cmd_discover(store, args):
    """Read-only signals of unfinished work. The agent reads them and adds items with a real source."""
    profile = store.profile()
    repo = project_repo(store, args.repo or profile.get("repo", "."))
    signals = []
    if not repo.is_dir():
        raise SystemExit(f"repo {repo} not found")
    gaps = gap_lane(profile)
    finished = " ".join(" ".join(str(i.get(k, "")) for k in ("title", "source", "goal", "evidence"))
                        for i in store.items() if i["state"] in ("done", "dropped"))
    for name, lane in (("juice-report.md", "juice"), ("PROJECT_REVIEW.md", gaps)):
        for path in list(repo.glob(name)) + list(repo.glob(f"ai-docs/{name}")):
            text = path.read_text(encoding="utf-8", errors="replace")
            marks = re.findall(r"^#+ (S-\d+[^\n]*)", text, re.M)
            left = [m for m in marks if not re.search(re.escape(m.split()[0]) + r"\b", finished)]
            if marks and not left:
                continue  # every suggestion is already in the ledger
            signals.append({"lane": lane, "file": str(path), "count": len(left) or None, "sample": left[:3]})
    for rel in ("Docs/Agent Todos.md", "TODO.md", "ai-docs/TODO.md"):
        path = repo / rel
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            signals.append({"lane": gaps, "file": str(path), "open_items": len(re.findall(r"^\s*[-*] (?:\[ \] )?", text, re.M))})
    tests = [p for p in ("Tests", "tests", "test") if (repo / p).is_dir()]
    test_lane = next((n for n, l in profile.get("lanes", {}).items() if l.get("kind") == "tests"), "testing")
    signals.append({"lane": test_lane, "test_dirs": tests or None,
                    "note": "run them; none means a gap. Then look for missing kinds: unit, integration, end-to-end, snapshot, "
                            "property, regression for each fixed bug, or a new check this project needs that nobody has named"})
    scan, marketing = scan_repo(repo)
    signals.append(dict(scan, lane=gaps))
    signals.append({"lane": "marketing", "files": marketing, "note": "no plan found" if not marketing else "check its age and stats"})
    if not args.no_gh and shutil.which("gh"):
        for kind, cmd in (("pr", "pr"), ("issue", "issue")):
            try:
                done = subprocess.run(["gh", cmd, "list", "--json", "number,title", "--limit", "30"], cwd=str(repo),
                                      capture_output=True, text=True, encoding="utf-8", timeout=30)
            except subprocess.TimeoutExpired:
                continue
            if done.returncode == 0:
                rows = json.loads(done.stdout or "[]")
                signals.append({"lane": gaps, kind + "s": len(rows), "sample": [r["title"] for r in rows[:5]]})
    if not args.dry_run:
        store.event("discover", signals=len(signals))
    rejected = [{"finding": e.get("finding"), "why": e.get("why")} for e in store.events() if e.get("type") == "rejected"]
    return {"signals": signals, "rejected": rejected, "open_lanes": sorted(profile.get("lanes", {})),
            "rule": "skip what is in rejected; add an item only with a real --source; markers miss dead data, so also check that data rows have code behind them; if nothing is worth doing, say so and stop"}


def cmd_metrics(store, args):
    lanes = {}
    for event in store.events():
        lane = event.get("lane")
        if not lane:
            continue
        row = lanes.setdefault(lane, {"claims": 0, "questions": 0, "accepted": 0, "rejected": 0, "redos": 0, "rules": 0, "done": 0})
        kind = event["type"]
        if kind == "claim":
            row["claims"] += 1
        elif kind == "asked":
            row["questions"] += event.get("questions", 0)
        elif kind == "resolved":
            row["accepted"] += event.get("accepted", 0)
            row["rejected"] += event.get("rejected", 0)
            row["rules"] += event.get("rules", 0)
        elif kind == "redo":
            row["redos"] += 1
        elif kind == "done":
            row["done"] += 1
    for row in lanes.values():
        row["questions_per_accepted"] = round(row["questions"] / row["accepted"], 2) if row["accepted"] else None
    sessions = [e for e in store.events() if e["type"] == "session_end"]
    finished = [i for i in store.items() if i["state"] == "done"]
    return {"machine_done": len(finished), "human_unproven": [i["id"] for i in finished if i.get("oracle") != "human"], "lanes": lanes, "sessions": len(sessions), "nothing_made": sum(1 for s in sessions if s.get("nothing_made"))}


def cmd_session(store, args):
    session = store.session()
    if args.action == "start":
        failures = eval_isolation_failures(store.profile())
        if failures:
            raise Refused(failures)
        session = {"started": stamp(), "budget": args.budget, "used": 0}
        store.save_session(session)
        store.event("session_start", budget=args.budget)
        mine = [i["id"] for i in store.items() if i["state"] == "running" and owner_of(i) == store.sid]
        answer = dict(session, sync=cmd_sync(store, args), next=cmd_next(store, args))
        if mine:
            answer["yours_running"] = mine
        knowledge = store.profile().get("work", {}).get("knowledge")
        if knowledge:
            answer["knowledge"] = knowledge
        return answer
    if args.action in ("pause", "release"):
        items = store.items()
        for item in items:
            if item.get("handling", {}).get("session") == store.sid:
                item.pop("handling")
            if item["state"] == "running" and owner_of(item) == store.sid:
                item["state"] = "ready"
                if store.sid != SOLO:
                    item["paused_by"] = store.sid
                item.setdefault("checkpoints", []).append({"ts": stamp(), "note": f"paused: {args.reason}"})
                item.pop("lease_until", None)
                touch(item)
        store.save_items(items)
        if args.action == "release":
            store.event("released")
            return {"released": store.sid}
        session.update({"paused": args.reason, "resume_after": args.until})
        store.save_session(session)
        store.event("paused", reason=args.reason, until=args.until)
        return session
    verdict = stop_verdict(store, args)
    if args.action == "check":
        return verdict
    if not verdict["may_stop"] and not args.force:
        raise Refused(verdict["why"], **verdict)
    started = session.get("started", "")
    made = [e for e in store.events() if e.get("ts", "") >= started and e["type"] in ("done", "asked", "detached", "resolved", "redo", "drafted")]
    store.event("session_end", made=len(made), nothing_made=not made, forced=bool(args.force), reason=args.force)
    return {"ended": True, "made": len(made), "nothing_made": not made,
            "reminder": ("run evergreen-wrapup if installed (skip quietly if not), then update HANDOFF.md and print the "
                         "one-line start command; a project prompt's own end steps add to these, never replace them")}


def stop_verdict(store, args):
    """A session may stop on a usage limit, an empty budget, or nothing selectable after a discovery pass."""
    session, items = store.session(), store.items()
    if session.get("paused"):
        return {"may_stop": True, "why": [f"paused: {session['paused']}"]}
    running = [i["id"] for i in items if i["state"] == "running" and owner_of(i) == store.sid and not unfinished_blockers(i, items)]
    if running:
        return {"may_stop": False, "why": ["still running: " + ", ".join(running) + ": finish, wait or checkpoint them"]}
    result = ranking(store, args)
    if result["ranked"]:
        top = result["ranked"][0]
        return {"may_stop": False, "why": [f"{top['id']} is selectable: {top['title']}"], "next": top}
    if session.get("budget") and any("budget" in " ".join(d["why"]) for d in result["deferred"]):
        return {"may_stop": True, "why": ["what is left costs more than the budget"], "deferred": result["deferred"]}
    if not result["discovered"] and store.profile().get("discover", []):
        return {"may_stop": False, "why": ["nothing selectable and no discovery pass this session: run discover, then " + ", ".join(store.profile().get("discover", []))]}
    waits = waiting_report(store)
    why = ["nothing selectable after a discovery pass"]
    if waits:
        why.append(f"nothing can move until {len(waits)} decision(s) come from a person: see WAITING.md and say so plainly")
    return {"may_stop": True, "why": why, "deferred": result["deferred"], "waiting_on": waits}


def cmd_plan(store, args):
    """The read-only dry run: road, ranked ledger, deferred work, queue, proposed questions."""
    profile, road, items = store.profile(), store.road(), store.items()
    result = ranking(store, args)
    out = [f"# Plan: {profile.get('project')} ({stamp()[:10]})", ""]
    confirmed = "confirmed" if road.get("confirmed") else "NOT confirmed yet"
    out += [f"## Road to finished ({confirmed})", "", road.get("finished_means") or "(not written)", ""]
    for stone in road.get("milestones", []):
        out.append(f"- **{stone.get('id')}** (weight {stone.get('weight', 1)}): {stone.get('title')}. {stone.get('status', '')}")
    closed = closed_lanes(profile)
    out += ["", "## Lanes closed by a missing plugin", ""]
    out += [f"- {k}: needs {', '.join(v)}" for k, v in closed.items()] or ["- none"]
    out += ["", "## Ranked", "", "| # | score | action | class | lane | item | why |", "|---|---|---|---|---|---|---|"]
    for n, row in enumerate(result["ranked"], 1):
        out.append(f"| {n} | {row['score']} | {row['action']} | {row['class']} | {row['lane']} | {row['title']} ({row['id']}) | {'; '.join(row['why'])} |")
    if result["capped"]:
        out += ["", "## Over their share cap", ""] + [f"- {c['title']} ({c['id']})" for c in result["capped"]]
    if result["deferred"]:
        out += ["", "## Deferred, and why", ""] + [f"- {d['title']} ({d['id']}): {'; '.join(d['why'])}" for d in result["deferred"]]
    waiting = [i for i in items if i["state"].startswith("waiting")]
    if waiting:
        out += ["", "## Waiting", ""] + [f"- {i['title']} ({i['id']}): {i['state']}, {i.get('person', '')} {i.get('waits_for', '')}" for i in waiting]
    queue = cmd_queue(store, args)
    if queue["proposed_questions"]:
        out += ["", "## Proposed questions, most unblocking first", ""]
        out += [f"- {q['person'] or '?'}: {q['question']} Guess: {q['guess']}" for q in queue["proposed_questions"]]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- parser

def build_parser():
    parser = argparse.ArgumentParser(prog="grw.py", description=__doc__.split("\n")[0])
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--state", default=os.environ.get("GRINDWRIGHT_STATE", "ai-docs/grind"), help="state folder")
    parser.add_argument("--session", default=os.environ.get("GRINDWRIGHT_SESSION", SOLO), help="this session's name when several share the state")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, func, help_text=""):
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(func=func)
        return p

    def probing(p):
        p.add_argument("--no-probe", action="store_true", help="do not contact machines")
        p.add_argument("--hosts-json", help=argparse.SUPPRESS)
        return p

    p = add("init", cmd_init, "scaffold a state folder")
    p.add_argument("--project", required=True)
    p.add_argument("--repo", default=".")
    p.add_argument("--force", action="store_true")

    p = add("add", cmd_add, "add a work item; --source says where the need came from")
    p.add_argument("title")
    p.add_argument("--lane", required=True)
    p.add_argument("--source", required=True, help="file, finding or observation that shows the need")
    p.add_argument("--value", type=int, required=True, choices=range(1, 6), help="how far it moves the project to finished and polished")
    p.add_argument("--human-min", type=int, default=0, help="minutes of a person's attention it will take")
    p.add_argument("--cost", choices=list(COST_UNITS), default="M")
    p.add_argument("--confidence", choices=list(CONFIDENCE), help="how sure the value is")
    p.add_argument("--goal")
    p.add_argument("--road")
    p.add_argument("--person")
    p.add_argument("--host", help="machine tag it needs, such as gpu")
    p.add_argument("--blocked-by", action="append")
    p.add_argument("--owner-note", action="store_true", help="the owner asked for this directly; ranks first")
    p.add_argument("--area", action="append", help="path or resource:name it works in")
    p.add_argument("--not-duplicate", help="it resembles an open item, and why it is different")
    p.add_argument("--question")
    p.add_argument("--guess")

    p = add("set", cmd_set, "change fields: key=value")
    p.add_argument("id")
    p.add_argument("field", nargs="+")

    p = add("show", cmd_show)
    p.add_argument("id")
    p = add("list", cmd_list)
    p.add_argument("--only", choices=STATES)

    probing(add("rank", cmd_rank, "rank everything and say why"))
    p = probing(add("next", cmd_next, "the one thing to do next"))
    p.add_argument("--claim", action="store_true", help="also claim it when the action is work or draft")
    probing(add("plan", cmd_plan, "read-only dry run in markdown"))
    probing(add("doctor", cmd_doctor, "which plugins and machines exist, which lanes that closes"))

    p = add("claim", cmd_claim, "start an item")
    p.add_argument("id")
    p.add_argument("--area", action="append", help="path or resource:name; refused if another session holds it")
    p.add_argument("--branch")
    p.add_argument("--new-route")
    p.add_argument("--take-over", action="store_true", help="claim an item another crew session paused; start from its branch")

    p = add("checkpoint", cmd_checkpoint, "save progress on an item")
    p.add_argument("id")
    p.add_argument("note")

    p = add("analyse", cmd_analyse, "decide a worst-class item: keep, cut or shave")
    p.add_argument("id")
    p.add_argument("--verdict", required=True, choices=["keep", "cut", "shave"])
    p.add_argument("--note", required=True)
    p.add_argument("--shave-title")
    p.add_argument("--shave-value", type=int, default=2)
    p.add_argument("--shave-human-min", type=int, default=0)

    p = add("derived", cmd_derived, "declare a review artifact and what it is built from")
    p.add_argument("id")
    p.add_argument("path")
    p.add_argument("--source", action="append", default=[])

    p = add("look", cmd_look, "record that you looked at a built artifact")
    p.add_argument("id")
    p.add_argument("path")

    p = add("wait-human", cmd_wait_human, "hand to a person; runs the gates")
    p.add_argument("id")
    p.add_argument("--set")
    p.add_argument("--person")
    p.add_argument("--why")
    p.add_argument("--pr")
    p.add_argument("--batch", type=int)
    p.add_argument("--tail", action="store_true", help="fewer than the batch minimum are left in the whole lane")

    p = add("wait-machine", cmd_wait_machine, "a detached render is running")
    p.add_argument("id")
    p.add_argument("--done-file", required=True, help="file that appears when the job ends")
    p.add_argument("--why", required=True)

    add("sync", cmd_sync, "pull in answers, finished renders, expired leases")

    p = add("relay", cmd_relay, "record feedback that came by another route")
    p.add_argument("id")
    p.add_argument("--person", required=True)
    p.add_argument("--note", required=True)

    p = add("resolve", cmd_resolve, "record what the answers became")
    p.add_argument("id")
    p.add_argument("--accepted", type=int, default=0)
    p.add_argument("--rejected", type=int, default=0)
    p.add_argument("--rule", action="append")
    p.add_argument("--no-rule", help="why this answer is a one-off")

    p = add("redo", cmd_redo, "a pass failed; escalates after the profile's limit")
    p.add_argument("id")
    p.add_argument("note")

    p = add("done", cmd_done, "finish an item; evidence is required")
    p.add_argument("id")
    p.add_argument("--evidence", required=True)
    p.add_argument("--oracle", choices=ORACLES, required=True, help="the strongest check it passed")
    p.add_argument("--provenance", help="tool, model, seed or source of a generated asset")

    p = add("hold", cmd_hold, "a draft is made but the person's review queue is full")
    p.add_argument("id")
    p.add_argument("--person", help="who reviews it; defaults to the item's person, required when it has none")
    p.add_argument("--evidence", required=True)
    p.add_argument("--provenance")

    p = add("log", cmd_log, "record finished work in one call")
    p.add_argument("title")
    p.add_argument("--lane", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--value", type=int, default=3)
    p.add_argument("--road")
    p.add_argument("--evidence", required=True)
    p.add_argument("--oracle", choices=ORACLES, required=True)
    p.add_argument("--provenance")

    p = add("reject", cmd_reject, "a finding was looked at and is not worth an item")
    p.add_argument("finding")
    p.add_argument("--source")
    p.add_argument("--why", required=True)

    p = add("drop", cmd_drop)
    p.add_argument("id")
    p.add_argument("--why", required=True)

    add("board", cmd_board, "who works where, notes, decisions waited on")
    p = add("note", cmd_note, "tell the other sessions something")
    p.add_argument("text")
    p.add_argument("--area")
    grw_work.add_parsers(add)

    add("queue", cmd_queue, "what each person has open, and proposed questions")

    p = add("guard", cmd_guard, "may I? merge, touch_main, stack_on_pending, touch, post, publish, deploy...")
    p.add_argument("action")
    p.add_argument("target", nargs="?")

    p = add("lint-text", cmd_lint_text, "check PR or commit text against the project's text bans")
    p.add_argument("file", nargs="?")

    p = add("discover", cmd_discover, "read-only signals of unfinished work")
    p.add_argument("--repo")
    p.add_argument("--no-gh", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="do not record the pass")

    add("metrics", cmd_metrics, "questions per accepted item, redos, empty sessions")

    p = probing(add("session", cmd_session, "start, check (may I stop?), pause, end"))
    p.add_argument("action", choices=["start", "check", "pause", "end", "release"])
    p.add_argument("--budget", type=int, help="work units for this session: S=1, M=3, L=8")
    p.add_argument("--reason", default="usage limit")
    p.add_argument("--until")
    p.add_argument("--force", help="end anyway; say why")
    return parser


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    store = Store(args.state, args.session)
    if args.command != "init":
        store.require()
    read_only = args.command in ("show", "rank", "next", "plan", "doctor", "list", "queue", "guard", "lint-text", "metrics", "init") and not getattr(args, "claim", False)
    try:
        if read_only:
            result = args.func(store, args)
        else:
            with state_lock(store.root):
                result = args.func(store, args)
                if args.command != "init":
                    write_board(store)
    except Refused as refusal:
        print(json.dumps(dict({"ok": False, "refused": refusal.reasons}, **refusal.extra), ensure_ascii=False, indent=1))
        return 2
    if isinstance(result, str):
        sys.stdout.write(result)
    else:
        print(json.dumps(dict({"ok": True}, **result), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
