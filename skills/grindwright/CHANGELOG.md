# Changelog: grindwright

## 0.3.3 · 2026-11-07

- Command table shows `done ... [--provenance P]` (generated assets are refused without it).
- Session end runs evergreen-wrapup when installed, before HANDOFF and the start command.

## 0.3.2 · 2026-11-07
Fixes from setting up the first film. Video and edit lanes open with cinewright or comfyui-gen, since a render-folder film can be cut with comfyui-gen and ffmpeg alone. `add --blocked-by` refuses an id that is not an item: a milestone name was accepted and would have blocked the item for ever, so an outside gate gets its own item held with `wait-human`. `grind_loop.py` passes the prompt as an absolute path, because the session runs in `--cwd` and a relative path missed. `--version` printed 0.2.2 since 0.2.2.

## 0.3.1 · 2026-11-07
Adding tests is its own lane kind, `tests`: unit, integration, end-to-end, snapshot, property and regression tests, or a check nobody has named yet. Discover points test gaps at that lane and lists the kinds to look for; the default discover list gains "missing tests". A new test must fail on a planted fault before it counts. Reason: the owner asked for test work to be one lane a session can pick.

## 0.3.0 · 2026-11-07
Not only for games. New lane kinds `writing` (everwrite or editwright), `voice` (voicewright) and `edit` (cinewright), and voice counts as an asset that needs provenance. The empty-queue messages now quote the profile's `discover` list instead of "test, balance". New `references/projects.md`: lanes, an example profile, road and oracle ladder for films, video series and stories. Games get writing and voice rows in the lane table. Reason: the owner wants to run long video projects on it, with video, audio and writing plugins in place of the game ones.

## 0.2.3 · 2026-11-07
Fixes from the first live crew. A member whose session ends without the plugin's marker gets one more pass before it stops; a session that ended its turn while a compile ran in the background had stopped its member after one pass. Each member writes its stop reason to its own log at once, since the crew prints results only when every member has ended. An item a stopped member paused stays with that member (`paused_by`), because its work is on that member's branch; `claim --take-over` moves it. Review caps match people without case: a ledger saying "Alex" against a profile key "alex" fell back to the default cap and offered drafts past the real one. `hold` works from ready and again on a drafted item. `issue-accept` and the other issue verbs take the issue number. The skill tells driven sessions not to end their turn on a background job.

## 0.2.2 · 2026-11-07
Crew files can set `worktree_root`. Reason: writing the first real crew file showed the default folder can already be a worktree, which would nest new ones inside it.

## 0.2.1 · 2026-11-07
A project can keep a todo file as its master list while the work runs through issues: `ticket --from-todo`, an `open_tickets` limit and `todo-sync`, which marks each line with its issue and strikes it through on close. Reason: the owner relayed this as a project's chosen way of working, and the plugin only offered a todo file or issues, not both. Tickets and issue comments now obey `text_bans`, as PRs did, and bans match whole words. Reason: found while writing a profile whose bans matter on another person's tracker. Tested with a fake gh only.

## 0.2.0 · 2026-11-07
The owner wants several sessions at once, across projects and on one project, and optional work sources. Sessions have names and their own session files; `claim --area` and lane areas keep them apart, including named resources; non-claim actions are held; one discovery pass serves a crew; `add` refuses look-alikes; `board`, `note`, BOARD.md and WAITING.md; `session check` lists the decisions a stalled run waits on; `session release`; `grind_loop --session-id`; new `grind_crew.py`, which refuses shared state and skips members with no work. New `grw_work.py`: GitHub issue sync and triage, agent-identified replies, PRs linked both ways with both cases argued, bug and feature tickets with duplicate checks, a read-only task list with green light by a named person's label, todo-file mode. Tokens reference points at tokenwright. Not yet run on a live crew or a real tracker: tests use a fake gh. Trigger evals not re-run for this change unless TESTS.md says so.

## 0.1.12 · 2026-11-07
`sync` leaves a part-answered set waiting while its answers are still changing: it frees the item once the person marks the set done or the answers have stood still for 15 minutes. Reason: a pilot session synced a set at 2 of 5 answers and acting then would have split the work.

## 0.1.11 · 2026-11-07
An item blocked on another item no longer counts as running: `claim` refuses it, `sync` and a shave send it back to ready, `session check` ignores it. The driver's fingerprint counts real progress only, not `discover` or a checkpoint on idle work. `discover` names an open lane instead of `gaps`, lists marker locations, skips suggestions the ledger has finished, and walks the repo once with engine caches pruned. `hold --person`. `wait-human` registers its set on the inbox. `sync` frees an item whose set is fully closed and shows `unsure` answers on waiting ones. Reason: the first overnight run, where one blocked item forced `--force` in about 15 of 25 sessions, kept the driver from ever stopping on the ledger, and three sessions at the end rediscovered nothing.

