"""The app factory's helpers: template globals and filters, configuration,
the SQLite connection, and the model helpers."""

import importlib
import os
import stat
from datetime import timedelta

import pytest
from flask import render_template_string

import hyprapp
from hyprapp.models import Item, Setting, User, db, get_setting, int_setting, set_setting, utcnow


# ———— template globals and filters ————


def test_static_url_carries_the_file_time(app):
    path = os.path.join(app.static_folder, "img", "logo.svg")
    with app.test_request_context():
        url = app.jinja_env.globals["static_url"]("img/logo.svg")
        missing = app.jinja_env.globals["static_url"]("img/none.svg")
    assert url == f"/static/img/logo.svg?v={int(os.path.getmtime(path))}"
    assert missing == "/static/img/none.svg?v=0"


@pytest.mark.parametrize(
    "age, label",
    [
        (timedelta(seconds=0), "now"),
        (timedelta(seconds=59), "now"),
        (timedelta(minutes=1), "1m ago"),
        (timedelta(minutes=59), "59m ago"),
        (timedelta(hours=1), "1h ago"),
        (timedelta(hours=23), "23h ago"),
        (timedelta(days=1), "1d ago"),
        (timedelta(days=6), "6d ago"),
    ],
)
def test_ago_relative(app, age, label):
    assert app.jinja_env.filters["ago"](utcnow() - age) == label


@pytest.mark.parametrize(
    "days, fmt", [(7, "%b %-d"), (364, "%b %-d"), (365, "%b %-d, %Y"), (900, "%b %-d, %Y")]
)
def test_ago_dates(app, days, fmt):
    when = utcnow() - timedelta(days=days)
    assert app.jinja_env.filters["ago"](when) == when.strftime(fmt)


def test_the_globals_every_template_reads(app):
    with app.test_request_context():
        out = render_template_string(
            "{{ app_name }}|{{ app_tagline }}|{{ app_version }}|{{ app_package }}|{{ source_url }}|"
            "{{ allow_registration }}|{{ turnstile_site_key }}|{{ csrf_token()|length }}|"
            "{{ app_changelog()[0].version }}"
        )
    assert out == (
        f"Hyprapp|A self-hosted Flask app.|{hyprapp.__version__}|hyprapp|"
        f"https://github.com/hyprlab/hyprapp|True||32|{hyprapp.__version__}"
    )


def test_the_csrf_token_is_stable_for_the_session(client, csrf, admin):
    html = client.get("/").data.decode()
    assert f'<meta name="csrf" content="{csrf}">' in html
    assert html.count(f'name="_csrf" value="{csrf}"') == 1  # the sign-out form


# ———— configuration ————


@pytest.fixture()
def config(monkeypatch, tmp_path):
    """Reload hyprapp.config under a given environment."""

    def load(**env):
        for key in (
            "SESSION_COOKIE_SECURE",
            "TRUST_PROXY",
            "ALLOW_REGISTRATION",
            "WORKER_MINUTES",
            "ITEMS_PER_PAGE",
            "SECRET_KEY",
            "APP_NAME",
            "DATABASE_URL",
            "SOURCE_URL",
        ):
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return importlib.reload(hyprapp.config)

    yield load
    importlib.reload(hyprapp.config)


@pytest.mark.parametrize(
    "raw, on",
    [
        ("0", False),
        ("false", False),
        ("No", False),
        ("", False),
        ("  FALSE ", False),
        ("1", True),
        ("yes", True),
        ("true", True),
        ("on", True),
    ],
)
def test_flags(config, raw, on):
    cfg = config(SESSION_COOKIE_SECURE=raw, ALLOW_REGISTRATION=raw).Config
    assert cfg.SESSION_COOKIE_SECURE is on and cfg.REMEMBER_COOKIE_SECURE is on
    assert cfg.ALLOW_REGISTRATION is on


