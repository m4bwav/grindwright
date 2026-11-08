# Lanes, scoring and the batch cycle

## How the selector scores

`score = value² × road weight × confidence × 1/(1 + human_min/30)`, then small nudges: items it unblocks, age (up to
+30%), a free machine (+10%). Answers already in always rank first. Value is how far the item moves the game to
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

## Lanes and what to do in them

| Lane | Tool when installed | Verify with |
|---|---|---|
| Card and placeholder graphics | artwright, comfyui-gen, the project's card tool | wired-art check, snapshots, human pick |
| Animation | pixelwright | its gates, snapshots, human pick |
| Models and blockouts | polywright | render sheet |
| Sound effects and music | sfxwright for effects when installed, else musicwright; musicwright for music | sfx.py check, mw.py measure, loop seam check, human listen |
| Intro video, trailers | cinewright, marketwright | human watch; drafts only |
| Writing: dialogue, lore, card text, scripts, narration | everwrite, editwright | everwrite check, a person reads it |
| Voices | voicewright | its checks, human listen |
| Feel | game-juice (juice-scan, juice-apply) | toggle works, snapshots |
| Balance | ludowright, ldw.py simulations | seeded Monte Carlo, findings file |
| Tests: add unit, integration, end-to-end, snapshot, property or regression tests, or invent a check the project lacks | the project's test tools, unity-agent, roblox-agent | the new test fails on a planted fault, then passes; never weakened to pass |
| Testing and bugs | unity-agent, roblox-agent, the project's tests | tests, headless boot, scripted play |
| Unfinished features | the road, open issues, TODOs | tests, then scripted play |
| Maintenance | everkeep if present, the package manager | tests, build |
| Marketing plan and stats | marketwright | drafts only; numbers cite their source |

Film and video projects use other lanes and another ladder: [projects.md](projects.md).

## Oracle ladder

Compile, tests, headless boot, scripted play, screenshot diff, human taste. Engine projects: one worktree per session with its own editor, a warm worktree pool, batchmode tests ([engine-verify](engine-verify.md)). Climb as far as the lane allows at the
cheapest rung that can catch the mistake. A game can run and still be wrong: a green rung proves only what it checks.
Agents dodge checks, so never weaken a test or a gate to pass, and treat a written excuse as a failure.

## Session end and limits

Only files and commits survive. Commit at each checkpoint. On a usage-limit warning: `grw.py checkpoint`, commit,
`grw.py session pause --reason "usage limit"`, update HANDOFF.md, print the start command. A session that dies leaves
a lease that expires after 6 hours; `sync` returns the item with a note to inspect the partial work.
