---
name: ship-flow
description: "How a Flask/Docker app ships: tools/prepare-release.sh (local commit+tag), push, tools/release-notes.sh -> gh release (title just vX.Y.Z), tools/publish-image.sh (amd64), pull the local instance, reply/close issues; CHANGELOG is the single record (no RELEASE_NOTES.md)"
metadata:
  type: project
---

Triggers and policy: [[release-cadence]]. The full procedure is
docs/RELEASING.md; the `ship-beta` and `ship-stable` skills walk it.

1. Preflight: clean tree, hooks on, `## Unreleased` written, contributors in
   `data/CONTRIBUTORS`, `tools/next-version.sh --why` agrees with the version
   ([[semver-strict]]).
2. `tools/prepare-release.sh beta|stable [VERSION]`: tests + docs check,
   version and changelog, commit `chore(release): X.Y.Z`, annotated tag. Local
   only.
3. Push the branch(es) and the tag.
4. `tools/release-notes.sh X.Y.Z > notes.md`, then
   `gh release create vX.Y.Z --title "vX.Y.Z" --notes-file notes.md`
   (`--prerelease` for a beta). **The title is the version and nothing else;
   no marketing name, no tagline.** Never hand CHANGELOG.md itself to
   `gh release`: that ships the whole history onto every release page.
5. `tools/publish-image.sh X.Y.Z`: builds from the tag via `git archive`,
   pushes `:X.Y.Z :X.Y :latest` (stable) or `:X.Y.Z-beta.K :beta` (beta).
   linux/amd64 only: the host's buildx has no arm64 builder.
6. Stable: `docker compose pull && docker compose up -d` on Jason's instance,
   check `/healthz` shows the new version.
7. Reply to and close fixed issues ([[issue-replies]]).

**CHANGELOG.md is the single record** (Jason's Hyprfeed decision, 2026-08-08:
do NOT reintroduce a RELEASE_NOTES.md). The About section renders it via
`about_docs.py`. From Hylki: **every release, patches included, gets a
section**; a skipped one is a gap users see in the app.

**Why:** these steps are what Hyprfeed and Hylki settled on; the scripts exist
because hand-typed commit messages and pin lines broke Hylki ships repeatedly.

**How to apply:** if a script fails mid-ship, fix the script, not just the
run, and say what happened. Write temporary files to fresh names.
