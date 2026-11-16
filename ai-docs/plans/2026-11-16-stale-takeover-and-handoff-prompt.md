# grindwright: take over stale work, and hand work over on purpose

Status: done, released as v0.14.0 (2026-11-16).

Run this on Claude Opus 5.5. Start in `D:/m4bwa/Claude/Projects/Ai`. Repo: `m4bwav/grindwright` (public, default branch main), clone at `D:/m4bwa/Claude/Projects/Ai/grindwright`.

This file is untracked in the shared clone. Commit it with the feature branch, and when the feature is released mark it done at the top.

## The request

Mark, 2026-11-16: "Normally the agents will be working to avoid each other using branches, but sometimes one person won't be around and it will be ok for another grindwrighter (my wife) to continue on the work that another agent has started once it's become apparent that it's stale. And also it would be good to be able to trigger a deliberate handoff in some fashion."

Two grindwrighters (Mark and Jennifer) each run agents. Today a session's claimed item, and an item `paused_by` a session (its work on that session's branch), is left alone by everyone else. `claim --take-over` exists but is a manual escape hatch.

Deliver:

1. **Stale takeover.** When an item's owner has clearly gone quiet (lease expired, no commits on its branch and no claim renewal for a set time, no live process or recent transcript where that can be seen), another grindwrighter's session may pick it up. It continues *from the existing branch* (fetch it, check it out in its own worktree), never restarts from main, and records who it took over from and why. The threshold has a sane default and is settable per project. The selector should surface such items as "stale, can be continued" rather than hiding them forever. A takeover is visible on BOARD.md / WAITING.md and in the run report, and leaves a note (PR or issue comment if one exists) so the original owner sees what happened when they return.
2. **Deliberate handoff.** A command by which a session or a person hands an item to another grindwrighter or to "anyone": it commits and pushes the work in progress, writes a short handoff note on the item (what is done, what is left, branch, next step), releases the claim (local and remote), and marks the item `handed_off` (to whom, when). The receiving side's selector ranks handed-off items addressed to it high, and claiming one starts from the branch and shows the note. It should also be possible for a person to trigger it from outside a running session (e.g. `grw.py handoff <id> --to jennifer` from a terminal while the owning session is away), in which case it only releases and marks, never touches the other session's worktree.

## Rules and limits

- Never delete or rewrite another session's worktree, branch or claim data; takeover means continuing on top, with a new worktree. Force-push is out.
- A takeover must not happen while the owner is demonstrably live (fresh lease, recent commits). When unsure, don't.
- Remote claims (`grw_remote.py`, `work.remote`) must follow the same rules across machines. Note the live `feat/remote-claims` worktree in `grindwright-wt-remote`: read its branch to see if it changes this area, and build on main without touching it.
- A separate session is building "no new work" (quiet) mode on branch `feat/quiet-mode` at the same time; it also edits `grw.py`. Rebase onto `origin/main` right before opening the PR and resolve conflicts. In quiet mode, continuing stale or handed-off work counts as finishing what is already open: classify it as allowed, and add the rows to the quiet-mode table if that has merged.
- Identity of a grindwrighter: find how grindwright names people today (crew members, `--person`, machines) and reuse it; don't invent a second scheme.

## Steps

1. Read `C:/Users/m4bwa/.claude/CLAUDE.md`, the repo `AGENTS.md`, `skills/grindwright/SKILL.md`, its references (`loop.md`, `crew.md`, `machines.md`, `work-sources.md`), `LEARNINGS.md`, `CHANGELOG.md`, and the scripts (`grw.py`, `grw_remote.py`, `grind_loop.py`, the crew runner, `grind_report.py`).
2. `git -C D:/m4bwa/Claude/Projects/Ai/grindwright fetch`, then `git worktree add ../grindwright-handoff -b feat/stale-takeover-handoff origin/main`. Work only there. Leave the main clone's uncommitted `LEARNINGS.md` and the other worktrees alone.
3. Design the smallest change on top of leases, `paused_by` and `--take-over`. Record names and rulings in a reference (`references/handoff.md` or in `crew.md`), a few lines in SKILL.md (it is near its token budget: `python scripts/budget.py`).
4. Tests: stale detection (fresh vs expired vs ambiguous), takeover continues from the branch and records provenance, refusal while the owner is live, handoff from inside a session and from a terminal, selector ranking of handed-off items for the addressee, remote-claim equivalents with the existing fakes. Whole suite stays green.
5. Docs: CHANGELOG, README section, the reference, dated entry at the top of `ai-docs/HANDOFF.md`, a line in `ai-docs/log.md`. Minor version bump.
6. Ship by the standing rules: PR, merge once checks pass, tag and release like earlier releases, update the installed copy (releasewright). Wiki owed unless the release routine requires it.
7. Do not start, stop or take over anything in Mark's or Jennifer's real projects.

## Report

The commands to hand over and to take over, the stale threshold and how to change it, the rulings, test counts, PR URL and merge state, release tag, installed version, anything owed. Then run the wrap-up and remove the worktree.
