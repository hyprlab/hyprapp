"""What stands in front of every route: the setup gate, sign-in, the admin
check, CSRF, the error shapes and the response headers."""

from urllib.parse import parse_qs, urlparse

import pytest
from flask import abort
from werkzeug.exceptions import Forbidden, MethodNotAllowed

from .conftest import token_for

SESSION_EXPIRED = {"error": "Your session expired. Reload the page and try again."}
SIGNED_OUT = {"error": "You are signed out. Reload the page to sign in again."}

ADMIN_POSTS = [
    "/admin/instance",
    "/admin/registration",
    "/admin/turnstile",
    "/admin/turnstile/disable",
    "/admin/users",
    "/admin/users/1/password",
    "/admin/users/1/toggle-admin",
    "/admin/users/1/delete",
]
USER_POSTS = [
    "/items",
    "/items/1",
    "/items/1/delete",
    "/items/restore",
    "/settings",
    "/account/password",
    "/logout",
]
ALL_POSTS = USER_POSTS + ADMIN_POSTS + ["/setup", "/login", "/register"]
SIGNED_IN_GETS = ["/", "/items/1", "/search?q=abc"]


# ———— CSRF ————


@pytest.mark.parametrize("url", ALL_POSTS)
def test_a_post_without_the_token_is_refused(client, csrf, admin, url):
    resp = client.post(url, json={})
    assert resp.status_code == 400 and resp.get_json() == SESSION_EXPIRED


@pytest.mark.parametrize("url", ["/items", "/login"])
def test_a_wrong_token_is_refused(client, csrf, admin, url):
    assert client.post(url, json={}, headers={"X-CSRF": "nope"}).get_json() == SESSION_EXPIRED
    assert client.post(url, data={"_csrf": "nope"}).get_json() == SESSION_EXPIRED


def test_a_session_without_a_token_refuses_even_an_empty_one(app, admin):
    stranger = app.test_client()
    resp = stranger.post("/login", data={"_csrf": ""}, headers={"X-CSRF": ""})
    assert resp.status_code == 400 and resp.get_json() == SESSION_EXPIRED


def test_the_form_field_and_the_header_both_carry_the_token(client, csrf, admin):
    assert client.post("/items", json={"title": "a"}, headers={"X-CSRF": csrf}).status_code == 200
    assert client.post("/logout", data={"_csrf": csrf}).status_code == 302


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_other_mutating_methods_need_the_token_too(client, csrf, admin, method):
    resp = getattr(client, method)("/items/1")
    assert resp.status_code == 400 and resp.get_json() == SESSION_EXPIRED


# ———— sign-in required ————


@pytest.mark.parametrize("url", SIGNED_IN_GETS)
def test_signed_out_api_calls_get_a_json_401(app, admin, url):
    resp = app.test_client().get(url, headers={"Accept": "application/json"})
    assert resp.status_code == 401 and resp.get_json() == SIGNED_OUT


@pytest.mark.parametrize("url", USER_POSTS + ADMIN_POSTS)
def test_signed_out_posts_get_a_json_401(app, admin, url):
    stranger = app.test_client()
    token = token_for(stranger)
    resp = stranger.post(url, json={}, headers={"X-CSRF": token})
    assert resp.status_code == 401 and resp.get_json() == SIGNED_OUT


@pytest.mark.parametrize("path, next_", [("/", "/"), ("/?filter=done&view=list", "/?filter=done&view=list")])
def test_signed_out_pages_go_to_sign_in_and_come_back(app, admin, path, next_):
    resp = app.test_client().get(path)
    assert resp.status_code == 302
    location = urlparse(resp.headers["Location"])
    assert location.path == "/login" and parse_qs(location.query)["next"] == [next_]


def test_a_signed_out_form_post_goes_to_sign_in(app, admin):
    stranger = app.test_client()
    token = token_for(stranger)
    resp = stranger.post("/logout", data={"_csrf": token})
    assert resp.status_code == 302 and "/login?next=/logout" in resp.headers["Location"]


def test_a_session_for_an_unknown_id_is_signed_out(app, admin):
    stranger = app.test_client()
    for bad in ("abc", "1", "1.wrongstamp", "999.abc"):
        with stranger.session_transaction() as session:
            session["_user_id"] = bad
        assert stranger.get("/").status_code == 302, bad


# ———— admin required ————


@pytest.mark.parametrize("url", ADMIN_POSTS)
def test_admin_routes_refuse_a_plain_account(second_user, url):
    other, token = second_user
    resp = other.post(url, json={"username": "bad"}, headers={"X-CSRF": token})
    assert resp.status_code == 403
    assert resp.get_json() == {"error": Forbidden.description}


@pytest.mark.parametrize(
    "url", ["/admin/users/99/delete", "/admin/users/99/password", "/admin/users/99/toggle-admin"]
)
def test_the_admin_check_comes_before_looking_up_the_user(second_user, url):
    other, token = second_user
    assert other.post(url, json={}, headers={"X-CSRF": token}).status_code == 403


# ———— the setup gate ————


@pytest.mark.parametrize(
    "method, url",
    [
        ("get", "/"),
        ("get", "/login"),
        ("get", "/register"),
        ("get", "/search?q=ab"),
        ("post", "/items"),
        ("post", "/login"),
        ("get", "/no-such-page"),
    ],
)
def test_before_setup_everything_goes_to_the_wizard(client, method, url):
    resp = getattr(client, method)(url)
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/setup")


