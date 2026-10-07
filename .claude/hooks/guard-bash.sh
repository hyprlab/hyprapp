#!/usr/bin/env bash
# PreToolUse guard for Bash. Blocks (exit 2; Claude reads the reason on
# stderr) the few commands that break a standing rule in CLAUDE.md:
#
#   * a push whose commits carry AI attribution
#   * staging CLAUDE.md or .claude/ in an app's repository
#   * pkill -f, which matches the tool's own shell and kills it
#
# Only commands in command position count (start of a line, or after ; & | or
# a parenthesis), so a heredoc that writes documentation mentioning these
# commands is not mistaken for running them. Commit messages themselves are
# checked by tools/git-hooks/commit-msg, which sees the real message.
set -uo pipefail

cmd=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)
[ -n "$cmd" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

block() { echo "Blocked by .claude/hooks/guard-bash.sh: $*" >&2; exit 2; }
at_start='(^|[;&|(]\s*)'
runs() { printf '%s\n' "$cmd" | grep -qE "${at_start}$1"; }

ATTRIBUTION='co-authored-by:.*(claude|anthropic)|noreply@anthropic[.]com|claude-session:|generated with .?claude'

if runs 'git\s+([^;&|]*\s)?push\b'; then
    upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)
    if [ -n "$upstream" ]; then range="$upstream..HEAD"; else range="HEAD --not --remotes"; fi
    # shellcheck disable=SC2086
    # Not grep -q: it stops reading at the first match, git log dies of
    # SIGPIPE, and under pipefail the whole test then counts as false, so a
    # long history with attribution in it would pass.
    if git log --format=%B $range 2>/dev/null | grep -iE "$ATTRIBUTION" >/dev/null; then
        block "a commit about to be pushed carries AI attribution. Find it with: git log --format='%h %s%n%b' $range"
    fi
fi

# Staging CLAUDE.md or .claude/ is refused in a repository that keeps them
# local (lists CLAUDE.md in .git/info/exclude). Which repository a `git add`
# stages into is worked out from the command itself: a `cd` before it on the
# same line, or `git -C <dir>`, else the project. The template's own
# repository tracks these files on purpose, so it is never refused.
staging_targets() {
    python3 - "$cmd" "${CLAUDE_PROJECT_DIR:-$PWD}" <<'PY'
import os, re, shlex, sys
cmd, cwd = sys.argv[1], sys.argv[2]
for part in re.split(r"&&|\|\||[;&|\n]", cmd):
    try:
        words = shlex.split(part)
    except ValueError:
        continue
    if not words:
        continue
    if words[0] == "cd" and len(words) > 1:
        cwd = os.path.join(cwd, os.path.expanduser(words[1]))
        continue
    if words[0] != "git":
        continue
    target, i = cwd, 1
    while i < len(words) and words[i].startswith("-"):
        if words[i] == "-C" and i + 1 < len(words):
            target = os.path.join(target, os.path.expanduser(words[i + 1]))
            i += 2
            continue
        i += 1
    if i < len(words) and words[i] == "add" and any(re.search(r"CLAUDE\.md|\.claude\b", w) for w in words[i + 1:]):
        print(target)
PY
}
while IFS= read -r target; do
    exclude=$(git -C "$target" rev-parse --path-format=absolute --git-path info/exclude 2>/dev/null) || continue
    if [ -f "$exclude" ] && grep -qx 'CLAUDE.md' "$exclude"; then
        block "CLAUDE.md and .claude/ are local only in $(git -C "$target" rev-parse --show-toplevel) and must not be staged."
    fi
done < <(staging_targets)

if runs '(sudo\s+)?pkill\s[^;&|]*-f'; then
    block "pkill -f matches this tool's own shell and kills it. Find the PID with 'pgrep -af <pattern>', then 'kill <pid>'."
fi

exit 0
