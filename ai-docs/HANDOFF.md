# Handoff

Updated 2026-11-06. Public `m4bwav/grindwright`, v0.1.9 tagged, wiki at 0.1.0 (`ai-docs/notes/2026-11-03-github-wiki.md`). Installed locally.

## State

- Built: `grw.py` (ledger, selector, gates), `grind_loop.py` (bounded driver, dry run by default), the skill, 20 eval cases. Unit tests pass.
- The owner ruled to keep the plugin and trim it. Trim shipped in 0.1.7; its saving is not measured. Evals have not been re-run since.
- Live runs: one pilot merged and played on the first game; the owner reported one fix, since merged. A pilot on a second game started 2026-11-06: three sessions, up to 4 hours, one art lane. Usage-limit detection is still a text match; what `claude -p` does at a subscription limit is unknown.

## Next

1. Read the overnight run's result on the first game (private sidecar has where). It started 2026-11-06 about 22:03, bounded at 10 hours and 25 sessions. Log what the loop got wrong and fix the plugin. It is the first real test of drafting past the cap and of `wait-human --pr`, and may be the first to meet a usage limit.
2. Re-run the evals and `evergreen.py worth --ab` on the value cases when a run is worth its cost, to measure the trim. They have not run since 0.1.7.

## Known limits

Claims and the state lock do not coordinate across git worktrees: each has its own ledger copy. The physical-sense check is only an instruction, not a gate. `wait-human` accepts `--why` with no question set (needed for PR reviews), so it can skip the page. `road_warning` is advice; `claim` does not enforce it. Drafts past the cap can go stale if a pending answer changes direction; `ask-drafted` only tells the agent to check. Apart from small-call, trap evals have not been re-run since `draft` was added. Eval isolation only covers fixture profiles.
