"""Paging: Load more by hand, or infinite scroll, both through ?partial=1."""

import re
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect


def query(url: str) -> dict:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query, keep_blank_values=True).items()}


def arrange(api, count, per_page=10, infinite=False):
    api.post("/admin/instance", {"items_per_page": per_page})
    api.post("/settings", {"infinite_scroll": infinite})
    api.items(count)


def test_load_more_by_hand(page, api):
    arrange(api, 25)
    page.reload()
    cards = page.locator(".grid--cards .card")
    expect(cards).to_have_count(10)
    expect(page.locator(".pager-auto")).to_be_hidden()
    with page.expect_request(re.compile(r"page=2&partial=1&view=cards")):
        page.get_by_role("button", name="Load more").click()
    expect(cards).to_have_count(20)
    expect(page.locator(".grid--cards")).to_have_count(1)
    page.get_by_role("button", name="Load more").click()
    expect(cards).to_have_count(25)
    expect(page.locator(".pager-end")).to_have_text("That's everything.")
    expect(page.locator("#load-more")).to_have_count(0)
    expect(cards.last.locator(".card-title")).to_have_text("Record 000")
    # A record that arrived by paging opens like any other.
    cards.last.click()
    expect(page.locator("#sheet-title")).to_have_text("Record 000")


def test_load_more_keeps_the_view_filter_and_sort(page, api):
    arrange(api, 15)
    page.goto("/?view=list&sort=oldest&open=")
    rows = page.locator(".grid--list .row")
    expect(rows).to_have_count(10)
    with page.expect_request(lambda r: "partial=1" in r.url) as request:
        page.get_by_role("button", name="Load more").click()
    assert query(request.value.url) == {"view": "list", "sort": "oldest", "page": "2", "partial": "1"}
    expect(rows).to_have_count(15)
    expect(rows.last.locator(".row-title")).to_have_text("Record 014")


def test_infinite_scroll(page, api):
    arrange(api, 100, per_page=40, infinite=True)
    page.reload()
    cards = page.locator(".grid--cards .card")
    expect(cards).to_have_count(40)
    expect(page.locator("#load-more")).to_be_hidden()
    expect(page.locator(".pager-auto")).to_be_visible()
    for expected in (80, 100):
        page.mouse.wheel(0, 20000)
        expect(cards).to_have_count(expected)
    expect(page.locator(".pager-end")).to_be_visible()


def test_infinite_scroll_fills_a_short_page_at_once(page, api):
    """The pager is watched with a 600px margin, so pages keep coming while
    it is that close to the viewport."""
    arrange(api, 35, infinite=True)
    page.reload()
    expect(page.locator(".grid--cards .card")).to_have_count(35)


def test_turning_infinite_scroll_on_needs_no_reload(page, api):
    arrange(api, 100, per_page=40)
    page.reload()
    page.get_by_role("button", name="Settings").click()
    page.locator("#infinite-scroll").check()
    expect(page.locator("#toast")).to_have_text("Records load as you scroll")
    expect(page.locator("#records-root")).to_have_attribute("data-infinite", "1")
    page.keyboard.press("Escape")
    page.mouse.wheel(0, 20000)
    expect(page.locator(".grid--cards .card")).to_have_count(80)
    page.get_by_role("button", name="Settings").click()
    page.locator("#infinite-scroll").uncheck()
    expect(page.locator("#toast")).to_have_text("Load more records by hand")
    page.keyboard.press("Escape")
    page.mouse.wheel(0, 20000)
    page.wait_for_timeout(500)
    expect(page.locator(".grid--cards .card")).to_have_count(80)
    expect(page.locator("#load-more")).to_be_visible()


def test_a_failed_page_says_so_and_can_be_retried(page, api):
    arrange(api, 15)
    page.reload()
    page.route("**/?*partial=1*", lambda route: route.fulfill(status=500, body="no"))
    page.get_by_role("button", name="Load more").click()
    expect(page.locator("#toast")).to_have_text("Couldn't load more records.")
    expect(page.locator("#toast")).to_have_class(re.compile(r"toast--error"))
    expect(page.get_by_role("button", name="Load more")).to_be_enabled()
    page.unroute("**/?*partial=1*")
    page.get_by_role("button", name="Load more").click()
    expect(page.locator(".grid--cards .card")).to_have_count(15)


def test_the_button_is_busy_while_loading(page, api):
    arrange(api, 15)
    page.reload()
    held = []
    page.route("**/?*partial=1*", lambda route: held.append(route))
    button = page.locator("#load-more")
    button.click()
    expect(button).to_be_disabled()
    expect(button.locator(".btn-busy")).to_be_visible()
    expect(button.locator(".btn-label")).to_be_hidden()
    held[0].continue_()
    expect(page.locator(".grid--cards .card")).to_have_count(15)
