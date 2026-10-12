---
name: code-shape
description: "STANDING RULE: keep the code's shape. Reuse a helper before writing a second copy; extract on the second use; split a file near its budget by concern; budgets in pyproject.toml [tool.hyprapp.checks] (300 lines py/js/css, 200 templates, functions 50 lines / complexity 10, no 6-line repeats); run tools/check.sh before claiming done"
metadata:
  type: feedback
---

- **Reuse before writing.** Look for the helper before writing a second copy
  of anything (validation.py, the model helpers, api.js, dom.js, the icon
  global, the button macros). On the second use of a pattern, extract it.
- **Budgets:** no file over 300 lines of Python, JavaScript or CSS, or 200 of
  a template; no function over 50 lines or complexity 10; no block of 6
  normalized lines repeated in two places; every JavaScript import names
  something its module exports. They live in `pyproject.toml` under
  `[tool.hyprapp.checks]`. Raising one, or adding an exception, is an edit to
  that table with its reason, never a skip in code.
- **A file near its budget is split by concern**, never by line number: each
  module has one job nameable in a sentence. CLAUDE.md's "Where code goes"
  table says which file a change belongs in.
- **Enforced three times:** the PostToolUse hook runs `tools/check-code.py`
  on every file Claude edits; `tools/git-hooks/pre-commit` runs ruff,
  check-code and check-docs; CI runs `tools/check.sh` stage by stage.
- **Before saying it's done:** `tools/check.sh` (or `--fast` while working:
  no browser, no Docker). Coverage has a floor (`fail_under` in pyproject.toml)
  that only goes up.

**Why:** the template grew a 1,200-line app.js, a 980-line app.css and a
430-line main.py with the same validation in four places before the October
2026 refactor split them; these rules and the tools keep every app made from
the template from drifting back.

**How to apply:** when a check fails, fix the shape (extract, split, reuse)
rather than raising the budget. The `tidy` skill walks a cleanup. See
[[test-loop]] for the run order and [[flask-stack]] for the layout.
