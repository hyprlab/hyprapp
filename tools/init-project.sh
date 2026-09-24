#!/usr/bin/env bash
# Turn a copy of this template into a new app. Run once, from the copy's root.
#
#   rsync -a --exclude .git ~/hyprapp/ ~/myapp/ && cd ~/myapp
#   tools/init-project.sh myapp "My App" "" "A tagline for it."
#
#   1  package name: lower case (becomes the Python package, the container and
#      the Docker image hyprlab/<name>)
#   2  display name (default: the package name, capitalized)
#   3  host port for docker compose (default: the first free port from 8090
#      up, skipping 8000, which is Portainer; see docs/TEMPLATE.md)
#   4  tagline (default: "A self-hosted Flask app.")
#
# It renames everything, resets the version to 0.1.0 with a fresh changelog and
# README, removes the template-only files (this script included), runs git
# init with the hooks enabled, keeps CLAUDE.md and .claude/ out of git, and
# installs the starter memories for Claude Code.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

OLD_PKG=hyprapp
OLD_NAME=Hyprapp
OLD_TAGLINE="A self-hosted Flask app."

PKG="${1:-}"
[ -n "$PKG" ] || { sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
printf '%s' "$PKG" | grep -Eq '^[a-z][a-z0-9_]*$' \
    || { echo "The package name must match [a-z][a-z0-9_]*" >&2; exit 1; }
NAME="${2:-$(printf '%s' "$PKG" | sed 's/^./\U&/')}"
PORT="${3:-}"
if [ -z "$PORT" ]; then
    used=$(docker ps -a --format '{{.Ports}}' 2>/dev/null | grep -oE ':[0-9]+->' | tr -d ':->' | sort -u)
    PORT=8090
    while printf '%s\n' $used | grep -qx "$PORT" || ss -ltn 2>/dev/null | grep -qE "[:.]$PORT\s"; do
        PORT=$((PORT + 1))
    done
    echo "==> host port $PORT (the first free one from 8090)"
fi
TAGLINE="${4:-$OLD_TAGLINE}"

[ -d "$OLD_PKG" ] || { echo "$OLD_PKG/ is missing: this is not a fresh copy of the template." >&2; exit 1; }
[ ! -e .git ] || { echo ".git already exists: copy the template without its history," >&2
                   echo "  rsync -a --exclude .git ~/hyprapp/ ~/myapp/" >&2; exit 1; }
if docker ps --format '{{.Ports}}' 2>/dev/null | grep -q ":$PORT->"; then
    echo "warning: host port $PORT is already published by a running container." >&2
fi

echo "==> $OLD_PKG -> $PKG, \"$OLD_NAME\" -> \"$NAME\", port $PORT"

# 1. The package, then every text reference to it.
mv "$OLD_PKG" "$PKG"
esc() { printf '%s' "$1" | sed 's/[\/&|]/\\&/g'; }
grep -rlI --exclude-dir={.git,.venv,var,claude-memory-hylki} -e "$OLD_PKG" -e "$OLD_NAME" . \
  | while read -r f; do
      sed -i "s|$OLD_PKG|$(esc "$PKG")|g; s|$OLD_NAME|$(esc "$NAME")|g" "$f"
    done
grep -rlI --exclude-dir={.git,.venv,var} -F "$OLD_TAGLINE" . \
  | while read -r f; do sed -i "s|$(esc "$OLD_TAGLINE")|$(esc "$TAGLINE")|g" "$f"; done

# The template's own location, for the template-origin memory. Filled in
# after the rename above, which would otherwise have turned it into $PKG.
sed -i "s|@TEMPLATE_DIR@|~/hyprapp|g" .claude/memory/template-origin.md .claude/memory/MEMORY.md

# 2. The compose port.
sed -i "s/\"8100:8000\"/\"$PORT:8000\"/; s/if 8100 is taken/if $PORT is taken/" docker-compose.yml

# 3. Version, changelog, README.
sed -i 's/^__version__ = ".*"/__version__ = "0.1.0"/' "$PKG/__init__.py"
TODAY=$(date +%F)
cat > CHANGELOG.md <<CHANGELOG
# Changelog

All notable changes to $NAME are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## Unreleased

## [0.1.0] — $TODAY

### Added
- The first version, started from the Hyprlab Flask template
CHANGELOG

cat > README.md <<README
<p align="center">
  <img src="$PKG/static/img/logo.svg" width="72" alt="$NAME logo">
</p>

<h1 align="center">$NAME</h1>

<p align="center"><strong>$TAGLINE</strong></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue" alt="AGPL-3.0 license"></a>
</p>

$NAME is a self-hosted web app that runs in one Docker container with its data
in a single SQLite volume.

## Features

- Accounts with a first-run setup wizard; the first account is the admin
- Light and dark themes that follow the system

## Install with Docker Compose

\`\`\`sh
curl -O https://raw.githubusercontent.com/hyprlab/$PKG/main/docker-compose.yml
docker compose up -d
\`\`\`

Then open http://localhost:$PORT. The first visit opens the setup wizard.
Configuration is covered in [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md).

## Documentation

| | |
| --- | --- |
| [Documentation](docs/DOCUMENTATION.md) | Configuration, deployment, backups |
| [Architecture](docs/ARCHITECTURE.md) | How the pieces fit, and why |
| [Contributing](docs/CONTRIBUTING.md) | Commits, prose style, tests |
| [Releasing](docs/RELEASING.md) | Versions, the beta and stable channels |
| [Changelog](CHANGELOG.md) | What changed in each release |

## AI notice

$NAME is built by a human maintainer who uses generative AI as a development
tool. The maintainer decides what gets built, reviews the results, tests every
release and signs off on everything that ships. Commits are made under the
maintainer's name; the tool is declared here once, for the whole repository,
instead of in a trailer on every commit. The app itself contains no AI and
makes no requests to AI services.

## License

$NAME is free software, licensed under the **GNU Affero General Public License
v3.0 or later** ([AGPL-3.0-or-later](LICENSE)).

© $(date +%Y) Hyprlab
README

# 4. Template-only files.
rm -f docs/TEMPLATE.md tests/test_template.py
sed -i '/TEMPLATE\.md/d' docs/README.md
rm -rf claude-memory-hylki var .venv .pytest_cache
find . -name __pycache__ -type d -prune -exec rm -rf {} +

# 5. Git, with the hooks on and the tool's files kept out of the repository.
git init -q -b main
git config core.hooksPath tools/git-hooks
# .git/info/exclude, not .gitignore, so the repository never names the tool.
printf '%s\n' 'CLAUDE.md' '.claude/' >> .git/info/exclude

# 6. Starter memories for Claude Code, keyed to this directory.
SLUG=$(printf '%s' "$ROOT" | sed 's/[^A-Za-z0-9]/-/g')
MEM="$HOME/.claude/projects/$SLUG/memory"
mkdir -p "$MEM"
for f in .claude/memory/*.md; do
    dest="$MEM/$(basename "$f")"
    if [ -e "$dest" ]; then echo "    keeping existing $(basename "$f")"; else cp "$f" "$dest"; fi
done
echo "==> memories installed in $MEM"

rm -f tools/init-project.sh
python3 tools/check-docs.py >/dev/null && echo "==> docs check passes"

cat <<DONE

$NAME is ready in $ROOT.

  python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
  .venv/bin/python -m pytest              # the suite should pass untouched
  .venv/bin/python run.py                 # http://localhost:8000
  tools/redeploy.sh                       # the container, http://localhost:$PORT

Next: redraw the mark ($PKG/static/img/logo.svg and
$PKG/templates/partials/mark.html), set --accent in $PKG/static/css/app.css if
the app gets its own color, replace the Item model, then make the first commit:

  git add -A && git commit -m "chore: start $PKG from the Hyprlab Flask template"
DONE
