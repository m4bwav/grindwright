# Stale takeover and handoff

Two people (each with their own agents) work one project. Normally each session keeps to its own items and branch. This page covers the two ways work moves between them: an owner who went quiet (stale takeover) and an owner who hands it over on purpose (handoff). Code: `scripts/grw_handoff.py`.

## Who is who

No new identity scheme. A session answers to its session name (`GRINDWRIGHT_SESSION`), its machine (`GRINDWRIGHT_MACHINE`, `work.remote.machine` or the host name), and any person in `profile.people` whose entry lists that session or machine:

```json
"people": {"jennifer": {"review_cap": 3, "sessions": ["jen-1", "jen-2"], "machines": ["jen-laptop"]}}
```

`--to` takes any of those names, or `anyone`.

## Stale takeover

An item is paused by a session when that session stopped (`session pause` or `release`) or when its lease ran out with a branch recorded (`sync` now keeps such an item with its owner instead of freeing it at once). Its work is on that session's branch.

The item becomes stale, and any other session may continue it, only when all of these hold:

- no fresh lease and no fresh host claim (`work.remote`) on another computer;
- the branch can be seen here (`origin/<branch>` or `<branch>`) and its last commit is older than the threshold;
- the last claim, checkpoint or update is older than the threshold.

When unsure (branch not fetched, no times recorded) it is not stale. Threshold: 12 hours by default; per project in `profile.json`:

```json
"takeover": {"stale_hours": 24}
```

`next` and `rank` list a stale item as action `continue-stale` ("stale, can be continued") instead of hiding it. `claim <id>` then takes it over without a flag. The answer carries:

- `took_over`: from whom, why, when (also stored on the item as `taken_over`, an event `takeover`, a BOARD.md line and the run report);
- `continue`: `git fetch origin <branch>` and `git worktree add ../<repo>-<id> -b <branch>-<session> origin/<branch>`. Work goes on top of the owner's branch in a new worktree and branch. The owner's branch, worktree and claim record are never changed, and force-push is out.

When the item has a PR or issue (and `work.prs.repo` or `work.issues.repo`), a comment says who took it over and which branch the work continues in, so the owner sees it when they return.

`claim --take-over` stays the manual override for an item that is paused but not yet stale, or handed to someone else. It is refused while the owner is live: a branch commit in the last 2 hours, a fresh lease, or a fresh host claim. A fresh host claim on another computer is never taken over, with or without the flag.

## Handoff

```
grw.py handoff <id> --to jennifer --left "the save writer" --next "write SaveWriter and its test" [--done "the parser"]
```

- Run by the owning session: commits the work in progress in its worktree (`--worktree`, default the current folder, must be on the item's branch), pushes the branch (never force), releases the local and host claim. `--no-push` when it is already pushed.
- Run by anyone else, such as a person at a terminal while the owning session is away: never touches the owner's worktree. It releases the local claim and ends the host claim's lease with a fast-forward update that records `handed_to` (the record is kept, not deleted).

Either way the item goes back to `ready` with `handed_off` (to, by, owner, when, branch, done, left, next), a checkpoint, a PR or issue comment, a BOARD.md line and a WAITING.md line under the addressee.

The addressee's `next` ranks it as `continue-handoff`, boosted 1.5x and sorted right after owner notes and answers. Others see it deferred ("handed off to jennifer"). The addressee's `claim` returns `handoff_note` and the same `continue` commands; `taken_over` records it with kind `handoff`.

## Rulings

- Continue, never restart: a takeover always builds on the old branch.
- When unsure, don't: an unseen branch or missing times means not stale.
- Live beats any flag: a recent commit or a fresh claim refuses even `--take-over`.
- Records are only added to: provenance (`taken_over`, events, comments) is appended; nobody's branch, worktree or claim ref is deleted by another session.
- Quiet mode (no new work): continuing stale or handed-off work is finishing open work, so it is allowed.
