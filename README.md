# grindwright

![A grindstone throwing sparks on a night-time desk, beside a board of colored work cards and a monitor showing a pixel art game](https://raw.githubusercontent.com/m4bwav/grindwright/main/.github/images/banner.jpg)

Keeps an indie game moving the way a grinding solo dev would. It ranks work across lanes by value first, with a person's minutes as the discount. It does what needs no person, asks its questions where the project already talks (issues, pull request comments, discussions, the wiki) or, when there is no such place or the owner prefers it, on an askwright decision page, and moves to another lane instead of waiting. Every session ends with the same start command.

Status: 0.1.0. Unit tests pass. No live pilot yet, so it has not yet moved a real game. Expect rough edges.

## Install

As a Claude Code plugin:

    /plugin marketplace add m4bwav/grindwright
    /plugin install grindwright@grindwright

Then say "grind on my game" in the game's folder. Details are in the [wiki](https://github.com/m4bwav/grindwright/wiki).

## What's inside

- `skills/grindwright/SKILL.md`: the loop and its rules.
- `skills/grindwright/scripts/grw.py`: ledger, selector, gates. `grw.py --help` lists the commands.
- `skills/grindwright/scripts/grind_loop.py`: bounded unattended driver. Dry run by default.

It does not promise a finished game. No game found in the survey shipped from truly unattended work, and whether a game is fun stays a person's call.

Plugs into artwright, pixelwright, musicwright, sfxwright, cinewright, game-juice, polywright, ludowright, comfyui-gen and marketwright when present, and says which lanes are closed when one is missing.

## Works with

grindwright picks the work. The real making happens in other plugins, and the more of them are installed, the more lanes it can run without you.

- [askwright](https://github.com/m4bwav/askwright): every question grindwright can't answer goes on an askwright page, recorded in the ledger. It switches lanes instead of waiting, and the next session reads your answers. Ten decisions take one sitting, not ten interruptions.
- Lane plugins: [pixelwright](https://github.com/m4bwav/pixelwright) (animation), [artwright](https://github.com/m4bwav/artwright) (art), [sfxwright](https://github.com/m4bwav/sfxwright) and [musicwright](https://github.com/m4bwav/musicwright) (sound and music), [voicewright](https://github.com/m4bwav/voicewright) (voices), [cinewright](https://github.com/m4bwav/cinewright) (shots and edits), [polywright](https://github.com/m4bwav/polywright) (3D models), [ludowright](https://github.com/m4bwav/ludowright) (balance) and [editwright](https://github.com/m4bwav/editwright) (writing). A lane counts as workable only when its plugin is installed, so the selector never ranks work that nothing can do.
- [tokenwright](https://github.com/m4bwav/tokenwright): holds skill and session budgets down, which matters when grindwright runs many sessions in a row.

Details and an example run: [Works with](https://github.com/m4bwav/grindwright/wiki/Works-With).
