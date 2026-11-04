# Log

## 2026-11-03: built 0.1.0
Survey in `ai-docs/research/`. Built grw.py, grind_loop.py, the skill, 16 eval cases, and read-only dry runs on two real games. Script named grw.py because gw.py is reserved for another plugin. Kept the name grindwright: nothing clearly better turned up.

## 2026-11-03: evals
Three eval runs, about $26. Results and limits in skills/grindwright/TESTS.md. Fixed the closed-lane ranking bug they exposed.

## 2026-11-03: write-capable trap runs
plugin eval stays read-only even with --allow-tools, so ran the 10 traps once each through subagents: 9 pass, small-call partial. Fixed discover's cwd bug, added road_warning to next, required guesses in plain replies. Details in skills/grindwright/TESTS.md.

## 2026-11-03: public
Published with fresh history. The earlier history, dry runs, session mining and open decisions on real games stay private with the maintainer. Restored CI on push and pull request, added a banner and a wiki.
