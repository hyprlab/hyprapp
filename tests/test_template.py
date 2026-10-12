"""tools/init-project.sh turns a copy of the template into a working app.

This file exists only in the template: init-project.sh deletes it along with
itself, since an app made from the template has no template to test.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
COPY_EXCLUDES = [".git", ".venv", "var", ".pytest_cache", "claude-memory-hylki", "visual-diffs"]

pytestmark = pytest.mark.skipif(
    not (ROOT / "tools" / "init-project.sh").exists() or not shutil.which("rsync") or not shutil.which("git"),
    reason="needs the template, rsync and git",
)


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    """A copy of the template turned into "newapp" by init-project.sh, and
    the HOME it installed the memories into."""
    tmp = tmp_path_factory.mktemp("template")
    app, home = tmp / "newapp", tmp / "home"
    excludes = [arg for name in COPY_EXCLUDES for arg in ("--exclude", name)]
    subprocess.run(["rsync", "-a", *excludes, f"{ROOT}/", f"{app}/"], check=True)
    subprocess.run(
        ["bash", "tools/init-project.sh", "newapp", "New App", "8123", "Does a thing."],
        cwd=app,
        env={**os.environ, "HOME": str(home)},
        check=True,
        capture_output=True,
    )
    return app, home


def test_init_project_renames_everything(made):
    app, _ = made
    assert (app / "newapp" / "__init__.py").exists() and not (app / "hyprapp").exists()
    leftovers = subprocess.run(
        ["grep", "-rIl", "-e", "hyprapp", "-e", "Hyprapp", "--exclude-dir=.git", "."],
        cwd=app,
        capture_output=True,
        text=True,
    )
    # Only the origin memory may name the template, and it must name it by path.
    assert set(leftovers.stdout.split()) <= {
        "./.claude/memory/template-origin.md",
        "./.claude/memory/MEMORY.md",
    }
    origin = (app / ".claude/memory/template-origin.md").read_text()
    assert "~/hyprapp" in origin and "@TEMPLATE_DIR@" not in origin
    assert "New App was created from the Hyprlab Flask template at `~/hyprapp`" in origin
    assert "name: newapp" in (app / "docker-compose.yml").read_text()
    assert '"8123:8000"' in (app / "docker-compose.yml").read_text()
    assert '__version__ = "0.1.0"' in (app / "newapp" / "__init__.py").read_text()
    assert not (app / "tools" / "init-project.sh").exists()
    assert not (app / "docs" / "TEMPLATE.md").exists()


def test_init_project_sets_up_git_and_the_memories(made):
    app, home = made

    def git(*a):
        return subprocess.run(["git", *a], cwd=app, capture_output=True, text=True).stdout.strip()

    assert git("config", "core.hooksPath") == "tools/git-hooks"
    exclude = (app / ".git" / "info" / "exclude").read_text()
    assert "CLAUDE.md" in exclude and ".claude/" in exclude

    memories = list((home / ".claude" / "projects").glob("*/memory/MEMORY.md"))
    assert memories, "the starter memories were not installed"


def test_the_new_app_passes_its_suite(made):
    app, _ = made
    # The browser tests run in the template's own suite; the new app's name
    # changes how its pages look, so its visual baselines start fresh.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-m", "not browser"],
        cwd=app,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout[-2000:]
