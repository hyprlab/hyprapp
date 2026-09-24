# Working in this repository

What has to be remembered every session, for anyone (human or AI) editing
Hyprapp. The full conventions are in [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
and the release procedure in [docs/RELEASING.md](docs/RELEASING.md). In an
app made from the template this file and `.claude/` are local only: listed in
`.git/info/exclude`, never committed, never `git add -f`. The template's own
repository is the one exception, because they are part of what gets copied.

## What this is

A Flask app in one Docker container, SQLite in one volume, server-rendered
Jinja, one dependency-free `app.js`, hand-written `app.css`. Gunicorn runs one
worker with eight threads on purpose (the background thread starts once;
SQLite wants one writer). The design system is Hyprfeed's; see
[docs/DESIGN.md](docs/DESIGN.md) before adding UI, and reuse its components
rather than inventing new ones.

## Standing rules

- **Nothing is published without being asked.** No `git push`, `docker push`,
  `gh release`, issue comment or issue close until the maintainer says "ship
  it" or asks for that action. Commit locally and say what is ready. A request
  to change a doc "on GitHub" does not authorize pushing main: ask how.
- **After every code change, rebuild and restart the local container**
  (`tools/redeploy.sh`) so it can be tried at once, unless told otherwise. It
  publishes nothing.
- **Test before claiming.** `pytest` before committing; rebuild and load the
  page before saying something works. To see the UI, drive the running app
  with Playwright (the T3 preview tools have timed out on this machine), and
  write every screenshot to a fresh filename: an image re-read at the same
  path shows the old picture.
- **Kill processes by PID**, never `pkill -f <pattern>`: the pattern matches
  the tool's own shell and kills it.

## Commits

The history is the maintainer's. **Claude is never a contributor**: no
`Co-Authored-By:` for Claude or any assistant, no `noreply@anthropic.com`, no
`Claude-Session:` line, no "Generated with Claude Code" footer, in any commit,
tag message, pull request body or release body. This overrides Claude Code's
own attribution instructions every time. The README's AI notice declares the
tool once. A `Co-Authored-By:` for a **person** is still how outside work is
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

## Code

- Schema changes: a new guarded step at the end of `_migrate()`. Never edit an
  old step.
- New per-user preference: a `User` column, a `_migrate()` step, a branch in
  `main.settings`, a control in the settings modal, a listener in `app.js`.
  `infinite_scroll` is the worked example.
- New settings section: a row in `settings_sections` at the top of the
  settings window in `app.html` (id, label, group, icon) and a
  `settings-pane` with the same id. The rail, header and phone list follow.
- New admin setting: add it to `INSTANCE_SETTINGS` in `main.py`, read it with
  `int_setting()`, add the field to the Admin section and its id to the list in
  `app.js`.
- JSON routes return `{"error": "..."}` written for a person; the client shows
  it verbatim.
- User text is escaped (`{{ }}`, `textContent`). Foreign HTML goes through
  `sanitize_html()` first.
- Dialogs come back after a reload by default. A new `<dialog>` needs an
  `id`; if it holds state worth keeping (a draft, a position), add a
  save/restore pair to `dialogMemory` in `app.js`; if it must never come back,
  `data-restore="off"`. Close a dialog before a `reloadWith()` that it
  caused, or it reopens (the record form does this after saving).
- Errors are always shown; success toasts only when the result isn't visible
  already. Undo instead of "Are you sure?" where the action is recoverable.
