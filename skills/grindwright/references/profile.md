# Project profile and road

State folder: `ai-docs/grind` in the game's repo, unless the repo's rules forbid it. If another person owns the repo or
its rules restrict what may appear there, keep the state outside it and pass `--state`.

## profile.json

```json
{
 "project": "Tiny Colony", "repo": "../tiny-colony", "min_value": 2, "escalate_after": 2,
 "people": {"owner": {"review_cap": 3, "aliases": ["owner-github-login"]}},
 "lanes": {
  "cards": {"kind": "art", "host": "gpu", "person": "owner"},
  "buildings": {"kind": "animation", "needs": ["pixelwright"], "batch_min": {"owner": 5}, "stack_on_pending": false},
  "bugs": {"kind": "code"},
  "deps": {"kind": "maintenance"},
  "plugin-work": {"kind": "meta"}
 },
 "hosts": {"pc": {"url": "http://127.0.0.1:8188/queue", "tags": ["gpu"]}},
 "guards": {"merge": "allow: after checks pass", "touch_main": "deny: branch", "stack_on_pending": "deny"},
 "read_only_paths": ["tasks.md"],
 "text_bans": [],
 "discover": ["test", "balance", "gaps", "marketing"],
 "order": ["owner-note", "pr-conflicts", "pr-comments", "answers", "handoff", "tickets", "other"]
}
```

- `review_cap`: open review sets or PRs a person may have before the plugin does other work.
- `aliases`: other names for the person (a GitHub login, a nickname). `--person` accepts the name or any alias, case ignored, and the ledger stores the name. Any other name is refused with the known names listed: ask the owner and add it here, never guess.
- `kind`: art, animation, sound, music, video, edit, voice, writing, tests, juice, balance, marketing, model, demo, code, maintenance, meta. It sets the
  default plugin and the share cap. `needs` overrides the plugin list (a nested list means any one of them; sound defaults to sfxwright or musicwright); `share_cap` overrides the cap.
- `batch_min`: smallest batch per person. `stack_on_pending`: `false` defers the lane while a review is open.
- Guard values start with `allow` or `deny: reason`. Anything unset is denied.
- `ask_py`: path to askwright's `ask.py` when askwright is not installed as a plugin or skill (a clone, say). Without it `sync` cannot read any decision page and every item waiting on one stays waiting; `sync` and `next` then carry a `warning`. `GRINDWRIGHT_ASK` overrides it.
- `ask_route`: where questions go. Default `"repo"` (issue, PR comment or discussion when the project has a repository); `"askwright"` when the owner prefers decision pages.
- `text_bans`: words PR and commit text must not use.
- `work`: issues, todo files, task lists and remote claims ([work-sources.md](work-sources.md)). Issue settings live in `work.issues`. Among them `acceptance`, off by default: `{"enabled": true, "label": "ready for acceptance", "comment": true}` labels open issues whose referencing PRs all merged, for a person's acceptance check. It never closes an issue.
- `demo`: off unless `{"enabled": true, "scope": ..., "build": ...}`; then `discover` raises the demo lane ([demo.md](demo.md)).
- `order`: which kind of work `next` picks first. The example is the default: what the owner said at session start,
  merge conflicts on the agent's open PRs, owner comments on them, askwright answers, another session's handoff,
  issue tickets (green-lit when `require_greenlight` is on), then everything else. Inside a category, priority and
  value rank as before. Categories left out follow the listed ones in default order; an unknown name is a `doctor`
  conflict. When nothing is selectable, the `stop` step names its `ticket_sources` to file proposals from:
  `work.tasks` and `work.todo` paths, `work.plans` (a list of design docs or folders, default "unbuilt design-doc
  sections"), and open issues.

Project specifics (snapshot suites, slots, required skills) stay here or in the project's own docs, never in the plugin.

## road.json

```json
{
 "finished_means": "One sentence a player would agree with.",
 "confirmed": false,
 "milestones": [{"id": "core", "title": "Full run playable start to end", "weight": 3, "status": "works; no ending"}]
}
```

Derive it from design docs, code and gaps. Weight 3 means the game cannot ship without it, 1 means polish. The owner
corrects it once on an askwright page. A complete run is rarely the whole game: draft what comes after it too (extra
modes, side systems, features), so the owner cuts milestones rather than has to think of them. On that page, set `confirmed` to true only after that.
