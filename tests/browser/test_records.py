"""The worked example in the browser: views, sort, filters, counts, the one
form and the optimistic pin. The detail sheet is test_sheet.py."""

import json
import re

from playwright.sync_api import expect

from .conftest import card, open_record, wait_for_reload


def test_cards_and_list_views(page, api):
    api.item("First", body="The body of the first")
    page.reload()
    expect(page.locator(".grid--cards .card")).to_have_count(1)
    expect(page.locator(".card-dek")).to_have_text("The body of the first")
    page.locator('.viewswitch-btn[title="List"]').click()
    expect(page).to_have_url(re.compile(r"view=list"))
    expect(page.locator(".grid--list .row")).to_have_count(1)
    expect(page.locator(".viewswitch-btn.is-active")).to_have_attribute("title", "List")
    page.locator('.viewswitch-btn[title="Cards"]').click()
    expect(page.locator(".grid--cards .card")).to_have_count(1)


def test_the_default_view_is_a_preference(page, api):
    api.item("First")
    page.get_by_role("button", name="Settings").click()
    page.locator(".seg").get_by_text("List").click()
    expect(page.locator("#toast")).to_have_text("Default view saved")
    page.goto("/")
    expect(page.locator(".grid--list .row")).to_have_count(1)
    expect(page.locator("#records-root")).to_have_attribute("data-view", "list")


def test_the_sort_menu(page, api):
    for title in ("banana", "Apple", "cherry"):
        api.item(title)
    page.reload()
    expect(page.locator(".card-title")).to_have_text(["cherry", "Apple", "banana"])
    menu = page.locator("#sort-menu")
    menu.locator(".menubtn").click()
    expect(menu.locator(".menupop")).to_be_visible()
    expect(menu.locator(".menubtn")).to_have_attribute("aria-expanded", "true")
    page.keyboard.press("Escape")
    expect(menu.locator(".menupop")).to_be_hidden()
    menu.locator(".menubtn").click()
    page.locator(".context-title").click()
    expect(menu.locator(".menupop")).to_be_hidden()
    menu.locator(".menubtn").click()
    menu.get_by_role("menuitem", name="Title, A to Z").click()
    expect(page).to_have_url(re.compile(r"sort=title"))
    expect(page.locator(".card-title")).to_have_text(["Apple", "banana", "cherry"])
    expect(page.locator(".title-chip")).to_have_text("Title, A to Z")
    expect(menu.locator(".menubtn-label")).to_have_text("Title, A to Z")
    menu.locator(".menubtn").click()
    menu.get_by_role("menuitem", name="Oldest first").click()
    expect(page.locator(".card-title")).to_have_text(["banana", "Apple", "cherry"])


def test_filters_and_their_counts(page, api):
    api.item("Open one")
    api.item("Pinned one", pinned=True)
    api.item("Done one", done=True)
    page.reload()
    nav = page.locator(".nav-primary")
    expect(nav.locator("#count-open")).to_have_text("2")
    expect(nav.get_by_role("link", name=re.compile("Pinned"))).to_contain_text("1")
    expect(nav.get_by_role("link", name=re.compile("Done"))).to_contain_text("1")
    nav.get_by_role("link", name=re.compile("Done")).click()
    expect(page).to_have_url(re.compile(r"filter=done"))
    expect(page.locator(".context-title")).to_have_text("Done")
    expect(page).to_have_title("Done — Hyprapp")
    expect(page.locator(".card-title")).to_have_text(["Done one"])
    expect(nav.locator(".navitem.is-active")).to_contain_text("Done")
    nav.get_by_role("link", name=re.compile("Pinned")).click()
    expect(page.locator(".card-title")).to_have_text(["Pinned one"])
    nav.get_by_role("link", name="All records").click()
    expect(page.locator(".card-title")).to_have_count(3)

    # The counts follow the data on the next load.
    open_record(page, "Open one")
    page.keyboard.press("d")
    expect(page.locator("#sheet-kicker")).to_have_text("Done")
    page.goto("/")
    expect(nav.locator("#count-open")).to_have_text("1")
    expect(nav.get_by_role("link", name=re.compile("Done"))).to_contain_text("2")


