"""The settings window: a rail and a pane on the desktop, a list and a pane
on a phone."""
import re

import pytest
from playwright.sync_api import expect

from .conftest import PHONE

SECTIONS = [("appearance", "Appearance"), ("account", "Account"), ("admin", "Admin"),
            ("security", "Security"), ("about", "About")]


def open_settings(page):
    page.locator(".sidebar-foot").get_by_role("button", name="Settings").click()
    expect(page.locator("#settings-modal")).to_be_visible()


def active(page):
    return page.locator(".settings-navitem.is-active").get_attribute("data-section")


def test_every_section_on_the_desktop(page):
    open_settings(page)
    modal = page.locator("#settings-modal")
    expect(modal.locator(".settings-nav-label")).to_have_text(["Preferences", "Instance"])
    expect(modal.locator(".settings-navitem")).to_have_text([label for _, label in SECTIONS])
    expect(modal.locator(".settings-nav-foot .settings-navitem")).to_have_text("About")
    expect(modal.locator(".settings-nav-version")).to_have_text(re.compile(r"^Hyprapp \d+\.\d+\.\d+"))
    expect(page.locator("#settings-section-title")).to_have_text("Appearance")
    for section, label in SECTIONS:
        modal.locator(f'.settings-navitem[data-section="{section}"]').click()
        expect(page.locator("#settings-section-title")).to_have_text(label)
        pane = modal.locator(f'.settings-pane[data-pane="{section}"]')
        expect(pane).to_be_visible()
        expect(modal.locator(".settings-pane:visible")).to_have_count(1)
        tab = modal.locator(f'.settings-navitem[data-section="{section}"]')
        expect(tab).to_have_attribute("aria-selected", "true")
        expect(tab).to_have_attribute("tabindex", "0")
    expect(modal.locator('.settings-navitem[aria-selected="true"]')).to_have_count(1)


def test_the_window_keeps_its_size(page):
    open_settings(page)
    modal = page.locator("#settings-modal")
    sizes = set()
    for section, _ in SECTIONS:
        modal.locator(f'.settings-navitem[data-section="{section}"]').click()
        box = modal.bounding_box()
        sizes.add((round(box["width"]), round(box["height"])))
    assert len(sizes) == 1


def test_it_reopens_where_it_was_left(page):
    open_settings(page)
    page.locator('.settings-navitem[data-section="security"]').click()
    page.keyboard.press("Escape")
    expect(page.locator("#settings-modal")).to_be_hidden()
    open_settings(page)
    assert active(page) == "security"


def test_the_account_row_opens_the_account_section(page):
    page.locator(".sidebar-foot .user").click()
    expect(page.locator("#settings-modal")).to_be_visible()
    expect(page.locator("#settings-section-title")).to_have_text("Account")


def test_arrow_keys_move_through_the_rail(page):
    open_settings(page)
    page.locator(".settings-navitem.is-active").focus()
    for key, expected in [("ArrowDown", "account"), ("ArrowDown", "admin"), ("End", "about"),
                          ("ArrowDown", "appearance"), ("ArrowUp", "about"), ("Home", "appearance")]:
        page.keyboard.press(key)
        assert active(page) == expected, key
        expect(page.locator(f'.settings-navitem[data-section="{expected}"]')).to_be_focused()
    expect(page.locator("#settings-section-title")).to_have_text("Appearance")


def test_a_section_keeps_its_scroll_when_chosen_again(page):
    """A quirk the refactor keeps (see the final report): the code resets the
    scroll while the pane is still hidden, which has no effect."""
    open_settings(page)
    page.locator('.settings-navitem[data-section="about"]').click()
    pane = page.locator('.settings-pane[data-pane="about"]')
    pane.evaluate("p => p.scrollTop = 200")
    page.locator('.settings-navitem[data-section="account"]').click()
    page.locator('.settings-navitem[data-section="about"]').click()
    assert pane.evaluate("p => p.scrollTop") == 200


def test_changing_the_name(page):
    open_settings(page)
    page.locator('.settings-navitem[data-section="account"]').click()
    page.fill("#acct-name", "Grace Hopper")
    page.locator("#acct-name").press("Tab")
    expect(page.locator("#toast")).to_have_text("Name saved")
    expect(page.locator("#user-name")).to_have_text("Grace Hopper")
    expect(page.locator("#user-avatar")).to_have_text("G")
    expect(page.locator("#user-email")).to_be_visible()
    page.fill("#acct-name", "")
    page.locator("#acct-name").press("Tab")
    expect(page.locator("#user-name")).to_have_text("admin@example.com")
    expect(page.locator("#user-avatar")).to_have_text("A")
    expect(page.locator("#user-email")).to_be_hidden()


