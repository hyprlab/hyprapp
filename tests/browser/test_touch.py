"""Pull to refresh, on a touch device."""
import re

from playwright.sync_api import expect

from .conftest import PHONE


def touch_page(new_page, api):
    page = new_page(api, viewport=PHONE, has_touch=True, is_mobile=True)
    page.goto("/")
    cdp = page.context.new_cdp_session(page)

    def touch(kind, y=0):
        points = [] if kind == "touchEnd" else [{"x": 195, "y": y}]
        cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points})
    return page, touch


def test_a_long_pull_reloads(new_page, api):
    page, touch = touch_page(new_page, api)
    ptr = page.locator("#ptr")
    expect(ptr).to_be_hidden()
    touch("touchStart", 100)
    for y in range(120, 420, 20):
        touch("touchMove", y)
    expect(ptr).to_have_class(re.compile(r"\bis-dragging\b"))
    expect(ptr).to_have_class(re.compile(r"\bis-armed\b"))
    expect(ptr).to_be_visible()
    with page.expect_navigation(wait_until="load"):
        touch("touchEnd")
    expect(page.locator("#ptr")).not_to_have_class(re.compile(r"\bis-refreshing\b"))


def test_a_short_pull_springs_back(new_page, api):
    page, touch = touch_page(new_page, api)
    ptr = page.locator("#ptr")
    touch("touchStart", 100)
    for y in (120, 140, 160):
        touch("touchMove", y)
    expect(ptr).to_have_class(re.compile(r"\bis-dragging\b"))
    expect(ptr).not_to_have_class(re.compile(r"\bis-armed\b"))
    page.evaluate("window.__stayed = true")
    touch("touchEnd")
    expect(ptr).not_to_have_class(re.compile(r"\bis-dragging\b"))
    assert page.evaluate("document.getElementById('ptr').style.transform") == ""
    page.wait_for_timeout(300)
    assert page.evaluate("window.__stayed") is True


def test_no_pull_while_a_dialog_is_open(new_page, api):
    page, touch = touch_page(new_page, api)
    page.get_by_role("button", name="Open menu").tap()
    expect(page.locator("#sidebar")).to_have_class(re.compile(r"\bis-open\b"))
    touch("touchStart", 100)
    for y in range(120, 420, 20):
        touch("touchMove", y)
    expect(page.locator("#ptr")).not_to_have_class(re.compile(r"\bis-dragging\b"))
    touch("touchEnd")
    page.locator(".sidebar").get_by_role("button", name="Settings").tap()
    expect(page.locator("#settings-modal")).to_be_visible()
    touch("touchStart", 300)
    for y in range(320, 620, 20):
        touch("touchMove", y)
    expect(page.locator("#ptr")).not_to_have_class(re.compile(r"\bis-dragging\b"))
    touch("touchEnd")


def test_the_phone_sidebar_is_a_drawer(new_page, api):
    page = new_page(api, viewport=PHONE)
    page.goto("/")
    sidebar, scrim = page.locator("#sidebar"), page.locator(".scrim")
    expect(scrim).to_be_hidden()
    page.get_by_role("button", name="Open menu").click()
    expect(sidebar).to_have_class(re.compile(r"\bis-open\b"))
    expect(scrim).to_be_visible()
    page.get_by_role("button", name="Close menu").click()
    expect(sidebar).not_to_have_class(re.compile(r"\bis-open\b"))
    expect(scrim).to_be_hidden()
    page.get_by_role("button", name="Open menu").click()
    scrim.click(position={"x": 370, "y": 400})
    expect(sidebar).not_to_have_class(re.compile(r"\bis-open\b"))
    # Opening a dialog from the drawer closes it.
    page.get_by_role("button", name="Open menu").click()
    page.locator(".sidebar-label").get_by_role("button", name="New record").click()
    expect(page.locator("#item-modal")).to_be_visible()
    expect(sidebar).not_to_have_class(re.compile(r"\bis-open\b"))
