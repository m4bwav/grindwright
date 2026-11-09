"""Claims shared through the repository host, so grind runs on different computers do not take the same item.

A local state folder only coordinates sessions on one machine. With "work.remote" in profile.json, every claim also
creates a branch ref `grind-claim/<key>` on the host. Creating a ref that already exists fails (HTTP 422), so the first
machine wins; renewing or taking over is a fast-forward update, which fails if another machine moved it first. The
ref points at an empty commit whose message carries who holds it and until when. Nothing here touches work branches.
"""
import json
import os
import socket

import grw_work
from grw_work import Refused

PREFIX = "grind-claim/"
LABEL = "agent-working"
HEAD = "grindwright claim"


def config(store):
    """The remote block with its repo filled in, or None when the project has one machine."""
    work = store.profile().get("work", {})
    block = work.get("remote")
    if not block:
        return None
    block = dict(block)
    block.setdefault("repo", (work.get("issues") or {}).get("repo"))
    if not block["repo"]:
        raise Refused(['"work.remote" needs a "repo" (or a "work.issues.repo")'])
    return block


def machine(block=None):
    return os.environ.get("GRINDWRIGHT_MACHINE") or (block or {}).get("machine") or socket.gethostname()


def key_for(item):
    if item.get("issue"):
        return f"issue-{item['issue']}"
    pr = item.get("review_of") or item.get("conflict_of")
    if pr:
        return f"pr-{pr}"
    return "t-" + grw_work.key_of(item.get("title", item["id"]))


def _api(method, path, body=None):
    argv = ["api", "-X", method, path]
    if body is not None:
        argv += ["--input", "-"]
    out = grw_work.gh(*argv, stdin=json.dumps(body) if body is not None else None)
    return json.loads(out) if out.strip() else {}


def _missing(failed):
    return any("404" in r or "Not Found" in r for r in failed.reasons)


def _lost_race(failed):
    return any("422" in r or "409" in r or "already exists" in r.lower() or "fast forward" in r.lower() for r in failed.reasons)


def read(repo, key):
    """Who holds this key: {sha, machine, session, until, ...} or None."""
    try:
        ref = _api("GET", f"repos/{repo}/git/ref/heads/{PREFIX}{key}")
    except Refused as failed:
        if _missing(failed):
            return None
        raise
    sha = ref["object"]["sha"]
    commit = _api("GET", f"repos/{repo}/git/commits/{sha}")
    info = parse(commit.get("message", ""))
    info.update(sha=sha, tree=commit["tree"]["sha"], key=key)
    return info


def parse(message):
    for line in reversed(message.strip().splitlines()):
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                break
    return {}


def _base(repo):
    default = _api("GET", f"repos/{repo}")["default_branch"]
    commit = _api("GET", f"repos/{repo}/commits/{default}")
    return commit["sha"], commit["commit"]["tree"]["sha"]


def _commit(repo, key, tree, parent, holder):
    message = f"{HEAD} {key}\n\nAn agent's claim on shared work; deleted when the work ends. Do not merge.\n\n{json.dumps(holder, sort_keys=True)}\n"
    return _api("POST", f"repos/{repo}/git/commits", {"message": message, "tree": tree, "parents": [parent]})["sha"]


def mine(info, me, sid):
    return info.get("machine") == me and info.get("session") == sid


def fresh(info, now_iso):
    return info.get("until", "") > now_iso


