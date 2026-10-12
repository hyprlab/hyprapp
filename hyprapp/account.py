"""The signed-in person's own preferences and password."""

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required, login_user

from .models import VIEWS, db
from .validation import check, clean_name, json_body, password_problem, refuse

bp = Blueprint("account", __name__)

THEMES = ("system", "light", "dark")


@bp.post("/settings")
@login_required
def settings():
    data = json_body()
    if "name" in data:
        current_user.name = clean_name(data.get("name"))
    if data.get("theme") in THEMES:
        current_user.theme = data["theme"]
    if data.get("view_mode") in VIEWS:
        current_user.view_mode = data["view_mode"]
    if "infinite_scroll" in data:
        current_user.infinite_scroll = bool(data["infinite_scroll"])
    db.session.commit()
    return jsonify(ok=True)


@bp.post("/account/password")
@login_required
def change_password():
    data = json_body()
    if not current_user.check_password(data.get("current", "")):
        refuse("Current password is wrong.", 403)
    new = data.get("new", "")
    check(password_problem(new, "New passwords"))
    user = current_user._get_current_object()
    user.set_password(new)
    db.session.commit()
    # Every other session of this account ends with the old password; this
    # one carries on under the new one.
    csrf = session.get("_csrf")
    login_user(user, remember=bool(request.cookies.get("remember_token")))
    if csrf:
        session["_csrf"] = csrf
    return jsonify(ok=True)
