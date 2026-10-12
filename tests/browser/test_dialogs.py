"""Dialogs: closing from the backdrop, and coming back after a reload."""

import json

from playwright.sync_api import expect

from .conftest import SHORT, scroll_partway, wait_for_reload


def open_form(page):
    page.keyboard.press("n")
    expect(page.locator("#item-modal")).to_be_visible()


def test_a_backdrop_click_closes_a_modal(page):
    open_form(page)
    page.mouse.click(15, 15)
    expect(page.locator("#item-modal")).to_be_hidden()


def test_a_click_inside_does_not(page):
    open_form(page)
    page.locator("#item-modal .modal-head h3").click()
    box = page.locator("#item-modal").bounding_box()
    page.mouse.click(box["x"] + 3, box["y"] + box["height"] - 3)
    expect(page.locator("#item-modal")).to_be_visible()


def test_a_drag_from_inside_to_outside_does_not(page):
    open_form(page)
    box = page.locator("#item-title").bounding_box()
    page.mouse.move(box["x"] + 5, box["y"] + 5)
    page.mouse.down()
    page.mouse.move(10, 10, steps=5)
    page.mouse.up()
    expect(page.locator("#item-modal")).to_be_visible()


def test_a_drag_from_outside_to_inside_does_not(page):
    open_form(page)
    box = page.locator("#item-title").bounding_box()
    page.mouse.move(10, 10)
    page.mouse.down()
    page.mouse.move(box["x"] + 5, box["y"] + 5, steps=5)
    page.mouse.up()
    expect(page.locator("#item-modal")).to_be_visible()


def test_the_sheet_closes_from_its_gutters_not_its_margins(page, api):
    api.item("Wide")
    page.reload()
    page.locator("[data-item]").click()
    sheet = page.locator("#sheet")
    expect(sheet).to_be_visible()
    box = sheet.bounding_box()
    assert box["width"] == 840
    page.mouse.click(box["x"] + 30, 400)  # the sheet's own side, beside the article
    expect(sheet).to_be_visible()
    page.mouse.click(box["x"] - 40, 400)  # the backdrop beside the sheet
    expect(sheet).to_have_class("sheet is-closing")
    expect(sheet).to_be_hidden()


def test_the_sheet_leaves_through_the_top(page, api):
    api.item("Animated")
    page.reload()
    page.locator("[data-item]").click()
    expect(page.locator("#sheet-title")).to_have_text("Animated")
    page.keyboard.press("Escape")
    expect(page.locator("#sheet")).to_have_class("sheet is-closing")
    expect(page.locator("#sheet")).to_be_hidden()
    expect(page.locator("#sheet")).to_have_class("sheet")


def test_with_reduced_motion_the_sheet_closes_at_once(new_page, api):
    api.item("Still")
    page = new_page(api, reduced_motion="reduce")
    page.goto("/")
    page.locator("[data-item]").click()
    expect(page.locator("#sheet-title")).to_have_text("Still")
    page.keyboard.press("Escape")
    assert page.evaluate("document.getElementById('sheet').open") is False


def test_the_page_behind_a_dialog_does_not_scroll(page, api):
    api.items(60)
    page.reload()
    page.mouse.wheel(0, 300)
    page.wait_for_function("window.scrollY >= 300")
    open_form(page)
    page.mouse.move(15, 400)
    page.mouse.wheel(0, 600)
    page.wait_for_timeout(200)
    assert page.evaluate("window.scrollY") == 300
    page.keyboard.press("Escape")
    assert page.evaluate("window.scrollY") == 300


# ———— coming back after a reload ————


def test_settings_come_back_with_their_section_and_scroll(new_page, api):
    page = new_page(api, viewport=SHORT)
    page.goto("/")
    page.locator(".sidebar-foot").get_by_role("button", name="Settings").click()
    page.locator('.settings-navitem[data-section="about"]').click()
    scrolled = scroll_partway(page.locator('.settings-pane[data-pane="about"]'))
    page.reload()
    expect(page.locator("#settings-modal")).to_be_visible()
    expect(page.locator("#settings-section-title")).to_have_text("About")
    page.wait_for_function(f"document.querySelector('.settings-pane.is-active').scrollTop === {scrolled}")


def test_a_draft_comes_back(page):
    open_form(page)
    page.fill("#item-title", "Half written")
    page.fill("#item-body", "Some notes")
    page.reload()
    expect(page.locator("#item-modal")).to_be_visible()
    expect(page.locator("#item-modal-title")).to_have_text("New record")
    expect(page.locator("#item-title")).to_have_value("Half written")
    expect(page.locator("#item-body")).to_have_value("Some notes")


