#!/usr/bin/env bash
# PostToolUse for Edit and Write: run tools/check-code.py on the file just
# changed. A broken budget (file or function size, complexity, a repeated
# block, a JavaScript import of a name that isn't exported) comes back to
# Claude at once (exit 2, the reason on stderr), while the change is fresh.
# The same checker runs in the pre-commit hook and in CI, so this is early
# warning, not the only line of defense.
set -uo pipefail

file=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)
[ -n "$file" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
[ -f tools/check-code.py ] || exit 0
case "$file" in *.py|*.js|*.css|*.html) ;; *) exit 0 ;; esac

if [ -x .venv/bin/python ]; then py=.venv/bin/python; else py=python3; fi
if ! out=$("$py" tools/check-code.py "$file" 2>&1); then
    {
        echo "$out"
        echo "Fix this now, by concern: reuse or extract a helper for a repeated block, split a long"
        echo "function into named steps, split a file by what its parts do. Budgets: pyproject.toml."
    } >&2
    exit 2
fi
exit 0
