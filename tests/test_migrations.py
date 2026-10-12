"""The migration steps that have shipped stay as they shipped.

tests/snapshots/migrations.txt holds them, byte for byte; the steps fenced in
migrate() must begin with exactly that text. A new step goes after them, and
joins the snapshot when it ships. A step is never edited, reordered or
merged: an install that ran it once will not run it again (docs/RELEASING.md).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = next(p for p in ROOT.glob("*/migrations.py") if p.parent.name not in ("tests", "tools"))
SNAPSHOT = Path(__file__).resolve().parent / "snapshots" / "migrations.txt"


def fenced_steps() -> str:
    source = MIGRATIONS.read_text(encoding="utf-8")
    start = source.index("    # fmt: off\n") + len("    # fmt: off\n")
    return source[start : source.index("    # fmt: on")].strip("\n") + "\n"


def test_the_shipped_steps_are_unchanged_and_first():
    shipped = SNAPSHOT.read_text(encoding="utf-8")
    assert fenced_steps().startswith(shipped), (
        "a shipped migration step changed; add a new step at the end instead"
    )
