"""Cloudflare Turnstile, configured in Settings > Security.

Cloudflare is never called: siteverify is replaced by a stand-in that accepts
one known token, so the tests cover the app's decisions, not the network.
"""

import pytest

from hyprapp import turnstile

GOOD_TOKEN = "passes"


@pytest.fixture(autouse=True)
def fake_cloudflare(monkeypatch):
    """Accept GOOD_TOKEN with any secret except "wrong-secret"."""

    class Response:
        def __init__(self, data):
            self._data = data

        def json(self):
            return self._data

    def post(url, data, timeout):
        if data["secret"] == "wrong-secret":
            return Response({"success": False, "error-codes": ["invalid-input-secret"]})
        if data["response"] != GOOD_TOKEN:
            return Response({"success": False, "error-codes": ["invalid-input-response"]})
        return Response({"success": True})

    monkeypatch.setattr(turnstile.requests, "post", post)


def turn_on(client, csrf, **overrides):
    body = {"site_key": "site-123", "secret_key": "secret-abcd", "token": GOOD_TOKEN, **overrides}
    return client.post("/admin/turnstile", json=body, headers={"X-CSRF": csrf})


def test_off_by_default(client, csrf, admin):
    body = client.get("/").data.decode()
    assert 'id="ts-chip">Off' in body


def test_turning_on_needs_a_passed_challenge(client, csrf, admin):
    resp = turn_on(client, csrf, token="")
    assert resp.status_code == 400 and "challenge" in resp.get_json()["error"].lower()
    resp = turn_on(client, csrf, token="bad")
    assert resp.status_code == 400
    # Nothing was saved by the failures: sign-in still has no challenge.
    client.post("/logout", headers={"X-CSRF": csrf})
    assert b"cf-turnstile" not in client.get("/login").data


def test_a_wrong_secret_is_refused_in_words(client, csrf, admin):
    resp = turn_on(client, csrf, secret_key="wrong-secret")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Cloudflare doesn't recognize that secret key."


def test_turned_on_the_sign_in_page_needs_the_challenge(client, csrf, admin, app):
    resp = turn_on(client, csrf)
    assert resp.status_code == 200 and resp.get_json()["status"]["on"] is True

    stranger = app.test_client()
    page = stranger.get("/login")
    assert b'data-sitekey="site-123"' in page.data
    from tests.conftest import CSRF_RE

    token = CSRF_RE.search(page.data).group(1).decode()
    creds = {"_csrf": token, "username": admin["username"], "password": admin["password"]}
    assert stranger.post("/login", data=creds).status_code == 400
    creds["cf-turnstile-response"] = GOOD_TOKEN
    assert stranger.post("/login", data=creds).status_code == 302


def test_the_secret_never_reaches_the_page(client, csrf, admin):
    turn_on(client, csrf)
    body = client.get("/").data.decode()
    assert "secret-abcd" not in body
    assert "ends in abcd" in body


def test_blank_secret_keeps_the_saved_one(client, csrf, admin):
    turn_on(client, csrf)
    resp = turn_on(client, csrf, site_key="site-456", secret_key="")
    assert resp.status_code == 200
    assert resp.get_json()["status"]["site_key"] == "site-456"
    assert resp.get_json()["status"]["secret_hint"] == "abcd"


def test_turning_off_wins_over_the_environment(client, csrf, admin, app):
    app.config["TURNSTILE_SITE_KEY"] = "env-site"
    app.config["TURNSTILE_SECRET_KEY"] = "env-secret"
    status = client.get("/").data.decode()
    assert "From the TURNSTILE_SITE_KEY" in status
    resp = client.post("/admin/turnstile/disable", headers={"X-CSRF": csrf})
    assert resp.get_json()["status"]["on"] is False
    client.post("/logout", headers={"X-CSRF": csrf})
    assert b"cf-turnstile" not in client.get("/login").data


