---
name: tidy
description: Tidy the code and check its shape. Use when the maintainer says "tidy this up", "check the code shape", "clean this up" or similar, or before calling a larger change done. Runs the checks, finds duplication and code in the wrong module in the changes since main, fixes them without changing behavior, and runs the checks again.
---

# Tidy this up

The rules are in CLAUDE.md ("Keep the shape", "Reuse before writing", and the
"Where code goes" table) and in the `code-shape` memory. This skill applies
them to what changed. It never changes behavior: the tests decide.

## 1. Measure

```sh
tools/check.sh --fast                         # ruff, check-code, check-docs, tests
python3 tools/check-code.py --report          # sizes, longest and most complex functions, repeats
git diff --stat main...HEAD; git status --short
```

## 2. Read the changes since main

For each file changed since `main` (`git diff main...HEAD` plus anything
uncommitted), look for:

- **A second copy.** Logic written twice, or a pattern that already has a
  helper: `validation.py` (JSON bodies, refusals, email, password, ranges),
  `User.find()` and `User.create()`, `admin_required`, `api.js` and `dom.js`,
  `{{ icon() }}`, the button macros, `remember()` and `onOpen()`. Reuse it,
  or extract one on the second use.
- **Code in the wrong module.** Compare with "Where code goes". A route in
  the wrong blueprint, a validation rule kept in one route when two use it,
  a style in the wrong stylesheet, a JavaScript feature reaching into
  another module's internals instead of exporting a function.
- **A file or function near its budget.** Split by concern (named steps,
  one module per job), never by line number.
- **Comments that say what instead of why**, and stale ones that describe
  code that has moved or gone.

## 3. Fix, without changing behavior

- No test's assertions change. Moving a test to another file is fine.
- Keep every URL, JSON shape, error text, environment variable and the
  database schema as they are; a migration step is never edited.
- Keep the ids, classes and data- attributes the JavaScript and the tests
  read; if markup moves into a partial, render the page before and after and
  compare.
- Raising a budget is a last resort, made in `pyproject.toml` with a reason,
  and said out loud in the summary.

## 4. Check again, and say what changed

```sh
tools/check.sh                                # the full run, browser and image included
tools/redeploy.sh
```

Commit as `refactor(area): ...` (or `test:` / `style:`), body on one line per
paragraph, no attribution. Report what was merged, moved or split, and
anything left as it was and why.
