# Handoff

Updated 2026-11-07. Public `m4bwav/grindwright`, v0.2.2, wiki at 0.1.0 (`ai-docs/notes/2026-11-03-github-wiki.md`). Installed locally.

## State

- Built: `grw.py` (ledger, selector, gates), `grind_loop.py` (bounded driver, dry run by default), the skill, 20 eval cases. Unit tests pass.
- The owner ruled to keep the plugin and trim it. Trim shipped in 0.1.7; its saving is not measured. Evals have not been re-run since.
- Live runs: one pilot and one overnight run on the first game, one pilot on a second. The overnight run stopped on its 25-session bound in under 2 of its 10 hours and met no usage limit, so what `claude -p` does at a limit is still unknown. Drafting past the cap and `wait-human --pr` worked. 0.1.11 and 0.1.12 fix its faults; those fixes have not run in a live chain.

## Next

0. 0.2.0 to 0.2.2 added crews, work sources and a todo file as master list, tested with a fake gh only. The owner chose the first crew: three sessions over two projects, with issues live. Crew file, moved state and profiles are ready and dry-run clean, in the private sidecar. It runs when the owner starts it. Design: `references/crew.md`, `references/work-sources.md`, research in `ai-docs/research/2026-11-07-multi-agent-coordination.md`. Beat: `multi-agent-grind` (private beat dir, public-safe), first scan not run.
1. On the next live run, check that the driver stops on the ledger with no `--force`, and that a large session bound is no longer the thing that stops it.
2. Re-run the evals and `evergreen.py worth --ab` on the value cases when a run is worth its cost, to measure the trim. They have not run since 0.1.7.


## Known limits

Claims coordinate across worktrees only when the state folder is outside them; `grind_crew.py` enforces that, a hand-run session does not. Areas are declared by agents and do not stop logical conflicts. Duplicate checks read the newest 100 issues. The green light is a label: profile must name who counts. The physical-sense check is only an instruction, not a gate. `wait-human` accepts `--why` with no question set (needed for PR reviews), so it can skip the page. `road_warning` is advice; `claim` does not enforce it. Drafts past the cap can go stale if a pending answer changes direction; `ask-drafted` only tells the agent to check. Apart from small-call, trap evals have not been re-run since `draft` was added. Eval isolation only covers fixture profiles.
