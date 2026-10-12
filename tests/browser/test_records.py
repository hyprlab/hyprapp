"""The worked example in the browser: views, sort, filters, the form, the
pin and done toggles, delete with Undo, the detail sheet and its keys."""
import json
import re

from playwright.sync_api import expect

from .conftest import wait_for_reload


def card(page, title):
    return page.locator("[data-item]", has_text=title)


def open_record(page, title):
    """Open a record's sheet by clicking it, and wait until it shows."""
    card(page, title).click()
    expect(page.locator("#sheet-title")).to_have_text(title)


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
    expect(page.locator("#sheet")).to_be_hidden()    # the click didn't open the record
    assert api.get(f"/items/{item['id']}")["item"]["pinned"] is True


def test_the_pin_rolls_back_when_the_server_refuses(page, api):
    item = api.item("Stubborn")
    page.reload()
    page.route(f"**/items/{item['id']}", lambda route: route.fulfill(
        status=400, content_type="application/json", body=json.dumps({"error": "No pinning today."})))
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
