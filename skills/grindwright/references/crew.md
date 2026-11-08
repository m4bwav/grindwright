# Several sessions at once

Start simple. One session per project needs nothing here but separate state folders. Add a second session on a project only when it has work that does not overlap and the owner has the tokens.

## Layout

- **One state folder per project.** Ledger, events, board, logs and knowledge never mix. `grind_crew.py` refuses two projects sharing one.
- **Two sessions on one project share one state folder, outside the repo.** A folder inside the repo gives each worktree its own ledger copy, and claims stop working. Copy the folder out, then keep a copy in the repo only if the project wants one.
- **Each session has a name, one branch and one worktree.** The driver sets `GRINDWRIGHT_SESSION` and `GRINDWRIGHT_STATE`; a hand-run session sets them itself. No name means `solo`, which behaves as before.
- If the project's rules restrict worktrees (for example a live game editor exists only in the main checkout), set `"worktrees": false` with one session, or give editor-bound lanes an exclusive area and send only art and docs to worktrees. The project's rules win. Where a session can open its own editor on its worktree, verify engine work there from a warm pool ([engine-verify](engine-verify.md)).

## How sessions stay out of each other's way

| Risk | What stops it |
|---|---|
| Two sessions take one item | `claim` runs under the state lock; a running item is not offered again |
| Two sessions edit the same files | `claim <id> --area src/ui/**`, or `add --area`. An overlapping area is refused and ranked out for others |
| Two sessions need one tool | An area can be a name: lane `"areas": ["resource:editor"]` makes that lane one at a time. Works for a GPU or a test server too |
| Two sessions act on the same answers, triage or analysis | `next --claim` holds the item for 2 hours for that session |
| Two sessions discover the same work | One discovery pass serves the whole crew for 4 hours. `add` refuses a title like an open item |
| A dead session keeps its areas | The driver runs `session release` when a member stops; otherwise the lease expires after 6 hours. Released items keep `paused_by`, so other members skip them; `claim --take-over` moves one |
| One undoes another's work | `next` lists `others_working`, `notes_from_others`, `done_by_others`. Before touching something near them: `note "<what changed>" --area <path>` |

`BOARD.md` in the state folder shows people who is where. Agents read `next` or `board` instead, which costs less. Do not edit it.

Name areas as narrowly as you honestly can, and name one on any item that edits shared files. Split the failure surface as well as the task list: when every test fails on one bug, parallel sessions all chase it, so give each a different subset. Areas do not prevent logical conflicts, so merges still go through tests and a person.

Keep structure and behaviour apart. A member's structure-only changes (renames, moved or extracted code, reordering, dead code removed) land in their own small PR or commit, before or after the behaviour change, never mixed in: small structural PRs merge before they collide with other members, and a reviewer reads each kind at the right pace. Tidy only what the item's next behaviour change needs, for minutes up to about an hour; a mess the item does not need goes on the ledger as its own item instead of into the PR. When an item ends as a tangle of both, redo it structure first rather than ship the tangle. Reversible changes (structure, code behind a flag) get a light check; irreversible ones (schemas, public APIs, data deletion, a split into a new service) get a full review before merge.

## Saying there is nothing to do

A session may stop only when `session check` says so. When only human decisions are left, `session check` returns `waiting_on`, most unblocking first, and `WAITING.md` lists the same. Say it plainly in the final message: "Nothing can move until these N decisions." Never invent work to stay busy. After another long run the same list may still be the answer, and that is correct.

`grind_crew.py` looks before it launches: a member with nothing selectable is not started, and is reported under `skipped`. A night with nothing to do costs one check, plus at most one discovery session every 4 hours while a member keeps being offered discovery.

## Running a night

The owner agrees hours, sessions and scheduling first. Write a crew file, dry-run it, then `--go`:

```json
{
 "max_hours": 10, "max_sessions_each": 8, "session_minutes": 120, "stagger_seconds": 120,
 "require_text": "grindwright",
 "projects": [
  {"name": "tiny-colony", "repo": "../tiny-colony", "state": "../grind-state/tiny-colony", "prompt": "../grind-state/tiny-colony/prompt.md", "sessions": 2},
  {"name": "star-market", "repo": "../star-market", "state": "../grind-state/star-market", "prompt": "../grind-state/star-market/prompt.md", "sessions": 1, "worktrees": false}
 ]
}
```

