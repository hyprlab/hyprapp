"""Toasts: confirmations, errors, and where they appear."""
import json
import re

from playwright.sync_api import expect


def test_a_confirmation_appears_and_leaves(page):
    page.get_by_role("button", name="Settings").click()
    page.locator(".seg").get_by_text("List").click()
    toast = page.locator("#toast")
    expect(toast).to_have_text("Default view saved")
    expect(toast).to_have_attribute("role", "status")
    expect(toast).not_to_have_class(re.compile(r"toast--error"))
    expect(toast).to_be_hidden(timeout=4000)


def test_a_toast_raised_in_a_dialog_shows_inside_it(page):
    page.get_by_role("button", name="Settings").click()
    page.locator(".seg").get_by_text("List").click()
    expect(page.locator("#toast")).to_be_visible()
    assert page.evaluate("document.getElementById('toast').parentNode.id") == "settings-modal"


def test_a_toast_outside_dialogs_lives_in_the_body(page, api):
    item = api.item("Pinnable")
    page.reload()
    page.route(f"**/items/{item['id']}", lambda route: route.fulfill(
        status=400, content_type="application/json", body=json.dumps({"error": "Refused."})))
    page.locator(".pinbtn").click()
    expect(page.locator("#toast")).to_be_visible()
    assert page.evaluate("document.getElementById('toast').parentNode.tagName") == "BODY"


def test_an_error_is_red_and_says_what_happened(page):
    page.route("**/settings", lambda route: route.fulfill(
        status=500, content_type="application/json",
        body=json.dumps({"error": "Something went wrong on the server."})))
    page.get_by_role("button", name="Settings").click()
    page.locator(".seg").get_by_text("List").click()
    toast = page.locator("#toast")
    expect(toast).to_have_text("Something went wrong on the server.")
    expect(toast).to_have_class(re.compile(r"\btoast--error\b"))


def test_an_error_without_a_body_still_says_something(page):
    page.route("**/settings", lambda route: route.fulfill(status=502, body="Bad gateway"))
    page.get_by_role("button", name="Settings").click()
    page.locator(".seg").get_by_text("List").click()
    expect(page.locator("#toast")).to_have_text("Something went wrong.")


def test_a_new_toast_replaces_the_last(page):
    page.get_by_role("button", name="Settings").click()
    page.locator(".seg").get_by_text("List").click()
    expect(page.locator("#toast")).to_have_text("Default view saved")
    page.locator("#infinite-scroll").uncheck()
    expect(page.locator("#toast")).to_have_text("Load more records by hand")
    expect(page.locator(".toast")).to_have_count(1)


def test_a_toast_survives_the_reload_it_asked_for(page):
    page.keyboard.press("n")
    page.fill("#item-title", "Made")
    with page.expect_navigation(wait_until="load"):
        page.locator("#item-modal").get_by_role("button", name="Save").click()
    expect(page.locator("#toast")).to_have_text("Record created")
    page.reload()
    page.wait_for_timeout(400)
    expect(page.locator("#toast")).to_be_hidden()
