# Handoff

Updated 2026-11-03. Public `m4bwav/grindwright`, v0.1.0 tagged, wiki at 0.1.0 (`ai-docs/notes/2026-11-03-github-wiki.md`).

## State

- Built: `grw.py` (ledger, selector, gates), `grind_loop.py` (bounded driver, dry run by default), the skill, 16 eval cases. Unit tests pass.
- Not proven: no live pilot. The driver has run only against fake agents. Usage-limit detection is a text match; what `claude -p` does at a subscription limit is unknown.
- Evals: triggers and decoys pass in `claude plugin eval`. Traps cannot pass there (read-only even with --allow-tools). Run once each through subagents with real writes: 9 pass, small-call partial, no baseline. Skill fixes since then are not re-run. See `skills/grindwright/TESTS.md`.

## Next

1. Re-run trap-small-call and trap-busywork through subagents to check the guess rule and `road_warning`.
2. `max_turns` in case.yaml was not honoured; low value now that traps run elsewhere.
3. evergreen-worth comparison: needs a baseline arm for the traps.
4. A first live pilot on a real game.

## Known limits

Claims and the state lock do not coordinate across git worktrees: each has its own ledger copy. The physical-sense check is only an instruction, not a gate. `wait-human` accepts `--why` with no question set (needed for PR reviews), so it can skip the page. `road_warning` is advice; `claim` does not enforce it.
