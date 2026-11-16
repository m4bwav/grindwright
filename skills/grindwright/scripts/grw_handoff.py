"""Stale takeover and deliberate handoff: work another grindwrighter started moves on, from its own branch.

An item paused by a session (its work on that session's branch) is left alone while the owner may come back. Once the
owner has gone quiet past the project's threshold (no claim renewal, checkpoint or commit on the branch, no fresh host
claim), any other session may continue it: on top of the branch, in its own worktree and branch, never from main. A
handoff does the same on purpose: the owner (or a person at a terminal) names who gets it, writes what is done and left,
and the claim is released. Nothing here deletes or rewrites another session's worktree, branch or claim record.
See references/handoff.md.
"""
import datetime as dt
import os
import subprocess

import grw_remote
import grw_work
from grw_work import Refused

STALE_HOURS = 12  # profile "takeover": {"stale_hours": N}
LIVE_HOURS = 2  # a commit this recent means the owner is live: even claim --take-over is refused
ANYONE = "anyone"
HANDOFF_BOOST = 1.5


def now():
    fixed = os.environ.get("GRINDWRIGHT_NOW")
    if fixed:
        return dt.datetime.fromisoformat(fixed)
    return dt.datetime.now().astimezone().replace(microsecond=0).replace(tzinfo=None)


def stamp():
    return now().isoformat(timespec="seconds")


def to_local(text):
    when = dt.datetime.fromisoformat(text)
    return when.astimezone().replace(tzinfo=None) if when.tzinfo else when


def stale_hours(profile):
    return float((profile.get("takeover") or {}).get("stale_hours", STALE_HOURS))


def git(repo, *argv):
    try:
        done = subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def branch_time(repo, branch):
    """Last commit time on the branch, remote copy first; None when it cannot be seen here."""
    for ref in (f"origin/{branch}", branch):
        out = git(repo, "log", "-1", "--format=%cI", ref, "--")
        if out:
            return to_local(out)
    return None


def owner(item):
    if item.get("paused_by"):
        return item["paused_by"]
    return item.get("session") if item.get("state") == "running" else None


def last_activity(item):
    marks = [item.get("updated"), item.get("lease_until") if item.get("state") != "running" else None]
    marks += [c.get("ts") for c in item.get("checkpoints", [])]
    marks = [to_local(m) for m in marks if m]
    return max(marks) if marks else None


def staleness(item, profile, repo):
    """{"stale": bool, "live": bool, "why": str}. Unsure counts as not stale."""
    limit = stale_hours(profile)
    if item.get("state") == "running" and item.get("lease_until") and to_local(item["lease_until"]) > now():
        return {"stale": False, "live": True, "why": f"lease fresh until {item['lease_until']}"}
    held = item.get("held_remote")
    if held and held.get("until", "") > stamp():
        return {"stale": False, "live": True, "why": f"machine {held.get('machine')} holds the host claim until {held.get('until')}"}
    branch = item.get("branch")
    if branch:
        last = branch_time(repo, branch)
        if last is None:
            return {"stale": False, "live": False, "why": f"branch {branch} cannot be seen here (fetch it): unsure, so not stale"}
        quiet = (now() - last).total_seconds() / 3600
        if quiet < LIVE_HOURS:
            return {"stale": False, "live": True, "why": f"branch {branch} got a commit {quiet:.1f}h ago"}
        if quiet < limit:
            return {"stale": False, "live": False, "why": f"branch {branch} quiet {quiet:.1f}h, under the {limit:g}h threshold"}
    last = last_activity(item)
    if last is None:
        return {"stale": False, "live": False, "why": "no claim, checkpoint or update time recorded: unsure, so not stale"}
    quiet = (now() - last).total_seconds() / 3600
    if quiet < limit:
        return {"stale": False, "live": False, "why": f"owner active {quiet:.1f}h ago, under the {limit:g}h threshold"}
    return {"stale": True, "live": False, "why": f"owner {owner(item)} quiet {quiet:.1f}h (threshold {limit:g}h)" + (f", branch {branch} too" if branch else "")}


def me(store):
    """Names this session answers to: its session name, its machine, and any person whose profile entry lists either."""
    try:
        block = grw_remote.config(store)
    except Refused:
        block = None
    names = {store.sid.lower(), grw_remote.machine(block).lower()}
    for person, entry in (store.profile().get("people") or {}).items():
        listed = {str(n).lower() for n in list(entry.get("sessions", [])) + list(entry.get("machines", []))}
        if names & listed:
            names.add(person.lower())
    return names


