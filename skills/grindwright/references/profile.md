# Project profile and road

State folder: `ai-docs/grind` in the game's repo, unless the repo's rules forbid it. If another person owns the repo or
its rules restrict what may appear there, keep the state outside it and pass `--state`.

## profile.json

```json
{
 "project": "Tiny Colony", "repo": "../tiny-colony", "min_value": 2, "escalate_after": 2,
 "people": {"owner": {"review_cap": 3}},
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
 "discover": ["test", "balance", "gaps", "marketing"]
}
```

- `review_cap`: open review sets or PRs a person may have before the plugin does other work.
- `kind`: art, animation, sound, music, video, juice, balance, marketing, model, code, maintenance, meta. It sets the
  default plugin and the share cap. `needs` overrides the plugin list; `share_cap` overrides the cap.
- `batch_min`: smallest batch per person. `stack_on_pending`: `false` defers the lane while a review is open.
- Guard values start with `allow` or `deny: reason`. Anything unset is denied.
- `text_bans`: words PR and commit text must not use.

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
corrects it once on an askwright page; set `confirmed` to true only after that.
