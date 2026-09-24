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
    if git log --format=%B $range 2>/dev/null | grep -qiE "$ATTRIBUTION"; then
        block "a commit about to be pushed carries AI attribution. Find it with: git log --format='%h %s%n%b' $range"
    fi
fi

if [ -f .git/info/exclude ] && grep -qx 'CLAUDE.md' .git/info/exclude &&
   runs 'git\s+add\b[^;&|]*(CLAUDE[.]md|\.claude\b)'; then
    block "CLAUDE.md and .claude/ are local only in this repository and must not be staged."
fi

if runs '(sudo\s+)?pkill\s[^;&|]*-f'; then
    block "pkill -f matches this tool's own shell and kills it. Find the PID with 'pgrep -af <pattern>', then 'kill <pid>'."
fi

exit 0