def test_an_edit_in_progress_comes_back(page, api, server):
    item = api.item("Original")
    page.reload()
    page.locator("[data-item]").click()
    expect(page.locator("#sheet-title")).to_have_text("Original")
    page.keyboard.press("e")
    expect(page.locator("#item-modal")).to_be_visible()
    expect(page).to_have_url(f"{server.url}/")  # the sheet's ?open= has gone
    page.fill("#item-title", "Changed")
    page.reload()
    expect(page.locator("#item-modal-title")).to_have_text("Edit record")
    expect(page.locator("#item-title")).to_have_value("Changed")
    expect(page.locator("#item-id")).to_have_value(str(item["id"]))
    wait_for_reload(page, lambda: page.locator("#item-modal").get_by_role("button", name="Save").click())
    expect(page.locator(".card-title")).to_have_text(["Changed"])
    expect(page.locator("#item-modal")).to_be_hidden()


def test_a_search_comes_back(page, api):
    api.item("Findable thing")
    page.keyboard.press("Control+k")
    page.locator("#search-input").fill("findable")
    expect(page.locator(".palette-item")).to_have_count(1)
    page.reload()
    expect(page.locator("#search-modal")).to_be_visible()
    expect(page.locator("#search-input")).to_have_value("findable")
    expect(page.locator(".palette-item")).to_have_count(1)


def test_an_open_record_comes_back_where_it_was_scrolled(page, api, server):
    item = api.item("Long read", body="\n\n".join(f"Paragraph {n} " + "word " * 60 for n in range(30)))
    page.reload()
    page.locator("[data-item]").click()
    expect(page.locator("#sheet-title")).to_have_text("Long read")
    page.locator("#sheet").evaluate("s => s.scrollTop = 900")
    page.reload()
    expect(page).to_have_url(f"{server.url}/?open={item['id']}")
    expect(page.locator("#sheet")).to_be_visible()
    page.wait_for_function("document.getElementById('sheet').scrollTop === 900")


def test_only_a_reload_brings_a_dialog_back(page, server):
    page.locator(".sidebar-foot").get_by_role("button", name="Settings").click()
    expect(page.locator("#settings-modal")).to_be_visible()
    page.goto(server.url + "/")
    page.wait_for_timeout(300)
    expect(page.locator("#settings-modal")).to_be_hidden()


def test_a_closed_dialog_does_not_come_back(page):
    open_form(page)
    page.keyboard.press("Escape")
    page.reload()
    page.wait_for_timeout(300)
    expect(page.locator("#item-modal")).to_be_hidden()


def test_a_saved_record_closes_its_form_before_the_reload(page):
    open_form(page)
    page.fill("#item-title", "Saved")
    wait_for_reload(page, lambda: page.locator("#item-modal").get_by_role("button", name="Save").click())
    page.wait_for_timeout(300)
    expect(page.locator("#item-modal")).to_be_hidden()


EXTRA_DIALOG = """
new MutationObserver(function (records, observer) {
  if (!document.body) return;
  observer.disconnect();
  var d = document.createElement("dialog");
  d.id = "extra-dialog";
  d.className = "modal";
  d.innerHTML = '<p>Nothing to remember</p>';
  document.body.appendChild(d);
}).observe(document, { childList: true, subtree: true });
"""


def test_a_dialog_with_nothing_to_remember_comes_back(page):
    page.add_init_script(EXTRA_DIALOG)
    page.reload()
    page.evaluate("document.getElementById('extra-dialog').showModal()")
    page.reload()
    expect(page.locator("#extra-dialog")).to_be_visible()


def test_restore_off_keeps_a_dialog_from_coming_back(page):
    page.evaluate("document.getElementById('search-modal').setAttribute('data-restore', 'off')")
    page.keyboard.press("Control+k")
    page.locator("#search-input").fill("anything")
    page.reload()
    page.wait_for_timeout(300)
    expect(page.locator("#search-modal")).to_be_hidden()


PLANT = """
(function () {
  var planted = sessionStorage.getItem("test-plant");
  if (planted) {
    sessionStorage.removeItem("test-plant");
    sessionStorage.setItem("app-dialog", planted);
  }
})();
"""
MARK_OFF = """
new MutationObserver(function () {
  var d = document.getElementById("search-modal");
  if (d) d.setAttribute("data-restore", "off");
}).observe(document, { childList: true, subtree: true });
"""


def test_restore_off_is_honored_on_the_way_back_too(page):
    """A remembered dialog marked data-restore="off" by the time the page
    loads stays closed."""
    remembered = json.dumps({"id": "search-modal", "path": "/", "state": {"q": "x"}})
    page.add_init_script(PLANT)
    page.evaluate("s => sessionStorage.setItem('test-plant', s)", remembered)
    page.reload()
    expect(page.locator("#search-modal")).to_be_visible()  # the control: it does come back
    page.keyboard.press("Escape")
    page.add_init_script(MARK_OFF)
    page.evaluate("s => sessionStorage.setItem('test-plant', s)", remembered)
    page.reload()
    page.wait_for_timeout(300)
    expect(page.locator("#search-modal")).to_be_hidden()