## 0.1.10 · 2026-11-06

Sfxwright, when installed: Hand sound effects to sfxwright when present and read its sounds.json; this plugin's own steps stay as the fallback.

The sound lane stays open when either sfxwright or musicwright is installed. Reason: it closed without musicwright even with sfxwright present. Any-of needs are a nested list; `doctor` also reports sfxwright.

## 0.1.9 · 2026-11-06
Finds plugins in the installed cache, which nests marketplace, plugin and version. Reason: run from an install, `doctor` called nearly every plugin missing and closed their lanes, so a run would have stopped at once. Found in a dry run. A skill outside any plugin, such as askwright here, still needs `GRINDWRIGHT_ASK`.

## 0.1.8 · 2026-11-06
A PR review now counts against the person's cap: `wait-human <id> --pr N` needs no set, and `sync` closes the item when `gh` says merged and reopens it when closed. `hold` takes `--provenance`. Reason: in a three-session pilot the ledger could not see open PRs, so `next` kept offering new reviews and every session ended with `--force` (L-003).

## 0.1.7 · 2026-11-06
Trimmed the bookkeeping: `session start` also syncs and names the next action, `next --claim` also claims, and SKILL.md carries the command syntax so `--help` turns go away. A request naming one item stops after that item. Reason: the owner kept the plugin on the ruling to trim its cost; T-20261106-2 measured x1.98 cost, mostly bookkeeping turns.

## 0.1.6 · 2026-11-06
The skill says to relay only words a person gave. Reason: in the first A/B (T-20261106-2), told "PR 12 looks ready", two of the three runs recorded a review from the PR's owner that the owner never gave. Added four value cases with fixtures that work without the skill, and a checker. Removed another plugin's worth verdict that had been copied into evergreen.json at creation.

## 0.1.5 · 2026-11-06
An eval fixture's profile is marked `eval`, and `session start` and `wait-human` refuse there unless `ASKWRIGHT_HOME` is set. `wait-human` drops the ledger's guess once the page holds it. The skill says not to ask for content it can invent, and road drafts include what comes after a complete run. Reason: the owner's answers to an eval game's question sets, which reached the real inbox.

## 0.1.4 · 2026-11-04
Past a person's review cap, items that need nobody yet come back as `draft`; `grw.py hold` parks them, at most the cap's number per person and never in a no-stacking lane, and `next` offers `ask-drafted` when room opens. A helper ranks with whatever waits on it and clears the value floor if needed. New `log` and `reject`; `discover` lists rejected findings. The guess gate reads `text` and `order`. Reason: the first live pilot stopped after 30 minutes at the cap, which would waste a 10-hour overnight run; the rest are the pilot's open items and L-002 `text-guess-gate-mismatch`.

## 0.1.3 · 2026-11-03
`grw.py show <id>`. The skill now names the `none` rung, the allowed guess confidence and when to force a session end. Reason: notes from the first live pilot, where a report was recorded as `compile` and a lint failed on confidence.

## 0.1.2 · 2026-11-03
The driver finds a .cmd wrapper on Windows, reports a missing agent command even in a dry run, kills the whole process tree on a timeout, and can log session output (`--log`). Reason: the first live pilot crashed before its first session, with a traceback, on a machine where the agent is a .cmd wrapper.

## 0.1.1 · 2026-11-03
The driver now stops a session past `--session-minutes` or the `--max-hours` deadline; before, one hung session could overrun every bound. Opening and closing a session no longer counts as progress; before, the no-progress stop could never fire on a real ledger. A direct owner request in the session is an owner note. The busywork and small-call fixtures have a confirmed road. Reason: runaway reports in the 2026-11-03 scan, and the re-run traps.

## 0.1.0 · 2026-11-03
Created from the kickoff: ledger, selector, gates, driver, skill, evals, dry runs over both games. Reason: stalling on one blocked lane was the real defect in the hand-run sessions.

Fixes from the first eval run: items in a lane closed by a missing plugin are deferred, not ranked; a read-only state folder gives a plain error.

Fixes from the first write-capable trap run (T-20261103-2b): a relative repo resolves against the project, not the shell; `next` warns while the road is unconfirmed; a guess is required in plain replies too. trap-post got a devlog in its fixture. Version unchanged: 0.1.0 is not tagged.
