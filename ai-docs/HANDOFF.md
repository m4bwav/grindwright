# Handoff

Updated 2026-11-08. Public `m4bwav/grindwright`, v0.6.0 (claims across computers: `work.remote`, `grind-claim/<key>` refs on the host, one winner, fast-forward renew and take-over, `ticket_first`, `grw.py remote`, `references/machines.md`; not yet run in a real two-computer grind. 0.5.0 screenshots is on another branch. 0.4.0 run report: `grind_report.py` page with stop reasons, progress, PRs and issues, sessions, charts and the chainwright tier page, shown when a run ends, on by default; 0.3.26: picture links on private repos use `blob/...?raw=true`; 0.3.25: `pr-sync` raises merge conflicts on agent PRs as items: resolve and push, or comment when a person must decide; 0.3.24: no-progress guard ignores claim and release; 0.3.23: questions go to the repository first, askwright when preferred). Earlier: v0.3.17 released and installed (0.3.17: priority tiers for bugs and issues, untagged = normal, plain work first within a tier; 0.3.16: idle milestones are surveyed every window, `grw.py surveyed`; 0.3.14 engine-verify reference: per-worktree editors, warm pool, batchmode test rungs; 0.3.15 `pr-sync` for owner PR comments; first run on the second game found an owner's issue note and its test lane PR), wiki at 0.1.0 (`ai-docs/notes/2026-11-03-github-wiki.md`). Installed locally.

## State

- Built: `grw.py` (ledger, selector, gates), `grind_loop.py` (bounded driver, dry run by default), the skill, 20 eval cases. Unit tests pass.
- The owner ruled to keep the plugin and trim it. Trim shipped in 0.1.7; its saving is not measured. Evals have not been re-run since.
- Live runs: one pilot and one overnight run on the first game, one pilot on a second. The overnight run stopped on its 25-session bound in under 2 of its 10 hours and met no usage limit, so what `claude -p` does at a limit is still unknown. Drafting past the cap and `wait-human --pr` worked. 0.1.11 and 0.1.12 fix its faults; those fixes have not run in a live chain.

## Next

00000000. 0.3.16 (2026-11-07): the 0.3.12 overnight run stopped after ~12 min of 12 h because milestones with only finished items never needed a survey. Fixed; next live run should survey core, feel, art and launch before stopping. Timing table: all 5 estimates high (10-40 min est vs 6-20 actual); turn that into a grw estimate-correction feature next.

0000000. 0.3.12 (2026-11-07): road-aware discovery and `survey`; the overnight run on the first game was restarted on it. Read its logs: did the survey add real items, did it run near its 12 hours, and what does the estimate-vs-actual table show (owner wants self-timing turned into a grw feature).

000000. 0.3.9 (2026-11-07): approval-gated issues (`require_greenlight`, `issue-question`, owners' comments as direction). Not yet run live. Future lane (owner, not yet): a demo track per game, making, publishing and maintaining a demo; publishing stays the owner's call.
00000. 0.3.4 (2026-11-07): a 4-hour run on the second game did one session and stopped on the ledger (reviews pending); it left found work out of the ledger and skipped the wrap-up. Fixed; not yet run live. Next: a run on the first game, size asked of the owner.
0000. Film run paused by the owner 2026-11-07. A one-hour single-member run on the second game stopped on the ledger after one session (cap full, reviews pending); 0.3.3 fixed two doc gaps it found. Next: a run on the first game, size from the owner.
000. First film project set up and its first run started 2026-11-07 (three driver sessions, 4 hours, state in a separate folder beside the renders; details in the private sidecar). Setup found three faults, fixed in 0.3.2. Read the run's pilot notes next. Wiki covers neither films nor 0.3.x.
00. First live crew read mid-run (0.2.2). Fixed in 0.2.3: one missed marker stopped a member (session ended its turn on a background compile); paused items handed to other members; review cap missed on person case; hold and issue verbs too strict; stop reasons now in each member log. 0.2.3 has not run live. Still open: `scan todo` shows only 10 lines; untrusted workspace ignores project allow lists (no denials cost work this run).
0. 0.2.0 to 0.2.2 added crews, work sources and a todo file as master list, tested with a fake gh only. The owner chose the first crew: three sessions over two projects, with issues live. Crew file, moved state and profiles are ready and dry-run clean, in the private sidecar. The owner started it on 2026-11-07; results not read yet. Design: `references/crew.md`, `references/work-sources.md`, research in `ai-docs/research/2026-11-07-multi-agent-coordination.md`. Beat: `multi-agent-grind` (private beat dir, public-safe), first scan not run.
1. On the next live run, check that the driver stops on the ledger with no `--force`, and that a large session bound is no longer the thing that stops it.
2. Re-run the evals and `evergreen.py worth --ab` on the value cases when a run is worth its cost, to measure the trim. They have not run since 0.1.7.


## Known limits

Claims coordinate across worktrees only when the state folder is outside them; `grind_crew.py` enforces that, a hand-run session does not. Areas are declared by agents and do not stop logical conflicts. Duplicate checks read the newest 100 issues. The green light is a label: profile must name who counts. The physical-sense check is only an instruction, not a gate. `wait-human` accepts `--why` with no question set (needed for PR reviews), so it can skip the page. `road_warning` is advice; `claim` does not enforce it. Drafts past the cap can go stale if a pending answer changes direction; `ask-drafted` only tells the agent to check. Apart from small-call, trap evals have not been re-run since `draft` was added. Eval isolation only covers fixture profiles.
