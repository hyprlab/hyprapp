"""The About section: the app, its stack, and the changelog."""

import re
from pathlib import Path

from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parent.parent.parent


def about(page):
    page.get_by_role("button", name="Settings").click()
    page.locator('.settings-navitem[data-section="about"]').click()
    pane = page.locator('.settings-pane[data-pane="about"]')
    expect(pane).to_be_visible()
    return pane


def test_the_about_section(page):
    from hyprapp import __version__

    pane = about(page)
    expect(pane.locator(".about-name")).to_have_text("Hyprapp")
    expect(pane.locator(".about-version")).to_have_text(f"Version {__version__}")
    expect(pane.locator(".about-tagline")).to_have_text("A self-hosted Flask app.")
    expect(pane.get_by_role("link", name="Source")).to_have_attribute(
        "href", "https://github.com/hyprlab/hyprapp"
    )
    expect(pane.get_by_role("link", name="GNU AGPL-3.0")).to_be_visible()
    expect(pane.locator(".tech-tile")).to_have_count(9)
    expect(pane.locator(".tech-tile-name").first).to_have_text("Python")
    icon = pane.locator(".tech-icon").first.evaluate("e => getComputedStyle(e).maskImage")
    assert re.search(r"/static/img/tech/python\.svg\?v=\d+", icon)


def test_the_changelog_renders(page):
    from hyprapp import about_docs

    entries = about_docs.changelog()
    pane = about(page)
    releases = pane.locator(".release-list > li")
    expect(releases).to_have_count(len(entries))
    expect(releases.first.locator(".rel-version")).to_have_text(
        re.compile(rf"^{re.escape(entries[0].version)}\s+latest$")
    )
    expect(releases.first.locator(".rel-meta")).to_have_text(entries[0].date_label)
    expect(releases.first.locator(".rel-body li").first).to_be_visible()
    expect(pane.locator(".about-details")).to_have_attribute("open", "")
    pane.locator(".about-summary").click()
    expect(releases.first).to_be_hidden()


def test_the_hero_animates_only_with_motion(new_page, api):
    page = new_page(api)
    page.goto("/")
    pane = about(page)
    assert pane.locator(".about-hero-bg").evaluate("c => c.width") == 200
    page.wait_for_function(
        "document.querySelector('.about-hero-bg').getContext('2d').getImageData(100, 60, 1, 1).data[3] === 255"
    )
    still = new_page(api, reduced_motion="reduce")
    still.goto("/")
    about(still)
    still.wait_for_timeout(300)
    assert still.locator(".about-hero-bg").evaluate("c => c.width") == 300
