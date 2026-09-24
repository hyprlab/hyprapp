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

pytestmark = pytest.mark.skipif(
    not (ROOT / "tools" / "init-project.sh").exists() or not shutil.which("rsync")
    or not shutil.which("git"), reason="needs the template, rsync and git")


def test_init_project_produces_a_working_app(tmp_path):
    app = tmp_path / "newapp"
    subprocess.run(["rsync", "-a", "--exclude", ".git", "--exclude", ".venv", "--exclude", "var",
                    "--exclude", ".pytest_cache", "--exclude", "claude-memory-hylki",
                    f"{ROOT}/", f"{app}/"], check=True)
    env = {**os.environ, "HOME": str(tmp_path / "home")}
    subprocess.run(["bash", "tools/init-project.sh", "newapp", "New App", "8123", "Does a thing."],
                   cwd=app, env=env, check=True, capture_output=True)

    assert (app / "newapp" / "__init__.py").exists() and not (app / "hyprapp").exists()
    leftovers = subprocess.run(["grep", "-rIl", "-e", "hyprapp", "-e", "Hyprapp",
                                "--exclude-dir=.git", "."], cwd=app, capture_output=True, text=True)
    # Only the origin memory may name the template, and it must name it by path.
    assert set(leftovers.stdout.split()) <= {"./.claude/memory/template-origin.md",
                                             "./.claude/memory/MEMORY.md"}
    origin = (app / ".claude/memory/template-origin.md").read_text()
    assert "~/hyprapp" in origin and "@TEMPLATE_DIR@" not in origin
    assert "New App was created from the Hyprlab Flask template at `~/hyprapp`" in origin
    assert 'name: newapp' in (app / "docker-compose.yml").read_text()
    assert '"8123:8000"' in (app / "docker-compose.yml").read_text()
    assert '__version__ = "0.1.0"' in (app / "newapp" / "__init__.py").read_text()
    assert not (app / "tools" / "init-project.sh").exists()
    assert not (app / "docs" / "TEMPLATE.md").exists()

    git = lambda *a: subprocess.run(["git", *a], cwd=app, capture_output=True, text=True).stdout.strip()
    assert git("config", "core.hooksPath") == "tools/git-hooks"
    exclude = (app / ".git" / "info" / "exclude").read_text()
    assert "CLAUDE.md" in exclude and ".claude/" in exclude

    memories = list((tmp_path / "home" / ".claude" / "projects").glob("*/memory/MEMORY.md"))
    assert memories, "the starter memories were not installed"

    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                            cwd=app, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout[-2000:]
