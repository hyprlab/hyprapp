# Architecture

One Flask process, SQLite in one volume, server-rendered HTML, and native
JavaScript modules with no build step. This page is how the pieces fit and why.

## Layout

```
hyprapp/
  __init__.py      __version__ and create_app(), which wires the modules below
  config.py        every environment variable, each with a working default
  models.py        the models, user lookup and creation, the runtime settings helpers
  database.py      how every SQLite connection is set up
  migrations.py    migrate(): the guarded schema steps
  security.py      the session CSRF token, the admin check, response headers
  errors.py        JSON errors for the API, error pages for people
  validation.py    reading a JSON body, the shared checks, refusing in words
  templating.py    template globals: static_url, the module import map, icons, ago
  icons.py         every icon, as inline SVG
  auth.py          sign in, sign up, sign out, the sign-in throttle
  setup.py         the first-run wizard and the gate that sends a fresh install to it
  main.py          the home page and the worked example's JSON API
  account.py       a person's own preferences and password
  admin.py         instance settings, registration and users
  turnstile.py     Cloudflare Turnstile: its keys, the challenge check, its admin routes
  health.py        /healthz
  cli.py           flask commands: create-user, reset-password, backup, turnstile
  worker.py        the periodic work and the thread that runs it
  about_docs.py    parses CHANGELOG.md for the About section
  sanitize.py      allowlist HTML sanitizer, stdlib only
  static/css/      tokens, base, layout, records, overlays, settings, pages
  static/js/       one module per feature, app.js imports them
  templates/       base and card layouts, the app shell, auth, setup, error, partials
tools/             release and repository tooling, and the checks (check.sh)
tests/             pytest; tests/browser drives the app in Chromium
```

`run.py` is the development server. Production runs gunicorn against
`hyprapp:create_app()`.

## Why the files are split this way

Each module has one job that can be named in a sentence, and the worked
example is in as few places as possible: `Item` in `models.py`, its routes in
`main.py`, its list in `partials/records.html`, its client in `records.js`,
`record-form.js` and `sheet.js`, its look in `records.css`. A new app replaces
those and keeps everything else.

A feature is a module: Turnstile is `turnstile.py`, `turnstile.js` and the
Security pane; pull to refresh is `pull-to-refresh.js`. Removing one is
removing its files and the line that wires them in. Shared pieces have one
home each, so there is one copy of every check, every icon and every request
helper, and the JavaScript modules reach each other through small registries
(`onOpen`, `remember`, `onOpenRecord`) rather than through each other's
insides.

## Where code goes

| A change | Goes in |
| --- | --- |
| A route | The blueprint for its concern: `main.py` (the home page and the worked example), `account.py`, `admin.py`, `auth.py`, `setup.py`, `turnstile.py`, `health.py`. A new blueprint joins `BLUEPRINTS` in `__init__.py`; a new route, `tests/snapshots/routes.txt` |
| A model or a column | `models.py`; a column on an existing table also needs a migration step |
| A migration step | The end of `migrate()` in `migrations.py`, inside its `fmt: off` fence |
| A validation rule or refusal | `validation.py` when more than one route checks it; the route's module otherwise |
| A per-user setting | See "Code" below; `infinite_scroll` is the worked example |
| An admin setting | `INSTANCE_SETTINGS` in `admin.py` (see "Code" below) |
| A settings section | A row in `settings_sections` in `partials/settings.html`, and `partials/settings/<id>.html` |
| A dialog | A partial in `templates/partials/`, included by `app.html`; its behavior in its JavaScript module |
| An icon | `icons.py`, drawn with `{{ icon("name") }}` |
| A JavaScript feature | One module in `static/js/` that guards on its own elements, imported by `app.js` |
| A style | The stylesheet for its part: `tokens`, `base`, `layout`, `records`, `overlays`, `settings`, `pages` (linked in that order) |
| A template global or filter | `templating.py` |
| A request guard or header | `security.py`; error pages in `errors.py` |
| Periodic work | `_work()` in `worker.py` |
| A command | `cli.py` |
| A test | `tests/test_<concern>.py`; behavior in the browser in `tests/browser/`; a deliberate new look, `UPDATE_BASELINES=1` and commit the screenshots |

