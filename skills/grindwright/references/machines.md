# Several computers on one project

Two people each start a grind on their own computer, on the same repository. Their state folders cannot be shared, so local claims do not see each other. With `work.remote`, the repository host keeps the claims, and each run skips what the other is doing.

## Setup (each computer)

```json
"work": {
 "remote": {"repo": "owner/tiny-colony", "machine": "pat-desktop", "lease_hours": 6, "ticket_first": true, "label": "agent-working"}
}
```

- `repo` defaults to `work.issues.repo`. `machine` defaults to the host name; give each computer a different one (or set `GRINDWRIGHT_MACHINE`). Two computers with the same `gh` login still tell apart by machine name.
- Each `gh` login needs push access: a claim is a branch ref.
- Create the `agent-working` label once in the repository. Without it, claims still work and only the label is skipped.
- `"offline": "local"` lets a run carry on when the host cannot be reached. The default refuses the claim instead, since a claim the other computer cannot see is how duplicate work starts.

## How a claim works

`claim` (and `next --claim`) first creates the ref `grind-claim/<key>` on the host, where the key is `issue-N`, `pr-N`, or `t-<hash of the title>` for an item with no issue. Creating a ref that already exists fails, so only one computer can win, even when both try in the same second. A test on GitHub with four simultaneous creates: one won and three got HTTP 422. The ref points at an empty commit whose message says which machine and session hold it and until when. It never touches work branches and is never merged.

| Event | What happens |
|---|---|
| The other computer holds a fresh claim | `claim` is refused with who and until when; the item is marked `held_remote` and `next` defers it ("another computer is on it") |
| `checkpoint` | Renews the claim with a fast-forward update; a renewal that loses to a take-over fails |
| `done`, `drop`, `session release` | Deletes the ref, and removes the label from the issue |
| The holder died | After `lease_hours` without renewal, another computer's `claim` takes it over with a fast-forward update (also only one winner) and continues from the dead holder's pushed branch |
| `sync` (every session start) | Reads every claim: marks items another computer holds, gives back refs this computer still holds for items no longer running, and lists claims for items this ledger does not know (`unknown_here`) |
| `grw.py remote` | Lists all claims, newest first |

On an issue, the first claim also adds the `agent-working` label and posts one marked comment naming the machine, so people and other tools see it too.

## Make shared work visible

A claim only protects work both computers know by the same key. Two discovery passes that word one idea differently get different `t-` keys. So:

- **Ticket first.** With `ticket_first: true`, an item with no issue or PR cannot be claimed: file it with `ticket` first. `ticket` already refuses duplicates by key and similar title across the newest 100 issues, so the second computer's discovery finds the first one's ticket instead of adding its own. Use this whenever two computers run on one project.
- **Push early, open a draft PR early.** Push the work branch after the first commit and open the PR as a draft (`gh pr create --draft`) that links the issue. The other computer's `pr-sync` and anyone reading the issue then see real progress, not just a claim.
- **Issues and PR comments carry questions and answers**, so both computers get them through `issue-sync` and `pr-sync` (see [work sources](work-sources.md)). A question asked on one computer's askwright page is invisible to the other; link it from the issue.
- **Discussions** (or `proposal` issues) hold design questions that span items, so neither run decides alone.
- **The wiki or `knowledge.remote`** keeps what runs learn about the project. Each computer reads it at session start; local `knowledge.local` stays per computer, so lessons both runs need belong in the shared one, through a PR or the wiki.
- **One road and one profile in the repository.** Keep the road, lanes and values the same on both computers, for example by committing a copy and reading it at start, so their selectors rank the same way.

## Limits

- A claim stops two computers taking one item; it does not stop overlapping edits from two different items. Areas are local only. Name narrow items, merge small PRs often, and let `pr-sync` raise conflicts.
- Each sync reads every claim ref (one call per claim). Fine for tens; a large crew should keep items few and short.
- GitHub does not document ref creation as atomic; the lock rests on the tested 422 and on fast-forward-only updates.
- Branch protection rules matching `grind-claim/*` would block claims. Leave that pattern unprotected.
