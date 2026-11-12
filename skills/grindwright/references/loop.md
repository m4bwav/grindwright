# Lanes, scoring and the batch cycle

## How the selector scores

`score = value² × road weight × confidence × 1/(1 + human_min/30)`, then small nudges: items it unblocks, age (up to
+30%), a free machine (+10%), plainness (cost S x1.15, L x0.85). Answers already in always rank first.

**Priority tiers come before score.** Items carry a priority from 0 (urgent) to 3 (low). An item with no priority is
normal, tier 2, exactly like one tagged normal. Every P0 outranks every P1, and so on; within one tier the score
decides, so the highest-value work goes first, and among equal value the straightforward, obvious task (small, sure)
beats the large, murky one. Issues get their tier from labels at sync; set others with `add --priority N` or
`set <id> priority=N` (add `priority_pinned=true` so sync leaves a hand-set tier alone). Value is how far the item moves the game to
finished and polished, 1 to 5. Be honest: inflating value defeats the selector. Value under the profile's floor
(default 2) is never selected.

| Class | Value | Human | What happens |
|---|---|---|---|
| best | 3+ | under 30 min | done first |
| worth-the-ask | 3+ | 30+ min | done; try to shave the human part |
| filler | 1-2 | under 30 min | only after the above |
| worst | 1-2 | 30+ min | an `analyse` task before any work |

Maintenance is capped at 20% of recent claims, work on the tooling itself at 10%. Capped work returns only after a
discovery pass found nothing better.

## Value starting points

Adjust per project in the road. 5: a gap that stops the game being finished (a missing core feature, a crash, a
broken save). 4: something a player sees in most sessions (missing card art, silent core verb). 3: polish in a common
path, a balance fault. 2: edge polish, cleanup that lowers risk. 1: nice to have.

## The batch cycle (every generative lane)

Generate a batch, make a contact sheet, form real guesses by looking at it, ask, sync answers, wire, verify, PR, merge,
next batch. While a batch waits, do another lane. Batch size follows the person's minimum in the profile. Answers to
a question kind recurring three times should be a rule, so stop asking it.

Pictures in a pull request or issue on a private repository: link them as `https://github.com/OWNER/REPO/blob/BRANCH/PATH?raw=true`. A `raw.githubusercontent.com` link to a private repository shows the reviewer a 404.

## What a reviewer gets

Every PR, issue and PR update comment is written for a person deciding whether to merge. Two rules:

**Screenshots of every visible change.** Art, animation, UI, scenes, effects, layouts, video, models, store pages:
attach pictures to the PR, the issue and every update comment that changes what shows. Before and after when a before
exists (same camera, same crop), one contact sheet for a batch. **Prefer an animated GIF** in every PR, for graphics
and gameplay alike: a looping GIF of the sprite, effect, UI or scene in motion, or a short gameplay capture of the
change in play (a few seconds, small enough to show inline, under about 10 MB). A still is the fallback only when
nothing moves or no capture route exists; say why in the PR. Capture with what the
project already has: the engine in batchmode or a scripted play-mode capture ([engine-verify](engine-verify.md)), a
browser screenshot for web pages, the contact sheet the batch cycle made. Commit them under `pr-media/<item>/` on the
branch and link them (private repositories: the `blob/...?raw=true` form above). `grw.py done` and `hold` refuse an
item on a visible lane without `--shots <files>` or `--no-shots "<why>"`; the run report shows them per item. A lane
sets `"visible": true|false` in the profile to override its kind.

An art PR with no art on its page is not reviewable. The pictures go **in the PR body itself**, inline, not only
in a later comment or a contact sheet the agent "looked at": at least one GIF or contact sheet per asset group
(per building, per sprite set), so the reviewer sees every piece without checking out the branch. This holds for
ports, cherry-picks and carry-overs of art that was shown on an older PR too: link the old pictures again or make
new ones. Before `gh pr create` on an art lane, check the body has image links; if it has none, it is not ready.

**Explanation grows with risk.** Large PRs test a merger's nerve, so the bigger and riskier the change, the more the
body must explain. Start every PR body from `grw.py pr-brief --base <base> --head <branch> --markdown`: it groups the
changed files by area and kind (code, tests, art and media, docs, settings, CI and build, generated), scores the risk
(files, code lines, risky paths such as settings, workflows and save formats, code without tests, mass deletions) and
gives a tier with what the body must hold:

| Tier | Must explain |
|---|---|
| small | what changed and why; how it was verified |
| medium | plus a breakdown by area, verification commands and results, screenshots |
| large | plus the reason for each group, risks and how each was checked, a reading order (what to skip as generated or moved), how to roll back |
| very large | plus why it is one PR or a split plan, a reviewer's checklist, a few-minute play or test script for the merger |

