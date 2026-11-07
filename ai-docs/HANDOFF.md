# Handoff

Updated 2026-11-07. Public `m4bwav/grindwright`, v0.1.12, wiki at 0.1.0 (`ai-docs/notes/2026-11-03-github-wiki.md`). Installed locally.

## State

- Built: `grw.py` (ledger, selector, gates), `grind_loop.py` (bounded driver, dry run by default), the skill, 20 eval cases. Unit tests pass.
- The owner ruled to keep the plugin and trim it. Trim shipped in 0.1.7; its saving is not measured. Evals have not been re-run since.
- Live runs: one pilot and one overnight run on the first game, one pilot on a second. The overnight run stopped on its 25-session bound in under 2 of its 10 hours and met no usage limit, so what `claude -p` does at a limit is still unknown. Drafting past the cap and `wait-human --pr` worked. 0.1.11 and 0.1.12 fix its faults; those fixes have not run in a live chain.

## Next

1. On the next live run, check that the driver stops on the ledger with no `--force`, and that a large session bound is no longer the thing that stops it.
2. Re-run the evals and `evergreen.py worth --ab` on the value cases when a run is worth its cost, to measure the trim. They have not run since 0.1.7.

3. Put L-004 `feel-per-row-blind` and L-008 `absence-claim-unchecked` into the discovery step of SKILL.md at the next change that re-runs evals.

## Known limits

Claims and the state lock do not coordinate across git worktrees: each has its own ledger copy. The physical-sense check is only an instruction, not a gate. `wait-human` accepts `--why` with no question set (needed for PR reviews), so it can skip the page. `road_warning` is advice; `claim` does not enforce it. Drafts past the cap can go stale if a pending answer changes direction; `ask-drafted` only tells the agent to check. Apart from small-call, trap evals have not been re-run since `draft` was added. Eval isolation only covers fixture profiles.
