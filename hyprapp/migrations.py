"""Schema changes for databases created by older versions."""
from flask import Flask

from .models import db


def migrate(app: Flask) -> None:
    """In-place migrations for databases created by older versions.

    Every step inspects the schema first, so it is safe to run on every boot
    and safe to run twice. Add new steps at the end and never edit an old one:
    an install that has already run it will not run it again. A step that makes
    the database unreadable to the previous version is a MAJOR release
    (docs/RELEASING.md).
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)

    def columns(table: str) -> set[str]:
        return {c["name"] for c in inspector.get_columns(table)}

    # The shape every step takes. Keep it as the pattern, or delete it once
    # the app has steps of its own.
    if "infinite_scroll" not in columns("users"):
        db.session.execute(text(
            "ALTER TABLE users ADD COLUMN infinite_scroll BOOLEAN NOT NULL DEFAULT 1"
        ))
        db.session.commit()
        app.logger.info("migrated: added users.infinite_scroll")
