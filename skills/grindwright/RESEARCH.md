# Research: grindwright

## Current understanding
Full survey with sources: `ai-docs/research/2026-11-03-autonomous-indie-dev-survey.md` in the repository. Session evidence from two real games is kept private; its findings are in SKILL.md and `references/loop.md`. No game found shipped from truly unattended work; verification and human taste are the limits. Fresh sessions from an outer driver beat Stop hooks and `/loop` as the chain.

## Open questions
- What `claude -p` does at a subscription usage limit (undocumented when checked 2026-11-03).
- Review caps and batch sizes: no agent-era study found; the numbers are guesses to tune. Human prior from inspection studies (Dooley 2017, ch. 17): 200 to 500 lines per review, about 125 to 200 lines an hour, two hours at most; pre-agent, so a starting point only.

## Search plan
Subject: the beat `indie-ai-games` signals and its "Unattended indie dev" searches. Tooling: Claude Code headless, hooks and permissions docs; `--bare` default change. Practice: Beads, Gas Town, game studio templates. Testing: evergreen-test.
