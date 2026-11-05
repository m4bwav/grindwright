# Learnings: grindwright

### L-001 · 2026-11-03 · `state-outside-others-repo`: a ledger in another person's repo can break their rules
- Trigger: a game owned by someone else had a rule that nothing in the repo may imply anyone else is involved; a ledger naming the people there would.
- Hypothesis: the kickoff's "in the game's repo" assumes the owner runs the plugin.
- Rule: when another person owns the repo, keep state outside it, and use text_bans on PR text.
- Evidence: that repo's agent rules, read 2026-11-03.
- Scope: skill
- Status: active · helpful 0 · harmful 0 · last_confirmed 2026-11-03

### L-002 · 2026-11-04 · `text-guess-gate-mismatch`: the wait-human gate refuses valid askwright text guesses
- Trigger: `wait-human` said "no real guess" for text questions whose guess used `text`, the only key `ask.py` lint accepts for that kind; `value`, which the gate accepts, fails the lint.
- Hypothesis: `question_failures` in grw.py reads option, options and value, but not text or order, so rank questions should fail the same way (not tested).
- Rule: fixed in 0.1.4, the gate reads `text` and `order`. Write the key `ask.py` lint asks for.
- Evidence: Tiny Colony set ask/card-style, questions finished and batch, 2026-11-04.
- Scope: skill
- Status: active · helpful 0 · harmful 0 · last_confirmed 2026-11-04
