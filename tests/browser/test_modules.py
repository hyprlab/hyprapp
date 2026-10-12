"""In a real page load, every script arrives versioned, once."""
import re

from playwright.sync_api import expect


def test_every_module_request_is_versioned_and_made_once(new_page, api):
    page = new_page(api)
    scripts = []
    page.on("request", lambda r: scripts.append(r.url) if "/static/js/" in r.url else None)
    page.goto("/")
    page.wait_for_load_state("networkidle")
    expect(page.locator(".context-title")).to_have_text("Open")
    assert scripts, "no modules were requested"
    paths = [re.sub(r"\?.*", "", url) for url in scripts]
    assert all(re.search(r"\.js\?v=\d+$", url) for url in scripts), scripts
    assert len(paths) == len(set(paths)), scripts
    # The app is wired up: a module far down the graph has run.
    page.keyboard.press("Control+k")
    expect(page.locator("#search-modal")).to_be_visible()
