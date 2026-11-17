# Commercial products and websites

The ledger, selector and crews work the same on a product or a website. What changes is where the work comes from: four tracks that a grind runs on a schedule, beside the issues and todo sources.

## Tracks

| Track | Finds | Script | Verify with |
|---|---|---|---|
| `tests` | no end-to-end tests, pages no e2e spec mentions, no approval or snapshot tests, no unit tests | `grw.py product-scan --track tests` | the new test fails on a broken page, then passes |
| `deps` | outdated npm packages (major 3, minor 2, patch 1) and `npm audit` vulnerabilities (critical 5 to low 2) | `--track deps` (`npm outdated`, `npm audit`) | build and tests green after the bump; read the changelog for a major |
| `deprecations` | direct npm packages marked deprecated, deprecation warnings printed by the project's own build or test commands | `--track deprecations` | the warning is gone from the same command's output |
| `features` | major and minor ideas the owners would pay for | none: the scan prints the prompts | the owner's answer |

`product-scan` never adds items. It lists findings with a ready `add` line keyed `product:<key>`. Check each against the code, then add it or `skip product:<key> --why W`. Added or skipped findings stop showing. One major bump is one item; patches in one folder can share an item.

Feature ideas go to the owner as questions (`add ... --question "..." --guess "..."`), valued by revenue, retention or support load, never by how fun they are to build. A major feature is never built unasked. Minor ones the owner approved in a batch can go straight to work.

## Periodic runs

`grw.py product-due` says which tracks are due. Defaults: deps every 7 days, tests 14, deprecations 30, features 30. Put `product-due` in `discover` so an idle session runs the due scan first.

## Profile

```json
{
 "project": "Shopfront", "repo": ".",
 "lanes": {
  "tests": {"kind": "testing"}, "deps": {"kind": "maintenance", "stack_on_pending": false},
  "deprecations": {"kind": "maintenance"}, "features": {"kind": "design"}
 },
 "product": {
  "every_days": {"deps": 7, "tests": 14, "deprecations": 30, "features": 30},
  "deprecation_cmds": ["npm run build", "npm test"],
  "lanes": {"deps": "deps"}
 },
 "discover": ["grw.py product-due, then the due product-scan", "open issues", "slowest pages"]
}
```

`product.lanes` maps a track to a lane name when the profile names lanes differently. `deprecation_cmds` run in the repo; keep them fast and side-effect free.

## Guards

Dependency bumps and deprecation fixes go through PRs like any code. Only the deps track runs network commands (`npm view`, `npm audit`). The npm route is the only package manager read today; others are a later step.
