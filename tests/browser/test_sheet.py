"""The detail sheet: opening it from a card, a link or the keyboard, its
toggles, delete with Undo, copying the link, and j and k."""
import re

from playwright.sync_api import expect

from .conftest import card, open_record, wait_for_reload


def test_done_and_pin_from_the_sheet(page, api):
    item = api.item("Toggle me")
    page.reload()
    open_record(page, "Toggle me")
    sheet = page.locator("#sheet")
    expect(sheet).to_be_visible()
    expect(page.locator("#sheet-kicker")).to_have_text("Open")
    page.locator("#sheet-done").click()
    expect(page.locator("#sheet-kicker")).to_have_text("Done")
    expect(page.locator("#sheet-done")).to_have_attribute("title", "Mark as open (d)")
    expect(card(page, "Toggle me")).to_have_class(re.compile(r"\bis-done\b"))
    expect(card(page, "Toggle me").locator(".card-meta")).to_have_text("Done")
    page.keyboard.press("p")
    expect(page.locator("#sheet-pin")).to_have_class(re.compile(r"\bis-pinned\b"))
    expect(page.locator("#sheet-pin")).to_have_attribute("title", "Unpin (p)")
    expect(card(page, "Toggle me").locator(".pinbtn")).to_have_class(re.compile(r"\bis-pinned\b"))
    page.keyboard.press("d")
    expect(page.locator("#sheet-kicker")).to_have_text("Open")
    saved = api.get(f"/items/{item['id']}")["item"]
    assert saved["pinned"] is True and saved["done"] is False


def test_delete_with_undo(new_page, api):
    api.item("Keep me")
    api.item("Doomed", body="Its body", pinned=True)
    # Reduced motion: see the next test for why the Undo needs it.
    page = new_page(api, reduced_motion="reduce")
    page.goto("/")
    open_record(page, "Doomed")
    page.locator("#sheet-delete").click()
    expect(page.locator("#sheet")).to_be_hidden()
    expect(card(page, "Doomed")).to_have_count(0)
    toast = page.locator("#toast")
    expect(toast).to_contain_text("Record deleted")
    wait_for_reload(page, lambda: toast.get_by_role("button", name="Undo").click())
    expect(page.locator("#toast")).to_have_text("Record restored")
    expect(page.locator(".card-title")).to_have_text(["Doomed", "Keep me"])
    expect(card(page, "Doomed").locator(".pinbtn")).to_have_class(re.compile(r"\bis-pinned\b"))


def test_with_motion_the_undo_toast_leaves_with_the_sheet(page, api):
    """A bug the refactor keeps (see the final report): the toast is raised
    while the sheet is still open during its exit animation, so it is placed
    inside the sheet and closes with it, and Undo can't be reached."""
    api.item("Doomed")
    page.reload()
    open_record(page, "Doomed")
    page.locator("#sheet-delete").click()
    expect(page.locator("#sheet")).to_be_hidden()
    assert page.evaluate("document.getElementById('toast').parentNode.id") == "sheet"
    expect(page.locator("#toast")).to_be_hidden()


def test_a_delete_left_alone_stays_deleted(page, api):
    api.item("Gone")
    page.reload()
    open_record(page, "Gone")
    page.locator("#sheet-delete").click()
    expect(page.locator("#toast")).to_be_hidden(timeout=6000)
    page.reload()
    expect(page.locator(".empty-title")).to_have_text("Nothing here yet")


def test_the_sheet_from_a_card(page, api, server):
    item = api.item("Readable", body="First paragraph.\n\nSecond paragraph.")
    page.reload()
    card(page, "Readable").click()
    sheet = page.locator("#sheet")
    expect(sheet).to_be_visible()
    expect(page.locator("#sheet-title")).to_have_text("Readable")
    expect(page.locator("#sheet-body p")).to_have_text(["First paragraph.", "Second paragraph."])
    expect(page.locator("#sheet-meta")).to_contain_text("Created ")
    expect(page).to_have_url(f"{server.url}/?open={item['id']}")
    page.keyboard.press("Escape")
    expect(sheet).to_be_hidden()
    expect(page).to_have_url(f"{server.url}/")
    card(page, "Readable").focus()
    page.keyboard.press("Enter")
    expect(sheet).to_be_visible()
    sheet.get_by_role("button", name="Close").click()
    expect(sheet).to_be_hidden()


def test_the_sheet_shows_text_as_text(page, api):
    api.item("<b>not bold</b>", body="<img src=x onerror=alert(1)>")
    page.reload()
    page.locator("[data-item]").first.click()
    expect(page.locator("#sheet-title")).to_have_text("<b>not bold</b>")
    expect(page.locator("#sheet-body")).to_have_text("<img src=x onerror=alert(1)>")
    expect(page.locator("#sheet-body img")).to_have_count(0)


def test_the_sheet_from_a_link(new_page, api, server):
    item = api.item("Linked")
    page = new_page(api)
    page.goto(f"/?open={item['id']}")
    expect(page.locator("#sheet")).to_be_visible()
    expect(page.locator("#sheet-title")).to_have_text("Linked")


def test_a_link_to_a_missing_record_says_so(new_page, api):
    page = new_page(api)
    page.goto("/?open=999")
    expect(page.locator("#toast")).to_have_text(re.compile("not found", re.I))
    expect(page.locator("#sheet")).to_be_hidden()


def test_copying_the_link(new_page, api, server):
    item = api.item("Share me")
    page = new_page(api, permissions=["clipboard-read", "clipboard-write"])
    page.goto(f"/?open={item['id']}")
    page.locator("#sheet-copy").click()
    expect(page.locator("#sheet-copy")).to_have_class(re.compile(r"\bshow-tip\b"))
    assert page.evaluate("navigator.clipboard.readText()") == f"{server.url}/?open={item['id']}"
    expect(page.locator("#sheet-copy")).not_to_have_class(re.compile(r"\bshow-tip\b"), timeout=3000)


def test_j_and_k_move_through_the_list(page, api):
    for title in ("Third", "Second", "First"):
        api.item(title)
    page.reload()
    open_record(page, "First")
    expect(page.locator("#sheet-title")).to_have_text("First")
    page.keyboard.press("j")
    expect(page.locator("#sheet-title")).to_have_text("Second")
    page.keyboard.press("j")
    expect(page.locator("#sheet-title")).to_have_text("Third")
    page.keyboard.press("j")
    expect(page.locator("#sheet-title")).to_have_text("Third")
    page.keyboard.press("k")
    expect(page.locator("#sheet-title")).to_have_text("Second")
    page.locator("#sheet-prev").click()
    expect(page.locator("#sheet-title")).to_have_text("First")
    page.locator("#sheet-next").click()
    expect(page.locator("#sheet-title")).to_have_text("Second")


def test_keys_are_ignored_while_typing(page, api):
    page.keyboard.press("n")
    page.fill("#item-title", "")
    page.locator("#item-title").type("nj/")
    expect(page.locator("#item-title")).to_have_value("nj/")
    expect(page.locator("#search-modal")).to_be_hidden()


def test_a_toggle_in_list_view_keeps_the_row_in_its_grid(page, api):
    api.item("Row")
    page.goto("/?view=list")
    row = page.locator(".row", has_text="Row")
    open_record(page, "Row")
    page.keyboard.press("d")
    expect(row).to_have_class(re.compile(r"\bis-done\b"))
    expect(row.locator(".new-dot")).to_be_hidden()
    box = row.locator(".row-title").bounding_box()
    page.keyboard.press("d")
    expect(row).not_to_have_class(re.compile(r"\bis-done\b"))
    assert row.locator(".row-title").bounding_box() == box
