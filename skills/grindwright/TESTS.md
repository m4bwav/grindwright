# Tests: grindwright

Cases are in `evals/evals.json`; unit tests in the repository's `tests/`. A test passes on evidence, never on prose.

## Runs

### T-20261103-1 · 2026-11-03 · claude plugin eval under WSL2 (16 cases x 3 runs each arm, --scaffold, -j 6) · about $26 over three runs
- Triggers 3/3 at 1.00 (0.00 without). Decoys 3/3 at 1.00 after a grader fix.
- Traps (with / without): other-owner-pr 1.00/0.00, small-call 1.00/0.00, sync 0.50/0.17, usage-limit 0.50/0.17, missing-plugin 0.33/0.00, busywork 0.17/0.17, empty 0.17/0.33, only-blocked 0.00/0.00, cap 0.00/0.00, post 0.00/0.00.
- Not a verdict on the state-changing traps: the sandbox mounts the workspace read-only for Bash, so `grw.py claim` cannot work and those graders cannot pass. Agents named the right item and said they could not write. max_turns in case.yaml was not honoured (still 10).
- trap-post failed its judge because the agent looked for a devlog that the fixture lacks; rewrite the case. It did not post.
- Found a real bug: the selector ranked an item in a closed lane first. Fixed, with a unit test. The evals were not rerun after that fix or after the last SKILL.md edit.
- No worth verdict recorded: the action cases are not valid yet.

### T-20261103-2b · 2026-11-03 · evergreen-tester subagents (Sonnet), 10 traps x 1 run, real writes in throwaway folders, ledgers on disk
- 9 pass: only-blocked, busywork, other-owner-pr, missing-plugin, empty, usage-limit, post, sync, cap. 1 partial: small-call decided the name and flagged it, but asked the art style with no guess.
- Weak evidence: one run each, no baseline arm, graded by the author from reports, and the tester was told to read SKILL.md, so triggering is not covered here. Work items were simulated, so oracle rungs in these runs prove nothing about a game.
- `claude plugin eval --allow-tools Bash Write Edit` still mounts the workspace read-only. case.yaml max_turns and timeout_seconds still read as defaults (10, 300); key not found.
- A headless `claude -p` runner with open Bash was refused by the auto-mode classifier and removed. It would need a permission rule from the owner, plus a baseline arm.
- Skill fixes after this run were not re-run.
