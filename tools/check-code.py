#!/usr/bin/env python3
"""Check the code's shape. Stdlib only, like check-docs.py.

  python3 tools/check-code.py             # every tracked source file
  python3 tools/check-code.py FILE...     # these files (the Claude Code hook)
  python3 tools/check-code.py --report    # sizes, largest functions, duplicates; never fails

  1. No file over its line budget (by type: py, js, css, html).
  2. No Python or JavaScript function over the line budget or the
     complexity budget (decision points: if, loops, except/catch, case,
     and in JavaScript also && || ?? and the ternary).
  3. No block of DUPLICATE_LINES normalized lines in two places. Python,
     JavaScript and templates compare lines; CSS compares declarations, one
     per line, so the same run of declarations in two rules counts too.

The budgets and the exceptions are in pyproject.toml under
[tool.hyprapp.checks]. An exception names "path" (over the line budget),
"path:function" (over a function budget) or "path:duplicates" (left out of
the duplicate search), each with its reason. Raising a budget or adding an
exception is an edit to that table, in the open, never a skip in the code.
"""

import subprocess
import sys
import tomllib
from pathlib import Path

from shape import TYPES, duplicates, functions_in, js_import_problems

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {
    "paths": ["."],
    "max_lines": {"py": 300, "js": 300, "css": 300, "html": 200, "sh": 300},
    "max_function_lines": 50,
    "max_complexity": 10,
    "duplicate_lines": 6,
    "exceptions": {},
}


def settings() -> dict:
    try:
        found = tomllib.loads((ROOT / "pyproject.toml").read_text())
    except OSError:
        found = {}
    cfg = {**DEFAULTS, **found.get("tool", {}).get("hyprapp", {}).get("checks", {})}
    # A type the table leaves out keeps its default budget.
    cfg["max_lines"] = {**DEFAULTS["max_lines"], **cfg["max_lines"]}
    return cfg


def source_files(paths: list[str]) -> list[Path]:
    try:
        names = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", *paths],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        files = [ROOT / name for name in names]
    except (OSError, subprocess.CalledProcessError):
        files = [p for path in paths for p in (ROOT / path).rglob("*")]
    return sorted(p for p in files if p.suffix in TYPES and p.is_file())


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


# ———— the checks ————


def file_problems(path: Path, cfg: dict) -> list[str]:
    found, name, kind = [], rel(path), TYPES[path.suffix]
    lines = len(path.read_text(encoding="utf-8").splitlines())
    if lines > cfg["max_lines"][kind] and name not in cfg["exceptions"]:
        found.append(
            f"{name}: {lines} lines; the budget for .{kind} is {cfg['max_lines'][kind]}. "
            "Split it by concern, not by line number"
        )
    if kind not in ("py", "js", "html"):
        return found
    try:
        functions = functions_in(path)
    except SyntaxError as err:
        return found + [f"{name}:{err.lineno}: does not parse: {err.msg}"]
    if kind == "js":
        found += [f"{name}: {problem}" for problem in js_import_problems(path)]
    for function, line, length, cx in functions:
        if f"{name}:{function}" in cfg["exceptions"]:
            continue
        if length > cfg["max_function_lines"]:
            found.append(
                f"{name}:{line}: {function}() is {length} lines; the budget is {cfg['max_function_lines']}"
            )
        if cx > cfg["max_complexity"]:
            found.append(
                f"{name}:{line}: {function}() has complexity {cx}; the budget is {cfg['max_complexity']}"
            )
    return found


def report(files: list[Path], cfg: dict) -> None:
    print("Lines per file, largest first:")
    sizes = sorted(((len(p.read_text(encoding="utf-8").splitlines()), rel(p)) for p in files), reverse=True)
    for lines, name in sizes:
        print(f"  {lines:6}  {name}")
    functions = [
        (length, cx, f"{rel(path)}:{line} {name}()")
        for path in files
        if path.suffix in (".py", ".js")
        for name, line, length, cx in functions_in(path)
    ]
    print("\nLongest functions (lines, complexity):")
    for length, cx, name in sorted(functions, reverse=True)[:15]:
        print(f"  {length:4} {cx:3}  {name}")
    print("\nMost complex functions (complexity, lines):")
    for length, cx, name in sorted(functions, key=lambda f: (-f[1], -f[0]))[:15]:
        print(f"  {cx:4} {length:4}  {name}")
    dups = duplicates(files, cfg["duplicate_lines"], None)
    print(f"\nDuplicated blocks ({len(dups)}):")
    for a, line, b, other in dups:
        print(f"  {rel(a)}:{line} and {rel(b)}:{other}")


def main(argv: list[str]) -> int:
    cfg = settings()
    everything = source_files(cfg["paths"])
    if "--report" in argv:
        report(everything, cfg)
        return 0
    targets = [Path(a).resolve() for a in argv if not a.startswith("-")]
    targets = [p for p in targets if p.suffix in TYPES and p.is_file() and ROOT in p.parents]
    if argv and not targets:
        return 0  # nothing this checker knows how to read
    files = targets or everything
    pool = [
        p for p in sorted(set(everything) | set(targets)) if f"{rel(p)}:duplicates" not in cfg["exceptions"]
    ]
    problems = [
        f"exception {name!r} has no reason"
        for name, why in cfg["exceptions"].items()
        if not isinstance(why, str) or not why.strip()
    ]
    problems += [problem for path in files for problem in file_problems(path, cfg)]
    window = cfg["duplicate_lines"]
    problems += [
        f"{rel(a)}:{line} and {rel(b)}:{other}: {window} or more lines repeated"
        for a, line, b, other in duplicates(pool, window, set(targets) or None)
    ]
    for problem in problems:
        print(f"check-code: {problem}", file=sys.stderr)
    if problems:
        print(
            f"check-code: {len(problems)} problem(s). Budgets and exceptions: "
            "pyproject.toml, [tool.hyprapp.checks]",
            file=sys.stderr,
        )
        return 1
    print(f"check-code: {len(files)} files, all within budget")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