```
python grind_crew.py crew.json        # dry run: refusals, and what each member would do now
python grind_crew.py crew.json --go
```

Worktrees go in `<repo>-grind/<member>`. Set `"worktree_root"` on a project when that folder is taken.

Logs go to `<state>/logs/<member>-<date>.log`, the summary to `<state>/logs/crew-<date>.json`. All members draw on one usage limit; on a limit each driver sleeps and retries on its own.

Grow in steps: one per project first, then two on the project with the most non-overlapping lanes. Docs and practitioners put the useful count low, around 3 to 5 on a repo, with cost about linear per session. Review is usually the real limit: past a person's review cap, more sessions only pile up drafts.

Size the crew by its serial share (Amdahl's law): if a share s of each item's time can only happen one at a time (the person's review, the merge, one GPU), the crew can never go faster than 1/s. Review at a quarter of each item's time caps the crew near 4x however many members run. Shrink s (smaller PRs, self-checks, tests the reviewer trusts) before adding members. Pull, do not push: when the review queue is full, members finish review-side work (tests, splitting a big PR, answering review notes) instead of claiming new items. Source: Dooley, Software Development, Design and Coding (2017), ch. 2 and 12, human teams applied by analogy.

Done means the planned checks ran. A member that says done without running them has stopped, not finished: record which checks ran on each item and treat a missing one as a failed item. A flaky check is a crew defect, not noise; fix or quarantine it, because a check that fails only sometimes trains everyone to rerun instead of read. Run the tests a diff touches on every item and the whole suite before merge. Watch the failure rate across a night: a sudden drop to zero more often means weak checks than perfect work, and items sitting long in review mean the cap is set too high. Source: Pezze and Young, Software Testing and Analysis (2008), ch. 3, 20 and 22, applied by analogy.

Tests must survive members running at once. Each test sets up and tears down its own state, so tests pass in any order and in any subset; members running suites side by side in their own worktrees never share a scratch file, database, port or account, so give each worktree its own temp folder and pick ports at random. A bug item starts with the smallest test that fails on the bug, and the member shows it failing before writing the fix. A member writes its item's test list before coding; a test idea outside the item goes on the ledger, not into the PR. Source: Beck, Test-Driven Development: By Example (2002), ch. 25 Isolated Test and Test List, ch. 26 Regression Test, applied by analogy.

Keep main green. When main goes red, no member merges until it is green again. The member whose merge broke it owns the fix, even when its own tests passed; it gets about ten minutes, then reverts its merge and fixes the item off main. Before merging, a member rebases on current main and reruns the item's checks, so two green items cannot land as one red main. A member never skips, comments out or loosens a failing test to land an item; the crew counts skipped tests and treats a rise as a failed night. Checks should run to the end and report every failure at once, so one fix round clears them. Tighten a gate only by ratchet (fail when warnings rise, never on a rule nobody agreed). Source: Humble and Farley, Continuous Delivery (2010), ch. 3 and 7, applied by analogy.

Split a change too big for one member into shards that each pass checks and merge on their own: cut along file-ownership lines, keep dependent edits (an interface and its callers that must move together) in one shard, and cap how many shards are open at once. Conflict odds grow with files touched and with members working, and a failure is cheap to trace in a small shard. A mechanical shard that hits a conflict is regenerated from fresh main, not hand-merged. Before a night, record which checks already fail on main: members ignore those and do not fix them inside unrelated items; they become their own item. Review mechanical PRs as a batch by the pattern they should follow and open only the odd ones, since owners who trust bulk changes tend to wave them through. After removing a pattern, add a check that rejects new uses of it, or later items bring it back. Source: Winters, Manshreck and Wright, Software Engineering at Google (2020), ch. 22, human teams applied by analogy.

`"discover_first": true` in the crew file or one project: that project's first member runs one session even when nothing is selectable (after a person widened the rules); it is otherwise skipped.
