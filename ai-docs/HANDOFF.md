# Handoff

Updated 2026-11-03. Public `m4bwav/grindwright`, v0.1.3 tagged, wiki at 0.1.0 (`ai-docs/notes/2026-11-03-github-wiki.md`).

## State

- Built: `grw.py` (ledger, selector, gates), `grind_loop.py` (bounded driver, dry run by default), the skill, 16 eval cases. Unit tests pass.
- One live pilot on a real game: 2 driver sessions, stopped on the ledger, branch left for review. Nobody has played the result. Usage-limit detection is a text match; what `claude -p` does at a subscription limit is unknown.
- Evals: triggers and decoys pass in `claude plugin eval`. Traps cannot pass there (read-only even with --allow-tools). Run once each through subagents with real writes: 9 pass, small-call partial, no baseline. Small-call and busywork re-run and passing, one run each (T-20261103-3). See `skills/grindwright/TESTS.md`.

## Next

1. The owner reviews the pilot branch, then decides on an overnight run.
2. Decide whether the review cap should also defer drafts that need no person until review.
3. `discover` has no way to mark a finding as looked at and rejected; a `log` command for finished work would save calls.
4. Dependencies between items are not ranked (a helper item can sort after its users).
5. evergreen-worth comparison: needs a baseline arm for the traps.

## Known limits

Claims and the state lock do not coordinate across git worktrees: each has its own ledger copy. The physical-sense check is only an instruction, not a gate. `wait-human` accepts `--why` with no question set (needed for PR reviews), so it can skip the page. `road_warning` is advice; `claim` does not enforce it.
