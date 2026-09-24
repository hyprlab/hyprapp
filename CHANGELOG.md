# Changelog

All notable changes to Hyprapp are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## Unreleased

### Added
- Reloading the page brings back the dialog that was open, as it was: the
  settings section and its scroll position, a record being written or edited,
  the search and its results, an open record. Arriving at the page any other
  way starts with nothing open
- Cloudflare Turnstile is set up in Settings > Security. The keys are saved
  only after a challenge rendered with them passes, so a wrong key can't lock
  anyone out of sign-in, and `flask turnstile off` turns it off from the
  server. The TURNSTILE_* variables still work as a fresh-install default

### Changed
- Settings opens as a two-pane window: the sections are listed in a rail on
  the left, with About pinned at its foot, and the chosen section fills the
  right. On a phone it opens as a list, and each section has a Back button

## [1.0.0] — 2026-09-24

### Added
- The application shell from Hyprfeed: a sidebar with pinned head and foot, a
  sticky topbar with search, sort and view controls, a tabbed settings modal,
  a detail sheet that slides in from below, a Ctrl/Cmd+K search palette,
  toasts with Undo, pull to refresh, and light and dark themes
- Email sign-in and sign-up with optional Cloudflare Turnstile, a throttle on
  failed sign-ins, and a first-run setup wizard that creates the admin account
- An admin panel for users, registration and instance settings, changeable
  while the app runs
- A worked example model, Item, wired through the list and card views, paging
  with optional infinite scroll, the detail sheet, search and the JSON API
- A Docker image running gunicorn with SQLite in one volume, a health check
  at `/healthz`, and `flask` commands to create users, reset passwords and
  back up the database
- The release machinery: SemVer, this changelog rendered in the About tab,
  Conventional Commits enforced by a git hook, a documentation checker, and
  the beta and stable procedures in docs/RELEASING.md
