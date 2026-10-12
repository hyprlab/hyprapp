"""Sign in, sign up, sign out, and who is signed in.

Usernames are email addresses: validated and lowercased at registration. The
sign-in field is deliberately ``type=text`` so an account created before that
rule (an app that started with plain usernames) can still sign in.
"""

import threading
import time

from flask import Blueprint, Flask, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user

from . import turnstile
from .errors import wants_json
from .models import User, db, get_setting
from .validation import clean_email, clean_name, email_problem, password_problem

bp = Blueprint("auth", __name__)

MAX_FAILURES = 8
FAILURE_WINDOW = 15 * 60
THROTTLED = "Too many attempts. Wait a few minutes and try again."


class Throttle:
    """Failed sign-ins per (address, account) in a sliding window. In memory is
    enough: there is one process (see the Dockerfile), and a restart forgetting
    the count costs an attacker a restart they cannot trigger."""

    def __init__(self):
        self._failures: dict[tuple[str, str], list[float]] = {}
        self._lock = threading.Lock()

    def too_many(self, key: tuple[str, str]) -> bool:
        now = time.monotonic()
        with self._lock:
            stamps = [t for t in self._failures.get(key, []) if now - t < FAILURE_WINDOW]
            self._failures[key] = stamps
            return len(stamps) >= MAX_FAILURES

    def record(self, key: tuple[str, str]) -> None:
        with self._lock:
            self._failures.setdefault(key, []).append(time.monotonic())

    def clear(self, key: tuple[str, str]) -> None:
        with self._lock:
            self._failures.pop(key, None)


def init_app(app: Flask) -> None:
    app.extensions["sign_in_throttle"] = Throttle()
    login_manager = LoginManager(app)
    login_manager.user_loader(load_user)
    login_manager.unauthorized_handler(unauthorized)


def load_user(user_id):
    # "7.<password stamp>" (User.get_id): a sign-in from before the
    # password changed is no longer anyone's.
    raw_id, _, stamp = str(user_id).partition(".")
    try:
        user = db.session.get(User, int(raw_id))
    except ValueError:
        return None
    return user if user is not None and stamp and user.password_stamp == stamp else None


def unauthorized():
    if wants_json():
        return jsonify(error="You are signed out. Reload the page to sign in again."), 401
    return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))


def registration_open() -> bool:
    """The admin-panel toggle wins; ALLOW_REGISTRATION is only the default."""
    stored = get_setting("registration_open")
    if stored is not None:
        return stored == "1"
    return current_app.config["ALLOW_REGISTRATION"]


def safe_next(dest: str | None) -> str:
    """Only same-site paths: an absolute or protocol-relative "next" would turn
    the sign-in form into an open redirect."""
    if dest and dest.startswith("/") and not dest.startswith("//") and "\\" not in dest:
        return dest
    return url_for("main.index")


def _refused(template: str, message: str, status: int):
    flash(message, "error")
    return render_template(template), status


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method != "POST":
        return render_template("auth/login.html")
    username = request.form.get("username", "").strip()
    throttle = current_app.extensions["sign_in_throttle"]
    key = (request.remote_addr or "?", username.lower())
    if throttle.too_many(key):
        return _refused("auth/login.html", THROTTLED, 429)
    if not turnstile.verify_form():
        return _refused("auth/login.html", "Verification failed. Please try again.", 400)
    password = request.form.get("password", "")
    user = User.find(username)
    if user and user.check_password(password):
        throttle.clear(key)
        login_user(user, remember=request.form.get("remember") == "on")
        return redirect(safe_next(request.args.get("next")))
    throttle.record(key)
    return _refused("auth/login.html", "Wrong email or password.", 401)


def _sign_up_problem(username: str, password: str, confirm: str) -> str | None:
    problem = email_problem(username) or password_problem(password)
    if problem:
        return problem
    if password != confirm:
        return "Passwords don't match."
    if User.find(username):
        return "An account with that email already exists."
    return None


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if not registration_open():
        flash("Registration is closed on this server.", "error")
        return redirect(url_for("auth.login"))
    if request.method != "POST":
        return render_template("auth/register.html")
    if not turnstile.verify_form():
        return _refused("auth/register.html", "Verification failed. Please try again.", 400)
    username = clean_email(request.form.get("username"))
    password = request.form.get("password", "")
    problem = _sign_up_problem(username, password, request.form.get("confirm", ""))
    if problem:
        return _refused("auth/register.html", problem, 400)
    # The first account on a fresh instance becomes the admin.
    user = User.create(
        username, password, name=clean_name(request.form.get("name")), is_admin=User.query.count() == 0
    )
    login_user(user)
    return redirect(url_for("main.index"))


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