def test_empty_states(page):
    expect(page.locator(".empty-title")).to_have_text("Nothing here yet")
    page.locator(".empty").get_by_role("button", name="New record").click()
    expect(page.locator("#item-modal")).to_be_visible()
    page.goto("/?filter=pinned")
    expect(page.locator(".empty-title")).to_have_text("Nothing pinned")


def test_creating_through_the_form(page):
    page.keyboard.press("n")
    modal = page.locator("#item-modal")
    expect(modal).to_be_visible()
    expect(page.locator("#item-modal-title")).to_have_text("New record")
    expect(page.locator("#item-title")).to_be_focused()
    page.fill("#item-title", "   ")
    modal.get_by_role("button", name="Save").click()
    expect(page.locator("#item-error")).to_have_text("Give it a title.")
    page.fill("#item-title", "Written in the form")
    page.fill("#item-body", "Some notes.\n\nA second paragraph.")
    wait_for_reload(page, lambda: modal.get_by_role("button", name="Save").click())
    expect(page.locator("#toast")).to_have_text("Record created")
    expect(modal).to_be_hidden()
    expect(page.locator(".card-title")).to_have_text(["Written in the form"])


def test_editing_through_the_same_form(page, api):
    api.item("Before", body="Old notes")
    page.reload()
    open_record(page, "Before")
    page.keyboard.press("e")
    modal = page.locator("#item-modal")
    expect(modal).to_be_visible()
    expect(page.locator("#sheet")).to_be_hidden()
    expect(page.locator("#item-modal-title")).to_have_text("Edit record")
    expect(page.locator("#item-title")).to_have_value("Before")
    expect(page.locator("#item-body")).to_have_value("Old notes")
    page.fill("#item-title", "After")
    wait_for_reload(page, lambda: modal.get_by_role("button", name="Save").click())
    expect(page.locator("#toast")).to_have_text("Record updated")
    expect(page.locator(".card-title")).to_have_text(["After"])
    # A new record after an edit starts empty.
    page.keyboard.press("n")
    expect(page.locator("#item-modal-title")).to_have_text("New record")
    expect(page.locator("#item-title")).to_have_value("")


def test_the_pin_answers_at_once_and_is_saved(page, api):
    item = api.item("Pin me")
    page.reload()
    pin = card(page, "Pin me").locator(".pinbtn")
    expect(pin).to_have_attribute("aria-label", "Pin")
    with page.expect_response(f"**/items/{item['id']}") as answer:
        pin.click()
        expect(pin).to_have_class(re.compile(r"\bis-pinned\b"))
    assert answer.value.ok
    expect(pin).to_have_attribute("aria-label", "Unpin")
    expect(page.locator("#sheet")).to_be_hidden()  # the click didn't open the record
    assert api.get(f"/items/{item['id']}")["item"]["pinned"] is True


def test_the_pin_rolls_back_when_the_server_refuses(page, api):
    item = api.item("Stubborn")
    page.reload()
    page.route(
        f"**/items/{item['id']}",
        lambda route: route.fulfill(
            status=400, content_type="application/json", body=json.dumps({"error": "No pinning today."})
        ),
    )
    pin = card(page, "Stubborn").locator(".pinbtn")
    pin.click()
    expect(page.locator("#toast")).to_have_text("No pinning today.")
    expect(page.locator("#toast")).to_have_class(re.compile(r"toast--error"))
    expect(pin).not_to_have_class(re.compile(r"\bis-pinned\b"))
    expect(pin).to_have_attribute("aria-label", "Pin")


def test_the_pin_rolls_back_when_the_server_is_gone(page, api):
    item = api.item("Offline")
    page.reload()
    page.route(f"**/items/{item['id']}", lambda route: route.abort())
    card(page, "Offline").locator(".pinbtn").click()
    expect(page.locator("#toast")).to_have_text("Can't reach the server.")
    expect(card(page, "Offline").locator(".pinbtn")).not_to_have_class(re.compile(r"\bis-pinned\b"))
