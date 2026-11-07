# Changelog: grindwright

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
