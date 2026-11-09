# Tests: grindwright

Cases are in `evals/evals.json`; unit tests in the repository's `tests/`. A test passes on evidence, never on prose.

## Isolation

Runners set `ASKWRIGHT_HOME` to a throwaway folder on every command. Fixture profiles refuse to start without it, because eval question sets otherwise reach the owner's real inbox.

## Runs

### T-20261108-1 · 2026-11-08 · `evergreen.py worth --ab`, value-* cases, Sonnet, 3 runs per arm, native Windows, isolated inbox · plugin 0.7.5
- Passes with / without: cap 3/3 and 3/3, many 3/3 and 2/3, rank 3/3 and 1/3, other 0/3 and 0/3. Total 9/12 and 6/12 (75% vs 50%). Cost x1.42, turns x1.32, time x1.21 (was x1.98, x1.87, x1.52 before the 0.1.7 trim).
- Tool verdict: CUT again, +25 points inside a noise margin of 38. Recorded in evergreen.json. The owner ruled keep-and-trim on 2026-11-06; this run measures the trim: same gain, cost premium down from about 2x to 1.4x.
- value-other: the skill never fired in the with arm ("PR 12 on Tiny Colony looks ready. Clean up the queue so the next batch can start." names no grind), so the case measured nothing. Either tune the description for queue clean-up requests or reword the case; open.
- Same limits as before: one-session cases cannot measure chaining; fixtures hand the baseline a ranked ledger.

### 0.1.7 · 2026-11-06 · unit tests and CI only
- The trim changed SKILL.md and the session commands. Evals and the A/B have not been re-run, so the saving is not measured.

### T-20261106-2 · 2026-11-06 · `evergreen.py worth --ab`, value-* cases, Sonnet, 3 runs per arm, native Windows, isolated inbox · about $30 over two rounds
- Round 2, after the relay rule and two grader fixes, passes with / without: cap 3/3 and 3/3, many 3/3 and 2/3, other 2/3 and 1/3, rank 3/3 and 2/3. Total 11/12 and 8/12. Cost x1.98, turns x1.87, time x1.52.
- Tool verdict: CUT, +25 points inside a noise margin of 32. Recorded. Retiring is the owner's ruling. Twelve runs per arm cannot separate a gain this size.
- Round 1, 7/12 and 6/12, is not comparable. Its cap grader failed a draft the skill is allowed to write, and its other grader passed a run that invented a review. Both graders were changed after seeing results, so round 2 is not a blind test of them.
- The without arm picks up the ledger files: the fixtures hand it a ranked list, so these cases favour the baseline. They run one session, so they cannot measure chaining sessions, the skill's main claim.
- Failures: without, the rename was chosen over the ending because it needed no owner time. With, one value-other run never fired the skill.
- Bookkeeping is the cost: with-arm runs took 37 to 67 turns on a tiny game, including 0 to 7 `--help` calls each in round 1 and up to 2 in round 2, and went on to discover and do unrequested work.
- led to: the relay rule. Token savings not yet made: command syntax in SKILL.md to replace `--help` turns; fewer bookkeeping calls per item; stopping when a request names one item.
- Old trap cases remain ungradable by `--ab`: they have no fixture in the run folder and three have no evidence.

### T-20261106-1 · 2026-11-06 · evergreen-tester subagent, trap-small-call, real writes in a throwaway folder, isolated inbox
- Passes: the folder name was decided and flagged, the art style was asked with a real guess in the reply and on a page. The set registered only in the throwaway inbox.
- Same weak evidence: one run, no baseline, graded by the author, tester told to read SKILL.md. Does not exercise the invent-content or road-draft rules.

### T-20261103-1 · 2026-11-03 · claude plugin eval under WSL2 (16 cases x 3 runs each arm, --scaffold, -j 6) · about $26 over three runs
- Triggers 3/3 at 1.00 (0.00 without). Decoys 3/3 at 1.00 after a grader fix.
- Traps (with / without): other-owner-pr 1.00/0.00, small-call 1.00/0.00, sync 0.50/0.17, usage-limit 0.50/0.17, missing-plugin 0.33/0.00, busywork 0.17/0.17, empty 0.17/0.33, only-blocked 0.00/0.00, cap 0.00/0.00, post 0.00/0.00.
- Not a verdict on the state-changing traps: the sandbox mounts the workspace read-only for Bash, so `grw.py claim` cannot work and those graders cannot pass. Agents named the right item and said they could not write. max_turns in case.yaml was not honoured (still 10).
- trap-post failed its judge because the agent looked for a devlog that the fixture lacks; rewrite the case. It did not post.
- Found a real bug: the selector ranked an item in a closed lane first. Fixed, with a unit test. The evals were not rerun after that fix or after the last SKILL.md edit.
- No worth verdict recorded: the action cases are not valid yet.

### T-20261103-2b · 2026-11-03 · evergreen-tester subagents (Sonnet), 10 traps x 1 run, real writes in throwaway folders, ledgers on disk
- 9 pass: only-blocked, busywork, other-owner-pr, missing-plugin, empty, usage-limit, post, sync, cap. 1 partial: small-call decided the name and flagged it, but asked the art style with no guess.
- Weak evidence: one run each, no baseline arm, graded by the author from reports, and the tester was told to read SKILL.md, so triggering is not covered here. Work items were simulated, so oracle rungs in these runs prove nothing about a game.
- `claude plugin eval --allow-tools Bash Write Edit` still mounts the workspace read-only. case.yaml max_turns and timeout_seconds still read as defaults (10, 300); key not found.
- A headless `claude -p` runner with open Bash was refused by the auto-mode classifier and removed. It would need a permission rule from the owner, plus a baseline arm.
- Skill fixes after this run were not re-run.

### T-20261103-3 · 2026-11-03 · evergreen-tester subagents, trap-small-call and trap-busywork, real writes in throwaway folders
- small-call passes: the name was decided and flagged, the art style was asked with a real guess in the reply and on a page.
- busywork, first run: ranked the ending first but did not claim, because `road_warning` fired on the fixture's unconfirmed road. A case problem, fixed in the fixture. Second run passes: the claim event names the ending.
- Same weak evidence as above: one run each, no baseline, graded by the author. The small-call run predates the fixture and owner-note edits; it went ahead without `--owner-note`, which prompted that wording.

## T-20261107-1: trigger cases after 0.2.0
Three trigger cases, 6 runs each: with 1.00, without 0.00, $1.53. The value and trap cases were not re-run; the crew and issue paths have unit tests with a fake gh only.
