"""Checks on what a request sends, and refusing it in words.

A JSON route calls refuse() or check(); the handler registered by
register() turns the refusal into {"error": "..."} with its status, which the
client shows as written. The sign-up form flashes the same texts instead, so
the checks return the text rather than raising.
"""

import re
from typing import NoReturn

from flask import Flask, jsonify, request

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8
MAX_EMAIL = 80  # users.username is VARCHAR(80)
MAX_NAME = 120  # users.name is VARCHAR(120)


class Refused(Exception):
    """A request turned down, with the reason written for a person."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def refuse(message: str, status: int = 400) -> NoReturn:
    raise Refused(message, status)


def check(problem: str | None, status: int = 400) -> None:
    """Refuse with the problem's text, if there is one."""
    if problem:
        refuse(problem, status)


def register(app: Flask) -> None:
    app.register_error_handler(Refused, lambda err: (jsonify(error=err.message), err.status))


def json_body() -> dict:
    """The request's JSON object, or an empty one for a body that isn't JSON."""
    return request.get_json(silent=True) or {}


def clean_email(raw) -> str:
    return (raw or "").strip().lower()


def clean_name(raw) -> str | None:
    return (raw or "").strip()[:MAX_NAME] or None


def email_problem(username: str) -> str | None:
    if len(username) > MAX_EMAIL or not EMAIL_RE.match(username):
        return "Enter a valid email address."
    return None


def password_problem(password: str, kind: str = "Passwords") -> str | None:
    if len(password) < MIN_PASSWORD:
        return f"{kind} need at least {MIN_PASSWORD} characters."
    return None


def bounded_int(value, low: int, high: int, label: str, unit: str = "") -> int:
    """An integer in [low, high], or a refusal naming the setting."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        refuse(f"{label} must be a number.")
    if not low <= number <= high:
        refuse(f"{label} must be between {low} and {high}{unit}.")
    return number
