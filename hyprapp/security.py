"""What guards every request: the session CSRF token, the admin check, and
the response headers."""
import secrets
from functools import wraps

from flask import Flask, abort, jsonify, request, session
from flask_login import current_user, login_required


def csrf_token() -> str:
    """The session's token. Forms post it as a hidden _csrf field; the JSON
    API sends it as X-CSRF."""
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def check_csrf():
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return None
    sent = request.headers.get("X-CSRF") or request.form.get("_csrf") or ""
    expected = session.get("_csrf", "")
    if not expected or not secrets.compare_digest(sent, expected):
        return jsonify(error="Your session expired. Reload the page and try again."), 400
    return None


def headers(resp):
    # Dynamic pages must never be replayed from the browser cache: a stale
    # page briefly shows records the user has since changed or deleted.
    if resp.mimetype == "text/html":
        resp.headers["Cache-Control"] = "no-store"
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return resp


def admin_required(view):
    """Signed in (a JSON 401 otherwise) and an admin (403), checked before
    the view looks anything up."""
    @wraps(view)
    @login_required
    def guarded(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return guarded


def init_app(app: Flask) -> None:
    app.before_request(check_csrf)
    app.after_request(headers)