def test_only_admins_can_change_it(second_user):
    other, token = second_user
    assert (
        other.post(
            "/admin/turnstile", json={"site_key": "x", "token": GOOD_TOKEN}, headers={"X-CSRF": token}
        ).status_code
        == 403
    )
    assert other.post("/admin/turnstile/disable", headers={"X-CSRF": token}).status_code == 403


def test_security_section_is_admin_only(client, csrf, admin, second_user):
    assert 'data-pane="security"' in client.get("/").data.decode()
    other, _ = second_user
    assert 'data-pane="security"' not in other.get("/").data.decode()


def test_cli_turns_it_off(client, csrf, admin, app):
    turn_on(client, csrf)
    runner = app.test_cli_runner()
    assert "on" in runner.invoke(args=["turnstile", "status"]).output
    result = runner.invoke(args=["turnstile", "off"])
    assert result.exit_code == 0, result.output
    assert "off" in runner.invoke(args=["turnstile", "status"]).output


# ———— characterization: every refusal, in words ————


@pytest.mark.parametrize(
    "overrides, error",
    [
        ({"site_key": ""}, "Enter the site key."),
        ({"site_key": "   "}, "Enter the site key."),
        ({"site_key": None}, "Enter the site key."),
        ({"secret_key": ""}, "Enter the secret key."),
        ({"site_key": "s" * 201}, "That doesn't look like a Turnstile key."),
        ({"secret_key": "k" * 201}, "That doesn't look like a Turnstile key."),
        ({"token": None}, "Complete the challenge first."),
        ({"token": "stale"}, "The challenge answer was not accepted. Try again."),
    ],
)
def test_refusals(client, csrf, admin, overrides, error):
    resp = turn_on(client, csrf, **overrides)
    assert resp.status_code == 400 and resp.get_json() == {"error": error}


def test_a_blank_secret_falls_back_to_the_environment(client, csrf, admin, app):
    app.config["TURNSTILE_SITE_KEY"] = "env-site"
    app.config["TURNSTILE_SECRET_KEY"] = "env-secret-wxyz"
    resp = turn_on(client, csrf, secret_key="")
    status = resp.get_json()["status"]
    assert status == {"on": True, "source": "settings", "site_key": "site-123", "secret_hint": "wxyz"}


def test_the_status_while_off_keeps_the_saved_keys(client, csrf, admin):
    turn_on(client, csrf)
    status = client.post("/admin/turnstile/disable", headers={"X-CSRF": csrf}).get_json()
    assert status == {
        "ok": True,
        "status": {"on": False, "source": None, "site_key": "site-123", "secret_hint": "abcd"},
    }
    html = client.get("/").data.decode()
    assert 'id="ts-site" value="site-123"' in html
    assert 'data-on="0" data-has-secret="1"' in html
    assert "Verify and turn on" in html and 'id="ts-off" hidden' in html


def test_the_status_while_on(client, csrf, admin):
    turn_on(client, csrf)
    html = client.get("/").data.decode()
    assert 'id="ts-chip">On' in html and "Sign-in and sign-up show a challenge." in html
    assert "Verify and save the keys" in html and 'id="ts-off" hidden' not in html
    assert "docker exec hyprapp flask turnstile off" in html


class Answer:
    def __init__(self, data=None, error=None):
        self.data, self.error = data, error

    def json(self):
        if self.error:
            raise self.error
        return self.data


