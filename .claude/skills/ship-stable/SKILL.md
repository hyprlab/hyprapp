---
name: ship-stable
description: Publish a stable release of this app. Use when the maintainer says "Ship it to stable", "ship X.Y.Z", or asks for an urgent patch release. Checks SemVer, versions and tags on main (or stable-X.Y for a patch), pushes, creates the GitHub release, pushes Docker :X.Y.Z, :X.Y and :latest, updates the local instance, then replies to and closes fixed issues. For a bare "ship it", ask beta or stable first.
---

# Ship it to stable

The policy is in docs/RELEASING.md. Stable is roughly weekly and only on the
maintainer's word; it promotes what the latest beta carried.

## 1. Preflight

1. `git status` is clean; `git config core.hooksPath` prints `tools/git-hooks`.
2. On `main` for a normal stable. For an urgent patch (a crash, data loss, a
   security hole, an instance that can't start or can't sign anyone in, and
   nothing else), follow "Urgent patches" in docs/RELEASING.md: fix on main
   first, then cherry-pick onto a `stable-X.Y` branch cut from the last tag.
3. **Main against the latest beta.** List what the beta never carried:
   `git log $(git tag -l 'v*-beta.*' --sort=-v:refname | head -1)..main --oneline`.
   If anything user-visible is there, **ask** whether to include it untested
   or cut another beta first.
4. `## Unreleased` in `CHANGELOG.md` holds every user-visible change, from the
   user's side, factual, no emoji.
5. `tools/next-version.sh --why`. If the maintainer named a version that does
   not fit, **stop and say so plainly**, and what SemVer calls for. A week
   with no features is a patch, not a minor. They decide.
6. New contributors are in `data/CONTRIBUTORS` and `docs/CREDITS.md`.

## 2. Prepare (local only)

```sh
tools/prepare-release.sh stable          # or give the version: stable X.Y.Z
git show --stat HEAD
tools/release-notes.sh X.Y.Z
```

Check that `git log origin/main..main --format=%B` carries no AI attribution
(the pre-push hook refuses it anyway).

## 3. Publish

```sh
git push origin main vX.Y.Z               # stable-X.Y instead of main for a patch
tools/release-notes.sh X.Y.Z > /tmp/notes-X.Y.Z.md
gh release create vX.Y.Z --title "vX.Y.Z" --notes-file /tmp/notes-X.Y.Z.md
tools/publish-image.sh X.Y.Z
docker compose pull && docker compose up -d      # the maintainer's own instance
curl -fsS http://localhost:<port>/healthz        # reports the new version
```

The title is the version and nothing else: no name, no tagline. The body is
that version's section plus the generated list; never hand CHANGELOG.md itself
to `gh release create`. No mention of the AI tool, no "Generated with" footer.

For a patch: merge `stable-X.Y` back into `main` afterwards, and ship a beta
from main alongside, so the beta is never missing a fix stable has. Never
delete a `stable-X.Y` branch.

## 4. After

- Reply to every issue this release fixes, then close it (docs/CONTRIBUTING.md,
  "Issue replies"): `*Agentic reply:*`, a blank line, one or two sentences
  naming the version, then the update command as its own paragraph. No thanks,
  no em dash. If the maintainer said they will answer an issue themselves,
  leave it open and alone.
- Issues fixed in a beta and left open close now, with this version named.
- Superseded releases (the previous patch on this line; the beta this stable
  promoted): delete the release and tag only after this one is live,
  `releases/latest` points at it, and its notes were generated, and only if
  the maintainer has agreed to that policy for this project. Never delete
  Docker tags or `stable-X.Y` branches.
- Report: the version, commit, tags pushed, release URL, issues closed, and
  anything that went wrong.
