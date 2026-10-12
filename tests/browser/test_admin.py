"""Every admin action, from Settings."""

import re

from playwright.sync_api import expect

from .conftest import Api, wait_for_reload


def admin_section(page):
    page.get_by_role("button", name="Settings").click()
    page.locator('.settings-navitem[data-section="admin"]').click()
    expect(page.locator('.settings-pane[data-pane="admin"]')).to_be_visible()


def row(page, username):
    return page.locator(f'.manage-item[data-username="{username}"]')


def test_registration(page, api, server):
    admin_section(page)
    page.locator("#reg-open").uncheck()
    expect(page.locator("#toast")).to_have_text("Registration is closed")
    assert "Create an account" not in Api(server).http.get(server.url + "/login").text
    page.locator("#reg-open").check()
    expect(page.locator("#toast")).to_have_text("Registration is open")


def test_instance_settings(page, api):
    admin_section(page)
    page.fill("#inst-worker", "30")
    page.locator("#inst-worker").press("Tab")
    expect(page.locator("#toast")).to_have_text("Background interval saved")
    page.fill("#inst-perpage", "5")
    page.locator("#inst-perpage").press("Tab")
    expect(page.locator("#toast")).to_have_text("The page size must be between 10 and 500.")
    expect(page.locator("#toast")).to_have_class(re.compile(r"toast--error"))
    page.fill("#inst-perpage", "50")
    page.locator("#inst-perpage").press("Tab")
    expect(page.locator("#toast")).to_have_text("Page size saved")
    page.reload()
    expect(page.locator("#inst-worker")).to_have_value("30")
    expect(page.locator("#inst-perpage")).to_have_value("50")


def test_the_instance_counts(page, api):
    api.item("One")
    page.reload()
    admin_section(page)
    expect(page.locator(".admin-stats")).to_have_text("1 user · 1 record")


def test_adding_a_user(page, api):
    admin_section(page)
    page.fill("#au-name", "Grace")
    page.fill("#au-email", "admin@example.com")
    page.fill("#au-password", "password1")
    page.get_by_role("button", name="Add user").click()
    expect(page.locator("#au-error")).to_have_text("An account with that email already exists.")
    page.fill("#au-email", "grace@example.com")
    page.check("#au-admin")
    wait_for_reload(page, lambda: page.get_by_role("button", name="Add user").click())
    expect(page.locator("#toast")).to_have_text("User created")
    # The reload brings the settings window back where it was.
    expect(page.locator("#settings-modal")).to_be_visible()
    expect(page.locator("#settings-section-title")).to_have_text("Admin")
    grace = row(page, "grace@example.com")
    expect(grace.locator(".manage-title")).to_contain_text("Grace")
    expect(grace.locator(".chip")).to_have_text("admin")
    expect(page.locator(".admin-stats")).to_have_text("2 users · 0 records")


def test_resetting_a_password(page, api, server):
    api.post("/admin/users", {"username": "bob@example.com", "password": "password1"})
    page.reload()
    admin_section(page)
    prompts = []

    def answer(dialog):
        prompts.append(dialog.message)
        dialog.accept(answers.pop(0)) if answers[0] is not None else (answers.pop(0), dialog.dismiss())

    answers = [None, "short", "password9"]
    page.on("dialog", answer)
    button = row(page, "bob@example.com").get_by_role("button", name="Reset password")
    with page.expect_event("dialog"):
        button.click()
    page.wait_for_timeout(300)
    expect(page.locator("#toast")).to_be_hidden()
    button.click()
    expect(page.locator("#toast")).to_have_text("Passwords need at least 8 characters.")
    button.click()
    expect(page.locator("#toast")).to_have_text("Password reset for bob@example.com")
    assert prompts[0] == 'New password for "bob@example.com" (at least 8 characters):'
    Api(server).login("bob@example.com", "password9")


def test_toggling_admin(page, api):
    api.post("/admin/users", {"username": "bob@example.com", "password": "password1"})
    page.reload()
    admin_section(page)
    expect(row(page, "admin@example.com").get_by_role("button", name=re.compile("admin"))).to_have_count(0)
    wait_for_reload(
        page, lambda: row(page, "bob@example.com").get_by_role("button", name="Make admin").click()
    )
    expect(page.locator("#toast")).to_have_text("bob@example.com is now an admin")
    expect(row(page, "bob@example.com").locator(".chip")).to_have_text("admin")
    wait_for_reload(
        page, lambda: row(page, "bob@example.com").get_by_role("button", name="Remove admin").click()
    )
    expect(page.locator("#toast")).to_have_text("bob@example.com is no longer an admin")


def test_deleting_a_user(page, api):
    api.post("/admin/users", {"username": "bob@example.com", "password": "password1"})
    page.reload()
    admin_section(page)
    messages = []
    page.once("dialog", lambda d: (messages.append(d.message), d.dismiss()))
    row(page, "bob@example.com").get_by_role("button", name="Delete user").click()
    page.wait_for_timeout(300)
    expect(row(page, "bob@example.com")).to_have_count(1)
    assert messages == ['Delete "bob@example.com" and everything they own? This cannot be undone.']
    page.once("dialog", lambda d: d.accept())
    wait_for_reload(
        page, lambda: row(page, "bob@example.com").get_by_role("button", name="Delete user").click()
    )
    expect(page.locator("#toast")).to_have_text("Deleted bob@example.com")
    expect(row(page, "bob@example.com")).to_have_count(0)


def test_a_plain_account_has_no_admin_sections(new_page, api, server):
    api.post("/admin/users", {"username": "bob@example.com", "password": "password1"})
    bob = Api(server).login("bob@example.com", "password1")
    page = new_page(bob)
    page.goto("/")
    page.get_by_role("button", name="Settings").click()
    expect(page.locator(".settings-navitem")).to_have_text(["Appearance", "Account", "About"])
    expect(page.locator(".settings-nav-label")).to_have_text(["Preferences"])
    expect(page.locator("#reg-open")).to_have_count(0)
    expect(page.locator("#ts-form")).to_have_count(0)