@pytest.mark.parametrize(
    "answer, error",
    [
        (
            Answer({"success": False, "error-codes": ["bad-thing"]}),
            "Cloudflare refused the challenge (bad-thing).",
        ),
        (Answer({"success": False, "error-codes": ["x", "y"]}), "Cloudflare refused the challenge (x, y)."),
        (Answer({"success": False}), "Cloudflare refused the challenge."),
        (
            Answer({"success": False, "error-codes": ["x", "timeout-or-duplicate"]}),
            "The challenge expired. Complete it again.",
        ),
        (
            Answer({"success": False, "error-codes": ["internal-error"]}),
            "Cloudflare had an internal error. Try again.",
        ),
        (Answer({"success": False, "error-codes": ["missing-input-secret"]}), "Enter the secret key."),
        (Answer(error=ValueError("not json")), "Couldn't reach Cloudflare to check the challenge."),
    ],
)
def test_what_cloudflare_says(client, csrf, admin, monkeypatch, answer, error):
    monkeypatch.setattr(turnstile.requests, "post", lambda url, data, timeout: answer)
    resp = turn_on(client, csrf)
    assert resp.status_code == 400 and resp.get_json() == {"error": error}


def test_cloudflare_out_of_reach(client, csrf, admin, monkeypatch):
    def unreachable(url, data, timeout):
        raise turnstile.requests.ConnectionError("down")

    monkeypatch.setattr(turnstile.requests, "post", unreachable)
    resp = turn_on(client, csrf)
    assert resp.get_json() == {"error": "Couldn't reach Cloudflare to check the challenge."}


def test_what_is_sent_to_cloudflare(client, csrf, admin, monkeypatch):
    sent = {}

    def capture(url, data, timeout):
        sent.update(url=url, data=data, timeout=timeout)
        return Answer({"success": True})

    monkeypatch.setattr(turnstile.requests, "post", capture)
    turn_on(client, csrf)
    assert sent == {
        "url": "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        "data": {"secret": "secret-abcd", "response": GOOD_TOKEN, "remoteip": "127.0.0.1"},
        "timeout": 10,
    }


def test_the_environment_alone_turns_it_on(client, csrf, admin, app):
    app.config["TURNSTILE_SITE_KEY"] = "env-site"
    app.config["TURNSTILE_SECRET_KEY"] = "env-secret"
    client.post("/logout", headers={"X-CSRF": csrf})
    html = client.get("/login").data.decode()
    assert '<div class="cf-turnstile" data-sitekey="env-site" data-theme="auto"></div>' in html
    assert '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>' in html


def test_sign_up_needs_the_challenge_when_on(client, csrf, admin, app):
    turn_on(client, csrf)
    stranger = app.test_client()
    page = stranger.get("/register")
    assert b'data-sitekey="site-123"' in page.data
    from tests.conftest import CSRF_RE

    token = CSRF_RE.search(page.data).group(1).decode()
    form = {"_csrf": token, "username": "n@example.com", "password": "password1", "confirm": "password1"}
    resp = stranger.post("/register", data=form)
    assert resp.status_code == 400 and b"Verification failed. Please try again." in resp.data
    form["cf-turnstile-response"] = GOOD_TOKEN
    assert stranger.post("/register", data=form).status_code == 302


def test_a_failed_challenge_on_sign_in_says_so(client, csrf, admin, app):
    turn_on(client, csrf)
    stranger = app.test_client()
    from tests.conftest import token_for

    token = token_for(stranger)
    resp = stranger.post(
        "/login",
        data={
            "_csrf": token,
            "username": "admin@example.com",
            "password": "password1",
            "cf-turnstile-response": "bad",
        },
    )
    assert resp.status_code == 400
    assert b'<div class="flash flash--error">Verification failed. Please try again.</div>' in resp.data


def test_cli_status_names_the_source(client, csrf, admin, app):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["turnstile", "status"]).output == "Turnstile is off.\n"
    turn_on(client, csrf)
    assert (
        runner.invoke(args=["turnstile", "status"]).output
        == "Turnstile is on, site key site-123, from the settings.\n"
    )
    assert (
        runner.invoke(args=["turnstile", "off"]).output
        == "Turnstile is off. Sign-in and sign-up no longer show a challenge.\n"
    )
    app.config["TURNSTILE_SITE_KEY"] = "env-site"
    app.config["TURNSTILE_SECRET_KEY"] = "env-secret"
    assert runner.invoke(args=["turnstile", "status"]).output == "Turnstile is off.\n"
