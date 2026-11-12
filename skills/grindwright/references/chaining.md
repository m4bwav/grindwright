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
missing `--require-text`. Runaways raise no errors, so set `--session-minutes`. The driver checks the ledger before session 1; after widening the rules (drafting past a cap, a new lane), pass `--discover-first` so one session runs and finds the work. Opening and closing a session does not
count as progress. Use `--log <file>` to keep session output, since refused tool calls are worth reading. Pass `--require-text <continue prompt file name>`: the plugin name is often absent from a healthy reply and stops the run as `plugin-missing`. Give the continue prompt a rule that `grw.py next` decides the work, not HANDOFF: driven sessions that read a run of idle HANDOFF entries quit in seconds and defer the top item as "needs a full session" (Arvum, 2026-11-11: two runs stopped `no-progress` with an owner note on top). A dry run
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

## Run report

Every run ends with a report unless the owner turned it off. `grind_loop` run alone and `grind_crew` (one per project) write `logs/run-ID.json`, then `grind_report.py` writes `logs/run-ID-report.html` and `.md` and opens the page:

- why each member stopped, in plain words, with the last session's own `session_end` reason;
- how far each road milestone and each lane got: this run's finished, drafted, asked and added items, and what is still open;
- PRs opened and updated, issues opened and touched, read from GitHub (`gh`, the run's account, the run's window); skipped quietly without `gh`;
- every item worked, with its evidence and links;
- every session: time, cost, tokens, outcome, a link to its transcript and its `claude --resume` id;
- charts: work by lane, cost and agent minutes by member, sessions on a timeline;
- the chainwright tier page for the same run (`run-ID.chain.json` drawn by `chain_report.py`) when chainwright is installed (`$CHAINWRIGHT_REPORT`, the plugin cache, or a clone beside this plugin).

Switches, most specific first: `--no-report` on the driver, `GRINDWRIGHT_REPORT=off`, `"report"` in the crew file, `"report"` in the profile. `"open_report": false` builds without opening (an unattended machine). A failed report never fails the run. Rebuild: `python scripts/grind_report.py build --state <folder> [--run logs/run-ID.json] [--open]`.

### Master page

`python scripts/grind_index.py build [--scan <folder>] [--open]` writes `~/.grindwright/index.html`: every grind session on this computer (from Claude Code transcripts that ran `grw.py session start`, cached) and every driven run, by project, with totals, sessions and hours per project, sessions per day, each run's report link and each session's `claude --resume` command (click to copy). The project comes from the grind profile: the session's own state, a profile whose `repo` holds the folder, or a crew member named in a state's `sessions/`. Every run report also records its run in `~/.grindwright/runs.jsonl` and rebuilds the page. `--scan` once finds run files from before the registry. Sessions in temp folders (eval sandboxes) and in grindwright's own clone are left out; `--include-temp` keeps temp ones. `GRINDWRIGHT_HOME` moves the folder.

## Live status

While a run goes, `grw.py --state <folder> status --serve` opens a read-only local page that refreshes itself: live members and agent sessions, open claims and their age, the run's events, counts, agent cost from the member logs, and what waits on people. `status` alone prints the same as JSON.
