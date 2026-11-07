# Log

## 2026-11-07: part-answered sets, 0.1.12
Closed the last fault left from the overnight notes: `sync` no longer calls a set ready while its person is still answering. Unit tests only; no live chain has run on this or on 0.1.11. Evals not re-run.

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

## 2026-11-07: owner's note on content feel
The owner merged the overnight PR and asked for grind items on content feel and balance. An audit showed discovery had called feel done while few content rows had any. Filed as L-004 `feel-per-row-blind`. No code change, no release.

## 2026-11-07: owner's "check your reasoning"
A held answer had been filed as "not sure", but its note asked for the reasoning to be checked. Checking it showed the question was wrong: the design doc states the rule and many cards print it. Asked again with the details on a new page. Filed L-008 `absence-claim-unchecked`. No code change, no release.

## 2026-11-07: 0.2.0, crews and work sources
The owner asked for several sessions a night across and within projects, each project's knowledge and logs kept apart, a way to say nothing can move without a decision, tokenwright awareness, GitHub issue handling, todo and task-list modes, and a scouting beat. Built all of it (see CHANGELOG). Chose ledger claims and areas over a lead agent: the survey found plain claims working at scale and heavy orchestration costly, and agent teams cannot run in `-p` mode. Also added an untrusted-author gate, not asked for, because anyone can file an issue on a public repo. L-004 and L-008 are now in the discovery step. Tests only, with a fake gh; no live crew yet.

## 2026-11-07: 0.2.1, a todo file as the master list
The owner answered the crew page: one session on the second game, two on the first, issues on the first, and for the second game a chosen flow where todo lines become issues and the file stays the master list. The plugin offered a file or issues, not both, so added `ticket --from-todo`, an open-ticket limit and `todo-sync`. Tickets and comments now obey `text_bans`. Tested with a fake gh only.

## 2026-11-07: 0.2.2, worktree_root
Writing the first real crew file showed its default worktree folder can already be taken. Added `worktree_root`. The crew file dry-runs clean on real projects: all three members would start. No live crew yet; it waits on the owner's start.

## 2026-11-07: first live crew started

The owner started the first crew on two projects, three sessions in all, with the driver from the installed 0.2.2. Results are not in yet.

## 2026-11-07: 0.2.3, fixes from the first live crew

Read the first crew run while it was still going (three members, two projects). One member stopped after one pass: its session ended its turn while a compile ran in the background, so the plugin marker was missing and the loop read that as a lost plugin. Another member kept being offered an item a stopped member had paused, though its code sat on that member's branch. On the second project the review cap never held because the ledger wrote the person with a capital letter and the profile key was lower case. Fixed all three, plus `hold` from ready or drafted, issue verbs taking the issue number, and stop reasons written to each member's log at once. 114 unit tests pass. Not yet run in a live crew.

## 2026-11-07: 0.3.0, beyond games

The owner asked for long video projects to run on grindwright, using video, audio and writing plugins, and noted game projects could use writing plugins too. The engine already took any lane from the profile; only the wording, the discover messages and the plugin map assumed a game. Added lane kinds writing, voice and edit, made the discover messages quote the profile, wrote `references/projects.md`, broadened the skill text. Two new tests, 116 pass. No video project has been set up yet; the owner picks which one.

## 2026-11-07: 0.3.1, a tests lane

The owner asked that adding tests of any kind be one lane. Added lane kind `tests`, a discover signal aimed at it, docs rows for games and films, one unit test (117 pass).
