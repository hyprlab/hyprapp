# Starting a new app from the template

This file is about the template itself. `tools/init-project.sh` deletes it,
and itself, once a copy has become a real app.

## Starting

```sh
rsync -a --exclude .git ~/hyprapp/ ~/myapp/ && cd ~/myapp
tools/init-project.sh myapp "My App" "" "What it does, in one line."
```

The script:

1. Renames the `hyprapp` package, the display name and the tagline everywhere.
2. Sets the host port in `docker-compose.yml`.
3. Resets `__version__` to `0.1.0` and writes a fresh `CHANGELOG.md` and a
   README skeleton in the house shape.
4. Deletes this file, `tests/test_template.py` and itself.
5. Runs `git init -b main` and sets `core.hooksPath tools/git-hooks`, so the
   commit rules hold from the first commit.
6. Lists `CLAUDE.md` and `.claude/` in `.git/info/exclude`, so the app's
   repository never names the tool.
7. Copies `.claude/memory/*.md` into the Claude Code memory directory for the
   new path.

It refuses to run where `.git` exists; copy without the template's history.

The third argument is the host port. Left empty, the script takes the first
port from 8090 up that no container and no listening socket is using. Host
8000 is Portainer, and the 8090s were full by September 2026 (Hyprfeed has
8098), so new apps continue at 8100 and up. To see what is taken:

```sh
docker ps --format '{{.Names}} {{.Ports}}'
```

The template itself runs on 8100 if started as it is.

The template is the one repository that does track `CLAUDE.md` and `.claude/`:
they are part of what gets copied.

## What to change first

| | |
| --- | --- |
| `README.md` | Fill in the skeleton. It is the front door and has a 200-line ceiling. |
| `<pkg>/static/img/logo.svg` and `templates/partials/mark.html` | The brand mark, in both places, with the same path |
| `<pkg>/static/css/app.css` | `--accent`, `--accent-ink` and `--accent-glow`, in both themes, if the app gets its own color |
| `<pkg>/models.py` | Replace `Item` with the app's own model |
| `<pkg>/worker.py` | The periodic work, or delete it and set `WORKER_MINUTES=0` |
| `<pkg>/config.py`, `SOURCE_URL` | The repository the About section links to (already `hyprlab/<pkg>`) |
| `docs/` | Written generically; adjust as the app takes shape |

## What to keep

The parts that are the same in every app and not worth rebuilding:

- **The app factory**: CSRF, the setup gate, security headers, JSON-or-page
  errors, SQLite pragmas, `static_url`, the `ago` filter, `_migrate()` and the
  worker thread.
- **`auth.py`, `setup.py`, `cli.py`** and the account and admin halves of
  `main.py`.
- **`static/css/app.css`** and the shell in `templates/app.html`: the design
  system ([DESIGN.md](DESIGN.md)).
- **`static/js/app.js`**: the API helper, toasts with Undo, the theme switch,
  the dialog handling (the backdrop-click detection is subtle and was hard won),
  settings, menus, the palette, paging and pull to refresh.
- **`about_docs.py`**: the About section renders `CHANGELOG.md`, so a release shows
  in the app with no second file to keep.
- **`tools/`, `tests/`, `.github/`, `.claude/`** and every doc in `docs/`
  except this one.

## What to delete when it is not needed

- `worker.py` and the `_start_worker` call, if there is no periodic work.
- `sanitize.py`, if the app never renders HTML it did not write.
- Turnstile (the Security section, its routes in `main.py`, the helpers in
  `auth.py` and the blocks in the auth templates), if the app will never face
  the public internet. Leaving it is harmless: it is off until turned on.
- The pull-to-refresh block in `app.js` and the `#ptr` element, if a reload
  would lose state.

## The worked example

`Item` exists so nothing in the shell is wired to a placeholder. Its title,
body, pinned flag and done flag between them exercise:

- a list and a card view over the same records, switched in the topbar, with
  the default a per-user preference
- a sort menu, and filters in the sidebar with live counts
- an optimistic toggle (the pin) that rolls back if the server refuses
- a detail sheet opened from a card, the palette, or `?open=<id>`, with
  `j`/`k` to move through the list
- delete with Undo instead of a confirmation dialog
- paging by "Load more" or infinite scroll (a user preference), both
  re-rendering the list through the same Jinja partial
- one form for create and edit

Replacing it means a new model, new routes in `main.py`, a new
`partials/records.html`, and the matching tests. Keep the shapes.
