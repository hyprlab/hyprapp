#!/usr/bin/env bash
# Everything CI checks, in the same order, so "it passes" means one thing.
#
#   tools/check.sh                  # all of it: static, tests, browser, image
#   tools/check.sh --fast           # static and tests: no browser, no Docker
#   tools/check.sh static tests     # just these stages
#
#   static   ruff (lint, format), check-code.py, check-docs.py, commit messages
#   tests    pytest without the browser, with the coverage floor
#   browser  the Playwright suite, visual comparison included
#   image    docker build
#
# CI runs each stage in its own job (.github/workflows/ci.yml) by calling this
# script, so a check is defined here once. CHECK_BASE is the commit the
# message check starts from; it defaults to origin/main, else main.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -x .venv/bin/python ]; then py=.venv/bin/python; else py=python3; fi
pkg=$(ls */__init__.py | grep -vE '^(tests|tools)/' | head -1 | cut -d/ -f1)

step() { printf '\n==> %s\n' "$*"; }

commit_messages() {
    local base="${CHECK_BASE:-}" status=0
    if [ -z "$base" ]; then
        base=$(git rev-parse -q --verify origin/main || git rev-parse -q --verify main || true)
    fi
    [ -n "$base" ] || { echo "no base to compare with; skipped"; return 0; }
    for sha in $(git rev-list --no-merges "$base..HEAD"); do
        git log -1 --format=%B "$sha" > "${TMPDIR:-/tmp}/check-msg-$$"
        if ! "$py" tools/git-hooks/commit-msg "${TMPDIR:-/tmp}/check-msg-$$"; then
            echo "    in $(git log -1 --format='%h %s' "$sha")" >&2
            status=1
        fi
    done
    rm -f "${TMPDIR:-/tmp}/check-msg-$$"
    return $status
}

static() {
    step "ruff check";            "$py" -m ruff check .
    step "ruff format --check";   "$py" -m ruff format --check .
    step "check-code";            "$py" tools/check-code.py
    step "check-docs";            "$py" tools/check-docs.py
    step "commit messages";       commit_messages
}

tests() {
    step "pytest, with the coverage floor"
    "$py" -m pytest -q -m "not browser" --cov --cov-report=term
}

browser() {
    step "browser suite, with the visual comparison"
    "$py" -m pytest -q -m browser
}

image() {
    step "docker build"
    docker build -q -t "$pkg-check" . >/dev/null && echo "built $pkg-check"
}

stages=("$@")
[ ${#stages[@]} -gt 0 ] || stages=(static tests browser image)
[ "${stages[0]}" != "--fast" ] || stages=(static tests)
for stage in "${stages[@]}"; do
    case "$stage" in
        static|tests|browser|image) "$stage" ;;
        *) echo "unknown stage: $stage (static, tests, browser, image, or --fast)" >&2; exit 2 ;;
    esac
done
step "all checks passed: ${stages[*]}"
