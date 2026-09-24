---
name: contributor-credit
description: "Outside PRs land as maintainer commits with Co-Authored-By using the contributor's GitHub NOREPLY address (<id>+<login>@users.noreply.github.com); add to data/CONTRIBUTORS + docs/CREDITS.md; @-mentions in release notes only for code/art/translation contributors, reporters named without @"
metadata:
  type: feedback
---

- Outside pull requests land as hand-applied commits on `main` (not merges),
  crediting the author with a `Co-Authored-By:` trailer.
- **Use their GitHub noreply address**: `<id>+<login>@users.noreply.github.com`,
  id from `gh api users/<login> --jq .id`. An address taken from their own
  commit may not be linked to their account; then they never appear as a
  contributor, and it can't be fixed after a tagged release without rewriting
  history (it happened in Vireo, PR #13).
- Add them to `data/CONTRIBUTORS` (`Name @login`) and describe the work in
  `docs/CREDITS.md`, **before** generating release notes: `tools/release-notes.sh`
  strips the @ from any handle not listed there.
- In release notes, an **@ is only for people whose code, art or translation
  is in the release.** Reporters and requesters are named plainly: an @
  notifies and reads as authorship (Hylki #277, agreed 2026-09-24).
- Close the PR with a comment saying what was taken, changed and left out
  ([[issue-replies]]).

**Why:** GitHub matches commits to accounts by verified email only.

**How to apply:** this is the one place a `Co-Authored-By:` belongs; the tool
never gets one ([[no-ai-attribution]]).
