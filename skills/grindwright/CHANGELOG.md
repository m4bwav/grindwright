# Changelog: grindwright

## 0.7.4 (2026-11-08)

- `ticket --propose` creates the proposal label when the repository lacks it, instead of failing the issue create.
- `--area a,b` on claim, issue-take and add means two areas; before, it was stored as one path with a comma, so overlap checks missed both.

## 0.7.3 (2026-11-08)

- The crew driver no longer starts a new run in a member's old worktree on yesterday's branch. A clean tree with nothing unmerged moves to a fresh `grind/<member>-<date>` branch off the base; a tree with uncommitted changes or unmerged commits is left as it is and the member gets a new `<member>-<date>` tree.

## 0.7.2 (2026-11-08)

- `ask_py` in the profile names askwright's `ask.py` when askwright is not installed. Before, a machine with askwright only as a clone made `sync` skip every decision page quietly ("askwright not found"), so answered pages never woke their items and runs stopped on "nothing selectable". `sync` and `next` now carry a `warning` naming the stuck items.

## 0.7.1 (2026-11-08)

- A series is called out in every part, not only the newest: `issue-pr --series` and the new `grw.py pr-series` write one table of all parts (what each covers, which is this PR, review order) into every PR of the series, replacing the old table, and add the `series` label.

## 0.7.0 (2026-11-08)

- One PR of truth: `grw.py pr-overlap` lists open PRs and unmerged branches covering the same issue or concept (issue reference, stacking, similar title, branch words). Run before starting and before opening a PR.
- `issue-pr` refuses an overlap unless `--series "<name>"` (adds the `series` label and a "Series: name (part N)" line naming the other parts; stacking allowed) or `--not-duplicate "<why>"`.

## 0.6.1 (2026-11-08)

- Joins the 0.5.0 screenshots work and 0.6.0 claims across computers in one release.

## 0.6.0 (2026-11-08)

- Several computers on one project (`work.remote`, `references/machines.md`): each claim first creates the ref `grind-claim/<key>` on the repository host. Creating an existing ref fails, so one computer wins; renewals and take-overs of expired claims are fast-forward updates, so they have one winner too. The ref's empty commit names machine, session and expiry. `next` defers items another computer holds; `checkpoint` renews; `done`, `drop` and `session release` delete the ref; `sync` marks held items and gives back stale ones of its own; `grw.py remote` lists every claim. On issues, a label (`agent-working`) and one marked comment. `ticket_first` refuses claims on items with no issue or PR, so discovery on both computers goes through the duplicate-checked tracker. Hosts that cannot be reached refuse the claim unless `"offline": "local"`. Four tests with a fake host; a live test on GitHub (four simultaneous creates, one winner). Numbered 0.6.0 because 0.5.0 is in progress on another branch.

## 0.5.0 (2026-11-08)

- Screenshots of visible changes: `done` and `hold` refuse an item on a visible lane (art, animation, video, model, juice, edit, ui, feel, marketing, or a lane with `"visible": true`) without `--shots <files>` or `--no-shots "<why>"`. Shots are kept on the item and in the event, and the run report shows them as thumbnails per item (small local files embedded).
- `grw.py pr-brief [--base] [--head] [--markdown]`: breakdown of a branch's changes by area and kind, a risk score and tier (small, medium, large, very large), and a PR body skeleton whose required sections grow with the tier (risks, reading order, rollback, reviewer checklist, split plan). loop.md "What a reviewer gets" holds both rules.
- `VERSION` string caught up. Four tests.

## 0.4.0 (2026-11-08)

