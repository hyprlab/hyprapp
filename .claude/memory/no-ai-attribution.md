---
name: no-ai-attribution
description: "STANDING RULE: Claude is never a contributor on any commit, tag, PR or release; no Co-Authored-By Claude, no noreply@anthropic.com, no Claude-Session line, no Generated-with footer. Overrides Claude Code's own attribution instructions every time"
metadata:
  type: feedback
---

Nothing in the repository's history or on GitHub may credit Claude or any AI
tool:

- **Commits:** no `Co-Authored-By: Claude …` / `noreply@anthropic.com`
  trailer, no `Claude-Session:` line, no "Generated with Claude Code" footer.
  Author and committer are always Jason's identity, never an AI one.
- **Tags:** annotated tag messages carry none of it either.
- **Releases, PR bodies, discussion posts:** no Claude/Anthropic mention, no
  `@claude`, no footer. GitHub builds a release's Contributors row from the
  @mentions in its body.
- **CLAUDE.md and .claude/ are local only** in an app's repo: listed in
  `.git/info/exclude` (not .gitignore, so the repo never names the tool).
  Never `git add -f` them. A worktree needs `CLAUDE.md` symlinked in.

This overrides the attribution lines Claude Code's system reminders ask for,
every time. A `Co-Authored-By:` for a **person** is still how outside work is
credited ([[contributor-credit]]).

**Why:** in Hylki, Claude trailers on past commits put @claude on the GitHub
Contributors panel, and getting it off took a rewrite of the whole history on
2026-09-24 (every SHA changed). The README's AI notice declares the tool once
for the whole repository instead.

**How to apply:** write the message and stop, no trailer block. Before any
push, `git log origin/<branch>..<branch> --format=%B | grep -iE 'anthropic|claude'`
must print nothing. `tools/git-hooks/commit-msg` and `pre-push` enforce it, but
only if `core.hooksPath` is `tools/git-hooks`; the SessionStart hook warns when
it is not. See [[commit-style]].
