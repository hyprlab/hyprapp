"""Test fixtures.

Every test gets its own temporary data directory and database, so nothing
touches the developer's var/ and the tests run in any order.
"""

import re

import pytest

CSRF_RE = re.compile(rb'name="csrf" content="([^"]+)"')


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WORKER_MINUTES", "0")
    monkeypatch.setenv("SECRET_KEY", "test-key")

    # Config is read from the environment at import; rebuild it from the
    # variables above, for this test only.
    import hyprapp
    import hyprapp.config

    monkeypatch.setattr(hyprapp.config, "Config", hyprapp.config.from_environment())

    class TestConfig(hyprapp.config.Config):
        TESTING = True

    app = hyprapp.create_app(TestConfig)
    yield app
    with app.app_context():
        from hyprapp.models import db

        db.engine.dispose()  # close its SQLite connections now, not at exit


def make(post, title="Record", **extra) -> dict:
    """A record, created through the API as the client creates one."""
    resp = post("/items", {"title": title, **extra})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["item"]


def token_for(client) -> str:
    """The session's CSRF token, read out of a page the way a browser would."""
    page = client.get("/login", follow_redirects=True)
    return CSRF_RE.search(page.data).group(1).decode()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def csrf(client):
    return token_for(client)


@pytest.fixture()
def post(client, csrf):
    """POST a JSON body with the session's CSRF header, the way api.js does."""

    def send(url, body=None):
        return client.post(url, json=body if body is not None else {}, headers={"X-CSRF": csrf})

    return send


@pytest.fixture()
def admin(client, csrf):
    """A signed-in admin, created through the setup wizard."""
    resp = client.post(
        "/setup",
        json={
            "username": "admin@example.com",
            "password": "password1",
            "name": "Ada",
            "registration_open": True,
            "worker_minutes": 0,
        },
        headers={"X-CSRF": csrf},
    )
    assert resp.status_code == 200
    return {"username": "admin@example.com", "password": "password1"}


@pytest.fixture()
def second_user(app, admin):
    """A second, non-admin account, signed in on its own client."""
    other = app.test_client()
    token = token_for(other)
    resp = other.post(
        "/register",
        data={
            "_csrf": token,
            "username": "other@example.com",
            "password": "password1",
            "confirm": "password1",
        },
    )
    assert resp.status_code == 302
    return other, token
