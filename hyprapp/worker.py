"""Periodic background work.

``run_once`` is called by the thread ``start`` starts, every
``worker_minutes`` (an admin setting whose default is the WORKER_MINUTES
environment variable). It runs in the web process, so keep it short and let it
fail loudly: the caller logs the traceback and tries again next cycle.

Replace ``_work`` with whatever the app does on a schedule: fetch, prune, send,
reconcile. If the work grows past a few seconds or needs more than one process,
move it to its own container rather than growing this thread.
"""

import logging
import os
import threading
import time
from functools import partial

from flask import Flask

from .models import db, int_setting

log = logging.getLogger(__name__)

# One thread per process, however many apps the process makes.
_lock = threading.Lock()
_running = False


def start(app: Flask) -> None:
    """Start the background thread.

    Gunicorn runs one worker with threads on purpose (see the Dockerfile): this
    thread must start exactly once, and SQLite prefers a single writing process.
    """
    global _running
    if app.config["WORKER_MINUTES"] <= 0 or app.config.get("TESTING"):
        return
    # Avoid a double start under the werkzeug reloader's parent process.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    with _lock:
        if _running:
            return
        _running = True
    threading.Thread(target=partial(_loop, app), daemon=True, name="hyprapp-worker").start()


def _loop(app: Flask) -> None:
    time.sleep(20)  # let the app finish booting first
    while True:
        # An admin can change the cadence at runtime; re-read it each cycle.
        with app.app_context():
            minutes = int_setting("worker_minutes", app.config["WORKER_MINUTES"])
        if minutes > 0:
            try:
                run_once(app)
            except Exception:
                logging.getLogger(__package__).exception("background work failed")
        time.sleep(max(minutes, 1) * 60)


def run_once(app: Flask) -> None:
    with app.app_context():
        started = time.monotonic()
        try:
            touched = _work()
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        finally:
            db.session.remove()
        log.info("background pass: %d rows in %.2fs", touched, time.monotonic() - started)


def _work() -> int:
    """The actual work. Returns the number of rows it changed, for the log."""
    return 0
