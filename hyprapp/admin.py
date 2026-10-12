"""Instance settings, registration and user management, for admins only."""

from flask import Blueprint, jsonify
from flask_login import current_user
from sqlalchemy import func

from . import turnstile
from .models import Item, User, db, int_setting, set_setting
from .security import admin_required
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

bp = Blueprint("admin", __name__, url_prefix="/admin")

INSTANCE_SETTINGS = {
    # key: (lowest, highest, how the error names it)
    "worker_minutes": (0, 1440, "The background interval"),
    "items_per_page": (10, 500, "The page size"),
}


def pane_context() -> dict:
    """What the Admin and Security sections need. Empty for anyone else, so
    the queries never run for an ordinary account."""
    if not current_user.is_admin:
        return {}
    return {
        "admin_users": User.query.order_by(User.created_at).all(),
        "admin_item_counts": dict(
            db.session.query(Item.user_id, func.count(Item.id)).group_by(Item.user_id).all()
        ),
        "admin_stats": {"users": User.query.count(), "records": Item.query.count()},
        "inst_worker": int_setting("worker_minutes", 15),
        "inst_per_page": int_setting("items_per_page", 40),
        "turnstile": turnstile.status(),
    }


@bp.post("/instance")
@admin_required
def instance():
    data = json_body()
    for key, (low, high, label) in INSTANCE_SETTINGS.items():
        if key in data:
            # Saved as each passes: a later bad value leaves earlier ones saved.
            set_setting(key, str(bounded_int(data[key], low, high, label)))
    return jsonify(ok=True)


@bp.post("/registration")
@admin_required
def registration():
    open_ = bool(json_body().get("open"))
    set_setting("registration_open", "1" if open_ else "0")
    return jsonify(ok=True, open=open_)


@bp.post("/users")
@admin_required
def create_user():
    data = json_body()
    username = clean_email(data.get("username"))
    password = data.get("password") or ""
    check(email_problem(username))
    check(password_problem(password))
    if User.find(username):
        refuse("An account with that email already exists.", 409)
    user = User.create(
        username, password, name=clean_name(data.get("name")), is_admin=bool(data.get("is_admin"))
    )
    return jsonify(ok=True, id=user.id)


@bp.post("/users/<int:user_id>/password")
@admin_required
def reset_password(user_id):
    user = db.get_or_404(User, user_id)
    new = json_body().get("new", "")
    check(password_problem(new))
    user.set_password(new)
    db.session.commit()
    return jsonify(ok=True)


@bp.post("/users/<int:user_id>/toggle-admin")
@admin_required
def toggle_admin(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        refuse("You can't change your own admin status.")
    user.is_admin = not user.is_admin
    db.session.commit()
    return jsonify(ok=True, is_admin=user.is_admin)


@bp.post("/users/<int:user_id>/delete")
@admin_required
def delete_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        refuse("You can't delete your own account from here.")
    db.session.delete(user)  # their records cascade through the relationship
    db.session.commit()
    return jsonify(ok=True)