def test_changing_the_password(page, api):
    open_settings(page)
    page.locator('.settings-navitem[data-section="account"]').click()
    expect(page.locator(".account-meta")).to_contain_text("Signed in as admin@example.com")
    page.fill("#pw-current", "wrong-password")
    page.fill("#pw-new", "password2")
    page.get_by_role("button", name="Update password").click()
    expect(page.locator("#pw-error")).to_have_text("Current password is wrong.")
    page.fill("#pw-current", "password1")
    page.get_by_role("button", name="Update password").click()
    expect(page.locator("#toast")).to_have_text("Password updated")
    expect(page.locator("#pw-error")).to_be_hidden()
    expect(page.locator("#pw-current")).to_have_value("")
    expect(page.locator("#pw-new")).to_have_value("")
    page.reload()
    expect(page.locator(".context-title")).to_have_text("Open")    # still signed in


def phone_settings(new_page, api):
    page = new_page(api, viewport=PHONE)
    page.goto("/")
    page.get_by_role("button", name="Open menu").click()
    page.locator(".sidebar-foot").get_by_role("button", name="Settings").click()
    expect(page.locator("#settings-modal")).to_be_visible()
    return page


@pytest.mark.parametrize("section, label", SECTIONS)
def test_every_section_on_a_phone(new_page, api, section, label):
    page = phone_settings(new_page, api)
    modal = page.locator("#settings-modal")
    expect(modal.locator(".settings-nav")).to_be_visible()
    expect(modal.locator(".settings-main")).to_be_hidden()
    expect(modal.locator(".settings-navitem-chev").first).to_be_visible()
    modal.locator(f'.settings-navitem[data-section="{section}"]').click()
    expect(modal.locator(".settings-nav")).to_be_hidden()
    expect(modal.locator(f'.settings-pane[data-pane="{section}"]')).to_be_visible()
    expect(page.locator("#settings-section-title")).to_have_text(label)
    box = modal.bounding_box()
    assert (box["width"], box["height"]) == (PHONE["width"], PHONE["height"])
    modal.get_by_role("button", name="All settings").click()
    expect(modal.locator(".settings-nav")).to_be_visible()
    expect(modal.locator(".settings-main")).to_be_hidden()


def test_escape_on_a_phone_goes_back_then_closes(new_page, api):
    page = phone_settings(new_page, api)
    modal = page.locator("#settings-modal")
    modal.locator('.settings-navitem[data-section="account"]').click()
    expect(modal.locator(".settings-main")).to_be_visible()
    page.keyboard.press("Escape")
    expect(modal.locator(".settings-nav")).to_be_visible()
    expect(modal).to_be_visible()
    expect(modal.locator('.settings-navitem[data-section="account"]')).to_be_focused()
    page.keyboard.press("Escape")
    expect(modal).to_be_hidden()


def test_a_phone_reopens_at_the_list(new_page, api):
    page = phone_settings(new_page, api)
    modal = page.locator("#settings-modal")
    modal.locator('.settings-navitem[data-section="account"]').click()
    modal.locator(".settings-head").get_by_role("button", name="Close").click()
    expect(modal).to_be_hidden()
    page.get_by_role("button", name="Open menu").click()
    page.locator(".sidebar-foot").get_by_role("button", name="Settings").click()
    expect(modal.locator(".settings-nav")).to_be_visible()
    expect(modal.locator(".settings-main")).to_be_hidden()
    # The account row still goes straight to its section.
    modal.locator(".settings-nav-close").click()
    page.get_by_role("button", name="Open menu").click()
    page.locator(".sidebar-foot .user").click()
    expect(modal.locator('.settings-pane[data-pane="account"]')).to_be_visible()


def test_arrow_keys_on_a_phone_stay_on_the_list(new_page, api):
    page = phone_settings(new_page, api)
    page.locator(".settings-navitem.is-active").focus()
    page.keyboard.press("ArrowDown")
    expect(page.locator("#settings-modal .settings-nav")).to_be_visible()
    expect(page.locator("#settings-modal .settings-main")).to_be_hidden()
    assert active(page) == "account"


def test_the_view_switch_lives_in_settings_on_a_phone(new_page, api):
    page = new_page(api, viewport=PHONE)
    page.goto("/")
    expect(page.locator(".viewswitch")).to_be_hidden()
    expect(page.locator(".menubtn-label")).to_be_hidden()
    expect(page.locator("#search-kbd")).to_be_hidden()
