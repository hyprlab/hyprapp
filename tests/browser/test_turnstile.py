"""Turnstile, set up in Settings > Security, with Cloudflare stubbed: the
widget script by fake_turnstile.js, siteverify by serve.py."""
import re

import pytest
from playwright.sync_api import expect

from .conftest import ADMIN, Api


@pytest.fixture()
def page(new_page, api):
    page = new_page(api, stub_cloudflare=True)
    page.goto("/")
    return page


def security(page):
    page.get_by_role("button", name="Settings").click()
    page.locator('.settings-navitem[data-section="security"]').click()
    expect(page.locator('.settings-pane[data-pane="security"]')).to_be_visible()


def turn_on(page, site="site-key-1", secret="secret-wxyz"):
    page.fill("#ts-site", site)
    page.fill("#ts-secret", secret)
    page.locator("#ts-verify").click()


def test_turning_it_on_and_off(page):
    requested = []
    page.on("request", lambda r: requested.append(r.url) if "challenges.cloudflare.com" in r.url else None)
    security(page)
    expect(page.locator("#ts-chip")).to_have_text("Off")
    expect(page.locator("#ts-status-text")).to_have_text("Sign-in and sign-up have no challenge.")
    expect(page.locator("#ts-off")).to_be_hidden()
    assert requested == []      # nothing is loaded until it is needed
    turn_on(page)
    expect(page.locator("#toast")).to_have_text("Turnstile is on")
    assert any("render=explicit" in url for url in requested)
    calls = page.evaluate("window.__turnstileCalls")
    assert calls[0] == ["render", "site-key-1", "light"]
    expect(page.locator("#ts-chip")).to_have_text("On")
    expect(page.locator("#ts-chip")).not_to_have_class(re.compile("chip--muted"))
    expect(page.locator("#ts-status-text")).to_have_text("Sign-in and sign-up show a challenge.")
    expect(page.locator("#ts-verify .btn-label")).to_have_text("Verify and save the keys")
    expect(page.locator("#ts-secret")).to_have_value("")
    expect(page.locator("#ts-secret")).to_have_attribute("placeholder", "Saved, ends in wxyz. Leave empty to keep it.")
    expect(page.locator("#ts-challenge")).to_be_hidden()
    expect(page.locator("#ts-off")).to_be_visible()

    page.locator("#ts-off").click()
    expect(page.locator("#toast")).to_have_text("Turnstile is off")
    expect(page.locator("#ts-chip")).to_have_text("Off")
    expect(page.locator("#ts-chip")).to_have_class(re.compile("chip--muted"))
    expect(page.locator("#ts-verify .btn-label")).to_have_text("Verify and turn on")
    expect(page.locator("#ts-off")).to_be_hidden()


def test_changing_only_the_site_key_keeps_the_secret(page):
    security(page)
    turn_on(page)
    expect(page.locator("#toast")).to_have_text("Turnstile is on")
    turn_on(page, site="site-key-2", secret="")
    expect(page.locator("#ts-site")).to_have_value("site-key-2")
    expect(page.locator("#ts-secret")).to_have_attribute("placeholder", re.compile("ends in wxyz"))


def test_what_is_checked_before_the_challenge(page):
    security(page)
    page.locator("#ts-verify").click()
    expect(page.locator("#ts-error")).to_have_text("Enter the site key.")
    page.fill("#ts-site", "site-key-1")
    page.locator("#ts-verify").click()
    expect(page.locator("#ts-error")).to_have_text("Enter the secret key.")
    assert page.evaluate("window.__turnstileCalls === undefined")


def test_a_wrong_secret_is_refused_and_the_widget_removed(page):
    security(page)
    turn_on(page, secret="wrong-secret")
    expect(page.locator("#ts-error")).to_have_text("Cloudflare doesn't recognize that secret key.")
    expect(page.locator("#ts-challenge")).to_be_hidden()
    expect(page.locator("#ts-verify")).to_be_enabled()
    expect(page.locator("#ts-chip")).to_have_text("Off")
    assert ["remove", "widget-1"] in page.evaluate("window.__turnstileCalls")


def test_the_widget_s_own_errors_in_words(page, server):
    security(page)
    page.evaluate("window.__turnstileMode = 'error:110200'")
    turn_on(page)
    expect(page.locator("#ts-error")).to_have_text(
        "This address isn't in the widget's hostname list. Add 127.0.0.1 to it in the Cloudflare dashboard.")
    for code, message in [
        ("110100", "Cloudflare doesn't recognize that site key."),
        ("300010", "The challenge failed in this browser (error 300010). Try again."),
        ("600010", "The challenge failed in this browser (error 600010). Try again."),
        ("999", "The challenge failed to load (error 999)."),
    ]:
        page.evaluate(f"window.__turnstileMode = 'error:{code}'")
        page.locator("#ts-verify").click()
        expect(page.locator("#ts-error")).to_have_text(message)
    page.evaluate("window.__turnstileMode = 'expire'")
    page.locator("#ts-verify").click()
    expect(page.locator("#ts-error")).to_have_text("The challenge expired. Press the button again.")
    expect(page.locator("#ts-chip")).to_have_text("Off")


def test_cloudflare_out_of_reach(page):
    page.context.unroute("https://challenges.cloudflare.com/**")
    page.context.route("https://challenges.cloudflare.com/**", lambda route: route.abort())
    security(page)
    turn_on(page)
    expect(page.locator("#ts-error")).to_have_text(
        "Couldn't load Cloudflare's challenge. Check the server's connection.")
    expect(page.locator("#ts-verify")).to_be_enabled()


def test_the_dark_theme_gets_a_dark_widget(new_page, api):
    api.post("/settings", {"theme": "dark"})
    page = new_page(api, stub_cloudflare=True)
    page.goto("/")
    security(page)
    turn_on(page)
    expect(page.locator("#toast")).to_have_text("Turnstile is on")
    assert page.evaluate("window.__turnstileCalls")[0] == ["render", "site-key-1", "dark"]


def test_sign_in_with_the_challenge_on(page, new_page, server):
    security(page)
    turn_on(page)
    expect(page.locator("#toast")).to_have_text("Turnstile is on")
    stranger = new_page(stub_cloudflare=True)
    stranger.goto("/login")
    expect(stranger.locator(".cf-turnstile")).to_have_attribute("data-sitekey", "site-key-1")
    stranger.fill('input[name="username"]', ADMIN["username"])
    stranger.fill('input[name="password"]', ADMIN["password"])
    stranger.get_by_role("button", name="Sign in").click()
    expect(stranger).to_have_url(server.url + "/")


def test_a_refused_challenge_blocks_sign_in(page, new_page, server):
    security(page)
    turn_on(page)
    expect(page.locator("#toast")).to_have_text("Turnstile is on")
    stranger = new_page(stub_cloudflare=True)
    stranger.add_init_script("window.__turnstileMode = 'refuse'")
    stranger.goto("/register")
    stranger.fill('input[name="username"]', "new@example.com")
    stranger.fill('input[name="password"]', "password1")
    stranger.fill('input[name="confirm"]', "password1")
    stranger.get_by_role("button", name="Create account").click()
    expect(stranger.locator(".flash--error")).to_have_text("Verification failed. Please try again.")


def test_with_the_challenge_off_the_script_is_not_loaded(new_page, server):
    Api(server).setup()
    page = new_page()
    requested = []
    page.on("request", lambda r: requested.append(r.url) if "cloudflare" in r.url else None)
    page.goto("/login")
    expect(page.locator(".cf-turnstile")).to_have_count(0)
    page.goto("/register")
    assert requested == []