def test_defaults(config, tmp_path):
    module = config()
    cfg = module.Config
    assert (cfg.APP_NAME, cfg.APP_TAGLINE) == ("Hyprapp", "A self-hosted Flask app.")
    assert cfg.SOURCE_URL == "https://github.com/hyprlab/hyprapp"
    assert (cfg.TRUST_PROXY, cfg.WORKER_MINUTES, cfg.ITEMS_PER_PAGE) == (0, 15, 40)
    assert cfg.ALLOW_REGISTRATION is True and cfg.SESSION_COOKIE_SECURE is False
    assert cfg.SQLALCHEMY_DATABASE_URI == f"sqlite:///{tmp_path / 'data' / 'hyprapp.db'}"
    assert (cfg.SESSION_COOKIE_HTTPONLY, cfg.SESSION_COOKIE_SAMESITE) == (True, "Lax")
    assert (cfg.REMEMBER_COOKIE_HTTPONLY, cfg.REMEMBER_COOKIE_SAMESITE) == (True, "Lax")
    assert cfg.SQLALCHEMY_ENGINE_OPTIONS == {"pool_pre_ping": True}
    assert (tmp_path / "data").is_dir()


def test_numbers_fall_back_when_garbled(config):
    cfg = config(TRUST_PROXY="two", WORKER_MINUTES="", ITEMS_PER_PAGE="25").Config
    assert (cfg.TRUST_PROXY, cfg.WORKER_MINUTES, cfg.ITEMS_PER_PAGE) == (0, 15, 25)


def test_a_secret_key_is_generated_once_and_kept(config, tmp_path):
    first = config().Config.SECRET_KEY
    keyfile = tmp_path / "data" / ".secret_key"
    assert len(first) == 64 and keyfile.read_text() == first
    assert stat.S_IMODE(keyfile.stat().st_mode) == 0o600
    assert config().Config.SECRET_KEY == first
    assert config(SECRET_KEY="from-env").Config.SECRET_KEY == "from-env"


def test_database_url_wins(config):
    assert config(DATABASE_URL="sqlite:////tmp/x.db").Config.SQLALCHEMY_DATABASE_URI == "sqlite:////tmp/x.db"


# ———— SQLite ————


def test_the_connection_pragmas(app):
    with app.app_context():
        pragma = lambda name: db.session.execute(db.text(f"PRAGMA {name}")).scalar()
        assert pragma("journal_mode") == "wal"
        assert pragma("synchronous") == 1
        assert pragma("busy_timeout") == 5000
        assert pragma("foreign_keys") == 1


def test_foreign_keys_cascade_in_the_database(app, admin):
    with app.app_context():
        owner = User.query.one()
        db.session.add(Item(user_id=owner.id, title="x"))
        db.session.commit()
        db.session.execute(db.text("DELETE FROM users"))
        db.session.commit()
        assert db.session.execute(db.text("SELECT COUNT(*) FROM items")).scalar() == 0


# ———— models ————


def test_display_name_and_password_stamp(app):
    with app.app_context():
        user = User(username="a@example.com")
        user.set_password("password1")
        assert user.display_name == "a@example.com"
        user.name = "Ada"
        assert user.display_name == "Ada"
        stamp = user.password_stamp
        assert len(stamp) == 12 and user.check_password("password1")
        user.set_password("password2")
        assert user.password_stamp != stamp and not user.check_password("password1")
        db.session.add(user)
        db.session.commit()
        assert user.get_id() == f"{user.id}.{user.password_stamp}"


def test_summary_is_one_line_and_short():
    item = Item(title="t", body="  one\n\ntwo\tthree  " + "x" * 300)
    assert item.summary.startswith("one two three ") and len(item.summary) == 220
    assert Item(title="t", body=None).summary == ""


def test_settings_helpers(app):
    with app.app_context():
        assert get_setting("k") is None and int_setting("k", 7) == 7
        set_setting("k", "12")
        assert get_setting("k") == "12" and int_setting("k", 7) == 12
        set_setting("k", "garbage")
        assert int_setting("k", 7) == 7
        assert db.session.query(Setting).filter_by(key="k").count() == 1


def test_utcnow_is_naive_utc():
    now = utcnow()
    assert now.tzinfo is None