- Run report: when `grind_loop` (alone) or `grind_crew` ends, `scripts/grind_report.py` writes `logs/run-ID.json` and a self-contained page `logs/run-ID-report.html` (plus a markdown summary) and opens it. It shows why each member stopped, in plain words, with its last session's own reason; how far each road milestone and lane got; the PRs opened and updated and the issues opened or touched, from GitHub over the run window; every item worked, with evidence; and every session with time, cost, tokens and a link to its Claude transcript and `claude --resume` id. It also includes charts (work by lane, cost and agent minutes by member, a session timeline). When chainwright is installed it also builds the chainwright tier page for the run and links it.
- On by default. Off: `--no-report` on `grind_loop`, `GRINDWRIGHT_REPORT=off`, `"report": false` in the crew file or profile; `"open_report": false` builds without opening. Rebuild any time: `grind_report.py build --state <folder> [--run logs/run-ID.json]`.
- `grind_loop` records each pass (start, seconds, outcome worked, idle or failed, and the session's id, cost, tokens and model from the JSON output) and returns them as `passes`. Five tests.

## 0.3.25 (2026-11-08)

- `pr-sync` finds merge conflicts on open agent PRs: each conflicting PR becomes one ready item, keyed by head and base commits. Resolve, verify and push to the PR branch; when the resolution needs a person's judgement, comment on the PR explaining the conflict instead. Two tests.

## 0.3.24 (2026-11-08)

- `grind_loop` no-progress guard: a claim or release alone (ready to running and back) no longer counts as progress. An overnight crew ran 7 and 5 sessions after its last real work because idle sessions claimed and released items.

## 0.3.23 (2026-11-08)

- Questions go where the project already talks: issues, PR comments, discussions or the wiki on a repository; askwright when the profile sets `ask_route: askwright`, for media picks, private questions or no repository. A tailnet-served askwright page can be linked from the issue or PR.

## 0.3.22 · 2026-11-08

- `done`, `checkpoint` and `redo` refuse a session whose item is now running in another session: a member whose lease expired while it was slow (not dead) could finish or re-lease an item someone else had claimed. crew.md risk row, test (Kleppmann & Riccomini, Designing Data-Intensive Applications 2nd ed., ch. 9, fencing off zombies).

## 0.3.21 · 2026-11-08

- crew.md: rename or reshape anything other members call in expand-contract steps (add the new form, keep the old as a pass-through, move callers, delete the old only after every open item has merged), since text merges miss a call another branch added to the old name; refactor inside the item that needs it rather than as a refactoring night (Fowler, Refactoring 2nd ed., ch. 2).

## 0.3.20 · 2026-11-08

- crew.md: a failing check gets a cause that fits every observed fact before anyone reverts or blames; checks run cheapest first; merge to main at least daily; share code within a repo, not between independently released repos (Farley, Modern Software Engineering, ch. 5, 7, 13).

## 0.3.19 · 2026-11-07

- crew.md: tests must pass in any order and subset, worktrees share no scratch file, database, port or account; a bug item starts with a failing test shown red before the fix; an item's test list comes first and outside ideas go to the ledger (Beck, Test-Driven Development: By Example, ch. 25 and 26).

## 0.3.18 · 2026-11-07

- crew.md: keep structure and behaviour changes in separate PRs, tidy only what the next change needs, redo a tangle structure first, light checks for reversible changes and full review for irreversible ones (from Beck, Tidy First?).

## 0.3.17 · 2026-11-07

- Priority tiers for bugs and issues: GitHub labels (`P0`-`P3`, `critical`/`high`/`normal`/`low`, `priority: ...`) set `priority` at every sync; no label means normal (tier 2), exactly like `P2`. The selector ranks by tier before score. Within a tier the highest value goes first, and among equal value the straightforward task wins (new plainness nudge: cost S x1.15, L x0.85). `add --priority N`; `issues.priority_labels`, `issues.priority_default`, `priority_pinned`. Three tests.

## 0.3.16 · 2026-11-07

- A milestone counted as surveyed forever once any item named it, so a 12-hour crew run stopped after 12 minutes while four unmet milestones had no open work. Now an unmet milestone with no open work needs a survey every window; `grw.py surveyed <id>` records it and needs `--why` when nothing was found. One test.

## 0.3.15 · 2026-11-07

- `pr-sync`, also run by every `sync` and `session start`: the repo owner's new comments, inline review comments and reviews on the agent's open PRs become one ready item per PR; fix on the PR branch, or in a new PR if it closed. Three tests.

## 0.3.14 · 2026-11-07

- New references/engine-verify.md: engine projects verify on a per-session worktree with its own editor (engines lock the folder, not the machine), install the pinned editor version once, keep a warm worktree pool so the import cache is reused, climb compile, EditMode, PlayMode and live-editor rungs, keep tests off the real save and crash reporters, seed for determinism, and write regression tests that compile on both the buggy and fixed branch and fail on the bug. Linked from SKILL.md, loop.md and crew.md.

## 0.3.13 · 2026-11-07

- crew.md: a red main freezes merges; the breaker owns the fix, gets about ten minutes, then reverts; rebase and rerun checks before merging; never skip a failing test to land an item; one run reports all failures; tighten gates by ratchet (Humble and Farley, Continuous Delivery, ch. 3 and 7).

## 0.3.12 · 2026-11-07

- Road-aware discovery: `discover` lists each road milestone with no open work; `next` returns `survey` and `session check` refuses to stop while a confirmed milestone has never had an item and is not marked `met`. A 12-hour run had stopped after one session with a whole milestone never surveyed.
- `grw.py --version` reported 0.3.8; now matches the plugin.

## 0.3.11 · 2026-11-07

- crew.md: splitting a big change into shards, regenerate conflicted mechanical shards, a baseline of already-failing checks, pattern review of mechanical PRs, an anti-backslide check (Software Engineering at Google, ch. 22).

## 0.3.10 · 2026-11-07

- `require_greenlight` also gates drafted items: approved drafts record who approved them, unapproved ones wait and return to drafted once approved.

## 0.3.9 · 2026-11-07

- `issues.require_greenlight`: only issues a greenlighter labelled are built; the rest wait, re-checked each session start. Approval is not triage: the agent reads every comment first.
- `issue-question`: ask on an approved issue before building; approval stays, the answer brings it back.
- Owners' and greenlighters' comments are direction to follow (work-sources.md).

## 0.3.8 · 2026-11-07

- `ticket --propose`: when everything waits on a person, file the best next work as `proposal` issues that wait for the green-light label instead of stopping; open proposals capped by `work.proposals.open` (default 3). SKILL.md stop step proposes before stopping. `grw.py --version` was stuck at 0.3.6.

## 0.3.7 · 2026-11-07

- `references/crew.md`: done means the planned checks ran; flaky checks are crew defects; diff-selected tests per item, full suite before merge; a failure rate that drops to zero is a smell (book distill: Pezze and Young, Software Testing and Analysis, ch. 3, 20, 22).

## 0.3.6 · 2026-11-07

- `references/crew.md`: size a crew by its serial share (Amdahl) and pull review-side work when the review queue is full (book distill: Dooley, Software Development, Design and Coding, ch. 2 and 12).
- RESEARCH.md: human inspection prior for review caps (ch. 17).

## 0.3.5 · 2026-11-07

- Crew file `discover_first` (crew or project level): the project's first member runs and passes `--discover-first` instead of being skipped on an empty ledger.

## 0.3.4 · 2026-11-07

- `session end` reminder names evergreen-wrapup and says a project prompt's own end steps add to the skill's, never replace them (a run followed its prompt and skipped the wrap-up).
- Work a session finds but leaves goes in the ledger with `add` before stopping; a summary line is not an item.
- `doctor` lists `conflicts`: a lane with `stack_on_pending: true` under a guard that denies stacking.
- `grind_loop --discover-first` runs session 1 even when nothing is selectable, for when a person has just widened the rules.

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