def test_before_setup_static_files_and_health_are_served(client):
    assert client.get("/static/img/logo.svg").status_code == 200
    assert client.get("/healthz").status_code == 200
    assert client.get("/setup").status_code == 200


def test_the_wizard_post_needs_the_token(client):
    resp = client.post("/setup", json={"username": "a@example.com", "password": "password1"})
    assert resp.status_code == 400 and resp.get_json() == SESSION_EXPIRED


# ———— errors ————


@pytest.fixture()
def failing_app(app):
    """Routes that fail on purpose, added before the first request."""

    def boom():
        raise RuntimeError("on purpose")

    app.add_url_rule("/_boom", "boom", boom)
    app.add_url_rule("/_forbidden", "forbidden", lambda: abort(403))
    app.add_url_rule("/_bad", "bad", lambda: abort(400))
    app.add_url_rule("/_teapot", "teapot", lambda: abort(418))
    return app


@pytest.fixture()
def signed_in(failing_app):
    client = failing_app.test_client()
    token = token_for(client)
    client.post(
        "/setup", json={"username": "a@example.com", "password": "password1"}, headers={"X-CSRF": token}
    )
    return client, token


def test_a_server_error_is_logged_and_shown(signed_in, caplog, monkeypatch):
    from hyprapp.models import db

    rolled_back = []
    monkeypatch.setattr(db.session, "rollback", lambda: rolled_back.append(True))
    client, token = signed_in
    page = client.get("/_boom")
    assert page.status_code == 500 and b'<p class="error-code">500</p>' in page.data
    assert b"Something went wrong on the server. It has been logged." in page.data
    assert b"<title>Server error \xe2\x80\x94 Hyprapp</title>" in page.data
    api = client.get("/_boom", headers={"X-CSRF": token})
    assert api.status_code == 500
    assert api.get_json() == {"error": "Something went wrong on the server."}
    assert rolled_back == [True, True]
    assert "unhandled error on GET /_boom" in caplog.text


@pytest.mark.parametrize(
    "url, code, title, text",
    [
        ("/no-such-page", 404, "Not Found", "There is nothing at this address."),
        ("/_forbidden", 403, "Forbidden", "Your account does not have access to this."),
        ("/_bad", 400, "Bad Request", "The request did not make sense to the server."),
    ],
)
def test_error_pages(signed_in, url, code, title, text):
    client, _ = signed_in
    page = client.get(url)
    assert page.status_code == code
    html = page.data.decode()
    assert f"<title>{title} — Hyprapp</title>" in html
    assert f'<p class="error-code">{code}</p>' in html and f'<p class="error-text">{text}</p>' in html
    assert '<a class="btn btn--primary btn--block" href="/">Back to Hyprapp</a>' in html


def test_an_error_without_its_own_text_shows_the_description(signed_in):
    client, _ = signed_in
    page = client.get("/_teapot")
    assert page.status_code == 418 and b"I&#39;m a teapot" in page.data


def test_a_wrong_method_is_405(signed_in):
    client, token = signed_in
    page = client.get("/logout")
    assert page.status_code == 405 and b"That action is not available here." in page.data
    api = client.get("/logout", headers={"X-CSRF": token})
    assert api.get_json() == {"error": MethodNotAllowed.description}


@pytest.mark.parametrize(
    "headers, wants_json",
    [
        ({}, False),
        ({"Accept": "text/html"}, False),
        ({"Accept": "*/*"}, False),
        ({"Accept": "text/html, application/json"}, False),
        ({"Accept": "application/json"}, True),
        ({"Accept": "application/json, text/html;q=0.5"}, True),
        ({"X-CSRF": "anything"}, True),
        ({"Content-Type": "application/json"}, True),
    ],
)
def test_json_or_a_page(signed_in, headers, wants_json):
    client, _ = signed_in
    resp = client.get("/no-such-page", headers=headers)
    assert resp.status_code == 404
    assert (resp.mimetype == "application/json") is wants_json


# ———— headers ————

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


@pytest.mark.parametrize("url", ["/setup", "/healthz", "/static/img/logo.svg"])
def test_every_response_carries_the_security_headers(client, url):
    resp = client.get(url)
    for name, value in SECURITY_HEADERS.items():
        assert resp.headers[name] == value


def test_only_html_is_no_store(client, csrf, admin):
    assert client.get("/").headers["Cache-Control"] == "no-store"
    assert client.get("/?partial=1").headers["Cache-Control"] == "no-store"
    assert "no-store" not in client.get("/healthz").headers.get("Cache-Control", "")
    assert "no-store" not in client.get("/search?q=ab").headers.get("Cache-Control", "")
    assert "no-store" not in client.get("/static/img/logo.svg").headers.get("Cache-Control", "")


def test_health_reports_the_version(client):
    from hyprapp import __version__

    assert client.get("/healthz").get_json() == {"ok": True, "version": __version__}


def test_health_fails_when_the_database_does(client, monkeypatch):
    from hyprapp.models import db

    def broken(*a, **k):
        raise RuntimeError("database gone")

    monkeypatch.setattr(db.session, "execute", broken)
    resp = client.get("/healthz")
    assert resp.status_code == 503 and resp.get_json() == {"ok": False}
