# Game systems an agent builds: tuning, traceability, AI turns

Read this when a lane builds or changes a game's runtime systems: numbers someone will tune, features the owner reviews one by one, or a system where a language model makes choices in play. Three small patterns, each cheap to add early and costly to retrofit.

## One hot-reloaded tuning file

Keep every number a designer or owner will want to tweak (speeds, damage, spawn rates, cooldowns) in one plain file (JSON, TOML or the engine's config format), not spread across scripts.

- **Reload on change.** Poll the file's modified time every second or so in debug builds and re-read it when it changes. No editor restart, no rebuild: the owner edits a value and sees it in play.
- **A bad file never crashes the game.** If the new file fails to parse or a value is out of range, keep the last good values, rename the broken file to `<name>.bad`, write the good one back, and show a one-line warning in game and in the log naming the key or line. The owner's edit is kept for them to fix, not lost.
- **In multiplayer the host's file wins.** The host sends its tuning to clients on join and on each reload; clients ignore their local copy while connected. Two players with different numbers is a desync, not a feature.
- Missing keys fall back to defaults in code, and a test loads the shipped file and checks every key is known.

## One feature per commit, versions on assets

- **One feature per commit, each with a version bump** (patch for a fix, minor for a feature) and a changelog line. The owner can bisect, revert or review one change at a time.
- **Stamp the version into generated asset filenames** (`boss_idle_v0.14.2.png`, `theme_menu_v0.14.2.ogg`). A screenshot, a bug report or a stray file in a build then says which commit and which prompt made it. Record the prompt and seed next to it when a model made the asset.
- Do not rename hand-made assets this way; only generated ones, so regenerating never overwrites a kept take.

## When a model plays a part: it proposes, code commits

For game systems where a language model decides (an AI opponent, a narrator, NPC dialogue that changes state):

- **The model proposes intents, never state.** It returns a small structured choice (`{"action": "move", "to": "B3"}`) through a tool or a JSON schema. Game code checks the intent against the rules (legal move, enough resources, the actor is alive), and only code changes the game state. A rejected intent goes back to the model with the reason, once or twice.
- **Cap model calls per turn** (a constant, 10 to 20 is a sane start) and give the model an explicit `end_turn` tool. At the cap the turn ends with a safe default action, so a looping model cannot stall or bankrupt the game.
- **Test without the model.** A scripted fake returns fixed intents, so rules, validation and the cap are unit tests; the live model is a smoke test only.

Idea credits (our own words, no code copied): sloppysteaks69/GPU-Bandits (hot-reloaded tuning, version stamps; no licence, ideas only), legend-of-alan/spookery agent crates (intents and call cap; MIT).
