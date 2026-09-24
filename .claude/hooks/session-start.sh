#!/usr/bin/env bash
# SessionStart: a short status Claude reads before the first message, so the
# repository's state is known instead of assumed.
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || { echo "Not a git repository yet."; exit 0; }

version=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' */__init__.py 2>/dev/null | head -1)
branch=$(git symbolic-ref --short HEAD 2>/dev/null || echo detached)
stable=$(git tag -l 'v*' --sort=-v:refname | grep -v -- '-' | head -1)
beta=$(git tag -l 'v*-*' --sort=-v:refname | head -1)
if ahead=$(git rev-list --count '@{u}..HEAD' 2>/dev/null); then
    ahead="$ahead local commit(s) not pushed"
else
    ahead="no upstream branch"
fi
hooks=$(git config core.hooksPath)

echo "Repository: branch $branch, __version__ $version, latest stable ${stable:-none}, latest beta ${beta:-none}, ${ahead}."
if [ "$hooks" != "tools/git-hooks" ]; then
    echo "WARNING: core.hooksPath is '${hooks:-unset}', so the commit hooks are NOT running. Fix: git config core.hooksPath tools/git-hooks"
fi
if [ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then
    echo "The working tree has uncommitted changes."
fi
unreleased=$(awk '/^## Unreleased/{f=1;next} /^## /{f=0} f && /^- /' CHANGELOG.md 2>/dev/null | wc -l)
echo "CHANGELOG.md has $unreleased unreleased entr$( [ "$unreleased" = 1 ] && echo y || echo ies)."
