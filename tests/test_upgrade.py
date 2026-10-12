"""An existing install's database survives an upgrade.

tests/fixtures/upgrade-1.0.0.db was written by version 1.0.0 with a row in
every table. Booting the app against a copy must keep every row and run the
migrations cleanly, twice. tests/snapshots/schema.sql is the schema a fresh
install gets; a change to it is a change to every install's database.
"""

import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

import hyprapp

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "upgrade-1.0.0.db"
SCHEMA = HERE / "snapshots" / "schema.sql"


def boot(data_dir: Path):
    class Upgraded(hyprapp.config.Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{data_dir / 'hyprapp.db'}"

    return hyprapp.create_app(Upgraded)


@pytest.fixture()
def installed(app, tmp_path):
    """A copy of the 1.0.0 database in a data directory of its own."""
    data = tmp_path / "installed"
    data.mkdir()
    shutil.copy(FIXTURE, data / "hyprapp.db")
    return data


def rows(db_file: Path, query: str) -> list[tuple]:
    with closing(sqlite3.connect(db_file)) as conn:
        return conn.execute(query).fetchall()


def schema(db_file: Path) -> str:
    entries = rows(
        db_file, "SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name"
    )
    text = "\n\n".join(f"-- {kind} {name}\n{sql};" for kind, name, sql in entries) + "\n"
    return "\n".join(line.rstrip() for line in text.splitlines()) + "\n"


def columns(db_file: Path) -> dict[str, list[tuple]]:
    tables = [t for (t,) in rows(db_file, "SELECT name FROM sqlite_master WHERE type='table'")]
    return {t: [(c[1], c[2], c[3]) for c in rows(db_file, f"PRAGMA table_info({t})")] for t in sorted(tables)}


def test_every_row_survives_two_boots(installed):
    boot(installed)
    app = boot(installed)  # migrate() runs at every boot; the second must be a no-op
    db_file = installed / "hyprapp.db"
    assert rows(
        db_file,
        "SELECT id, username, name, is_admin, theme, view_mode, infinite_scroll FROM users ORDER BY id",
    ) == [
        (1, "admin@example.com", "Ada", 1, "dark", "list", 0),
        (2, "bob@example.com", "Bob", 0, "system", "cards", 1),
    ]
    assert rows(db_file, "SELECT id, user_id, title, body, pinned, done FROM items ORDER BY id") == [
        (1, 1, "Open record", "Body of the open record", 0, 0),
        (2, 1, "Pinned and done", "", 1, 1),
        (3, 2, "Bob's record", "", 0, 0),
    ]
    assert dict(rows(db_file, "SELECT key, value FROM settings")) == {
        "items_per_page": "25",
        "registration_open": "0",
        "turnstile_enabled": "0",
        "turnstile_secret_key": "secret-fixture",
        "turnstile_site_key": "site-fixture",
        "worker_minutes": "30",
    }

    client = app.test_client()
    from .conftest import token_for

    token = token_for(client)
    resp = client.post(
        "/login", data={"_csrf": token, "username": "admin@example.com", "password": "password1"}
    )
    assert resp.status_code == 302
    html = client.get("/?filter=all").data.decode()
    assert 'data-theme-pref="dark"' in html and 'class="grid--list"' in html
    assert "Pinned and done" in html and "Bob&#39;s record" not in html


def test_the_upgraded_schema_matches_a_fresh_one(installed, tmp_path):
    boot(installed)
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    boot(fresh)
    assert columns(installed / "hyprapp.db") == columns(fresh / "hyprapp.db")


def test_the_migration_step_adds_its_column(installed, caplog):
    db_file = installed / "hyprapp.db"
    with closing(sqlite3.connect(db_file)) as conn:
        conn.execute("ALTER TABLE users DROP COLUMN infinite_scroll")
        conn.commit()
    caplog.set_level("INFO")
    boot(installed)
    assert "migrated: added users.infinite_scroll" in caplog.text
    assert rows(db_file, "SELECT infinite_scroll FROM users ORDER BY id") == [(1,), (1,)]
    caplog.clear()
    boot(installed)
    assert "migrated" not in caplog.text


def test_a_fresh_install_gets_the_recorded_schema(tmp_path):
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    boot(fresh)
    assert schema(fresh / "hyprapp.db") == SCHEMA.read_text()