def addressed_to(item, names):
    to = str((item.get("handed_off") or {}).get("to", "")).lower()
    return to == ANYONE or to in names


def gates(store, items):
    """Per item, what the selector does with paused and handed-off work: defer it, or offer it to continue."""
    profile, repo, names, out = store.profile(), store.repo_path(), None, {}
    for item in items:
        if item.get("state") != "ready":
            continue
        handed = item.get("handed_off")
        if handed:
            names = names if names is not None else me(store)
            if addressed_to(item, names):
                out[item["id"]] = {"action": "continue-handoff", "boost": HANDOFF_BOOST,
                                   "why": [f"handed to {handed['to']} by {handed.get('by')}: claim it, start from {handed.get('branch') or 'its notes'}; next: {handed.get('next')}"]}
            else:
                out[item["id"]] = {"defer": [f"handed off to {handed['to']}: leave it to them (claim --take-over overrides)"]}
            continue
        if item.get("paused_by") and item["paused_by"] != store.sid and store.sid != "solo":
            verdict = staleness(item, profile, repo)
            if verdict["stale"]:
                out[item["id"]] = {"action": "continue-stale", "boost": 1.0,
                                   "why": [f"stale, can be continued: {verdict['why']}; claim it and continue from {item.get('branch') or 'its checkpoints'}"]}
            else:
                out[item["id"]] = {"defer": [f"paused by {item['paused_by']}: its work is on that session's branch, so leave it to that session ({verdict['why']})"]}
    return out


def check_claim(store, item, take_over):
    """Before a claim: None for ordinary work, a provenance record for a takeover or handoff, or Refused."""
    handed = item.get("handed_off")
    if handed:
        if addressed_to(item, me(store)):
            return {"kind": "handoff", "from": handed.get("by"), "why": f"handed to {handed['to']}", "branch": handed.get("branch") or item.get("branch"), "note": handed}
        if not take_over:
            raise Refused([f"handed off to {handed['to']}: take other work, or claim --take-over to override"])
        return {"kind": "override", "from": handed.get("by"), "why": f"took a handoff addressed to {handed['to']}", "branch": handed.get("branch") or item.get("branch"), "note": handed}
    if not item.get("paused_by") or item["paused_by"] == store.sid:
        return None
    verdict = staleness(item, store.profile(), store.repo_path())
    if verdict["live"]:
        raise Refused([f"paused by {item['paused_by']}, who is live: {verdict['why']}; take other work"])
    if verdict["stale"]:
        return {"kind": "stale", "from": item["paused_by"], "why": verdict["why"], "branch": item.get("branch")}
    if not take_over:
        raise Refused([f"paused by {item['paused_by']}, whose work is on its own branch ({verdict['why']}): take other work, or claim --take-over and start from that branch"])
    return {"kind": "manual", "from": item["paused_by"], "why": "claim --take-over: " + verdict["why"], "branch": item.get("branch")}


def continue_steps(store, item, branch):
    """Commands that continue on top of the owner's branch in a new worktree and a new branch; theirs is never moved."""
    if not branch:
        return None
    mine = f"{branch}-{store.sid}" if store.sid != "solo" else f"{branch}-continued"
    path = f"../{store.repo_path().resolve().name}-{item['id']}"
    return {"from_branch": branch, "branch": mine,
            "commands": [f"git fetch origin {branch}", f"git worktree add {path} -b {mine} origin/{branch}"]}


def leave_note(store, item, text):
    """Best effort: a comment on the item's PR, else its issue, so the original owner sees it when they come back."""
    work = store.profile().get("work") or {}
    repo = ((work.get("prs") or {}).get("repo")) or ((work.get("issues") or {}).get("repo"))
    number = item.get("pr") or item.get("review_of") or item.get("issue")
    if not repo or not number:
        return None
    try:
        kind = "pr" if (item.get("pr") or item.get("review_of")) else "issue"
        grw_work.refuse_banned(store, text, "comment")
        return grw_work.gh(kind, "comment", str(number), "-R", repo, "--body-file", "-", stdin=text + "\n\n" + grw_work.MARKER + "\n").strip() or True
    except Refused as failed:
        return {"error": failed.reasons}


