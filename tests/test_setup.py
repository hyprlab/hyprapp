"""The first-run wizard: shown while there are no users, then never again."""

import pytest

from hyprapp.models import User, get_setting

GOOD = {"username": "admin@example.com", "password": "password1"}


def submit(client, csrf, **fields):
    return client.post("/setup", json={**GOOD, **fields}, headers={"X-CSRF": csrf})


def test_the_wizard_page(client):
    html = client.get("/setup").data.decode()
    assert "<title>Set up Hyprapp</title>" in html
    assert 'data-step="3"' in html and 'id="wiz-worker" type="number" min="0" max="1440"' in html


@pytest.mark.parametrize(
    "fields, error",
    [
        ({"username": "nope"}, "Enter a valid email address."),
        ({"username": None}, "Enter a valid email address."),
        ({"username": "x" * 75 + "@e.com"}, "Enter a valid email address."),
        ({"password": "short"}, "Passwords need at least 8 characters."),
        ({"password": None}, "Passwords need at least 8 characters."),
        ({"worker_minutes": "x"}, "The background interval must be a number."),
        ({"worker_minutes": None}, "The background interval must be a number."),
        ({"worker_minutes": -1}, "The background interval must be between 0 and 1440 minutes."),
        ({"worker_minutes": 1441}, "The background interval must be between 0 and 1440 minutes."),
    ],
)
def test_refusals_create_nothing(app, client, csrf, fields, error):
    resp = submit(client, csrf, **fields)
    assert resp.status_code == 400 and resp.get_json() == {"error": error}
    assert client.get("/").headers["Location"].endswith("/setup")
    with app.app_context():
        assert User.query.count() == 0


def test_setting_up(app, client, csrf):
    resp = submit(
        client,
        csrf,
        username="  Admin@Example.COM ",
        name="  Ada  ",
        registration_open=False,
        worker_minutes="30",
    )
    assert resp.status_code == 200 and resp.get_json() == {"ok": True}
    assert client.get_cookie("remember_token") is not None
    assert client.get("/").status_code == 200
    with app.app_context():
        admin = User.query.one()
        assert (admin.username, admin.name, admin.is_admin) == ("admin@example.com", "Ada", True)
        assert get_setting("registration_open") == "0" and get_setting("worker_minutes") == "30"


def test_the_defaults(app, client, csrf):
    submit(client, csrf, name="   ")
    with app.app_context():
        assert User.query.one().name is None
        assert get_setting("registration_open") == "1" and get_setting("worker_minutes") == "15"
        assert get_setting("items_per_page") is None


def test_the_wizard_runs_once(client, csrf):
    submit(client, csrf)
    again = submit(client, csrf, username="b@example.com")
    assert again.status_code == 409 and again.get_json() == {"error": "This instance is already set up."}
    assert client.get("/setup").headers["Location"].endswith("/login")


def test_after_setup_a_stranger_sees_sign_in(app, client, csrf):
    submit(client, csrf)
    stranger = app.test_client()
    assert stranger.get("/setup").headers["Location"].endswith("/login")
    assert stranger.get("/").headers["Location"].startswith("/login")
