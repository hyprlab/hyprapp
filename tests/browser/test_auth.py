"""The setup wizard, signing in and out, and registration, in the browser."""
from playwright.sync_api import expect

from .conftest import ADMIN, Api


def test_the_setup_wizard(new_page, server):
    page = new_page()
    page.goto("/")
    expect(page).to_have_url(server.url + "/setup")
    expect(page.locator(".wiz-step.is-active .wiz-title")).to_have_text("Welcome")
    page.get_by_role("button", name="Get started").click()

    step = page.locator('.wiz-step[data-step="1"]')
    expect(step).to_have_class("wiz-step is-active")
    expect(page.locator("#wiz-name")).to_be_focused()
    page.fill("#wiz-email", "not-an-email")
    step.get_by_role("button", name="Continue").click()
    expect(page.locator("#wiz-error-1")).to_have_text("Enter a valid email address.")
    page.fill("#wiz-email", "admin@example.com")
    page.fill("#wiz-password", "short")
    step.get_by_role("button", name="Continue").click()
    expect(page.locator("#wiz-error-1")).to_have_text("Passwords need at least 8 characters.")
    page.fill("#wiz-password", "password1")
    page.fill("#wiz-confirm", "password2")
    step.get_by_role("button", name="Continue").click()
    expect(page.locator("#wiz-error-1")).to_have_text("Passwords don't match.")
    page.fill("#wiz-confirm", "password1")
    page.fill("#wiz-name", "Ada")
    step.get_by_role("button", name="Continue").click()
    expect(page.locator("#wiz-error-1")).to_be_hidden()
    expect(page.locator(".wiz-dot.is-active")).to_have_count(3)

    step = page.locator('.wiz-step[data-step="2"]')
    step.get_by_role("button", name="Back").click()
    expect(page.locator('.wiz-step[data-step="1"]')).to_have_class("wiz-step is-active")
    page.locator('.wiz-step[data-step="1"]').get_by_role("button", name="Continue").click()
    page.uncheck("#wiz-registration")
    page.fill("#wiz-worker", "99999")
    step.get_by_role("button", name="Create the instance").click()
    expect(page.locator("#wiz-error-2")).to_have_text(
        "The background interval must be between 0 and 1440 minutes.")
    page.fill("#wiz-worker", "0")
    step.get_by_role("button", name="Create the instance").click()

    step = page.locator('.wiz-step[data-step="3"]')
    expect(step).to_have_class("wiz-step is-active")
    page.fill("#wiz-title", "My first record")
    step.get_by_role("button", name="Add").click()
    expect(page.locator("#wiz-added li")).to_have_text(["My first record"])
    expect(page.locator("#wiz-title")).to_have_value("")
    page.get_by_role("button", name="Open Hyprapp").click()

    expect(page).to_have_url(server.url + "/")
    expect(page.locator(".card-title")).to_have_text(["My first record"])
    expect(page.locator("#user-name")).to_have_text("Ada")
    page.get_by_role("button", name="Settings").click()
    page.locator('.settings-navitem[data-section="admin"]').click()
    expect(page.locator("#reg-open")).not_to_be_checked()
    expect(page.locator("#inst-worker")).to_have_value("0")


def test_signing_in_and_out(new_page, server):
    Api(server).setup()
    page = new_page()
    page.goto("/")
    expect(page).to_have_url(server.url + "/login?next=/")
    expect(page.locator('input[name="username"]')).to_be_focused()
    page.fill('input[name="username"]', ADMIN["username"])
    page.fill('input[name="password"]', "wrong-password")
    page.get_by_role("button", name="Sign in").click()
    expect(page.locator(".flash--error")).to_have_text("Wrong email or password.")
    expect(page.locator('input[name="username"]')).to_have_value(ADMIN["username"])

    page.fill('input[name="password"]', ADMIN["password"])
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(server.url + "/")
    expect(page.locator(".context-title")).to_have_text("Open")

    page.get_by_role("button", name="Sign out").click()
    expect(page).to_have_url(server.url + "/login")
    page.goto("/?filter=done")
    expect(page).to_have_url(server.url + "/login?next=/?filter%3Ddone")
    page.fill('input[name="username"]', ADMIN["username"])
    page.fill('input[name="password"]', ADMIN["password"])
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(server.url + "/?filter=done")


def test_registration_open(new_page, server):
    Api(server).setup()
    page = new_page()
    page.goto("/login")
    page.get_by_role("link", name="Create an account").click()
    expect(page).to_have_url(server.url + "/register")
    page.fill('input[name="name"]', "Grace")
    page.fill('input[name="username"]', "grace@example.com")
    page.fill('input[name="password"]', "password1")
    page.fill('input[name="confirm"]', "password2")
    page.get_by_role("button", name="Create account").click()
    expect(page.locator(".flash--error")).to_have_text("Passwords don't match.")
    expect(page.locator('input[name="name"]')).to_have_value("Grace")
    page.fill('input[name="password"]', "password1")
    page.fill('input[name="confirm"]', "password1")
    page.get_by_role("button", name="Create account").click()
    expect(page).to_have_url(server.url + "/")
    expect(page.locator("#user-name")).to_have_text("Grace")
    page.get_by_role("button", name="Settings").click()
    expect(page.locator(".settings-navitem")).to_have_text(["Appearance", "Account", "About"])


def test_registration_closed(new_page, server):
    Api(server).setup(registration_open=False)
    page = new_page()
    page.goto("/login")
    expect(page.get_by_role("link", name="Create an account")).to_have_count(0)
    page.goto("/register")
    expect(page).to_have_url(server.url + "/login")
    expect(page.locator(".flash--error")).to_have_text("Registration is closed on this server.")
