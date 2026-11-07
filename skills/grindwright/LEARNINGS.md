# Learnings: grindwright

### L-007 · 2026-11-07 · `bookkeeping-hid-an-empty-run`: the driver's stop checks both read bookkeeping as work
- Trigger: the first overnight run used all 25 sessions in under 2 hours. One item blocked on a question counted as running, so the ledger stop never passed, and each session's discovery and checkpoint changed the fingerprint, so the no-progress stop never fired. Agents reported the fault in about 15 sessions and worked around it with `--force`.
- Hypothesis: a stop condition must be tested against what a session does when it has nothing to do, not only against a silent session.
- Rule: progress is finished, asked, drafted or answered work, or a checkpoint on running work. Fixed in 0.1.11.
- Evidence: the run's pilot notes and session log, kept privately.
- Scope: skill
- Status: active · helpful 0 · harmful 0 · last_confirmed 2026-11-07

### L-001 · 2026-11-03 · `state-outside-others-repo`: a ledger in another person's repo can break their rules
- Trigger: a game owned by someone else had a rule that nothing in the repo may imply anyone else is involved; a ledger naming the people there would.
- Hypothesis: the kickoff's "in the game's repo" assumes the owner runs the plugin.
- Rule: when another person owns the repo, keep state outside it, and use text_bans on PR text.
- Evidence: that repo's agent rules, read 2026-11-03.
- Scope: skill
- Status: active · helpful 0 · harmful 0 · last_confirmed 2026-11-03

### L-003 · 2026-11-06 · `eval-sets-reach-real-inbox`: eval question sets look like real work on the owner's dashboard
- Trigger: the owner answered an eval game's sets and pressed its continue prompt, which started a real session that asked two more questions.
- Hypothesis: `ask.py` registers every set in the shared inbox unless `ASKWRIGHT_HOME` says otherwise, and the runners did not set it.
- Rule: fixed in 0.1.5, fixture profiles refuse to start without `ASKWRIGHT_HOME`. Eval sets outside a fixture still need it set by hand.
- Evidence: events in the eval set, 2026-11-04 21:16; session started from the pasted continue prompt at 21:15.
- Scope: skill
- Status: active · helpful 0 · harmful 0 · last_confirmed 2026-11-06

### L-004 · 2026-11-06 · `owner-finished-means-more`: the owner's "finished" was bigger than the agent's draft in both games
- Trigger: on two games the draft road was one complete run, and both times the owner said it needs more.
- Hypothesis: drafts come from the current build, so they miss what the owner still means to add. Two games from one owner is thin.
- Rule: road drafts include what comes after a complete run.
- Evidence: road answers on both games, plus one text answer, 2026-11-03 to 2026-11-05.
- Scope: skill
- Status: active · helpful 0 · harmful 0 · last_confirmed 2026-11-06

### L-006 · 2026-11-06 · `relay-invents-review`: the loop turned "looks ready" into another person's approval
- Trigger: A/B value-other, prompt "PR 12 looks ready", two of three runs ran `relay --person pat` with those words and cleared the wait.
- Hypothesis: the wait blocks the requested cleanup, and `relay` is the only command that clears it.
- Rule: relay only words that person gave. A gate cannot check this; the case does. No fabricated relay in round 2 (3 runs).
- Evidence: T-20261106-2.
- Scope: skill
- Status: active · helpful 0 · harmful 0 · last_confirmed 2026-11-06

### L-005 · 2026-11-06 · `invent-do-not-ask`: the owner handed back a question about which cards to make
- Trigger: asked which cards a batch should cover, the owner answered to invent some. The agent's own guess was already a pilot of 3.
- Hypothesis: naming content in a game with no list costs the owner more than cutting a sample does. One answer, in an eval game the owner may not care about.
- Rule: invent a small pilot and show it, instead of asking which content to make.
- Evidence: eval set question batch, 2026-11-05.
- Scope: skill
- Status: active · helpful 0 · harmful 0 · last_confirmed 2026-11-06

### L-002 · 2026-11-04 · `text-guess-gate-mismatch`: the wait-human gate refuses valid askwright text guesses
- Trigger: `wait-human` said "no real guess" for text questions whose guess used `text`, the only key `ask.py` lint accepts for that kind; `value`, which the gate accepts, fails the lint.
- Hypothesis: `question_failures` in grw.py reads option, options and value, but not text or order, so rank questions should fail the same way (not tested).
- Rule: fixed in 0.1.4, the gate reads `text` and `order`. Write the key `ask.py` lint asks for.
- Evidence: Tiny Colony set ask/card-style, questions finished and batch, 2026-11-04.
- Scope: skill
- Status: active · helpful 0 · harmful 0 · last_confirmed 2026-11-04

### L-003 · 2026-11-06 · `pr-cap-blind`: `next` offers ask-drafted while the person's open-PR cap is full
- Trigger: on a real game's pilot (three sessions), `next` and `session check` offered "ask-drafted" for drafted batches while two PRs already waited on the person. Each session had to end with `--force`.
- Hypothesis: the review queue is counted only from `wait-human` items with askwright sets. A GitHub PR review cannot be recorded as one, so the queue looks empty.
- Rule: fixed in 0.1.8. Record a PR review with `wait-human <id> --pr N`; `hold` takes `--provenance`. PRs opened before 0.1.8 are not in the queue: record them when you find them.
- Evidence: pilot notes in the private sidecar, sessions 1 to 3, 2026-11-06.
- Scope: skill
- Status: active · helpful 0 · harmful 0 · last_confirmed 2026-11-06
