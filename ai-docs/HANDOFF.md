# Handoff

Updated 2026-11-06. Public `m4bwav/grindwright`, v0.1.7 tagged, wiki at 0.1.0 (`ai-docs/notes/2026-11-03-github-wiki.md`). Installed locally.

## State

- Built: `grw.py` (ledger, selector, gates), `grind_loop.py` (bounded driver, dry run by default), the skill, 20 eval cases. Unit tests pass.
- The owner ruled to keep the plugin and trim it. Trim shipped in 0.1.7; its saving is not measured. Evals have not been re-run since.
- Live runs: one pilot merged and played on the first game; the owner reported one fix, since merged. A pilot on a second game started 2026-11-06: three sessions, up to 4 hours, one art lane. Usage-limit detection is still a text match; what `claude -p` does at a subscription limit is unknown.

## Next

1. Read the second pilot's result (private sidecar has where). Log what the loop got wrong and fix the plugin.
2. The overnight run on the first game is the owner's to start, the next night possible. Reconcile that game's ledger first. It is the first real test of drafting past the cap.
3. Re-run `evergreen.py worth --ab` on the value cases when a run is worth its cost, to measure the trim.

## Known limits

Claims and the state lock do not coordinate across git worktrees: each has its own ledger copy. The physical-sense check is only an instruction, not a gate. `wait-human` accepts `--why` with no question set (needed for PR reviews), so it can skip the page. `road_warning` is advice; `claim` does not enforce it. Drafts past the cap can go stale if a pending answer changes direction; `ask-drafted` only tells the agent to check. Apart from small-call, trap evals have not been re-run since `draft` was added. Eval isolation only covers fixture profiles.