Fill every TODO; replace the table's "Why" column with real reasons. A change that scores very large and is not one
idea should be split before it is opened.

## Lanes and what to do in them

| Lane | Tool when installed | Verify with |
|---|---|---|
| Card and placeholder graphics | artwright, comfyui-gen, the project's card tool | wired-art check, snapshots, human pick |
| Animation | pixelwright; `grw.py track record` each render's start and end images, `track check --add` files redos when one changes | its gates, snapshots, human pick |
| Models and blockouts | polywright | render sheet |
| Sound effects and music | sfxwright for effects when installed, else musicwright; musicwright for music | sfx.py check, mw.py measure, loop seam check, human listen |
| Intro video, trailers | cinewright, marketwright | human watch; drafts only |
| Writing: dialogue, lore, card text, scripts, narration | everwrite, editwright | everwrite check, a person reads it |
| Voices | voicewright | its checks, human listen |
| Feel | game-juice (juice-scan, juice-apply) | toggle works, snapshots |
| Balance | ludowright, ldw.py simulations | seeded Monte Carlo, findings file |
| Tests: add unit, integration, end-to-end, snapshot, property or regression tests, or invent a check the project lacks | the project's test tools, unity-agent, roblox-agent | the new test fails on a planted fault, then passes; never weakened to pass |
| Testing and bugs | unity-agent, roblox-agent, the project's tests | tests, headless boot, scripted play; for game state, the state-dump and replay-fixture recipe in unity-agent-workflow's test ladder (text rows at a timestamp diffed against a saved expected file) |
| Pre-launch checks (before any public build, store page or server goes live) | the project's build and server tests, everkeep | grep the shipped build for keys and tokens; the server, not the client, decides score, currency and purchases; one account cannot read or change another's data; crashes reach a log someone reads; one backup restored for real. Source: a contractor's list of what breaks in AI-built games after launch, r/aigamedev 2026-07 |
| Unfinished features | the road, open issues, TODOs | tests, then scripted play |
| Maintenance | everkeep if present, the package manager | tests, build |
| Marketing plan and stats | marketwright | drafts only; numbers cite their source |

Film and video projects use other lanes and another ladder: [projects.md](projects.md).

## Approved files

When the owner approves a spec, design doc or asset, record it: `grw.py approve <files>` stores each file's sha256 in `approved.lock` in the state folder. An approved file changes only after a new approval. `grw.py approved --check [files]` exits 1 and names every approved file that changed or vanished, and any named file never approved; run it before a session claims work done, and ask again for anything it names.

## Oracle ladder

Compile, tests, headless boot, scripted play, screenshot diff, human taste. Engine projects: one worktree per session with its own editor, a warm worktree pool, batchmode tests ([engine-verify](engine-verify.md)). Climb as far as the lane allows at the
cheapest rung that can catch the mistake. A game can run and still be wrong: a green rung proves only what it checks.
Agents dodge checks, so never weaken a test or a gate to pass, and treat a written excuse as a failure.

## Learn from the work

A grind is only as good as the plugins it drives, so every session leaves them better. Lessons come from the work and from people: a render the owner rejected and why, a reviewer's PR comment, a redo, a command that failed or needed a workaround, a step that cost many turns, an estimate far off its timing row.

- **A plugin you used** (pixelwright, artwright, comfyui-gen, sfxwright, musicwright, voicewright, cinewright, polywright, ludowright, game-juice, marketwright, askwright, chainwright, grindwright itself): write the lesson to that plugin's `LEARNINGS.md` through evergreen-learn, or fix the plugin when the fix is small and clear (its own branch and PR, under its repository's rules). Never put the game's private details in a public plugin; keep the lesson general.
- **The project**: its own docs, skills or HANDOFF.
- **Bigger plugin work** (a missing feature, a broken script): `grw.py add` an item in a `meta` lane, so it competes for time under the meta share cap instead of being forgotten.

`grw.py session end` refuses after a session that made something until it gets `--lesson "<plugin or project>: <lesson> -> <where it went>"` (repeatable) or `--no-lessons "<why>"`. Then evergreen-wrapup (chainwright runs it as every chained session's last step) harvests the transcript for anything missed and sends it to the same homes. The lessons are kept in the session_end event for the run report.

## Session end and limits

Only files and commits survive. Commit at each checkpoint. On a usage-limit warning: `grw.py checkpoint`, commit,
`grw.py session pause --reason "usage limit"`, update HANDOFF.md, print the start command. A session that dies leaves
a lease that expires after 6 hours; `sync` returns the item with a note to inspect the partial work.