def record_takeover(store, item, got):
    """After a claim that took over or received an item: provenance, the note, the branch to continue from."""
    entry = {"at": stamp(), "by": store.sid, "from": got["from"], "kind": got["kind"], "why": got["why"]}
    steps = continue_steps(store, item, got.get("branch"))
    if steps:
        entry["from_branch"] = steps["from_branch"]
        item["continued_from"] = steps["from_branch"]
        item["branch"] = steps["branch"]
    item.setdefault("taken_over", []).append(entry)
    item.pop("handed_off", None)
    verb = "Continuing" if got["kind"] == "handoff" else "Taking over"
    text = (f"{verb} this from `{got['from']}` in session `{store.sid}` ({got['why']}). "
            + (f"The work continues on top of `{steps['from_branch']}` in branch `{steps['branch']}`; `{steps['from_branch']}` is not changed." if steps else ""))
    entry["comment"] = leave_note(store, item, text)
    answer = {"took_over": entry}
    if steps:
        answer["continue"] = steps
    if got.get("note"):
        answer["handoff_note"] = {k: got["note"].get(k) for k in ("by", "to", "at", "done", "left", "next", "branch")}
    return answer, entry


def commit_and_push(worktree, branch, item_id, to):
    """Inside the owning session: save the work in progress on its own branch. Plain push, never force."""
    current = git(worktree, "rev-parse", "--abbrev-ref", "HEAD")
    if current is None:
        raise Refused([f"{worktree} is not a git worktree: pass --worktree, or --no-push when the work is already pushed"])
    if not branch:
        raise Refused(["the item names no branch, so the worktree to save cannot be checked: claim with --branch, or --no-push"])
    if current != branch:
        raise Refused([f"{worktree} is on {current}, the item's branch is {branch}: pass the right --worktree, or --no-push"])
    steps = []
    if git(worktree, "status", "--porcelain"):
        if git(worktree, "add", "-A") is None or git(worktree, "commit", "-q", "-m", f"wip: hand off {item_id} to {to}") is None:
            raise Refused(["could not commit the work in progress; nothing was handed off"])
        steps.append("committed")
    if git(worktree, "push", "-q", "-u", "origin", current) is None:
        raise Refused([f"could not push {current}; nothing was handed off (the work would not reach the next session)"])
    steps.append("pushed")
    return current, steps


def handoff(store, items, item, args):
    """Hand an item to a named grindwrighter or to anyone: push, note, release, mark."""
    if item["state"] not in ("running", "ready"):
        raise Refused([f"{item['id']} is {item['state']}: only running or paused work is handed off"])
    holder = owner(item) or item.get("session")
    inside = holder == store.sid and (item["state"] == "running" or item.get("paused_by") == store.sid)
    branch, pushed = item.get("branch"), []
    if inside and not args.no_push:
        branch, pushed = commit_and_push(args.worktree or os.getcwd(), branch, item["id"], args.to)
    remote = None
    block = grw_remote.config(store) if item.get("remote_claim") or item.get("held_remote") or item["state"] == "running" else None
    if block:
        try:
            if inside:
                remote = "released" if grw_remote.release(block, item, store.sid) else None
            else:  # a person at a terminal: end the other session's lease, never delete its record
                remote = "lease ended" if grw_remote.hand_back(block, item, store.sid, args.to, stamp()) else None
        except Refused as failed:
            remote = {"error": failed.reasons}
        item.pop("remote_claim", None)
    note = {"to": args.to, "by": store.sid, "owner": holder, "at": stamp(), "branch": branch, "done": args.done,
            "left": args.left, "next": args.next, "from_terminal": not inside}
    item.update(state="ready", handed_off=note)
    item.pop("lease_until", None)
    item.pop("paused_by", None)
    item.pop("handling", None)
    item.setdefault("checkpoints", []).append({"ts": stamp(), "note": f"handed off to {args.to}: left {args.left}; next {args.next}"})
    text = (f"Handed off to `{args.to}` by `{store.sid}`" + (f" (owner `{holder}` was away)" if not inside else "") + ".\n\n"
            + (f"- Done: {args.done}\n" if args.done else "") + f"- Left: {args.left}\n- Next: {args.next}\n"
            + (f"- Branch: `{branch}`\n" if branch else ""))
    note["comment"] = leave_note(store, item, text)
    return {"id": item["id"], "handed_off": note, "pushed": pushed, "remote": remote,
            "worktree": "untouched: the owner's session is away" if not inside else (args.worktree or os.getcwd())}


def add_parser(add):
    p = add("handoff", None, "hand an item to another grindwrighter or anyone: push, note, release, mark")
    p.add_argument("id")
    p.add_argument("--to", required=True, help="a person from profile people, a session or machine name, or 'anyone'")
    p.add_argument("--left", required=True, help="what is left to do")
    p.add_argument("--next", required=True, help="the next step")
    p.add_argument("--done", help="what is done")
    p.add_argument("--worktree", help="the owning session's worktree (default: the current folder)")
    p.add_argument("--no-push", action="store_true", help="the work is already pushed")
    return p
