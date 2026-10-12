"""The background worker: one pass of work, and the thread that repeats it.

The thread is checked in a separate Python process, because it starts at most
once per process and these tests need to see it start.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hyprapp import worker

ROOT = Path(__file__).resolve().parent.parent


def test_a_pass_commits_and_logs(app, caplog, monkeypatch):
    from hyprapp.models import Setting, db
    def work():
        db.session.add(Setting(key="worked", value="1"))
        return 1
    monkeypatch.setattr(worker, "_work", work)
    caplog.set_level("INFO")
    worker.run_once(app)
    with app.app_context():
        assert db.session.get(Setting, "worked").value == "1"
    assert "background pass: 1 rows in" in caplog.text


def test_a_failed_pass_rolls_back_and_raises(app, monkeypatch):
    from hyprapp.models import Setting, db
    def work():
        db.session.add(Setting(key="half-done", value="1"))
        db.session.flush()
        raise RuntimeError("broken")
    monkeypatch.setattr(worker, "_work", work)
    with pytest.raises(RuntimeError):
        worker.run_once(app)
    with app.app_context():
        assert db.session.get(Setting, "half-done") is None


def test_the_template_work_changes_nothing(app):
    with app.app_context():
        assert worker._work() == 0


def run(script: str, tmp_path, **env) -> dict:
    """Run a script in a fresh interpreter against an empty data directory."""
    full_env = {**os.environ, "DATA_DIR": str(tmp_path), "SECRET_KEY": "x", **env}
    full_env.pop("WERKZEUG_RUN_MAIN", None)
    full_env.update(env)
    out = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=full_env,
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


THREADS = """
import json, threading
from hyprapp import config, create_app
class C(config.Config):
    TESTING = {testing}
    DEBUG = {debug}
create_app(C)
create_app(C)
print(json.dumps([t.name for t in threading.enumerate() if t.name.endswith("-worker")]))
"""


@pytest.mark.parametrize("minutes, testing, debug, run_main, expected", [
    ("5", False, False, None, ["hyprapp-worker"]),   # once, though two apps were made
    ("0", False, False, None, []),
    ("5", True, False, None, []),
    ("5", False, True, None, []),                     # the reloader's parent process
    ("5", False, True, "true", ["hyprapp-worker"]),   # the reloader's child
])
def test_when_the_thread_starts(tmp_path, minutes, testing, debug, run_main, expected):
    env = {"WORKER_MINUTES": minutes}
    if run_main:
        env["WERKZEUG_RUN_MAIN"] = run_main
    script = THREADS.format(testing=testing, debug=debug)
    assert run(script, tmp_path, **env) == expected


LOOP = """
import json, logging, threading, time
calls, passes = [], []

class Stop(BaseException):
    pass

def fake_sleep(seconds):
    calls.append(seconds)
    if len(calls) >= 4:
        raise Stop

class InlineThread:
    def __init__(self, *args, **kwargs):
        self.target = kwargs.get("target") or args[1]
        self.name = kwargs.get("name")
    def start(self):
        try:
            self.target()
        except Stop:
            pass

from hyprapp import config, create_app, worker
from hyprapp.models import set_setting
logged = []
logging.getLogger().addHandler(type("H", (logging.Handler,), {"emit": lambda s, r: logged.append(r.getMessage())})())

def work():
    passes.append(1)
    if len(passes) == 1:
        raise RuntimeError("first pass fails")
    if len(passes) == 2:
        set_setting("worker_minutes", "0")
    return 0
worker._work = work

class Quiet(config.Config):
    WORKER_MINUTES = 0
create_app(Quiet)
time.sleep, threading.Thread = fake_sleep, InlineThread

class C(config.Config):
    WORKER_MINUTES = 7
create_app(C)
print(json.dumps({"sleeps": calls, "passes": len(passes), "failed": "background work failed" in logged,
                  "thread": InlineThread.__name__}))
"""


def test_the_loop_rereads_the_cadence_and_survives_a_failure(tmp_path):
    result = run(LOOP, tmp_path)
    # Boot delay; a failed pass, logged; a good pass that sets the cadence to
    # 0; then no pass, waiting a minute at a time.
    assert result["sleeps"] == [20, 7 * 60, 7 * 60, 60]
    assert result["passes"] == 2 and result["failed"] is True
