"""Light, dark and system themes, set before the first paint."""

import pytest
from playwright.sync_api import expect

THEME_AT_BODY = """
window.__themeAtBody = "unset";
new MutationObserver(function (records, observer) {
  if (document.body) {
    window.__themeAtBody = document.documentElement.getAttribute("data-theme");
    observer.disconnect();
  }
}).observe(document, { childList: true, subtree: true });
"""


def theme(page):
    return page.evaluate(
        "[document.documentElement.dataset.themePref, document.documentElement.dataset.theme]"
    )


@pytest.mark.parametrize(
    "pref, scheme, expected",
    [
        ("system", "dark", "dark"),
        ("system", "light", "light"),
        ("dark", "light", "dark"),
        ("light", "dark", "light"),
    ],
)
def test_the_theme_is_set_before_the_body_exists(new_page, api, pref, scheme, expected):
    api.post("/settings", {"theme": pref})
    page = new_page(api, color_scheme=scheme)
    page.add_init_script(THEME_AT_BODY)
    page.goto("/")
    assert page.evaluate("window.__themeAtBody") == expected
    assert theme(page) == [pref, expected]
    inline = page.evaluate(
        "Array.from(document.head.querySelectorAll('script:not([src])')).map(s => s.textContent).join('')"
    )
    assert "data-theme" in inline


@pytest.mark.parametrize("path", ["/login", "/setup"])
def test_signed_out_pages_follow_the_system(new_page, server, path):
    if path == "/login":
        from .conftest import Api

        Api(server).setup()
    page = new_page(color_scheme="dark")
    page.add_init_script(THEME_AT_BODY)
    page.goto(path)
    assert page.evaluate("window.__themeAtBody") == "dark"


def test_system_follows_the_system_live(new_page, api):
    page = new_page(api, color_scheme="light")
    page.goto("/")
    assert theme(page) == ["system", "light"]
    page.emulate_media(color_scheme="dark")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    api.post("/settings", {"theme": "light"})
    page.reload()
    page.emulate_media(color_scheme="light")
    page.emulate_media(color_scheme="dark")
    assert theme(page) == ["light", "light"]


def test_the_theme_choices_in_settings(page, api):
    page.get_by_role("button", name="Settings").click()
    for choice in ("Dark", "Light", "System"):
        page.locator(".theme-chip", has_text=choice).click()
        value = choice.lower()
        expect(page.locator("html")).to_have_attribute("data-theme-pref", value)
        page.wait_for_function(f"document.documentElement.dataset.themePref === '{value}'")
    page.locator(".theme-chip", has_text="Dark").click()
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    page.wait_for_timeout(300)
    page.reload()
    assert theme(page) == ["dark", "dark"]
    expect(page.locator('input[name="theme"][value="dark"]')).to_be_checked()


@pytest.mark.parametrize("where", [".topbar", ".sidebar-foot"])
def test_the_switches_flip_and_remember(page, api, where):
    switch = page.locator(where).get_by_role("button", name="Toggle theme")
    expect(page.locator(where + " .icon-moon")).to_be_visible()
    expect(page.locator(where + " .icon-sun")).to_be_hidden()
    switch.click()
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("html")).to_have_attribute("data-theme-pref", "dark")
    expect(page.locator(where + " .icon-sun")).to_be_visible()
    expect(page.locator('input[name="theme"][value="dark"]')).to_be_checked()
    page.wait_for_timeout(300)
    page.reload()
    assert theme(page) == ["dark", "dark"]
    page.locator(where).get_by_role("button", name="Toggle theme").click()
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    page.wait_for_timeout(300)
    page.reload()
    assert theme(page) == ["light", "light"]
