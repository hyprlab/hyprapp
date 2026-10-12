"""The changelog parser behind the About section."""
import os
import textwrap

import pytest

from hyprapp import about_docs

CHANGELOG = textwrap.dedent("""\
    # Changelog

    Intro text that belongs to no version.

    ## Unreleased

    - Not shown

    ## [1.2.0] — 2026-08-07 — Short title

    ### Added
    - A **thing**, see [the docs](https://example.com)

    ## [1.1.0] (latest) - 2026-07-01

    Plain paragraph.

    ## 1.0.0

    - First

    ## [0.9.0] – 2026-13-45

    [1.0.0]: https://example.com/compare
    """)


@pytest.fixture()
def changelog(tmp_path, monkeypatch):
    path = tmp_path / "CHANGELOG.md"
    path.write_text(CHANGELOG, encoding="utf-8")
    monkeypatch.setattr(about_docs, "_CHANGELOG", path)
    return path


def test_versions_dates_and_titles(changelog):
    entries = about_docs.changelog()
    assert [(e.version, e.date_label, e.title, e.is_latest) for e in entries] == [
        ("1.2.0", "Aug 7, 2026", "Short title", False),
        ("1.1.0", "Jul 1, 2026", "", True),
        ("1.0.0", "", "", False),
        ("0.9.0", "", "2026-13-45", False),
    ]


def test_bodies_are_rendered_markdown(changelog):
    first, second, third, fourth = about_docs.changelog()
    assert "<h3>Added</h3>" in first.body_html
    assert "<strong>thing</strong>" in first.body_html
    assert '<a href="https://example.com">the docs</a>' in first.body_html
    assert second.body_html == "<p>Plain paragraph.</p>"
    assert third.body_html == "<ul>\n<li>First</li>\n</ul>"
    assert fourth.body_html == ""     # link references are dropped


def test_the_first_entry_is_latest_unless_one_says_so(changelog):
    changelog.write_text(CHANGELOG.replace(" (latest)", ""), encoding="utf-8")
    os.utime(changelog, ns=(1, 1))
    assert [e.is_latest for e in about_docs.changelog()] == [True, False, False, False]


def test_parsing_is_cached_until_the_file_changes(changelog):
    first = about_docs.changelog()
    assert about_docs.changelog() is first
    changelog.write_text("## [2.0.0]\n\n- New\n", encoding="utf-8")
    os.utime(changelog, ns=(2, 2))
    assert [e.version for e in about_docs.changelog()] == ["2.0.0"]


def test_no_changelog_means_no_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(about_docs, "_CHANGELOG", tmp_path / "missing.md")
    assert about_docs.changelog() == []


def test_the_real_changelog_parses():
    entries = about_docs.changelog()
    from hyprapp import __version__
    assert entries and entries[0].version == __version__ and entries[0].is_latest
