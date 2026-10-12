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
4. Deletes this file, `tests/test_template.py`, the visual baselines (they
   show the template's name; the app's first browser run writes its own) and
   itself, then reformats with ruff if it is installed, since the new name
   changes line lengths.
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
| `<pkg>/static/css/tokens.css` | `--accent`, `--accent-ink`, `--accent-glow` and `--wash`, in both themes, if the app gets its own color |
| `<pkg>/models.py` | Replace `Item` with the app's own model (see "The worked example" below) |
| `<pkg>/worker.py` | `_work()`, the periodic work, or delete the worker and set `WORKER_MINUTES=0` |
| `tests/browser/baselines/` | Written by the first `tools/check.sh`; look at them and commit them |
| `<pkg>/config.py`, `SOURCE_URL` | The repository the About section links to (already `hyprlab/<pkg>`) |
| `docs/` | Written generically; adjust as the app takes shape |

## What to keep

The parts that are the same in every app and not worth rebuilding:

- **The app factory and what it wires together**: `security.py` (CSRF, the
  admin check, headers), `setup.py` (the wizard and its gate), `errors.py`
  (JSON or a page), `database.py` (the SQLite pragmas), `templating.py`
  (`static_url`, the module import map, `icon()`, the `ago` filter),
  `migrations.py`, `validation.py` and `worker.py`.
- **`auth.py`, `account.py`, `admin.py`, `cli.py`**: accounts, preferences,
  the admin panel and the commands.
- **The stylesheets** in `static/css/` and the shell in `templates/app.html`
  and `templates/partials/`: the design system ([DESIGN.md](DESIGN.md)).
- **The JavaScript modules** in `static/js/`: `api.js`, toasts with Undo, the
  theme switch, the dialog handling in `dialogs.js` and `restore.js` (the
  backdrop-click detection is subtle and was hard won), settings, menus, the
  palette, paging and pull to refresh.
- **`about_docs.py`**: the About section renders `CHANGELOG.md`, so a release shows
  in the app with no second file to keep.
- **`tools/`, `tests/`, `.github/`, `.claude/`**, the checks and their budgets
  in `pyproject.toml`, and every doc in `docs/` except this one.

## What to delete when it is not needed

- The worker: `worker.py`'s `_work()` can stay empty with `WORKER_MINUTES=0`;
  to remove it, delete `worker.py` and the `worker.start(app)` call in
  `create_app()`.
- `sanitize.py`, if the app never renders HTML it did not write.
- Turnstile, if the app will never face the public internet: `turnstile.py`
  and its blueprint in `__init__.py`, the two `turnstile.verify_form()` calls
  in `auth.py`, its context value in `templating.py`, `static/js/turnstile.js`
  and its import in `app.js`, the Security row in `partials/settings.html` with
  `partials/settings/security.html`, the blocks in `auth/form.html`, and its
  tests. Leaving it is harmless: it is off until turned on.
- Pull to refresh, if a reload would lose state: `static/js/pull-to-refresh.js`
  and its import in `app.js`, the `#ptr` element in `app.html`, and its rules in
  `overlays.css`.

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

It lives in as few places as possible, so replacing it is replacing these and
keeping the shapes:

| | |
| --- | --- |
| `<pkg>/models.py` | `Item` (and `VIEWS`, if the views change) |
| `<pkg>/main.py` | The home page (`main.index`, which stays the home page's name) and the records API |
| `templates/partials/records.html` | The list, rendered for a page load and for `?partial=1` |
| `templates/partials/record_form.html`, `sheet.html`, `sidebar.html` | The form, the detail sheet, and the sidebar's filters |
| `static/js/records.js`, `record-form.js`, `sheet.js` | The list, the form and the sheet in the browser |
| `static/css/records.css` | Cards, rows, empty states and the pager |
| `admin.py`'s `pane_context()` | The record counts in the Admin section |
| `tests/test_items.py`, `test_listing.py`, `tests/browser/test_records.py`, `test_sheet.py` | Their tests, with `tests/snapshots/routes.txt` for the routes |
