# Log

## 2026-11-04: 0.1.4, drafts past the cap
Decided the open cap question: past a review cap the loop keeps drafting, bounded at the cap per person, so a long run does not stop on the review queue. Questions are never drafted and no-stacking lanes still wait. Risk accepted: drafts can go stale if a pending answer changes direction, so ask-drafted tells the agent to check first. Also: helpers rank with their users, `log` and `reject`, gate reads text and order guesses.

## 2026-11-03: built 0.1.0
Survey in `ai-docs/research/`. Built grw.py, grind_loop.py, the skill, 16 eval cases, and read-only dry runs on two real games. Script named grw.py because gw.py is reserved for another plugin. Kept the name grindwright: nothing clearly better turned up.

## 2026-11-03: evals
Three eval runs, about $26. Results and limits in skills/grindwright/TESTS.md. Fixed the closed-lane ranking bug they exposed.

## 2026-11-03: write-capable trap runs
plugin eval stays read-only even with --allow-tools, so ran the 10 traps once each through subagents: 9 pass, small-call partial. Fixed discover's cwd bug, added road_warning to next, required guesses in plain replies. Details in skills/grindwright/TESTS.md.

## 2026-11-03: public
Published with fresh history. The earlier history, dry runs, session mining and open decisions on real games stay private with the maintainer. Restored CI on push and pull request, added a banner and a wiki.

## 2026-11-03: 0.1.1, driver guards
Scan notes on silent runaways led to two driver fixes: a per-session time limit, and bookkeeping events no longer count as progress. Re-ran the small-call and busywork traps, both pass after a fixture fix. Scan folded into the survey. Pilot still waits on the owner's answers.

## 2026-11-03: first live pilot, 0.1.2 and 0.1.3
A three-session, four-hour pilot on a real game. The first start crashed before any session because the agent is a .cmd wrapper on Windows (0.1.2). The second ran 2 sessions in about 30 minutes and stopped on the ledger, with items finished on a branch, nothing merged, and 3 questions queued while work moved to other lanes. No usage limit was met, so limit behaviour is still untested. Open design question: the review cap also defers drafting that needs no person until review.

## 2026-11-05: pilot merged
The owner merged the pilot branch. No plugin change this session. The pilot ledger went stale after other sessions worked the same game outside the loop; the selector still reads the review queue as full. Worth fixing if it recurs in the overnight run.

## 2026-11-06: Tiny Colony evaluation queued
The owner answered the eval game's question sets on the real dashboard and wants grindwright to evaluate them. Queued in HANDOFF; nothing evaluated yet.
