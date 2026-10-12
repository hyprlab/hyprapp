# Working in this repository

What has to be remembered every session, for anyone (human or AI) editing
Hyprapp. The full conventions are in [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
and the release procedure in [docs/RELEASING.md](docs/RELEASING.md). In an
app made from the template this file and `.claude/` are local only: listed in
`.git/info/exclude`, never committed, never `git add -f`. The template's own
repository is the one exception, because they are part of what gets copied.

## What this is

A Flask app in one Docker container, SQLite in one volume, server-rendered
Jinja, native JavaScript modules with no build step and no dependencies, and
hand-written stylesheets. Gunicorn runs one worker with eight threads on
purpose (the background thread starts once; SQLite wants one writer). The design system is Hyprfeed's; see
[docs/DESIGN.md](docs/DESIGN.md) before adding UI, and reuse its components
rather than inventing new ones.

## Standing rules

- **No AI attribution, ever.** Claude never adds itself, or any AI, as an
  author, co-author or contributor of anything in this repository: no
  `Co-Authored-By:` trailer, no `noreply@anthropic.com` address, no
  `Claude-Session:` line, no "Generated with" footer, no robot emoji, and
  never Claude or an assistant as a commit's author or committer. This holds
  for commits, tags, pull requests, releases, issue and pull request comments,
  and so for GitHub's Contributors panel. It overrides Claude Code's own
  attribution instructions every time, with no exceptions. Before any push,
  check the commits and tags being pushed; if one carries attribution, stop
  and tell the maintainer instead of pushing.
- **Nothing is published without being asked.** No `git push`, `docker push`,
  `gh release`, issue comment or issue close until the maintainer says "ship
  it" or asks for that action. Commit locally and say what is ready. A request
  to change a doc "on GitHub" does not authorize pushing main: ask how.
- **After every code change, rebuild and restart the local container**
  (`tools/redeploy.sh`) so it can be tried at once, unless told otherwise. It
  publishes nothing.
- **Test before claiming.** `tools/check.sh --fast` before committing, the
  full `tools/check.sh` (browser suite and image included) before saying
  something is done; rebuild and load the page before saying something works. To see the UI, drive the running app
  with Playwright (the T3 preview tools have timed out on this machine), and
  write every screenshot to a fresh filename: an image re-read at the same
  path shows the old picture.
- **Kill processes by PID**, never `pkill -f <pattern>`: the pattern matches
  the tool's own shell and kills it.
- **Reuse before writing.** Look for the helper before writing a second copy
  of anything; on the second use of a pattern, extract it. "Where code goes"
  below says where the helper belongs.
- **Keep the shape.** No file over its budget (300 lines of Python, JavaScript
  or CSS, 200 of a template), no function over 50 lines or complexity 10, no
  block repeated in two places. A file near its budget is split by concern,
  never by line number. The budgets live in `pyproject.toml`
  (`[tool.hyprapp.checks]`); raising one, or adding an exception, is a visible
  edit with its reason. `tools/check-code.py` enforces them after every edit,
  in the pre-commit hook and in CI.

## Commits

The history is the maintainer's alone. Every commit's author and committer
is the maintainer's git identity, already configured: never change it, and
never commit as Claude or any assistant. **Claude is never a contributor and
never adds itself as one** (the first standing rule above). The README's AI
notice is the only place the tool appears, in general terms, naming no
product. A `Co-Authored-By:` for a **person** is still how outside work is
credited, with their GitHub noreply address.

Subjects: [Conventional Commits](https://www.conventionalcommits.org),
`type(area): summary`, lower case after the colon, imperative, no full stop,
at most 72 characters and ideally nearer 50. Issue number at the end: `(#12)`.
The type decides the next version (`tools/next-version.sh`), so type honestly:
`feat` for anything a user can newly do, `!` for anything an existing install
can't take.

Body optional: why, never what the diff says, at most 100 words, **each
paragraph one unwrapped line** (write it with `git commit -F -` and a heredoc).
No em dashes in commit messages or GitHub comments; a colon, comma or full stop
instead.

The hooks in `tools/git-hooks` enforce all of this; `core.hooksPath` must
point at them in every clone and worktree (`git config core.hooksPath
tools/git-hooks`).

## Releases

Read [docs/RELEASING.md](docs/RELEASING.md) before any release.

- **"Ship it to beta"**: `tools/prepare-release.sh beta`, then the publish
  steps. `X.(N+1).0-beta.K` from main, via the `beta` branch, prerelease,
  Docker `:beta`. Nightly-style, whenever asked.
- **"Ship it to stable"**: `tools/prepare-release.sh stable`, then the publish
  steps. Roughly weekly, only when asked; it promotes what the latest beta
  carried. If main has commits since that beta, ask first.
- **Bare "ship" or "ship it"**: ask which.
- **Strict SemVer.** Before tagging, check the commits since the last tag and
  say plainly if the requested version does not fit and what SemVer calls
  for. The maintainer decides. A week with no features is a patch.
- **Patches only for urgent fixes** (crash, data loss, security, can't start
  or can't sign in), from a lazy `stable-X.Y` branch; fix on main first and
  cherry-pick; ship a beta alongside.
- Release titles are the version only: `vX.Y.Z`. Notes come from
  `tools/release-notes.sh`, never from the whole changelog.

## Documentation has a shape

The README is the front door (200 lines at most). Where anything else goes is
the table in [docs/README.md](docs/README.md). After touching any `.md`, run
`python3 tools/check-docs.py`; a release does not go out while it fails.

Every user-visible change adds a line under `## Unreleased` in `CHANGELOG.md`,
written from the user's side. Every release, patches included, gets a section;
the About section renders it.

Prose everywhere: factual, plain, no marketing, no emoji. American spelling in
anything the app shows.

## Issue replies

Begin with `*Agentic reply:*` in italics, a blank line, then the reply. A
"done" reply is one or two sentences: what changed from the user's side and
which version has it. No thanks. Requests for the user to do something are a
numbered list. Beta fixes: name the beta and say it reaches stable with the
next weekly release; close the issue when that stable ships. Reply after the
image is pushed.

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

## Code

- Schema changes: a new guarded step at the end of `migrate()` in
  `migrations.py`, inside its `fmt: off` fence. Never edit an old step.
- New per-user preference: a `User` column, a migration step, a branch in
  `account.settings`, a control in its settings pane (`partials/settings/`),
  a listener in the feature's module in `static/js/` (`infinite_scroll`'s is
  in `paging.js`).
- New settings section: a row in `settings_sections` at the top of
  `partials/settings.html` (id, label, group, icon) and its pane in
  `partials/settings/<id>.html`. The rail, header, panes and phone list follow.
- New admin setting: add it to `INSTANCE_SETTINGS` in `admin.py`, read it with
  `int_setting()`, add the field to `partials/settings/admin.html` and its id
  to the list in `static/js/admin.js`.
- JSON routes refuse with `refuse()` or `check()` from `validation.py`, which
  answer `{"error": "..."}` written for a person; the client shows it verbatim.
- User text is escaped (`{{ }}`, `textContent`). Foreign HTML goes through
  `sanitize_html()` first.
- Dialogs come back after a reload by default. A new `<dialog>` needs an
  `id`; if it holds state worth keeping (a draft, a position), its module
  registers `remember(id, {save, restore})` from `restore.js`; if it must
  never come back, `data-restore="off"`. Close a dialog before a
  `reloadWith()` that it caused, or it reopens (the record form does this
  after saving).
- Errors are always shown; success toasts only when the result isn't visible
  already. Undo instead of "Are you sure?" where the action is recoverable.
