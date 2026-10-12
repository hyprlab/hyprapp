"""tools/check-code.py, run on small sample trees: each budget, the
exceptions table, and the one-file mode the Claude Code hook uses."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = """
[tool.hyprapp.checks]
paths = ["src"]
max_function_lines = 10
max_complexity = 3
duplicate_lines = 4

[tool.hyprapp.checks.max_lines]
py = 30
js = 30
css = 30
html = 20

[tool.hyprapp.checks.exceptions]
{exceptions}
"""


def lines(n: int, indent: str = "") -> str:
    """n distinct lines, so a sample is never duplication of itself."""
    return "".join(f"{indent}x{i} = {i}\n" for i in range(n))


def tree(tmp_path, files: dict, exceptions: str = "") -> Path:
    """The checker, with the sample settings and files under src/."""
    (tmp_path / "tools").mkdir()
    for name in ("check-code.py", "shape.py"):
        shutil.copy(ROOT / "tools" / name, tmp_path / "tools" / name)
    (tmp_path / "pyproject.toml").write_text(SETTINGS.format(exceptions=exceptions))
    for name, text in files.items():
        (tmp_path / "src" / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / name).write_text(text)
    return tmp_path


def run(root: Path, *args) -> tuple[int, str]:
    out = subprocess.run(
        [sys.executable, str(root / "tools" / "check-code.py"), *args],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return out.returncode, out.stdout + out.stderr


def test_the_repository_is_within_budget():
    code, output = run(ROOT)
    assert code == 0, output


def test_a_file_over_its_budget(tmp_path):
    page = "".join(f"<p>{i}</p>\n" for i in range(20))
    code, output = run(tree(tmp_path, {"big.py": lines(31), "ok.html": page}))
    assert code == 1 and "src/big.py: 31 lines; the budget for .py is 30" in output
    assert "ok.html" not in output


def test_a_long_or_branchy_python_function(tmp_path):
    long = "def long():\n" + lines(10, "    ")
    branchy = "def branchy(a):\n" + "".join(
        f"    {kw}:\n        pass\n" for kw in ("if a", "for b in a", "while a")
    )
    code, output = run(tree(tmp_path, {"f.py": long + "\n\n" + branchy}))
    assert "src/f.py:1: long() is 11 lines; the budget is 10" in output
    assert "branchy() has complexity 4; the budget is 3" in output


def test_a_long_or_branchy_javascript_function(tmp_path):
    js = "function busy(a) {\n  if (a && b || c) { return 1; }\n}\n"
    code, output = run(tree(tmp_path, {"a.js": js}))
    assert code == 1 and "src/a.js:1: busy() has complexity 4; the budget is 3" in output


def test_repeated_blocks_across_files(tmp_path):
    block = "".join(f"value_{n} = compute({n})\n" for n in range(5))
    code, output = run(tree(tmp_path, {"one.py": block, "two.py": "x = 0\n" + block}))
    assert code == 1 and "src/one.py:1 and src/two.py:2: 4 or more lines repeated" in output


def test_repeated_css_declarations_count(tmp_path):
    rule = "color: red; margin: 0; padding: 1px; border: 0;"
    code, output = run(tree(tmp_path, {"a.css": f".a {{ {rule} }}\n.b {{ {rule} }}\n"}))
    assert code == 1 and "repeated" in output


def test_import_lists_are_not_duplication(tmp_path):
    imports = "from x import (\n" + "".join(f"    name_{n},\n" for n in range(6)) + ")\n"
    code, output = run(tree(tmp_path, {"one.py": imports, "two.py": imports}))
    assert code == 0, output


def test_a_javascript_import_must_exist_and_be_exported(tmp_path):
    files = {
        "js/lib.js": "export function real() {}\nexport var also = 1;\n",
        "js/app.js": 'import { real, also, fake } from "./lib.js";\nimport "./gone.js";\n',
    }
    code, output = run(tree(tmp_path, files))
    assert "src/js/app.js: imports fake from ./lib.js, which does not export it" in output
    assert "src/js/app.js: imports ./gone.js, which does not exist" in output
    assert "imports real" not in output and "imports also" not in output


def test_exceptions_are_named_with_a_reason(tmp_path):
    files = {"big.py": lines(31), "f.py": "def long():\n" + lines(10, "    ")}
    exceptions = (
        '"src/big.py" = "generated"\n"src/f.py:long" = "a table"\n"src/big.py:duplicates" = "a table"'
    )
    code, output = run(tree(tmp_path, files, exceptions))
    assert code == 0, output


def test_one_file_mode_reports_only_that_file(tmp_path):
    block = "".join(f"value_{n} = compute({n})\n" for n in range(5))
    root = tree(tmp_path, {"big.py": lines(31), "one.py": block, "two.py": block, "fine.py": "y = 1\n"})
    code, output = run(root, str(root / "src" / "fine.py"))
    assert code == 0, output
    code, output = run(root, str(root / "src" / "one.py"))
    assert code == 1 and "repeated" in output and "big.py" not in output
    assert run(root, str(root / "src" / "notes.txt"))[0] == 0  # not a file it reads


def test_the_report_never_fails(tmp_path):
    code, output = run(tree(tmp_path, {"big.py": lines(31)}), "--report")
    assert code == 0 and "Lines per file" in output and "31  src/big.py" in output
