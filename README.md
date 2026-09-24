<p align="center">
  <img src="hyprapp/static/img/logo.svg" width="72" alt="Hyprapp logo">
</p>

<h1 align="center">Hyprapp</h1>

<p align="center"><strong>The Hyprlab Flask template: a finished shell, a design system and the release machinery, ready to be shaped into an app.</strong></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue" alt="AGPL-3.0 license"></a>
  <img src="https://img.shields.io/badge/python-3.12-blue" alt="Python 3.12">
  <img src="https://img.shields.io/badge/docker-SQLite%20in%20one%20volume-blue" alt="Docker, SQLite in one volume">
</p>

Every Hyprlab web app is a Flask app in one Docker container with SQLite in
one volume, and every one needs the same accounts, settings, layout and
release process. This template has all of that built and running, taken from
Hyprfeed's interface and Hylki's conventions, so a new app starts at the part
that is actually new.

## What it starts with

- **The shell**: a sidebar with a pinned head and foot, a sticky topbar with
  search, sort and view controls, a two-pane settings window, a detail sheet that
  rises from below, a Ctrl/Cmd+K palette, toasts with Undo, pull to refresh,
  and light and dark themes
- **Accounts**: email sign-in, a first-run setup wizard, per-user preferences,
  a sign-in throttle, and Cloudflare Turnstile, set up from Settings
- **An admin panel**: the first account is the admin; manage users and
  passwords, open or close registration, change instance settings live
- **A worked example**: one model wired through cards and a list, paging or
  infinite scroll, the sheet, search and the JSON API
- **Operations**: gunicorn, SQLite in WAL mode, guarded migrations, a
  background worker, `/healthz`, and `flask` commands for users and backups
- **The release machinery**: strict SemVer read from Conventional Commits, beta
  and stable channels, the changelog shown in the About section, commit hooks that
  keep AI attribution out of the history, and a documentation checker
- **Claude Code set up**: `CLAUDE.md`, project settings with guard hooks, ship
  skills for both channels, and starter memories

## Starting a new app

```sh
rsync -a --exclude .git ~/hyprapp/ ~/myapp/ && cd ~/myapp
tools/init-project.sh myapp "My App" "" "What it does, in one line."
```

That renames everything, resets the version to 0.1.0, starts git with the
hooks enabled, and installs the memories. Then:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
tools/redeploy.sh                  # builds and runs the container
```

The first visit opens the setup wizard. **[The full walkthrough →](docs/TEMPLATE.md)**

## Documentation

| | |
| --- | --- |
| [Starting a new app](docs/TEMPLATE.md) | What to rename, keep and delete |
| [Documentation](docs/DOCUMENTATION.md) | Installing, configuration, proxies, backups, commands |
| [Architecture](docs/ARCHITECTURE.md) | How the pieces fit, and why |
| [Design system](docs/DESIGN.md) | Tokens, components and interface rules |
| [Contributing](docs/CONTRIBUTING.md) | Commits, prose style, credit, issue replies |
| [Releasing](docs/RELEASING.md) | SemVer, the beta and stable channels, shipping |
| [Security](docs/SECURITY.md) | What it defends against, and reporting |
| [Changelog](CHANGELOG.md) | What changed in each release |

## AI notice

Hyprapp is built by a human maintainer who uses generative AI as a development
tool. Most of the code was written by Anthropic's Claude, through Claude Code,
following the maintainer's direction; the maintainer decides what gets built,
reviews the results, tests every release and signs off on everything that
ships. Commits are made under the maintainer's name; the tool is declared here
once, for the whole repository, instead of in a trailer on every commit.

The app itself contains no AI. It has no AI features and makes no requests to
AI services.

## License

Hyprapp is free software, licensed under the **GNU Affero General Public
License v3.0 or later** ([AGPL-3.0-or-later](LICENSE)). Inter is under the SIL
Open Font License ([credits](docs/CREDITS.md)).

© 2026 Hyprlab
