"""The visual baseline: every page, and every settings section, on the
desktop and a phone, in light and dark. See visual.py for the comparison.

The data is fixed, dates included, so the pages look the same on every run.
Masked: the version and the changelog, which change with each release, and
any paragraph with <code> in it, which is drawn in the system's monospace
font and so differs from machine to machine.
"""
import sqlite3
from contextlib import closing

import pytest
from playwright.sync_api import expect

from .conftest import DESKTOP, PHONE, Api, Server

# Between the breakpoints: 820px is past 1060 and 900, 640px past 700 too
# but not 560, so a media query applied out of order shows up here.
TABLET = {"width": 820, "height": 1000}
SMALL = {"width": 640, "height": 900}
from .visual import compare

MASKS = [".settings-nav-version", ".about-version", ".release-list", "p:has(code)"]
SECTIONS = ["appearance", "account", "admin", "security", "about"]
RECORDS = [
    ("Plan the garden", "Seeds, soil and a fence before the first frost.", {"pinned": True}),
    ("Write the quarterly report", "Numbers from finance, then the summary for the board.", {}),
    ("Call the plumber", "", {"done": True}),
    ("Read the field guide", "Chapters four to six, with notes on the birds by the river.", {}),
    ("Renew the passport", "Photos first.", {}),
]


@pytest.fixture(scope="module")
def shots_server(tmp_path_factory):
    """One instance with fixed data for every shot in this module."""
    with Server(tmp_path_factory.mktemp("visual")) as server:
        admin = Api(server).setup(worker_minutes=15)
        admin.post("/admin/users", {"username": "bob@example.com", "password": "password1", "name": "Bob"})
        for title, body, flags in reversed(RECORDS):
            admin.item(title, body, **flags)
        with closing(sqlite3.connect(server.data_dir / "hyprapp.db")) as db:
            db.execute("UPDATE users SET created_at = '2024-01-15 09:00:00.000000'")
            db.execute("UPDATE items SET created_at = datetime('2024-03-01', '+' || id || ' days'), "
                       "updated_at = created_at")
            db.commit()
        bob = Api(server).login("bob@example.com", "password1")
        yield server, {"admin": admin, "bob": bob}


@pytest.fixture(scope="module")
def fresh_server(tmp_path_factory):
    with Server(tmp_path_factory.mktemp("fresh")) as server:
        yield server


SHOTS = {}


def shot(name, viewport=DESKTOP, user="admin", fresh=False):
    def register(scene):
        SHOTS[name] = (viewport, user, fresh, scene)
        return scene
    return register


def open_settings(page, section, phone=False):
    if phone:
        page.get_by_role("button", name="Open menu").click()
    page.locator(".sidebar-foot").get_by_role("button", name="Settings").click()
    if section:
        page.locator(f'.settings-navitem[data-section="{section}"]').click()
        expect(page.locator(f'.settings-pane[data-pane="{section}"]')).to_be_visible()


# ———— pages ————

@shot("login", user=None)
def _login(page):
    page.goto("/login")


@shot("register", user=None)
def _register(page):
    page.goto("/register")


@shot("setup-welcome", user=None, fresh=True)
def _setup(page):
    page.goto("/setup")


@shot("setup-account", user=None, fresh=True)
def _setup_account(page):
    page.goto("/setup")
    page.get_by_role("button", name="Get started").click()
    page.locator("#wiz-name").blur()


@shot("error-404")
def _error(page):
    page.goto("/no-such-page")


@shot("cards")
def _cards(page):
    page.goto("/")


@shot("list")
def _list(page):
    page.goto("/?view=list&filter=all")


@shot("empty", user="bob")
def _empty(page):
    page.goto("/")


@shot("sort-menu")
def _menu(page):
    page.goto("/?sort=title")
    page.locator("#sort-menu .menubtn").click()


@shot("sheet")
def _sheet(page):
    page.goto("/")
    page.locator("[data-item]", has_text="Plan the garden").click()
    expect(page.locator("#sheet-title")).to_have_text("Plan the garden")


@shot("palette")
def _palette(page):
    page.goto("/")
    page.keyboard.press("Control+k")
    page.locator("#search-input").fill("the")
    expect(page.locator(".palette-item")).to_have_count(5)


@shot("record-form")
def _form(page):
    page.goto("/")
    page.keyboard.press("n")
    page.fill("#item-title", "A new record")


for _section in SECTIONS:
    @shot(f"settings-{_section}")
    def _settings(page, section=_section):
        page.goto("/")
        open_settings(page, section)


# ———— phones ————

@shot("phone-login", viewport=PHONE, user=None)
def _phone_login(page):
    page.goto("/login")


@shot("phone-cards", viewport=PHONE)
def _phone_cards(page):
    page.goto("/")


@shot("phone-drawer", viewport=PHONE)
def _phone_drawer(page):
    page.goto("/")
    page.get_by_role("button", name="Open menu").click()


@shot("phone-sheet", viewport=PHONE)
def _phone_sheet(page):
    page.goto("/")
    page.locator("[data-item]", has_text="Read the field guide").click()
    expect(page.locator("#sheet-title")).to_have_text("Read the field guide")


@shot("phone-settings", viewport=PHONE)
def _phone_settings(page):
    page.goto("/")
    open_settings(page, None, phone=True)


for _section in SECTIONS:
    @shot(f"phone-settings-{_section}", viewport=PHONE)
    def _phone_section(page, section=_section):
        page.goto("/")
        open_settings(page, section, phone=True)


# ———— between the breakpoints ————

for _prefix, _viewport in (("tablet", TABLET), ("small", SMALL)):
    @shot(f"{_prefix}-cards", viewport=_viewport)
    def _mid_cards(page):
        page.goto("/")

    @shot(f"{_prefix}-list", viewport=_viewport)
    def _mid_list(page):
        page.goto("/?view=list&filter=all")

    @shot(f"{_prefix}-drawer", viewport=_viewport)
    def _mid_drawer(page):
        page.goto("/")
        page.get_by_role("button", name="Open menu").click()

    @shot(f"{_prefix}-sheet", viewport=_viewport)
    def _mid_sheet(page):
        page.goto("/")
        page.locator("[data-item]", has_text="Plan the garden").click()
        expect(page.locator("#sheet-title")).to_have_text("Plan the garden")

    @shot(f"{_prefix}-settings-admin", viewport=_viewport)
    def _mid_admin(page):
        page.goto("/")
        open_settings(page, "admin", phone=True)


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("name", list(SHOTS))
def test_looks_unchanged(browser, shots_server, fresh_server, name, theme):
    viewport, user, fresh, scene = SHOTS[name]
    server, sessions = (fresh_server, {}) if fresh else shots_server
    context = browser.new_context(base_url=server.url, viewport=viewport, color_scheme=theme,
                                  reduced_motion="reduce", locale="en-US", timezone_id="UTC")
    context.set_default_timeout(5000)
    errors = []
    try:
        if user:
            context.add_cookies(sessions[user].cookies())
        page = context.new_page()
        page.on("pageerror", lambda err: errors.append(str(err)))
        scene(page)
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")
        page.mouse.move(0, 0)
        png = page.screenshot(animations="disabled", caret="hide",
                              mask=[page.locator(selector) for selector in MASKS])
    finally:
        context.close()
    assert not errors, errors
    compare(png, f"{name}-{theme}")
