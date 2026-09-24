---
name: flask-stack
description: "House Flask architecture decisions: app factory; gunicorn 1 worker + threads (background thread starts once, SQLite single writer); SQLite WAL; _migrate() guarded ALTER TABLE, no framework; session CSRF via X-CSRF; runtime settings table overrides env defaults; first account is admin; email usernames"
metadata:
  type: project
---

Decisions from Hyprfeed that every app keeps (docs/ARCHITECTURE.md has the
reasoning):

- Flask app factory, blueprints; SQLite in the `/data` volume.
- **Gunicorn runs 1 worker with 8 threads on purpose**: the background worker
  thread must start once, and SQLite prefers one writing process. If work
  outgrows that, move it to its own container.
- SQLite pragmas: WAL, `busy_timeout=5000`, `foreign_keys=ON`.
- **Schema changes go in `_migrate()`** in `__init__.py`: `ALTER TABLE`
  guarded by a column check, safe to run twice. New steps at the end; never
  edit an old one. A step an older version can't read back is MAJOR
  ([[semver-strict]]).
- Hand-rolled session CSRF: hidden `_csrf` in forms, `X-CSRF` header from
  `fetch`. JSON routes return `{"error": "..."}` written for a person.
- **Two kinds of setting:** env vars are fresh-install defaults; admin-edited
  values live in the `settings` table and win. The setup wizard seeds them.
- **No seeded account:** zero users steers every request to `/setup`; the
  wizard's account is the admin.
- **Usernames are email addresses**, validated and lowercased at sign-up; the
  sign-in field is deliberately `type=text` so older non-email accounts still
  sign in.
- Turnstile is optional: enforced only when `TURNSTILE_SECRET_KEY` is set.
- `docker-compose.yml` pulls the published image; the committed
  `docker-compose.override.yml` adds `build: .` for clones. The README embeds
  the compose example.
- HTML is served `no-store`: a stale page replayed from cache showed records
  the user had already changed (Hyprfeed 1.7.2).
- Version constant: `__version__` in the package `__init__.py`, the single
  source ([[ship-flow]]).
