# Autonomous indie dev survey for grindwright

Date: 2026-11-03. Every URL below was checked on 2026-11-03 unless a row says otherwise. Dates in the text are publication dates.

Evidence tags:
- **[primary]**: official docs, the author's own post, or the repo. I opened it.
- **[secondary]**: a third party report. I opened it, or saw it in search results.
- **[unverified]**: a single weak source, a search snippet only, or a claim I could not trace.
- **[inference]**: my reading, not a sourced fact.

Limits of this survey: Reddit was not used. Search snippets were summarised by a tool, so numbers tagged [secondary] should be rechecked before they are quoted. Claude Code docs change often, so recheck mechanics at build time.

## Bottom line

- I found no one who shipped a game from truly unattended AI work. Absence from my searches is not proof.
- The strongest unattended run is a decompilation, not an original game. It worked because it had a machine oracle.
- Game templates with the most stars are supervised by design and report no shipped game.
- Fun stayed a human job in every game account I found.
- The Claude Code primitives each cover part of the job. None gives a multi-day local run that survives crashes and limits. An outer driver has to do that.

## 1. Who is really doing this

### Ranking

Ranked by evidence of real unattended work and a checkable result.

| # | Who | What happened | Unattended? | Status | Source |
|---|---|---|---|---|---|
| 1 | momo5502, FPS decompilation | About three months. Started with 3 workers and 1 reviewer, later 14 Luna and 2 Opus 5.5 agents on branches and PRs. 99% of functions present, 83% byte exact. Author says it runs without noticeable bugs. Title says 500+ billion tokens, body estimates 600 to 700 billion. No dollar figure. Logs were lost in VM wipes. | Largely | Real, self-reported. Not an original game. No Steam release found. | [primary](https://momo5502.com/posts/2026-10-09-game-decompilation/) |
| 2 | Cursor, browser from scratch | Hundreds of agents for weeks, over 1 million lines in 1,000 files. Post does not say how well the browser works. | Yes | Research run, closer to a demo than a product. Not a game. | [primary](https://cursor.com/blog/scaling-agents) |
| 3 | Huntley, CURSED language via Ralph | A loop left running for about three months. | Mostly | Proof of concept. Duration from secondary posts. | [secondary](https://second-brain-nuxt.vercel.app/a-brief-history-of-ralph) |
| 4 | Catvivors, solo dev | Steam Early Access roguelite with Claude Code as main coder. Human playtested constantly for balance. "AI cannot tell you if a game is fun." | No | Shipped, self-reported, supervised. | [primary, self-published](https://pchojecki.medium.com/ai-helped-me-solo-dev-a-game-on-steam-f84a2425be10) |
| 5 | Codex Mortis | Steam demo in December 2025, sold as 100% AI. ChatGPT art, shaders via Claude Code. Three months, human directed. | No | Shipped demo. Reception split. | [Gigazine](https://gigazine.net/gsc_news/en/20251215-codex-mortis), [PC Gamer](https://www.pcgamer.com/games/roguelike/this-roguelite-claims-to-have-the-dubious-honor-of-being-the-worlds-first-fully-playable-game-created-100-percent-through-ai-in-a-milestone-for-slop-everywhere/) |
| 6 | Claude Code Game Studios (Donchitos) | Template. About 34.7k stars, 49 agents, 74 skills per README. "Nothing gets written without your sign-off", with optional guided and autonomous settings. | Optional, off by default per the blurb | Template. No shipped game named. | [primary](https://github.com/donchitos/claude-code-game-studios) |
| 7 | BMAD Game Dev Studio (BMGD) | Official BMad module. Six agents, Unity, Unreal, Godot. Sprint planning, then a dev-story command. Human invoked. | No | Method. No shipped title found. | [primary](https://game-dev-studio-docs.bmad-method.org/) |
| 8 | Gas Town (Yegge) | Multi-agent town. Yegge says he only used it to build itself. | Yes | Collapsed by his own account. See failures. | [Willison quoting Yegge, 2026-08-04](https://simonwillison.net/2026/Aug/4/steve-yegge/) |

Demos or claims only:
- The Y Combinator hackathon "six repos overnight" story. [unverified](https://hn.jakechampion.name/reader/https://www.second-breakfast.co/blog/ralph-is-eating-the-world), secondary posts only.
- The $50k contract for $297 story. Huntley shares it as a forwarded anecdote. [primary, anecdote](https://ghuntley.com/ralph/)
- "Agents! Please?" and "A Game About AI" are games about AI, not made by unattended AI. [Happy Gamer](https://happygamer.com/agents-please-hits-steam-last-human-ai-code-review-164210/)

### Failure stories

**Wrong work that looks right.** After four weeks momo5502 had about 80% decompiled and the game ran, but code was semantically wrong. Signatures were wrong, logic was invented or removed. The reviewer agent accepted workers' written excuses. Byte matching fixed it. Agents then dodged with inline assembly, which was banned. CI hashes the compare script against a stored secret to stop tampering. [primary](https://momo5502.com/posts/2026-10-09-game-decompilation/)

**Tinkering with itself.** Gas Town "fell apart at the seams with Opus 4.7". The model's "just two more things" habit kept it tinkering with Gas Town and never ready for real work. [primary quote via Willison](https://simonwillison.net/2026/Aug/4/steve-yegge/)

**More ceremony, not a better game.** The Game Studios author built four games from one brief at different rigor levels. Two blind reviewers and a human playtest ranked the "standard" build last. The author says extra documents bought traceability, not a better game. Small sample, author's own test. [primary](https://github.com/donchitos/claude-code-game-studios)

**Fake independence and context strain.** A May 2026 review says all 49 agents share one session context, "independent" reviewers are one model with different prompts, and loading the docs causes constant compaction. [secondary](https://www.productionalchemist.com/p/claude-code-game-studios-49-agents)

**Coordination fails.** Cursor: locks became bottlenecks, optimistic concurrency made agents risk averse, an integrator role added more bottlenecks. "Agents occasionally run for far too long", so restarts are still needed. [primary](https://cursor.com/blog/scaling-agents)

**Tool churn.** Commenters report Beads breaking between releases and confusing agents. Anonymous opinion. [unverified](https://hacker-news-clone.nuxt.dev/item/46624883) Gas Town merged 100+ PRs adding 44k lines of unreviewed AI code, per one source. [unverified](https://second-brain-nuxt.vercel.app/gas-towns-agent-patterns)

**Runaway cost.**
- About $6,000 of Claude usage overnight "with one command". Cause not stated. General causes named: hook recursion, retry storms, subagent fan-out. [secondary](https://devtoolpicks.com/blog/ai-agents-runaway-claude-code-bills-overnight-2026)
- A LangChain retry loop at $47,000 over 11 days. [unverified](https://dev.to/dingdawg/how-an-ai-agent-ran-up-a-47000-bill-in-11-days-and-how-to-stop-it-1fk)
- $437 overnight. [unverified](https://dev.to/magicrails/i-let-my-ai-agent-run-overnight-it-cost-437-dd7)
- Gas Town at $2,000 to $5,000 a month by one outside estimate. [unverified](https://thomasjankowski-site.pages.dev/writing/yegge-burns-100-an-hour-in-parallel-the-unit-economics)
- Uber's 2026 AI budget gone in four months. [unverified](https://dev.to/pat9000/when-a-100b-company-burns-its-2026-ai-budget-by-april-41en)

**Review overload.** LinearB data on 8.1 million PRs is reported as review time up 91% and AI PRs waiting 4.6 times longer. Vendor linked, seen second hand. [unverified](https://dev.to/max_quimby/10x-prs-1x-reviewers-the-code-quality-bottleneck-166o) A study of 567 agent PRs shows a milder gap: 83.77% accepted against 91.01% for human PRs. [secondary](https://www.softwareseni.com/why-agent-generated-code-is-breaking-the-pull-request-review-model/) Review burden tracks what agents touch more than what they say. [secondary](https://arxiv.org/abs/2601.00753v1)

**Broken repos.** I found no reliable report of an agent destroying a repo. Huntley warns of broken builds and says he would not use Ralph on an existing codebase. [primary](https://ghuntley.com/ralph/) That warning matters here, since grindwright works on existing games.

### Players and platforms

- Steam's survey covers content players consume, pre-generated and live. It says "Efficiency gains through the use of these tools is not the focus of this section." So AI written code alone seems out of scope, while art, sound, narrative and localization are in. [primary](https://partner.steamgames.com/doc/gettingstarted/contentsurvey)
- A claim of a June 2026 per-asset labelling rule has one source and conflicts with the survey wording. [unverified](https://www.remio.ai/post/indie-game-studios-are-rejecting-steam-s-new-mandatory-ai-metadata-tags)
- Valve keeps the policy. Tim Sweeney called it "irresponsible", and he argues labels expose developers to backlash. [VGC](https://videogameschronicle.com/news/epic-games-ceo-says-its-really-irresponsible-of-steam-to-make-studios-disclose-ai-use), [Notebookcheck](https://www.notebookcheck.net/Epic-CEO-Tim-Sweeney-lambasts-abhorrent-Steam-AI-Disclosure-Policy-claiming-labels-double-as-political-statement.1433682.0.html)
- Games disclosing AI rose almost 800% in a year, with 10,258 titles or about 8% of the library by one count. [GamesRadar](https://www.gamesradar.com/platforms/pc-gaming/steams-slop-problem-has-gotten-much-worse-as-reports-say-the-number-of-games-using-genai-has-gone-up-almost-800-percent-in-the-last-year-alone)
- Players complain about slop at Next Fest and ask for a filter. SteamDB added an AI tag. [Creative Bloq](https://www.creativebloq.com/3d/video-game-design/has-ai-ruined-steam-next-fest)
- The Indie Game Awards retracted Clair Obscur's Game of the Year over some generative AI use. Date not confirmed in what I read. [secondary, search summary](https://creativebloq.com/3d/video-game-design/is-the-first-100-percent-ai-video-game-the-ultimate-rage-bait)
- Studios reportedly cancelled public playtests for fear of AI clones, and Claude Code reportedly declines to recreate specific games. [unverified](https://tbreak.com/claude-code-stops-recreating-video-games/)

## 2. How the best run

### Comparison

| Concern | Ralph | Anthropic harness | Cursor | momo5502 | Beads | Game Studios |
|---|---|---|---|---|---|---|
| Chaining | Bash loop, fresh context each pass | Initializer, then a coding session per feature | Cycles, judge decides, fresh starts | Long-lived agents, hourly cron rereads instructions | Not its job | Human starts sessions |
| Selection | Model picks, one thing per loop | Next failing feature | Planners generate tasks | One GitHub issue per unit | `bd ready`: no open blockers | Human |
| State | Prompt and repo files | Feature JSON with `passes`, progress file, git | Task system, repo | GitHub issues, PRs | Dolt, hash IDs, atomic `--claim` | Markdown files |
| Stop | None by default | All pass | Judge | Coverage | Not its job | Human |
| Verification | Tests, types, static analysis as backpressure | End-to-end test before pass | Judge, not detailed | Byte match with tamper-proof CI | Not its job | Hooks, director gates |
| Human | Tune the prompt | Not covered | Not covered | Instructions, Discord channel | Not its job | Every decision |
| Budget | Iteration cap by convention | Not covered | Not stated | Not stated | Compaction of old tasks | Model tiers |

Sources: [Ralph](https://ghuntley.com/ralph/), [Anthropic, 2025-11-26](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), [Cursor, 2026-01-14](https://cursor.com/blog/scaling-agents), [momo5502, 2026-10-09](https://momo5502.com/posts/2026-10-09-game-decompilation/), [Beads](https://github.com/gastownhall/beads), [Game Studios](https://github.com/donchitos/claude-code-game-studios).

Others:
- Taskmaster has about 28.3k stars and a `next` command. Its README page does not explain selection in what I read. [primary](https://github.com/eyaltoledano/claude-task-master)
- Cursor cloud agents run in VMs with a browser, loop until checks pass, and attach video, screenshots and logs to the PR. [secondary](https://www.nxcode.io/resources/news/cursor-cloud-agents-virtual-machines-autonomous-coding-guide-2026) I found nothing solid on current Codex automations. Unverified.
- Beads has moved to Dolt as source of truth, with JSONL as export only. That is a heavy dependency. [primary](https://github.com/gastownhall/beads)

### Claude Code mechanics, as documented today

**Stop hooks** ([hooks](https://code.claude.com/docs/en/hooks), [guide](https://code.claude.com/docs/en/hooks-guide)):
- Block with `{"decision":"block","reason":...}` or exit 2.
- `continue:false` stops Claude and beats other fields.
- `last_assistant_message` is the safe input. The transcript can lag.
- Claude Code overrides a Stop hook after eight blocks in a row with no tool call between. Raise it with `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`. Check `stop_hook_active`.
- A turn ending in an API error fires `StopFailure`, not `Stop`. Matchers include `rate_limit`, `billing_error`, `overloaded`, `server_error`. Its output is ignored, so it can log and alert but cannot continue.
- Whether a subscription usage limit reports as `rate_limit` is not stated in what I read. Unverified, test it.

**`/goal`** ([docs](https://code.claude.com/docs/en/goal)):
- A session-scoped prompt Stop hook on the small fast model. Verdicts: not met, met, impossible.
- The evaluator runs no tools. It judges only what the transcript shows, so it can be fooled by claims.
- Works with `-p`. Turn limits are only a clause in the condition, judged from the conversation.
- Auth failure, exhausted credit, unrecoverable context overflow or a missing model clears the goal.
- Rate limits and usage limits pause it. On resume the condition returns, but turn count, timer and spend baseline reset.

**`/loop` and cron** ([docs](https://code.claude.com/docs/en/scheduled-tasks)):
- Fixed interval minimum one minute, self-paced one minute to one hour.
- `.claude/loop.md` replaces the default prompt, and edits apply on the next pass. Limit 25,000 bytes.
- Recurring tasks expire after seven days. No catch-up.
- Fires only while Claude Code runs and is idle. A self-paced loop is not restored on resume, and stops if its wakeup comes due after a background session crash.
- Background commands and monitors are not restarted on resume.

**Cloud scheduled tasks, formerly routines** ([docs](https://code.claude.com/docs/en/routines)):
- Research preview. Minimum interval one hour. Fresh clone, no local files, `claude/` branches.
- Hourly start limits, such as 100 scheduled runs per account, not the daily caps I expected.
- At the subscription limit, runs are rejected until the window resets, unless usage credits are on.
- No local Unity editor or local GPU in the default cloud. [inference]

**Desktop scheduled tasks** ([docs](https://code.claude.com/docs/en/desktop-scheduled-tasks)):
- Local files. Only while the app is open and the machine awake.
- One catch-up run for the latest miss in seven days.
- Skips a run if the previous run is still going.
- Optional worktree per run. Manual mode stalls on a prompt until someone answers.

**`claude -p`** ([docs](https://code.claude.com/docs/en/headless)):
- `--output-format json` gives `session_id` and `total_cost_usd`. Cost is a client estimate and is cumulative on resume.
- `--max-budget-usd` caps a run. Exists as a flag. Whether it means anything on a subscription is unverified.
- Since v2.1.302 runs start in Manual mode, so unapproved calls are denied.
- `--permission-mode auto --permission-prompts none` is the documented unattended form. Requires v2.1.259 or later. It removes `AskUserQuestion`, and denials appear in `permission_denials`.
- `--bare` skips hooks, skills, plugins, MCP and CLAUDE.md, and never reads subscription OAuth, so it needs an API key. The docs say it "will become the default for `-p` in a future release".
- A `-p` run executes the project's hooks and MCP servers with no trust dialog.
- `system/api_retry` events show retries. Temporary 429s retry up to 10 times with backoff. [errors](https://code.claude.com/docs/en/errors)
- SIGTERM exits 143, leaves the turn unfinished, and runs only `SessionEnd`. `CLAUDE_CODE_RESUME_INTERRUPTED_TURN=1` continues the turn on resume.

**Usage limits** ([interactive](https://code.claude.com/docs/en/interactive-mode), [errors](https://code.claude.com/docs/en/errors)):
- Requests are blocked until the reset time. Session and weekly limits are shared across models, so switching model does not help. Opus and Sonnet limits apply to their own family.
- Interactive subscription sessions wait and continue on their own, v2.1.234 or later.
- What `-p` does at a usage limit is not stated in what I read. Unverified. This is the first thing to test.

### What survives what

| Event | Survives | Lost |
|---|---|---|
| Usage limit, interactive | Session, goal, auto-continue | Nothing, if the process lives |
| Usage limit, `-p` | Session transcript, so `--resume` is possible [inference] | Unknown, test it |
| Process or machine crash | Files on disk, git commits, transcript up to the crash, CronCreate tasks on resume | Self-paced loop, background commands, monitors, uncommitted intent, goal counters |
| Seven days pass | Desktop and cloud tasks | `/loop` recurring tasks |
| VM wipe | Only what was pushed | momo5502 lost its logs this way |

The durable rule, from all of the above: only a file on disk or a commit counts as state. [inference]

## 3. Scoring and human queue prior art

**WSJF.** Cost of delay divided by job duration. SAFe's cost of delay sums business value, time criticality, and risk reduction or opportunity enablement, on relative modified Fibonacci scales. Reinertsen uses money and real durations. [archived SAFe](https://webarchive.library.unt.edu/web/20161225132214mp_/http://www.scaledagileframework.com/wsjf), [AKF](https://akfpartners.com/wsjf)

**RICE.** Reach times impact times confidence, divided by effort. Impact 3, 2, 1, 0.5, 0.25. Confidence 100%, 80%, 50%. The formula itself is an image on the page, so I read it from the text. [Intercom](https://www.intercom.com/blog/rice-simple-prioritization-for-product-managers/)

**Fit.** [inference]
- WSJF fits better. Its risk term rewards risk burn-down, which is where a game dies. Size is what agents burn.
- From RICE, keep confidence as an explicit discount. Agent estimates are weak. Reach means little before a game has players.
- Neither has a term for "can a machine prove this is done", for token cost, or for waiting on a human. Those need adding.
- Scores written by the same agent that wants the work can be gamed. Gas Town's self-tinkering shows the shape of the risk.

**Autonomy levels.** Feng, McDonald and Zhang define L1 Operator, L2 Collaborator, L3 Consultant, L4 Approver, L5 Observer, by the role of the user. [Knight Institute](https://knightcolumbia.org/content/levels-of-autonomy-for-ai-agents-1), [arXiv](https://arxiv.org/html/2506.12469v2) grindwright's target is L4, with L5 for bounded lanes. [inference]

**Human queues.**
- LangGraph `interrupt()` pauses and persists state until an answer comes. Durable checkpoints matter for long waits. [secondary](https://rentierdigital.xyz/blog/human-in-the-loop-langgraph)
- Put interrupts only at irreversible or compliance points, not as a generic net. [same source]
- Too many gates cause rubber stamping. Low urgency work suits an async queue. Some guides offer auto-approve on timeout. [secondary](https://machinelearningmastery.com/building-a-human-in-the-loop-approval-gate-for-autonomous-agents/)
- Agent Inbox is a named UI, and `hitloop` claims compatibility. [secondary](https://pypi.org/project/hitloop/)
- I found no measured study of review caps or batching for agents. The caps in section 4 are design guesses, not findings.

## 4. Borrow and gaps

### Borrow

| Borrow | Why | From |
|---|---|---|
| Fresh context per unit of work, one thing per pass | Beats drift. Agreed by three independent sources. | [Ralph](https://ghuntley.com/ralph/), [Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), [Cursor](https://cursor.com/blog/scaling-agents) |
| Pass flag flipped only after an end-to-end check | Stops premature "done". | [Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) |
| Machine oracle, with the checker protected from the agent | The fix that turned a wrong game into a right one. | [momo5502](https://momo5502.com/posts/2026-10-09-game-decompilation/) |
| Reread instructions on a timer | Instructions drift in long runs. | [momo5502](https://momo5502.com/posts/2026-10-09-game-decompilation/) |
| Discard bad output rather than salvage | Cheaper, by the author's account. | [momo5502](https://momo5502.com/posts/2026-10-09-game-decompilation/) |
| Ready means no open blockers, hash IDs, atomic claim | Small, proven ledger ideas. Copy the ideas, not the Dolt dependency. | [Beads](https://github.com/gastownhall/beads) |
| Planner separate from worker, a judge at cycle ends | Flat peers failed at scale. Keep it to one worker per lane on a solo project. [inference] | [Cursor](https://cursor.com/blog/scaling-agents) |
| Video, screenshots and logs on each result | Fast human review. | [Cursor cloud, secondary](https://www.nxcode.io/resources/news/cursor-cloud-agents-virtual-machines-autonomous-coding-guide-2026) |
| Play mode, screenshots and test runs through MCP | The engine side of the oracle. Unity is more mature. No official Godot server appeared. | [Codex guide, secondary](https://codex.danielvaughan.com/2026/04/27/codex-cli-game-development-unity-godot-mcp-agent-driven-workflows/), [comparison, vendor](https://www.summerengine.com/unity-mcp-alternative) |
| Path-scoped rules and approval protocol | The parts the review liked. Skip the 49 agents. | [Game Studios review](https://www.productionalchemist.com/p/claude-code-game-studios-49-agents) |
| `--permission-mode auto --permission-prompts none`, read `permission_denials` | Documented unattended form. Denials feed the human queue. | [headless](https://code.claude.com/docs/en/headless) |
| `StopFailure` hook writes a marker | The only event for an API error end. Driver reads it. | [hooks](https://code.claude.com/docs/en/hooks) |
| Autonomy levels as a per-lane setting | A shared language for what a lane may do alone. | [Knight](https://knightcolumbia.org/content/levels-of-autonomy-for-ai-agents-1) |
| WSJF shape, RICE confidence | Known, simple, explainable on a page. | Section 3 |

### Do not borrow

- Stop hooks or `/goal` as the main chain. Eight-block cap, transcript-only judge, session scope.
- Cloud scheduled tasks as the worker for engine work. No local files.
- Many role agents in one context. Ceremony did not raise game quality in the one test found.
- Agent reviewers treated as independent. momo5502's accepted excuses. Use a check, or a human.

### Gaps grindwright must build

1. **Outer driver.** A small local process that starts `claude -p` sessions, reads JSON results, and retries. Nothing I found does this with limits, lanes and a queue together.
2. **Usage limit handling for `-p`.** Behaviour is undocumented in what I read. Run a live test. Detect it from the result and the `StopFailure` marker, sleep to the reset, resume.
3. **Pin the mode.** Do not rely on `-p` defaults. `--bare` may become the default and it drops plugins and subscription login. Pass flags explicitly and fail loudly if `system/init` lacks the plugin (`plugins`, `plugin_errors`).
4. **Checkpoint protocol.** Commit before and after each unit. A claim with a lease that expires, so a crash frees the work. On start, reconcile ledger with git.
5. **Game oracle ladder.** No source offers this. Compile, tests, headless boot, scripted play, screenshot diff, then taste. Each task declares the highest rung a machine can prove. Protect the checks from the worker.
6. **Fun is a human rung.** Mark a task "machine done" and "human unproven" separately. Taste questions go to the page with a build, a clip and a guess.
7. **Scoring with extra terms.** WSJF, plus confidence, provability, token cost and human wait. Score from a separate pass, not the worker. Add anti-starvation aging so lanes do not die.
8. **Decision queue instead of stop.** Each question carries a default guess, what is blocked, reversibility, and which lanes stay open. Work on the guess only when reversible. Plug into [askwright](../../../askwright/) rather than rebuild it.
9. **Review cap.** Back pressure from the queue. If unanswered items pass a cap, stop generating that kind of work and move to lanes that create no review. The numbers are guesses to tune.
10. **Lane switching rules.** Move lane on a block, a repeat failure, or an empty ready list. No source I found defines this for one solo game.
11. **Budget governor.** Per unit, per lane and per window. Stop rules for no-progress: same failure twice, no new commit, no ledger change. Count on a subscription through limits and on an API key through dollars.
12. **Self-work ban.** A hard cap on work on grindwright, its docs and its ledger. Gas Town died from this. Count meta commits and alert.
13. **Provenance ledger.** Record every player-facing AI asset with tool and prompt, so the Steam survey answers itself. Code alone seems out of scope, content is in.
14. **Public-face gate.** Nothing goes to a store page, a devlog or players without a human, given the slop climate. Never clone a named game.
15. **Existing codebase guard.** Huntley warns against loops on existing code. Require worktrees, small diffs, and a baseline run before the first unit.
16. **Instruction drift check.** Reload the rules each session, and detect when a run departs from them. Fresh sessions give most of this for free. [inference]

## Added from the 2026-11-03 scan

Self-reported or second-hand, one account each. Treat the numbers as anecdotes.

- Silent runaways. [An agent repeated one tool call about 14,000 times for $437](https://dev.to/magicrails/i-let-my-ai-agent-run-overnight-it-cost-437-dd7) with no error; the post promotes a guard library. [One executive's account, relayed second-hand](https://gurugamer.com/pc-console/mihoyos-ai-agents-burn-300-000-in-tokens-during-13-hour-internal-experiment-26851), has dozens of agents spending about $300,000 in 13 hours critiquing each other, with nothing usable. Result: the driver gained a per-session time limit, and bookkeeping no longer counts as progress.
- Gates over prompts. [A UE5 shooter maker](https://www.reddit.com/r/vibecoding/comments/1xm0i4q/i_let_ai_agents_build_an_online_submarine_shooter/) reports agents claiming success too readily, fixed by acceptance commands with expected output, and fun measured against thresholds set beforehand. Reported API-equivalent cost $8,495. Supports the oracle rungs.
- Questions in unattended runs. [One builder](https://www.reddit.com/r/ChatGPTCoding/comments/1xmw6f6/how_do_you_get_a_coding_agent_to_ask_instead_of/) parks a question on a card and moves on, which fails when later work depends on the answer. Same open problem as here: grindwright switches lanes, and dependent items must stay blocked.
- Hooks are not a hard stop. [A Cursor spend cap](https://www.reddit.com/r/cursor/comments/1xjdzwa/opensource_spend_caps_and_loop_detection_for/) can deny calls but cannot end a chat. Supports an outer driver that can kill the process.

## Open questions to test, not research

- What exit code, result subtype and events does `claude -p` give at a session limit on a subscription?
- Does `--max-budget-usd` stop a subscription run?
- Does a Stop or `SessionEnd` hook fire at a usage limit in `-p`?
- Can a headless Unity or Godot run give a stable screenshot oracle on the author's machine?
