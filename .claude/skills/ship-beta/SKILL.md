---
name: ship-beta
description: Publish a beta release of this app. Use when the maintainer says "Ship it to beta", "ship a beta" or "cut a beta". Merges main into the beta branch, versions it X.(N+1).0-beta.K, tags, pushes, creates the GitHub prerelease and pushes the Docker :beta image. Not for "ship it to stable"; for a bare "ship it", ask beta or stable first.
---

# Ship it to beta

The policy is in docs/RELEASING.md ("Channels and cadence"). A beta is the gate
before a stable, nightly-style: whatever is on main, whenever the maintainer
asks. There are no automatic catch-up betas after a stable.

## 1. Preflight

1. `git status` is clean and you are on `main`. `git config core.hooksPath`
   prints `tools/git-hooks`.
2. `CHANGELOG.md` has entries under `## Unreleased`. If a user-visible change
   has no line, write it now (from the user's side, factual, no emoji) and
   commit it as `docs(changelog): note <thing>`.
3. `tools/next-version.sh beta --why` says which version SemVer calls for and
   why. If the maintainer named a different version, **stop and say so
   plainly**: what doesn't fit, and what SemVer calls for. They decide.
4. Anyone whose code, art or translation is in this beta is in
   `data/CONTRIBUTORS`, or their @ is stripped from the notes.

## 2. Prepare (local only)

```sh
tools/prepare-release.sh beta            # or give the version: beta X.Y.0-beta.K
```

It runs the tests and the docs check, merges main into `beta` (creating the
branch the first time), rebuilds the changelog section, commits
`chore(release): X.Y.0-beta.K` and tags it. Then check:

```sh
git show --stat HEAD
tools/release-notes.sh X.Y.0-beta.K
```

and that `git log origin/beta..beta --format=%B` carries no AI attribution.

## 3. Publish

```sh
git push origin main beta vX.Y.0-beta.K
tools/release-notes.sh X.Y.0-beta.K > /tmp/notes-X.Y.0-beta.K.md
gh release create vX.Y.0-beta.K --prerelease --title "vX.Y.0-beta.K" --notes-file /tmp/notes-X.Y.0-beta.K.md
tools/publish-image.sh X.Y.0-beta.K
git checkout main
```

Always `--prerelease`, so `releases/latest` keeps pointing at stable. The
title is the version and nothing more. Nothing in the release body mentions
the AI tool or carries a "Generated with" footer.

## 4. After

- The previous beta is superseded. Delete its release and tag only after this
  one is live and its notes were generated, and only if the maintainer has
  agreed to that policy for this project (docs/RELEASING.md, "The Releases
  page"). Never delete Docker tags.
- Issues fixed in this beta: reply per docs/CONTRIBUTING.md ("Issue
  replies"), naming the beta and saying it reaches stable with the next weekly
  release. **Leave them open**; they close when that stable ships. Every reply
  begins with `*Agentic reply:*`, has no thanks and no em dash.
- Report: the version, the tag's commit, the image tags pushed, the release
  URL, and anything that went wrong.
