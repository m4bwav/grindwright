**Done 2026-11-16: released as v0.14.0.**

# grindwright: "no new work" mode

Run this on Claude Opus 5.5. Start in `D:/m4bwa/Claude/Projects/Ai`. Repo: `m4bwav/grindwright` (public, default branch main), clone at `D:/m4bwa/Claude/Projects/Ai/grindwright`.

This file is untracked in the shared clone. Commit it with the feature branch, and when the feature is released mark it done at the top.

## The request

Mark, 2026-11-16: "my wife and I were talking about how we would like to be able to run grindwright in a don't do new work mode, where it just addresses open questions and requests for update. So that we can turn the spicket of new work back on when we feel we're ready to handle it cognitive."

Grinds produce pull requests, issues and questions faster than the two owners can review. They want a persistent switch per project, which also works for crews and the unattended driver.

While the switch is on, a grind still:

- reads and acts on answers the owners gave (askwright pages, issue and PR comments, greenlights);
- handles owners' requests for changes or updates on existing PRs and issues (review comments, merge conflicts, stale picture links, "please update X");
- finishes or repairs what is already open where an owner asked.

While it is on, a grind does not:

- pick fresh backlog items;
- run discovery or surveys that add items;
- open new PRs, issues or proposals for new work;
- post new questions that are not a follow-up to something an owner raised.

When nothing owner-driven is left it stops cleanly with its own stop reason. That must not read as "drained", must not trip the no-progress guard, and must not trigger the "grind is never drained" behaviour: in this mode idle is the right outcome. Turning the switch off restores normal selection with nothing lost.

## State on 2026-11-16

Nothing is built. An earlier attempt was stopped before it changed anything; its worktree and branch were removed. The main clone has an uncommitted `skills/grindwright/LEARNINGS.md` edit from another session, and two other worktrees are live (`grindwright-wt-remote`, `grindwright-wt-tdd`). Leave all three alone.

## Steps

1. Read the rules: `C:/Users/m4bwa/.claude/CLAUDE.md`, the repo's `AGENTS.md`, `skills/grindwright/SKILL.md`, its references (`loop.md`, `crew.md`, `work-sources.md`), `LEARNINGS.md`, `CHANGELOG.md`, and the scripts in `skills/grindwright/scripts` (`grw.py`, `grind_loop.py`, the crew runner, `grind_report.py`).
2. Make a worktree: `git -C D:/m4bwa/Claude/Projects/Ai/grindwright fetch`, then `git worktree add ../grindwright-quiet -b feat/quiet-mode origin/main`. Work only there.
3. Design the smallest honest change:
   - a stored mode in the project's grind state, plus a one-shot flag on the driver and the crew runner;
   - commands to turn it on, off and show it, named in the house style (decide the name and record the ruling);
   - the selector filters to owner-driven items;
   - discovery, survey and proposal verbs refuse or do nothing, with a clear message, while it is on;
   - the status page and the run report show the mode and the new stop reason.
4. Write one table in a reference file that classifies every existing item kind and source as owner-driven or new work. Decide the edge cases and list them. Two guesses: an agent PR with failing checks and no owner comment may be repaired, since that lowers the owners' load; a new bug found while fixing something is noted in the ledger as held and not started.
5. Tests: the selector filter, the switch surviving between runs, each refusing verb, the driver and crew stop reason, and the same pick order after the switch is turned back off. The whole existing suite stays green. Add one trigger eval case ("run grindwright but don't start anything new, just answer what's waiting on us") if the eval format makes it cheap.
6. Keep `SKILL.md` inside its token budget. `python scripts/budget.py` already reports yellow on SKILL.md tokens, so put the detail in a reference and a few lines in the skill.
7. Docs: `CHANGELOG.md`, a README section, the reference, a dated entry at the top of `ai-docs/HANDOFF.md`, a line in `ai-docs/log.md`. Minor version bump where the repo keeps its version.
8. Ship by the standing rules: open the PR, merge it once checks pass, tag and release as earlier releases did (`gh release list`), update the installed copy (releasewright). Note the wiki as owed unless the release routine requires it.
9. Do not start or stop any running grind, crew or driver, and do not turn the mode on in any of Mark's projects. He turns it on himself.

## Report

Give Mark the exact commands to turn new work off, turn it on and check it, with what the project folder argument is; what counts as owner-driven; the rulings made; test counts; the PR URL and whether it merged; the release tag; the installed version; anything owed. Then run the wrap-up and remove the worktree.
