# New work off: only answer what the owners raised

A grind makes pull requests, issues and questions faster than its owners can review them. Turning new work off lets a
grind keep answering the owners without adding to their pile. Turning it back on restores normal selection; nothing
in the ledger is lost or reordered.

## Commands

The state folder is the project's grind folder (`ai-docs/grind` by default; pass `--state <folder>` when it lives
elsewhere, as it does for a crew).

```
grw.py --state <folder> new-work off [--why "catching up on reviews"]   # stored in <folder>/mode.json
grw.py --state <folder> new-work on
grw.py --state <folder> new-work show       # mode, owner-driven items, held items
grind_loop.py <prompt> ... --no-new-work    # this run only; mode.json is untouched
grind_crew.py <crew.json> --no-new-work     # every member of this run; or "no_new_work": true in the crew file or one project
```

`GRINDWRIGHT_NO_NEW_WORK=1` in the environment does the same for one process; the driver and crew set it for their
sessions and checks.

## What a grind does while it is off

- `next` and `rank` list only owner-driven items. The rest show in `deferred` with `"held": "new-work-off"`.
- `discover`, `surveyed`, `ticket` (proposals included) refuse with exit 2. So do `claim`, `wait-human`,
  `issue-accept`, `issue-question`, `issue-ask` and `issue-pr` on an item that is not owner-driven.
- `add` still records what it finds, so nothing is forgotten, and answers `"held"` when the item is not owner-driven.
- `session start` still syncs (answers, `pr-sync`, `issue-sync`): that is how owner requests arrive.
- When nothing owner-driven is left, `next` says `stop` with `"stopped": "no-new-work"` and `session check` allows the
  stop with the same reason. That is the right outcome in this mode. It is not "drained", so do not discover, survey
  or propose; say plainly that new work is off and stop. The driver stops with `no-new-work`, never `no-progress`,
  and the run report and status page show the mode.

## Owner-driven or new work

| Item or source | Ledger mark | Counts as |
|---|---|---|
| Owner's words at session start or a direct request | `owner_note` | owner-driven |
| Answers came in on an askwright page or by relay | `answered` | owner-driven |
| Owner review comment on an agent PR (`pr-sync`) | `review_of` | owner-driven |
| Merge conflict on an open agent PR (`pr-sync`) | `conflict_of` | owner-driven (repair of open work) |
| Stale picture links on an open agent PR (`pr-sync`) | `images_of` | owner-driven (repair of open work) |
| Agent PR with failing checks, no owner comment | `repair_of` (`add --repair-of N`) | owner-driven (repair of open work) |
| Agent PR merged, issue to close or finalize | `closeout` | owner-driven |
| Issue or proposal an owner green-lit | `greenlit_by` | owner-driven |
| Issue reopened by a reply after the agent asked | `issue_seen`, not triaged, not replied | owner-driven |
| Brand-new issue from `issue-sync`, never triaged | `issue`, no `issue_seen` | new work |
| Backlog item from `add`, `todo-sync`, a survey or discovery | none of the above | new work |
| Draft waiting to be put to a person (`ask-drafted`) | `drafted` | new work |
| Paused or unfinished agent work nobody asked about | `ready` with checkpoints | new work |
| Proposal waiting for a green light | `proposal`, waiting | waits; nothing to do |

## Rulings (2026-11-16)

- Name: `new-work off|on|show`. It follows the owners' own words ("turn the spigot of new work back on") and reads as
  a switch; "quiet" or "pause" would clash with `session pause`.
- An agent PR with failing checks and no owner comment may be repaired: it lowers the owners' load. No sync creates
  such an item, so add it by hand with `--repair-of <PR>`; that flag is only for an open agent PR.
- A new bug found while fixing something goes in with `add` and is held, not started.
- Follow-up questions on an owner-driven item are allowed (`wait-human`, `issue-question`); a question on anything
  else is refused.
- A green-lit issue counts as an answer, so a pile of green lights still runs. Remove the label to hold one.
- Drafts already made are not put to a person: that would be a new ask.
- The one-shot flag can only turn new work off. A run cannot turn it on over a stored `off`.
