"""Sign in, sign up, sign out, the sign-in throttle and the proxy setting."""
import time

import pytest

import hyprapp
from hyprapp.models import User

from .conftest import token_for

WRONG = "Wrong email or password."
THROTTLED = "Too many attempts. Wait a few minutes and try again."


@pytest.fixture()
def stranger(app, admin):
    """A signed-out browser with a session token, after setup."""
    client = app.test_client()
    return client, token_for(client)


def login(client, token, username="admin@example.com", password="password1", **extra):
    return client.post("/login" + extra.pop("query", ""),
                       data={"_csrf": token, "username": username, "password": password, **extra})


# ———— sign in ————

def test_the_sign_in_page(stranger):
    client, _ = stranger
    html = client.get("/login").data.decode()
    assert "<title>Sign in — Hyprapp</title>" in html
    assert 'name="username" required autofocus' in html and 'type="password"' in html
    assert '<input type="checkbox" name="remember" checked>' in html
    assert "cf-turnstile" not in html and "challenges.cloudflare.com" not in html
    assert '<a href="/register">Create an account</a>' in html


def test_signing_in(stranger):
    client, token = stranger
    resp = login(client, token)
    assert resp.status_code == 302 and resp.headers["Location"] == "/"
    assert client.get_cookie("remember_token") is None
    assert client.get("/").status_code == 200


def test_keep_me_signed_in_sets_the_remember_cookie(stranger):
    client, token = stranger
    login(client, token, remember="on")
    assert client.get_cookie("remember_token") is not None


def test_the_username_ignores_case_and_spaces(stranger):
    client, token = stranger
    assert login(client, token, username="  ADMIN@Example.com ").status_code == 302


def test_sign_in_returns_to_the_page_asked_for(stranger):
    client, token = stranger
    resp = login(client, token, query="?next=/%3Ffilter%3Ddone")
    assert resp.headers["Location"] == "/?filter=done"


@pytest.mark.parametrize("username, password", [
    ("admin@example.com", "wrong-password"), ("nobody@example.com", "password1"), ("", ""),
])
def test_a_failed_sign_in(stranger, username, password):
    client, token = stranger
    resp = login(client, token, username=username, password=password)
    assert resp.status_code == 401
    html = resp.data.decode()
    assert f'<div class="flash flash--error">{WRONG}</div>' in html
    assert f'value="{username}"' in html


def test_a_signed_in_visit_to_sign_in_or_up_goes_home(client, admin):
    assert client.get("/login").headers["Location"] == "/"
    assert client.get("/register").headers["Location"] == "/"


# ———— the throttle ————

def test_eight_failures_lock_the_pair_even_with_the_right_password(stranger):
    client, token = stranger
    for _ in range(8):
        assert login(client, token, password="nope").status_code == 401
    resp = login(client, token)
    assert resp.status_code == 429 and THROTTLED.encode() in resp.data


def test_the_lock_is_per_account(stranger, post):
    post("/admin/users", {"username": "b@example.com", "password": "password1"})
    client, token = stranger
    for _ in range(8):
        login(client, token, password="nope")
    assert login(client, token, username="b@example.com").status_code == 302


def test_a_success_clears_the_count(stranger):
    client, token = stranger
    for _ in range(7):
        login(client, token, password="nope")
    assert login(client, token).status_code == 302
    client.post("/logout", data={"_csrf": token})
    codes = [login(client, token, password="nope").status_code for _ in range(9)]
    assert codes == [401] * 8 + [429]


def test_the_lock_lifts_after_fifteen_minutes(stranger, monkeypatch):
    client, token = stranger
    for _ in range(8):
        login(client, token, password="nope")
    later = time.monotonic() + 15 * 60 + 1
    monkeypatch.setattr(time, "monotonic", lambda: later)
    assert login(client, token).status_code == 302


def test_without_trust_proxy_forwarded_addresses_are_ignored(stranger):
    client, token = stranger
    for n in range(8):
        client.post("/login", data={"_csrf": token, "username": "admin@example.com",
                                    "password": "nope"}, headers={"X-Forwarded-For": f"10.0.0.{n}"})
    assert login(client, token).status_code == 429


def test_with_trust_proxy_each_forwarded_address_counts_alone(app, admin):
    class Proxied(hyprapp.config.Config):
        TESTING = True
        TRUST_PROXY = 1
    proxied = hyprapp.create_app(Proxied)
    client = proxied.test_client()
    token = token_for(client)
    for _ in range(8):
        client.post("/login", data={"_csrf": token, "username": "admin@example.com",
                                    "password": "nope"}, headers={"X-Forwarded-For": "10.0.0.1"})
    resp = client.post("/login", data={"_csrf": token, "username": "admin@example.com",
                                       "password": "password1"}, headers={"X-Forwarded-For": "10.0.0.2"})
    assert resp.status_code == 302


# ———— sign up ————

def register(client, token, **fields):
    data = {"_csrf": token, "username": "new@example.com", "password": "password1",
            "confirm": "password1", **fields}
    return client.post("/register", data=data)


def test_the_sign_up_page(stranger):
    client, _ = stranger
    html = client.get("/register").data.decode()
    assert "<title>Create account — Hyprapp</title>" in html
    assert 'name="confirm" type="password" required minlength="8"' in html


@pytest.mark.parametrize("fields, error", [
    ({"username": "not-an-email"}, "Enter a valid email address."),
    ({"username": "x" * 75 + "@e.com"}, "Enter a valid email address."),
    ({"password": "short", "confirm": "short"}, "Passwords need at least 8 characters."),
    ({"confirm": "password2"}, "Passwords don&#39;t match."),
    ({"username": "ADMIN@example.com"}, "An account with that email already exists."),
])
def test_sign_up_refusals(stranger, fields, error):
    client, token = stranger
    resp = register(client, token, name="Keep me", **fields)
    assert resp.status_code == 400
    html = resp.data.decode()
    assert f'<div class="flash flash--error">{error}</div>' in html
    assert 'value="Keep me"' in html


def test_signing_up(app, stranger):
    client, token = stranger
    resp = register(client, token, username="  New@Example.com ", name="  " + "z" * 130)
    assert resp.status_code == 302 and resp.headers["Location"] == "/"
    assert client.get("/").status_code == 200
    with app.app_context():
        created = User.query.filter_by(username="new@example.com").one()
        assert created.is_admin is False and created.name == "z" * 120


def test_a_closed_sign_up_goes_back_to_sign_in(stranger, post):
    post("/admin/registration", {"open": False})
    client, token = stranger
    resp = client.get("/register", follow_redirects=True)
    assert b"Registration is closed on this server." in resp.data
    assert b"Create an account" not in resp.data
    assert register(client, token).status_code == 302


# ———— sign out ————

def test_signing_out(client, csrf, admin):
    resp = client.post("/logout", data={"_csrf": csrf})
    assert resp.status_code == 302 and resp.headers["Location"] == "/login"
    assert client.get("/").status_code == 302
