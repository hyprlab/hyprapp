"""First-run setup wizard.

Shown exactly once: while the instance has zero users, every request is steered
to /setup. The wizard creates the admin account and the initial instance
settings in one POST, signs the admin in, and hands over to the app. There is
no seeded account and no default password.
"""

from flask import Blueprint, Flask, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import login_user

from .models import User, db, set_setting
from .validation import (
    bounded_int,
    check,
    clean_email,
    clean_name,
    email_problem,
    json_body,
    password_problem,
    refuse,
)

bp = Blueprint("setup", __name__)

# What a fresh install may still reach: the wizard, its files, the health check.
OPEN_BEFORE_SETUP = ("setup.wizard", "setup.submit", "static", "health.healthz")


def init_app(app: Flask) -> None:
    # Once a user exists the answer can never go back to True, so it is kept
    # for the life of the app and the query skipped on every request.
    app.extensions["setup_done"] = False
    app.before_request(steer_to_setup)


def needs_setup() -> bool:
    if current_app.extensions["setup_done"]:
        return False
    if db.session.query(User.id).first() is not None:
        current_app.extensions["setup_done"] = True
        return False
    return True


def steer_to_setup():
    """A fresh install (zero users) goes to the wizard, nowhere else."""
    if request.endpoint in OPEN_BEFORE_SETUP:
        return None
    if needs_setup():
        return redirect(url_for("setup.wizard"))
    return None


@bp.route("/setup")
def wizard():
    if not needs_setup():
        return redirect(url_for("auth.login"))
    return render_template("setup.html")


@bp.route("/setup", methods=["POST"])
def submit():
    if not needs_setup():
        refuse("This instance is already set up.", 409)
    data = json_body()
    username = clean_email(data.get("username"))
    password = data.get("password") or ""
    check(email_problem(username))
    check(password_problem(password))
    worker = bounded_int(data.get("worker_minutes", 15), 0, 1440, "The background interval", " minutes")

    admin = User.create(username, password, name=clean_name(data.get("name")), is_admin=True)
    set_setting("registration_open", "1" if data.get("registration_open", True) else "0")
    set_setting("worker_minutes", str(worker))

    current_app.extensions["setup_done"] = True
    login_user(admin, remember=True)
    return jsonify(ok=True)
