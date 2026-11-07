# Log

## 2026-11-07: overnight run read, 0.1.11
The first overnight run on a real game stopped on its bound: 25 sessions in about 1 h 50 of the 10 hours allowed, about $33 at list prices, no usage limit met. It finished real work, opened one PR, and left three question sets for the owner. Its largest fault: an item blocked on a question stayed running, so nearly every session needed `--force` and the driver could not stop on the ledger, then three sessions found nothing. Fixed in 0.1.11 with the other repeated notes. Eval re-run still owed.

## 2026-11-06: baseline comparison, 0.1.6
First with and without comparison, on four new cases with fixtures that work in both arms. 11/12 with, 8/12 without, at about twice the cost. The tool says CUT because the gain is inside its noise margin; the ruling is the owner's. It found a real defect: the skill invented another person's review. Fixed by a rule. Details in skills/grindwright/TESTS.md.

## 2026-11-06: eval game evaluated, 0.1.5
Read the owner's answers to the eval game's question sets. Eval sets reached the real inbox because runners did not isolate it, so fixtures now refuse to start without `ASKWRIGHT_HOME`. The extra questions came from a session started with the set's continue prompt, not from an eval agent. Answers led to two skill rules: road drafts include what follows a complete run, and invent content rather than ask for it. Both rest on few answers. The eval game is closed as a live game.

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

## 2026-11-06: rulings put to the owner
All open calls went on one decision page: keep or retire, whether the pilot was played, the overnight start, the first pilot on the second game, local install. No plugin change. The trim waits for the ruling.

## 2026-11-06: rulings answered, 0.1.7
The owner kept the plugin and asked for the trim. Released 0.1.7: `session start` syncs and names the next action, `next --claim` claims, the skill carries command syntax, a named single item stops after that item. Saving not measured. Installed locally. A second real game's art-lane pilot started: three driver sessions, up to 4 hours. Overnight run on the first game stays the owner's to start.

## 2026-11-06: second pilot read, 0.1.8 and 0.1.9, overnight run started
The second game's pilot ran 3 sessions in about 32 minutes and stopped on its session bound. Its repeated fault was the PR cap, fixed in 0.1.8 (`wait-human --pr`, sync follows the PR, `hold --provenance`). A dry run before the overnight start showed an installed grw.py called nearly every plugin missing, because the cache nests a version folder, so the run would have stopped at once. Fixed in 0.1.9. A real game's name had reached LEARNINGS.md on main; removed from the current text, still in git history. The owner started the overnight run on the first game.
