# Films, video series and stories

The ledger, selector, gates and crews do not care what the project is. A non-game project changes only the profile and the road.

## Lanes

| Lane kind | Tool when installed | Verify with |
|---|---|---|
| `writing`: script, story, narration, shot list | everwrite, editwright | everwrite check, a person reads it |
| `art`: stills, references, keyframes | artwright, comfyui-gen | human pick |
| `video`: shots | cinewright, comfyui-gen | the project's review criteria, human watch |
| `edit`: cuts, joins, timing | cinewright | runtime, gaps, human watch |
| `voice` | voicewright | its checks, human listen |
| `sound` | sfxwright | sfx check, human listen |
| `music`: score | musicwright (musicwright-score) | mw.py measure, hits on cuts, human listen |
| `model`: blockouts, crowds | polywright | render sheet |
| `marketing`: posters, posts | marketwright | drafts only |

Games use the writing and voice lanes too: dialogue, lore, card text, store copy.

## Profile

```json
{
 "project": "Lantern Road", "repo": ".", "min_value": 2,
 "people": {"owner": {"review_cap": 2}},
 "lanes": {
  "script": {"kind": "writing"},
  "shots": {"kind": "video", "host": "gpu", "batch_min": {"owner": 4}},
  "cut": {"kind": "edit", "stack_on_pending": false},
  "voices": {"kind": "voice"},
  "score": {"kind": "music"}
 },
 "discover": ["review the latest cut", "gaps against the script", "continuity", "loudness and sync"]
}
```

`discover` is what the agent does when nothing is selectable. The selector echoes it, so write it for the medium.

## Road

`finished_means` is a viewer's sentence ("a 12 minute cut that holds attention and has no lens talk or set drift"). Milestones follow the pipeline: script locked, every scene with a kept take, rough cut, voices, score, sound, final cut and delivery. Weight 3 means it cannot be released without it.

## Oracle ladder

Renders finished, files measured (duration, loudness, black or frozen frames), checked against the project's review criteria, then a person watching. Only the last proves the film works. A take nobody has watched stays `waiting-on-human`, never done.

## Where state lives

Keep `ai-docs/grind` beside the project's own docs. If the project is a render folder with no repo, keep the state in a separate folder and pass `--state`, so the renders stay out of git.
