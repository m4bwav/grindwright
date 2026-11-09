# Coordinating grind runs on different computers (2026-11-08)

Question from the owner: two people each run a grind on their own computer, on one repository. How do the runs avoid doing the same work, using what the repository host provides (issues, discussions, wiki, PRs)?

## Findings

- Practitioner tools converge on atomic first-claim-wins plus leases that reclaim stranded work (Beads, Retasc, BeadHub, Gecko). Several add a server because plain GitHub issues have no compare-and-swap: labels and assignees are last-writer-wins (see the 2026-11-07 survey). Sources: https://beads.gascity.com/multi-agent/coordination, https://www.cipherprojects.com/blog/posts/retasc-ai-coding-agent-queue-2026/, https://dev.to/odrin/why-ai-coding-agents-need-work-attempts-leases-and-checkpoints-53k4, https://arxiv.org/html/2606.19616
- Git refs give compare-and-swap without a server. GitHub's "create a reference" fails with HTTP 422 "Reference already exists"; GitHub's docs do not promise atomicity (https://docs.github.com/en/rest/git/refs). Tested on the public repo on 2026-11-08: four simultaneous creates of one ref, one succeeded, three got 422. A PATCH with `force: false` only lands as a fast-forward, so renew and take-over are compare-and-swap too.
- Git conflicts alone catch collisions too late: both runs have already done the work.

## Design

Claim ref `grind-claim/<key>` on an empty commit carrying holder JSON; issue label and comment as the human-visible signal; ticket-first so discovery goes through the duplicate-checked tracker; draft PRs early; questions on issues and PRs; shared lessons in the wiki. Built in 0.6.0, see `skills/grindwright/references/machines.md`.
