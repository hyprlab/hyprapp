---
name: release-branching
description: "Hotfixing a shipped stable while main carries unreleased work: a LAZY stable-X.Y branch cut from the last tag only when an urgent patch is needed; fix on main first, cherry-pick; merge back; never delete stable-X.Y"
metadata:
  type: project
---

Features for the next minor develop on `main`; there is no long-lived feature
branch. For an urgent patch ([[release-cadence]], rule 4):

1. `git branch stable-X.Y vX.Y.Z`: cut lazily from the last release **tag**,
   never from main, and only when a hotfix is actually needed.
2. Fix on `main` first, in its own commit, then `git cherry-pick` onto
   `stable-X.Y` (or fix there directly if it doesn't apply to main).
3. Changelog line under `## Unreleased` on the branch, then
   `tools/prepare-release.sh stable X.Y.Z+1` there, and ship per [[ship-flow]]
   pushing `stable-X.Y` instead of main.
4. Merge `stable-X.Y` back into `main` afterwards, so the changelog entry
   survives.
5. Ship a beta from main alongside.
6. **Never delete a `stable-X.Y` branch**: after a Releases-page trim, some
   patch commits may exist only there.

**Why:** agreed with Jason for Hylki (2026-08-30): the daily loop stays one
working tree, and the branching cost falls on the rare hotfix.
