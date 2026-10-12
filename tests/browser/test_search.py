"""The Ctrl/Cmd+K search palette."""

import re

from playwright.sync_api import expect


def test_opening_the_palette(page):
    palette = page.locator("#search-modal")
    expect(page.locator("#search-kbd")).to_have_text("Ctrl K")
    page.keyboard.press("Control+k")
    expect(palette).to_be_visible()
    expect(page.locator("#search-input")).to_be_focused()
    page.keyboard.press("Escape")
    expect(palette).to_be_hidden()
    page.wait_for_function("document.activeElement === document.body")
    page.keyboard.press("/")
    expect(palette).to_be_visible()
    page.keyboard.press("Escape")
    page.locator("#search-btn").click()
    expect(palette).to_be_visible()
    # Ctrl+K works while typing in another dialog too, and opens on top of it.
    page.keyboard.press("Escape")
    page.keyboard.press("n")
    page.locator("#item-title").click()
    page.keyboard.press("Control+k")
    expect(palette).to_be_visible()
    expect(page.locator("#item-modal")).to_be_visible()
    # "/" does not, while a dialog is open.
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")
    page.keyboard.press("n")
    expect(page.locator("#item-modal")).to_be_visible()
    page.locator("#item-modal .modal-head").click()
    page.keyboard.press("/")
    expect(palette).to_be_hidden()


def test_results_with_the_match_marked(page, api):
    api.item("Groceries", body="milk and eggs")
    api.item("Milkshake")
    api.item("Done thing with milk", done=True)
    page.keyboard.press("Control+k")
    page.locator("#search-input").fill("m")
    expect(page.locator("#search-results")).to_be_hidden()
    page.locator("#search-input").fill("milk")
    results = page.locator(".palette-item")
    expect(results).to_have_count(3)
    expect(page.locator(".palette-label")).to_have_text("Records")
    expect(results.locator(".palette-item-title")).to_have_text(
        ["Done thing with milk", "Milkshake", "Groceries"]
    )
    expect(results.nth(1).locator("mark")).to_have_text("Milk")
    expect(results.nth(2).locator("mark")).to_have_count(0)  # matched in the body
    expect(results.nth(0)).to_have_class(re.compile(r"\bis-done\b"))
    expect(results.nth(0)).to_have_class(re.compile(r"\bis-active\b"))
    expect(results.nth(0).locator(".palette-item-meta")).to_have_text(re.compile(r"^[A-Z][a-z]{2} \d{1,2}$"))


def test_nothing_matches(page, api):
    api.item("Something")
    page.keyboard.press("Control+k")
    page.locator("#search-input").fill("zzz")
    expect(page.locator(".palette-empty")).to_have_text("Nothing matches “zzz”.")
    page.locator("#search-input").fill("z")
    expect(page.locator("#search-results")).to_be_hidden()


def test_keyboard_selection_opens_the_record(page, api):
    for title in ("Gamma", "Beta", "Alpha"):
        api.item(title + " term")
    page.keyboard.press("Control+k")
    page.locator("#search-input").fill("term")
    items = page.locator(".palette-item")
    expect(items).to_have_count(3)
    page.keyboard.press("ArrowDown")
    expect(items.nth(1)).to_have_class(re.compile(r"\bis-active\b"))
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    expect(items.nth(2)).to_have_class(re.compile(r"\bis-active\b"))
    page.keyboard.press("ArrowUp")
    expect(items.nth(1)).to_have_class(re.compile(r"\bis-active\b"))
    expect(items.nth(0)).not_to_have_class(re.compile(r"\bis-active\b"))
    page.keyboard.press("Enter")
    expect(page.locator("#search-modal")).to_be_hidden()
    expect(page.locator("#sheet")).to_be_visible()
    expect(page.locator("#sheet-title")).to_have_text("Beta term")


def test_the_pointer_selects_and_opens(page, api):
    api.item("One hit")
    api.item("Two hit")
    page.keyboard.press("Control+k")
    page.locator("#search-input").fill("hit")
    items = page.locator(".palette-item")
    expect(items).to_have_count(2)
    items.nth(1).hover()
    expect(items.nth(1)).to_have_class(re.compile(r"\bis-active\b"))
    items.nth(1).click()
    expect(page.locator("#sheet-title")).to_have_text("One hit")


def test_a_slow_answer_never_replaces_a_newer_one(page, api):
    api.item("apple")
    api.item("apricot")
    slow = []

    def hold_first(route):
        if "q=ap" in route.request.url and not slow:
            slow.append(route)
            return
        route.continue_()

    page.route("**/search?*", hold_first)
    page.keyboard.press("Control+k")
    page.locator("#search-input").fill("ap")
    page.wait_for_timeout(300)
    page.locator("#search-input").fill("apr")
    expect(page.locator(".palette-item-title")).to_have_text(["apricot"])
    slow[0].continue_()
    page.wait_for_timeout(300)
    expect(page.locator(".palette-item-title")).to_have_text(["apricot"])


def test_reopening_starts_empty(page, api):
    api.item("Findable")
    page.keyboard.press("Control+k")
    page.locator("#search-input").fill("find")
    expect(page.locator(".palette-item")).to_have_count(1)
    page.keyboard.press("Escape")
    page.keyboard.press("Control+k")
    expect(page.locator("#search-input")).to_have_value("")
    expect(page.locator("#search-results")).to_be_hidden()
