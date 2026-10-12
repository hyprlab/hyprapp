"""What every template can use: globals, the context processor and filters."""

import os
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from flask import Flask, current_app, request, url_for

from . import about_docs, icons
from .models import utcnow
from .security import csrf_token


YEAR = 365 * 24 * 3600


def _version(filename: str) -> int:
    try:
        return int(os.path.getmtime(os.path.join(current_app.static_folder, filename)))
    except OSError:
        return 0


def static_url(filename: str) -> str:
    """Static URL with an mtime cache-buster, so a redeploy invalidates
    browser caches at once."""
    return url_for("static", filename=filename, v=_version(filename))


def static_max_age(filename: str) -> int | None:
    """A file asked for at its current version is cached for a year: a new
    version is a new URL. Anything else is revalidated on every use."""
    return YEAR if request.args.get("v") == str(_version(filename)) else None


# import ... from "./name.js" and import "./name.js", the only forms the modules use.
IMPORT_RE = re.compile(r"""^\s*import\s+(?:[^"';]+?\s+from\s+)?["']\./([\w-]+\.js)["']""", re.M)
ENTRY = "app.js"


@lru_cache(maxsize=16)
def _js_assets(folder: str, base: str, stamp: tuple) -> tuple[dict, tuple[str, ...]]:
    """The import map, and the versioned URLs of the entry module and every
    module it imports. Cached until a file in static/js changes."""
    versioned = {name: f"{base}{name}?v={int(mtime)}" for name, mtime in stamp}
    graph, queue = [], [ENTRY]
    while queue:
        name = queue.pop(0)
        if name not in graph:
            graph.append(name)
            queue += IMPORT_RE.findall((Path(folder) / name).read_text(encoding="utf-8"))
    import_map = {"imports": {f"{base}{name}": url for name, url in versioned.items()}}
    return import_map, tuple(versioned[name] for name in graph)


def _js() -> tuple[dict, tuple[str, ...]]:
    folder = os.path.join(current_app.static_folder, "js")
    # st_mtime, as static_url() reads it, so the versions agree.
    stamp = tuple(sorted((e.name, e.stat().st_mtime) for e in os.scandir(folder) if e.name.endswith(".js")))
    return _js_assets(folder, url_for("static", filename="js/"), stamp)


def js_import_map() -> dict:
    """Every module's plain URL mapped to its versioned one. A module imports
    another by a relative path, which has no version on it; the browser looks
    the resolved URL up here, so a redeploy is never served from a stale cache."""
    return _js()[0]


def js_preloads() -> tuple[str, ...]:
    """The entry module and everything it imports, for modulepreload: fetched
    at once, rather than discovered one import at a time."""
    return _js()[1]


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
    app.get_send_file_max_age = static_max_age
    app.add_template_global(icons.icon)
    app.add_template_global(js_preloads)
    app.add_template_global(js_import_map)
    app.jinja_env.globals["app_changelog"] = about_docs.changelog
    app.add_template_filter(ago)
