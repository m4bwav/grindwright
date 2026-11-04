# grindwright

![A grindstone throwing sparks on a night-time desk, beside a board of colored work cards and a monitor showing a pixel art game](https://raw.githubusercontent.com/m4bwav/grindwright/main/.github/images/banner.jpg)

Keeps an indie game moving the way a grinding solo dev would. It ranks work across lanes by value first, with a person's minutes as the discount. It does what needs no person, queues questions on a decision page and moves to another lane instead of waiting. Every session ends with the same start command.

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

Plugs into artwright, pixelwright, musicwright, cinewright, game-juice, polywright, ludowright, comfyui-gen and marketwright when present, and says which lanes are closed when one is missing.
