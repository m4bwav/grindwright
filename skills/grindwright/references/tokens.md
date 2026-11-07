# Spending fewer tokens on a grind

Long runs pay for every token again on each later turn. If tokenwright is installed, its skill has the habits and `tw.py`; call it, do not copy it. The ones that matter most here:

- **Fresh sessions over long ones.** Stop at a natural boundary with `session end --force "<why>"` when context is large; state is on disk.
- **Do not load what the ledger can tell you.** `next` and `board`, not the whole ledger or `BOARD.md`. Read the handoff and the item, not the repo.
- **Search, then read a range.** Trim command output at the source. Do not re-read after your own edit; `tw.py changed <paths>` before a re-read.
- **Batch independent calls in one turn.** Each turn re-sends the context.
- **Use the smallest model for mechanical steps.** Triage, scans and log reading can go to a cheap subagent or local-delegate when the input is large. Skip it for small lookups: a subagent starts cold.
- **Script what repeats.** A step repeated across sessions becomes a script (tokenwright-script).
- **Measure.** After a run, `tw.py score <transcript>` ranks the sinks. Fix the largest. A repeated sink becomes a rule in the project, not a note.
- **Do not cut a check that prevents a retry.** A failed attempt costs more than the check.

In a crew, a second session costs about as much as the first, so add one only if it has separate work. When all that is left waits on a person, stop: idle sessions spend real tokens.
