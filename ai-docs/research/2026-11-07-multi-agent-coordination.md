# Coordinating parallel agents on one repo (2026-11-07)

Survey for the crew design. About 14 searches and fetches by a subagent. Reddit was read only through search snippets and a third-party archive. The beat `multi-agent-grind` keeps watching this.

## What held up

- Git-based claims with no orchestrator: Anthropic's compiler run used lock files, one container per agent and pull/merge/push. 16 agents, about 2,000 sessions, about $20k. https://www.anthropic.com/engineering/building-c-compiler
- That run's main failure: all agents hit one kernel bug and overwrote each other. The fix split the failure surface. So split what fails as well as the task list.
- Near-perfect tests decide the outcome (same source).
- Claude Code agent teams use file-locked claims and advise 3 to 5 teammates and file ownership, but are experimental and cannot be spawned in `-p` mode, so they do not fit headless nights. https://code.claude.com/docs/en/agent-teams
- Worktree or clone per task is the common default. Practitioner evidence only (HN item 46739808).
- Cloud sandboxes per task: Cursor, Codex, Jules docs.

## What failed or stays weak

- Worktrees defer conflicts to merge; they do not remove them.
- Heavy orchestration: Gas Town reports of about 10x tokens and broken auto-merges. Second-hand, not verified.
- Daemons sharing one directory overwrite each other's state files. One Reddit snapshot, thread unconfirmed.
- Overnight evidence is anecdote. No measured data found.

## GitHub mechanics

- Closing keywords link and close only for a PR into the default branch. https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue
- Comments from a personal token show the human's login, so the agent must identify itself in the text. General knowledge, not fetched.
- Label and assignee edits are not compare-and-swap, so they are poor claims. General knowledge, not fetched.

## Design consequences

Ledger claims under the existing lock, in a state folder outside the worktrees; areas for overlap, including named resources; one worktree per member; plain outer drivers rather than agent teams; a lead agent left out for now as unproven value for its tokens.
