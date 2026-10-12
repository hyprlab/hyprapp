# Contributing

The conventions anyone editing this repository follows, human or AI. Bug
reports, ideas and pull requests are all welcome, and a clear bug report is
often as useful as a patch.

## Setting up

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium   # for the browser tests
git config core.hooksPath tools/git-hooks         # once per clone or worktree
tools/check.sh                                    # everything CI checks
.venv/bin/python run.py                           # http://localhost:8000
```

The hooks enforce the commit rules below and run the quick checks before
every commit. Without `core.hooksPath` they silently do nothing, so set it in
every clone and every worktree.

To try a change the way it will run in production, rebuild the container:
`tools/redeploy.sh`.

## Checks

`tools/check.sh` runs what CI runs, in the same order, so passing locally and
passing in CI mean the same thing. `--fast` leaves out the browser and Docker;
a stage can be run alone (`tools/check.sh static`).

| Stage | What it runs |
| --- | --- |
| `static` | `ruff check`, `ruff format --check`, `tools/check-code.py`, `tools/check-docs.py`, and the commit message hook over the commits not yet on `main` |
| `tests` | `pytest` without the browser, with the coverage floor |
| `browser` | The Playwright suite in `tests/browser`, the visual comparison included |
| `image` | `docker build` |

The pre-commit hook runs the `static` checks but the commit messages, in
under a second. Claude Code runs `tools/check-code.py` on every file it edits.

**The budgets** are in `pyproject.toml` under `[tool.hyprapp.checks]`, and
cover every tracked file of the types the checker reads, wherever it is: no
file over 300 lines of Python, JavaScript, CSS or shell, or 200 of a
template; no function over 50 lines or complexity 10, including the
functions in a template's inline scripts; no block of 6 lines repeated in two
places; every JavaScript import names something its module exports. A file
near its budget is split by concern, not by line number. An exception is an
entry in that table with its reason, and the checker refuses one without.
Raising a budget also means changing `tests/test_check_code.py`, which pins
them, so it can't happen in passing.

**The coverage floor** is `fail_under` in `pyproject.toml`, measured over
branches as well as lines. It only goes up: when coverage rises, raise the
floor to the new figure, rounded down; when a change would lower it, test the
change instead. The same test pins it.

**The migration steps** that have shipped are pinned in
`tests/snapshots/migrations.txt`; a new step goes at the end of `migrate()`
and joins the snapshot when it ships.

**The visual comparison** checks screenshots of every page and settings
section, at four widths in both themes, against `tests/browser/baselines/`.
When a change is meant to change the look, run
`UPDATE_BASELINES=1 .venv/bin/python -m pytest tests/browser/test_visual.py`,
look at the new screenshots, and commit them with the change. A change of
more than 8 levels in any color, over more than 0.01% of a screenshot, fails.
A failure writes the new screenshot and a diff to
`tests/browser/visual-diffs/`, which CI uploads.

## Commits

**The history is the maintainer's.** Commits carry no AI tool attribution: no
`Co-Authored-By:` line for Claude or any other assistant, no "Generated with"
footer, no session line, in a commit, a tag message, a pull request body or a
release body. The [AI notice](../README.md#ai-notice) declares how the project
is built, once, for the whole repository. One stray trailer puts the tool on
GitHub's Contributors panel, and removing it again means rewriting history.

A `Co-Authored-By:` trailer is still how a **person** is credited, with the
GitHub noreply address that resolves to their profile (see
[Credit](#credit)).

Subjects follow [Conventional Commits](https://www.conventionalcommits.org):
`type(area): summary`, lower case after the colon, imperative, no full stop,
72 characters at most and ideally nearer 50.

- Types: `feat`, `fix`, `perf`, `refactor`, `docs`, `build`, `ci`, `test`,
  `style`, `chore`, `revert`. A `!` after the type (`feat(api)!:`) marks a
  breaking change. The type is not decoration: `tools/next-version.sh` reads
  it to decide the next version ([RELEASING.md](RELEASING.md)).
- The area is where the change lives: `auth`, `setup`, `admin`, `settings`,
  `sidebar`, `sheet`, `search`, `worker`, `db`, `ui`, `docker`, `release`,
  plus the app's own. Leave it out only when there is no single place.
- An issue number goes at the end: `fix(auth): keep the next page after sign-in (#12)`.
- Releases: `chore(release): 1.4.0`, `chore(release): 1.5.0-beta.1`.

The body is optional and short: why the change exists, never what the diff
already says. Past 100 words the detail belongs in `docs/` or `CHANGELOG.md`,
or the commit wants splitting. **Each body paragraph is one line, not
wrapped:** GitHub keeps every line break in a body, so text wrapped at 72
breaks a second time on a phone. Write it with `git commit -F -` and a heredoc.

No em dashes in commit messages: a colon, a comma or a full stop replaces
them.

`tools/git-hooks/commit-msg` refuses the attribution lines, em dashes, a
subject without a type, and an overlong subject or body. `pre-push` refuses to
publish any commit or tag carrying attribution.

## CLAUDE.md and .claude/

Both are local only: listed in `.git/info/exclude`, not `.gitignore`, so the
repository never names the tool. Never `git add -f` them. A new worktree does
not get them: symlink `CLAUDE.md` into it before working there.

## Prose style

Documentation, the changelog, release notes, UI text and issue replies:

- Factual, plain language. Say what the app does, not what it enables you to
  do. No marketing, no superlatives, no "finally", no emoji.
- American spelling in anything the app shows: color, behavior, canceled.
- Changelog lines describe the change from the user's side. How it was built
  belongs in the commit.
- Comments in code explain *why*, not *what*.

## Documentation

The README is the front door and has a 200-line ceiling. Before writing a word
of documentation, decide where it goes: the table in
[docs/README.md](README.md) says. After touching any `.md`, run:

```sh
python3 tools/check-docs.py
```

It checks every relative link and anchor, that every `docs/*.md` is indexed,
that `docs/` holds Markdown only, the README's length, and the changelog's
shape and version.

Every release, patches included, gets a `CHANGELOG.md` section. The About section
renders the changelog, so a skipped section is a gap users see.

## Code

- Match what is there: one module per concern ("Where code goes" in
  [ARCHITECTURE.md](ARCHITECTURE.md#where-code-goes) has the map), blueprints, `refuse()` for the `{"error": "..."}` shape
  of JSON failures, `api()` from `static/js/api.js` for every mutating call.
- Reuse before writing: look for the helper before writing a second copy, and
  extract one on the second use of a pattern.
- Schema changes go in `migrate()` in `migrations.py` as guarded `ALTER TABLE`
  steps. Never edit an old step. A step an older version can't read back is a
  MAJOR release.
- Anything the user typed is rendered with Jinja's escaping or `textContent`,
  never `|safe` or `innerHTML`. Foreign HTML goes through
  `sanitize.sanitize_html()` first.
- User-facing failures say what happened and what to do, in a sentence.
- Checks before committing (`tools/check.sh --fast`), the full
  `tools/check.sh` before calling a change done, and rebuild and run the app
  (`tools/redeploy.sh`) before saying something works.

## Credit

Outside pull requests land as commits on `main` made by the maintainer,
crediting the author with a trailer that uses their GitHub noreply address:

```
Co-Authored-By: Jane Doe <12345678+janedoe@users.noreply.github.com>
```

Get the id with `gh api users/<login> --jq .id`. An address taken from their
own commit may not be linked to their account, and then they never appear as a
contributor; that can't be fixed after a tagged release without rewriting
history.

Add them to `data/CONTRIBUTORS` (their name and `@login`) and describe the
work in [CREDITS.md](CREDITS.md). Close the pull request with a comment saying
what was taken, what changed and what was left out.

In release notes an `@` is for people whose code, art or translation is in the
release. Reporters and requesters are named without the `@`: an @ notifies
someone and reads as authorship. `tools/release-notes.sh` strips the @ from any
handle not in `data/CONTRIBUTORS`.

## Issue replies

Every reply to an issue or pull request written by an agent begins with
`*Agentic reply:*` in italics, then a blank line, then the reply.

- A reply saying something is done is one or two sentences: what changed from
  the user's side, and which version carries it. How it was built is in the
  commit and the changelog.
- No thanks, no pleasantries, no em dashes. Plain, brief, human.
- Anything the user has to do (send a log, try something, check a setting) is
  a numbered list, one request per item.
- Fixed in a beta: name the beta version and say it reaches stable with the
  next weekly release. The issue closes when that stable ships.
- Fixed in a stable: name the version and how to update. Reply once the image
  is pushed, not before.

```
*Agentic reply:*

Fixed in 1.4.0: the sign-in page now returns you to the page you asked for.

Update with `docker compose pull && docker compose up -d`.
```

Only a reply that asks for something or explains a decline runs longer.
