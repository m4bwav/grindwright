# AGENTS.md

Rules for any AI agent working in this repository. `CLAUDE.md` imports this file; `.github/copilot-instructions.md` points here.

## What this is

grindwright: one skill, `skills/grindwright/`. SKILL.md holds the loop and rules, `references/` the details,
`scripts/grw.py` the ledger, selector and gates, `scripts/grind_loop.py` the bounded unattended driver. Research,
decisions, the log and the handoff are under `ai-docs/` (start with `ai-docs/HANDOFF.md`).

## Rules

- `grw.py` and `grind_loop.py` stay standard-library Python 3.9+, UTF-8, LF. Every change gets a test. Run
  `python -m unittest discover -s tests` before committing.
- Project specifics go in a project's profile, never in the plugin. Plugins are called, never copied.
- This repo is public. Real games, people, ledgers, session mining and local paths never go here: no person other than
  the author credit. They live in the maintainer's private sidecar, outside the repo. Examples use made-up names.
- Size budget: `python scripts/budget.py`; SKILL.md under 200 lines.
- Evergreen unit: read `skills/grindwright/evergreen.json` before editing; log changes in its CHANGELOG with the reason,
  lessons in LEARNINGS with Trigger and Hypothesis. Re-run evals after SKILL.md changes. The beat `indie-ai-games` feeds refreshes.
- A release bumps `.claude-plugin/plugin.json`, `plugin.json`, `VERSION` in `grw.py`, `metadata.version` in SKILL.md and the CHANGELOG together.
- Plain short sentences, no em dashes, relative links. No AI attribution anywhere.

## Commands

- Tests: `python -m unittest discover -s tests`
- Evals: `claude plugin eval . --no-publish --trust-plugin --case "trigger-*"`
