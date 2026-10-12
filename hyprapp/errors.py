"""Errors: JSON for the API, a page for people."""

import logging

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from .models import db
from .validation import Refused

log = logging.getLogger("hyprapp")

ERROR_TEXT = {
    400: "The request did not make sense to the server.",
    403: "Your account does not have access to this.",
    404: "There is nothing at this address.",
    405: "That action is not available here.",
    429: "Too many attempts. Wait a few minutes and try again.",
    500: "Something went wrong on the server. It has been logged.",
}


def json_error(message: str, status: int):
    """{"error": "..."}, written for the person who will read it: the client
    shows it as it is."""
    return jsonify(error=message), status


def wants_json() -> bool:
    """API callers get JSON errors; page loads get the error page."""
    if request.headers.get("X-CSRF") or request.is_json:
        return True
    # HTML first: a client that accepts anything (curl, */*) gets the page;
    # only one that asks for JSON by name gets JSON.
    best = request.accept_mimetypes.best_match(["text/html", "application/json"])
    return best == "application/json"


def http_error(err):
    if wants_json():
        return json_error(err.description or err.name, err.code)
    return render_template(
        "error.html", code=err.code, title=err.name, message=ERROR_TEXT.get(err.code, err.description)
    ), err.code


def server_error(err):
    log.exception("unhandled error on %s %s", request.method, request.path)
    db.session.rollback()
    if wants_json():
        return json_error("Something went wrong on the server.", 500)
    return render_template("error.html", code=500, title="Server error", message=ERROR_TEXT[500]), 500


def init_app(app: Flask) -> None:
    app.register_error_handler(Refused, lambda err: json_error(err.message, err.status))
    app.register_error_handler(HTTPException, http_error)
    app.register_error_handler(Exception, server_error)
