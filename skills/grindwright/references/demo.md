# Demo lane

A demo is a cut of the game people can play before launch: one slice, built on its own, kept working while the full game moves on. The lane is dormant. It appears in `discover` only when the profile turns it on:

```json
"demo": {"enabled": true, "scope": "first colony, up to the first launch", "build": "Builds/Demo", "branch": "demo"}
```

`scope` says where the demo starts and stops in words a player would use. `build` is where its build lands. `branch` is optional: a demo branch is only worth it when main will break the slice for a while.

## Work the lane does

1. **Scope.** Draft the slice from the road: the milestones it shows, what is cut or locked, how it ends (a closing screen that says what the full game adds). The owner confirms the scope; until then nothing else in the lane is ready.
2. **Make.** A build target or flag for the demo, the locks, the ending screen, a save that does not carry into the full game unless the owner wants it.
3. **Check.** Build it, play its whole path (scripted where the project has scripted play), and record time to finish and anything broken. Visible changes carry screenshots like any visible lane.
4. **Maintain.** After merges to main, list what changed inside the slice and rebuild; a broken demo is a bug item at the demo's priority.
5. **Feedback.** When the demo is out, read where players talk about it (store reviews, the project's issues or forum) through the project's work sources and file items for what they hit.

## Owner calls

Publishing the demo anywhere (a store page, itch.io, a festival entry), its price and its date stay with the owner, as every outward-facing step does. The lane may prepare the upload, the store text (marketwright) and the trailer (cinewright), and stops there.
