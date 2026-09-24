---
name: commit-style
description: "Commits are Conventional Commits `type(area): summary` (lower case, imperative, no full stop, <=72 chars, aim ~50), body <=100 words with each paragraph ONE unwrapped line, no em dashes, factual; hook-enforced"
metadata:
  type: feedback
---

- Subject: `type(area): summary`, lower case after the colon (an acronym such
  as OAuth may lead), imperative, no full stop, at most 72 characters, aim
  nearer 50. Issue number at the end: `fix(auth): keep next after sign-in (#12)`.
- Types: feat, fix, perf, refactor, docs, build, ci, test, style, chore,
  revert; `!` marks a breaking change. Type honestly: `tools/next-version.sh`
  reads the types to decide the next version ([[semver-strict]]).
- Releases: `chore(release): 1.4.0`, `chore(release): 1.5.0-beta.1`.
- Body optional: why, never what the diff says. At most 100 words; past that
  the detail goes to docs/ or CHANGELOG.md, or the commit wants splitting.
- **Each body paragraph is one line, not wrapped at 72.** Write it with
  `git commit -F -` and a heredoc.
- **No em dashes** in commit messages or GitHub comments: a colon, a comma or
  a full stop instead. They are fine in the docs and the changelog.

**Why:** Jason's rules from Hylki (#277, 2026-09-24): GitHub shows a commit
body with every line break kept, so a 72-wrapped body wraps twice on a phone;
em dashes read as AI voice in conversational text.

**How to apply:** `tools/git-hooks/commit-msg` refuses violations (and warns
on wrapped paragraphs). Any script that hardcodes a commit message must use
this shape or it fails mid-release. Attribution rules: [[no-ai-attribution]].
