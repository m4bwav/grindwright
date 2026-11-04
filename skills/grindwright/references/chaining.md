# Chaining sessions and running unattended

Default is attended: each session ends with one start command for the owner to paste. The prompt never changes; state
lives in HANDOFF.md and the ledger.

Unattended needs the owner's go-ahead on hours, budget and scheduling. The driver is `scripts/grind_loop.py`:

```
python grind_loop.py <continue prompt> --state <state> --cwd <repo> --max-sessions 5 --max-hours 4        # dry run
python grind_loop.py <continue prompt> --state <state> --cwd <repo> --max-sessions 5 --max-hours 4 --go
```

It starts a fresh session per pass and stops on: the ledger allowing a stop, either bound, two passes that change
nothing, a failed session, a session past `--session-minutes` or the `--max-hours` deadline, repeated usage limits, or
missing `--require-text`. Runaways raise no errors, so set `--session-minutes`. Opening and closing a session does not
count as progress. Use `--log <file>` to keep session output, since refused tool calls are worth reading. A dry run
checks that the agent command exists.

Why an outer driver (survey, 2026-11-03, `ai-docs/research/` in the plugin repo):
- Stop hooks are overridden after repeated blocks, the `/goal` judge reads only the transcript, recurring `/loop` tasks
  expire and a self-paced loop is not restored on resume. Fresh sessions from files survive all of that.
- `--permission-mode auto --permission-prompts none` removes AskUserQuestion, so the askwright queue is the only way
  to ask. Refused tool calls are worth reading after a run.
- Documented flags change (`--bare` is to become the `-p` default and drops plugins and hooks). Pin flags, and use
  `--require-text` so a session without the plugin stops the run.
- What `claude -p` does at a subscription usage limit was not documented when checked. The driver's limit detection
  is a text match; test it before trusting a long run.