def claim(block, item, sid, now_iso, until_iso, take_over=False):
    """Returns {"ok": True, ...} or {"ok": False, "held_by": {...}}. Ref creation is the lock."""
    repo, me, key = block["repo"], machine(block), key_for(item)
    holder = {"machine": me, "session": sid, "item": item["id"], "title": item.get("title", "")[:120],
              "issue": item.get("issue"), "at": now_iso, "until": until_iso}
    info = read(repo, key)
    if info and not mine(info, me, sid) and fresh(info, now_iso) and not take_over:
        return {"ok": False, "key": key, "held_by": public(info)}
    try:
        if info:  # renew, or take over an expired or released claim: a fast-forward only lands if nobody moved it first
            sha = _commit(repo, key, info["tree"], info["sha"], holder)
            _api("PATCH", f"repos/{repo}/git/refs/heads/{PREFIX}{key}", {"sha": sha, "force": False})
        else:
            parent, tree = _base(repo)
            sha = _commit(repo, key, tree, parent, holder)
            _api("POST", f"repos/{repo}/git/refs", {"ref": f"refs/heads/{PREFIX}{key}", "sha": sha})
    except Refused as failed:
        if not _lost_race(failed):
            raise
        return {"ok": False, "key": key, "held_by": public(read(repo, key) or {}), "race": True}
    return {"ok": True, "key": key, "ref": PREFIX + key, "machine": me, "until": until_iso, "took_over": public(info) if info and not mine(info, me, sid) else None}


def release(block, item, sid):
    """Delete the ref when this machine and session hold it. Someone else's claim is never touched."""
    repo, key = block["repo"], key_for(item)
    info = read(repo, key)
    if not info or not mine(info, machine(block), sid):
        return False
    try:
        _api("DELETE", f"repos/{repo}/git/refs/heads/{PREFIX}{key}")
    except Refused as failed:
        if not _missing(failed):
            raise
    return True


def claims(block):
    repo = block["repo"]
    try:
        refs = _api("GET", f"repos/{repo}/git/matching-refs/heads/{PREFIX}")
    except Refused as failed:
        if _missing(failed):
            return []
        raise
    out = []
    for ref in refs if isinstance(refs, list) else []:
        key = ref["ref"].split(PREFIX, 1)[-1]
        commit = _api("GET", f"repos/{repo}/git/commits/{ref['object']['sha']}")
        out.append(dict(parse(commit.get("message", "")), key=key, sha=ref["object"]["sha"]))
    return out


def public(info):
    return {k: info.get(k) for k in ("machine", "session", "item", "title", "issue", "until", "at") if info.get(k) is not None}


def sync(block, items, sid, now_iso):
    """Mark items another machine holds; give back refs this machine holds for items no longer running."""
    me = machine(block)
    held = {c["key"]: c for c in claims(block)}
    report = {"machine": me, "others": [], "expired": [], "released": []}
    for item in items:
        info = held.get(key_for(item))
        if info and not (info.get("machine") == me) and fresh(info, now_iso):
            item["held_remote"] = public(info)
            report["others"].append(dict(public(info), id=item["id"]))
            continue
        item.pop("held_remote", None)
        if info and info.get("machine") != me:
            report["expired"].append(dict(public(info), id=item["id"]))
        if info and info.get("machine") == me and item["state"] != "running":
            if release(block, item, info.get("session")):
                report["released"].append(item["id"])
    known = {key_for(i) for i in items}
    report["unknown_here"] = [public(c) | {"key": k} for k, c in held.items() if k not in known and c.get("machine") != me and fresh(c, now_iso)]
    return report


def announce(store, block, item, until_iso):
    """Once per claim on an issue: a label and a marked comment, so people and the other machine's sync see it."""
    if not item.get("issue") or item.get("remote_announced") == machine(block):
        return
    label = block.get("label", LABEL)
    try:
        grw_work.gh("issue", "edit", str(item["issue"]), "-R", block["repo"], "--add-label", label)
    except Refused:
        pass  # a missing label must not stop the work; the ref is the real claim
    grw_work.post_issue_comment(store, block["repo"], item["issue"],
                                f"Working on this from machine `{machine(block)}` (claim `{PREFIX}{key_for(item)}`, held until {until_iso} and renewed while work goes on). "
                                "Other agents leave it alone until the claim is released or expires.")
    item["remote_announced"] = machine(block)


def unannounce(block, item):
    if not item.get("issue") or not item.pop("remote_announced", None):
        return
    try:
        grw_work.gh("issue", "edit", str(item["issue"]), "-R", block["repo"], "--remove-label", block.get("label", LABEL))
    except Refused:
        pass
