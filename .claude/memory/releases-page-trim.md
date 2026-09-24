---
name: releases-page-trim
description: "Releases page keeps the newest release of each X.Y line plus the current beta; delete a superseded release AND its tag only after the new one is live; never delete Docker tags or stable-X.Y branches; confirm with Jason the first time per project"
metadata:
  type: project
---

Jason's choice for Hylki (2026-09-24, against my advice on deleting tags): the
Releases page and the tags mirror each other and hold only the newest release
of each `X.Y` line plus the current beta.

At ship time, a new patch `X.Y.Z+1` supersedes `X.Y.Z`, and a new beta
supersedes the previous beta. Delete the superseded GitHub release **and** its
tag only after:
- the new release is published and `releases/latest` points at it, and
- `tools/release-notes.sh` has run for it (it diffs against the previous tag
  of the same kind, so that tag must still exist when it runs).

Never delete Docker image tags (someone may have pinned one) or `stable-X.Y`
branches ([[release-branching]]). Before deleting any tag, check its commit is
reachable from a branch that stays. GitHub creates no push event when more
than three tags change in one push, so deleting tags in batches of more than
three fires no workflows.

**Why:** 249 releases made the page useless for finding the current version.

**How to apply:** this is a per-project policy: **confirm with Jason the
first time** it comes up in a new app, then follow it at every ship
([[ship-flow]]).
