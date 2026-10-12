"""What every template can use: globals, the context processor and filters."""
import os
from datetime import datetime

from flask import Flask, current_app, url_for

from . import about_docs
from .models import utcnow
from .security import csrf_token


def static_url(filename: str) -> str:
    """Static URL with an mtime cache-buster, so a redeploy invalidates
    browser caches at once."""
    try:
        version = int(os.path.getmtime(os.path.join(current_app.static_folder, filename)))
    except OSError:
        version = 0
    return url_for("static", filename=filename, v=version)


def ago(dt: datetime) -> str:
    seconds = int((utcnow() - dt).total_seconds())
    if seconds < 60:
        return "now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 7:
        return f"{days}d ago"
    if days < 365:
        return dt.strftime("%b %-d")
    return dt.strftime("%b %-d, %Y")


def init_app(app: Flask, version: str) -> None:
    from . import auth, turnstile

    @app.context_processor
    def inject_globals():
        return {
            "csrf_token": csrf_token,
            "turnstile_site_key": (turnstile.config() or {}).get("site_key", ""),
            "allow_registration": auth.registration_open(),
            "app_name": app.config["APP_NAME"],
            "app_tagline": app.config["APP_TAGLINE"],
            "source_url": app.config["SOURCE_URL"],
            "app_version": version,
            # The package name, which is also the container name in compose.
            "app_package": app.import_name,
        }

    app.add_template_global(static_url)
    app.jinja_env.globals["app_changelog"] = about_docs.changelog
    app.add_template_filter(ago)