The sizes are enforced, not hoped for: no file over 300 lines of Python,
JavaScript or CSS or 200 of a template, no function over 50 lines or
complexity 10, no block repeated in two places. `tools/check-code.py` checks
them on every commit and in CI ([CONTRIBUTING.md](CONTRIBUTING.md#checks)).

## Decisions

**One gunicorn worker, eight threads.** The background thread must start
exactly once, and SQLite is happiest with one writing process. Threads carry
the concurrency. If the app outgrows that, the answer is moving the background
work to its own container, not adding web workers against one SQLite file.

**SQLite in WAL mode.** Readers don't wait for the writer, and
`busy_timeout` makes a writer wait for the lock instead of failing. Foreign
keys are switched on, which SQLite leaves off by default. The sqlite3
driver's own transaction handling is turned off on connect and SQLAlchemy
emits `BEGIN` itself, because the driver's way breaks savepoints: releasing
one would commit it. So `db.session.begin_nested()` rolls back as it should.

**No migration framework.** Schema changes are steps in `migrate()` in
`migrations.py`: an `ALTER TABLE` guarded by a column check, run at every boot,
safe to run twice. New steps go at the end and old ones are never edited, not
even by the formatter, which is fenced off from them. It is enough for a
database that lives on one machine, and a deployment stays
`docker compose up -d` with nothing to remember.

**Server-rendered HTML, native JavaScript modules.** Jinja renders pages; the
modules in `static/js/` handle what would be worse as a page load. Paging
asks the server for the same list template (`?partial=1`) and splices it in,
so there is one renderer for the list, not two that drift apart. Nothing is
compiled, so what is in the repository is what runs. A module imports another
by a relative path, which carries no version, so `base.html` renders an import
map that sends each module's URL to its `static_url()` version, and
`modulepreload` links that fetch the whole graph at once.

**Session CSRF, not an extension.** A token in the session goes back as a
hidden `_csrf` field from forms and an `X-CSRF` header from `fetch`, compared
with `secrets.compare_digest`. One `before_request` covers every mutating
method.

**JSON errors for the API, pages for people.** A request that sent `X-CSRF`,
a JSON body, or prefers JSON gets `{"error": "..."}`; anything else gets the
error page. The client shows `error` as written, so it is written for a person.

**Two kinds of setting.** Environment variables are fresh-install defaults.
Anything an admin changes while the app runs is a row in `settings`, and the
stored value wins. A compose file can move between machines without carrying
one machine's choices with it.

**Preferences on the account.** Theme, default view and infinite scroll are
columns on `User`, so they follow the person to another browser. The theme is
applied by an inline script in `<head>` before first paint, or the page flashes
the wrong one.

**The first account is the admin.** No seeded account, no default password.
While the instance has no users every request goes to `/setup`.

**The changelog is the single record.** The About section renders `CHANGELOG.md`,
so one file is updated per release and the app shows exactly what the
repository says.

## A request

1. `ProxyFix` rewrites the client address and scheme, if `TRUST_PROXY` is set.
2. `steer_to_setup` sends everything to `/setup` while there are no users.
   Static files and `/healthz` are exempt.
3. `check_csrf` rejects a mutating request without the session token.
4. The route runs; `@login_required` covers everything but the auth pages,
   the wizard and `/healthz`, and `@admin_required` the admin routes. A
   signed-out API call gets a JSON 401, a signed-in one that isn't an admin's
   a 403. A route refuses a request with `refuse()`, which answers
   `{"error": "..."}`.
5. `headers` adds `no-store` to HTML (the back button must never show records
   that have since changed) and the security headers.

## Where state lives

| | |
| --- | --- |
| `DATA_DIR` (`/data` in Docker, `./var` locally) | The SQLite database and the generated `.secret_key` |
| `users` | Accounts and per-user preferences |
| `settings` | Instance settings an admin changes at runtime |
| The session cookie | The signed-in user and the CSRF token |

Backing up the app is backing up `DATA_DIR` (see
[DOCUMENTATION.md](DOCUMENTATION.md#backups)).
