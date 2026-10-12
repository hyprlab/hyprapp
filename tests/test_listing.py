"""The record list: filters, sorts, views, paging, empty states and counts,
as the server renders them for a page load and for ?partial=1."""

import re
from datetime import timedelta

import pytest

from hyprapp.models import Item, User, db, utcnow

from .conftest import make


def titles(html: str) -> list[str]:
    return re.findall(r'class="(?:card|row)-title">([^<]*)<', html)


def page(client, **params) -> str:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return client.get(f"/?{query}").data.decode()


@pytest.fixture()
def records(post, admin):
    """One record in each state, created oldest first."""
    made = {
        name: make(post, title)
        for name, title in [
            ("open", "banana open"),
            ("pinned", "Apple pinned"),
            ("done", "cherry done"),
            ("both", "Date pinned and done"),
        ]
    }
    post(f"/items/{made['pinned']['id']}", {"pinned": True})
    post(f"/items/{made['done']['id']}", {"done": True})
    post(f"/items/{made['both']['id']}", {"pinned": True, "done": True})
    return made


@pytest.mark.parametrize(
    "filter_name, expected",
    [
        ("open", ["Apple pinned", "banana open"]),
        ("all", ["Date pinned and done", "Apple pinned", "cherry done", "banana open"]),
        ("pinned", ["Date pinned and done", "Apple pinned"]),
        ("done", ["Date pinned and done", "cherry done"]),
        ("nonsense", ["Apple pinned", "banana open"]),
    ],
)
def test_filters(client, records, filter_name, expected):
    assert titles(page(client, filter=filter_name, partial=1)) == expected


def test_no_filter_means_open(client, records):
    assert titles(page(client, partial=1)) == ["Apple pinned", "banana open"]


@pytest.mark.parametrize(
    "sort, expected",
    [
        ("newest", ["Date pinned and done", "Apple pinned", "cherry done", "banana open"]),
        ("oldest", ["Apple pinned", "Date pinned and done", "banana open", "cherry done"]),
        ("title", ["Apple pinned", "Date pinned and done", "banana open", "cherry done"]),
        ("sideways", ["Date pinned and done", "Apple pinned", "cherry done", "banana open"]),
    ],
)
def test_sorts_keep_pinned_records_first(client, records, sort, expected):
    assert titles(page(client, filter="all", sort=sort, partial=1)) == expected


def test_records_made_in_the_same_instant_sort_newest_id_first(app, client, admin):
    with app.app_context():
        owner, when = User.query.one(), utcnow()
        db.session.add_all(Item(user_id=owner.id, title=t, created_at=when) for t in ("First", "Second"))
        db.session.commit()
    assert titles(page(client, partial=1)) == ["Second", "First"]


def test_views(client, post, admin):
    make(post, "Shown")
    assert 'class="grid--cards"' in page(client)
    assert 'class="grid--list"' in page(client, view="list")
    assert 'class="grid--cards"' in page(client, view="mosaic")
    post("/settings", {"view_mode": "list"})
    assert 'class="grid--list"' in page(client)
    assert 'class="grid--cards"' in page(client, view="cards")


def test_cards_and_rows_carry_what_the_client_reads(client, post, admin):
    item = make(post, "Shape", body="Summary text")
    post(f"/items/{item['id']}", {"pinned": True, "done": True})
    cards = page(client, filter="all")
    assert f'class="card is-done" data-item="{item["id"]}" tabindex="0"' in cards
    assert f'class="pinbtn is-pinned" data-pin="{item["id"]}"' in cards
    assert 'aria-label="Unpin" title="Unpin"' in cards
    assert '<p class="card-dek">Summary text</p>' in cards and '<p class="card-meta">Done</p>' in cards
    assert "<span>Pinned</span>" in cards and ">now</time>" in cards
    rows = page(client, filter="all", view="list")
    assert f'class="row is-done" data-item="{item["id"]}" tabindex="0"' in rows
    assert '<p class="row-dek">Summary text</p>' in rows


@pytest.mark.parametrize("value", ["0", "-3", "abc"])
def test_a_bad_page_number_means_the_first(client, post, admin, value):
    make(post, "Only")
    assert titles(page(client, page=value, partial=1)) == ["Only"]


def test_paging(app, client, post, admin):
    with app.app_context():
        owner, start = User.query.one(), utcnow()
        db.session.add_all(
            Item(user_id=owner.id, title=f"Item {n:02d}", created_at=start + timedelta(seconds=n))
            for n in range(12)
        )
        db.session.commit()
    post("/admin/instance", {"items_per_page": 10})

    first = page(client)
    assert len(titles(first)) == 10 and titles(first)[0] == "Item 11"
    assert '<button class="btn btn--ghost" id="load-more" data-page="2">' in first
    assert "That's everything." not in first

    second = page(client, page=2, partial=1)
    assert titles(second) == ["Item 01", "Item 00"]
    assert "load-more" not in second and '<p class="pager-end">That\'s everything.</p>' in second
    assert "<aside" not in second and "<html" not in second

    beyond = page(client, page=3, partial=1)
    assert titles(beyond) == [] and "That's everything." not in beyond and "empty" not in beyond


def test_a_full_first_page_has_no_pager(client, post, admin):
    post("/admin/instance", {"items_per_page": 10})
    for n in range(10):
        make(post, f"R{n}")
    html = page(client)
    assert "load-more" not in html and "That's everything." not in html


def test_the_page_size_is_the_stored_setting_else_forty(app, client, admin, monkeypatch):
    """ITEMS_PER_PAGE is not consulted: until an admin saves a page size, it is 40."""
    with app.app_context():
        owner = User.query.one()
        db.session.add_all(Item(user_id=owner.id, title=f"N{n}") for n in range(45))
        db.session.commit()
    app.config["ITEMS_PER_PAGE"] = 10
    assert len(titles(page(client))) == 40


@pytest.mark.parametrize(
    "filter_name, heading, onboard",
    [
        ("open", "Nothing here yet", True),
        ("pinned", "Nothing pinned", False),
        ("done", "Nothing done yet", False),
        ("all", "Nothing to show", False),
    ],
)
def test_empty_states(client, admin, filter_name, heading, onboard):
    html = page(client, filter=filter_name)
    assert f'<h2 class="empty-title">{heading}</h2>' in html
    assert ("empty--onboard" in html) is onboard
    assert ('data-open="item-modal">New record</button>' in html) is onboard


def test_sidebar_counts(client, records):
    html = page(client)
    assert '<span class="count count--accent" id="count-open">2</span>' in html
    assert re.search(r"<span>Pinned</span>\s*<span class=\"count\">2</span>", html)
    assert re.search(r"<span>Done</span>\s*<span class=\"count\">2</span>", html)


def test_zero_counts_are_hidden(client, admin):
    html = page(client)
    assert 'id="count-open"' not in html and 'class="count"' not in html


def test_the_open_count_stops_at_999(app, client, admin):
    with app.app_context():
        owner = User.query.one()
        db.session.add_all(Item(user_id=owner.id, title="n") for _ in range(1000))
        db.session.commit()
    assert 'id="count-open">999+</span>' in page(client, partial=0)


def test_titles_and_the_sort_chip(client, records):
    assert "<title>Hyprapp</title>" in page(client)
    assert "<title>Pinned — Hyprapp</title>" in page(client, filter="pinned")
    assert "<title>All records — Hyprapp</title>" in page(client, filter="all")
    html = page(client, filter="done", sort="title")
    assert '<h2 class="context-title">Done<span class="title-chip">Title, A to Z</span></h2>' in html
    assert '<h2 class="context-title">Open</h2>' in page(client)


def test_sort_and_view_links_keep_the_other_choices(client, records):
    html = page(client, filter="done", sort="oldest", view="list")
    assert 'href="/?filter=done&amp;sort=title&amp;view=list"' in html
    assert 'href="/?view=cards&amp;filter=done&amp;sort=oldest"' in html
    assert '<p class="menupop-head">Sort done</p>' in html
    assert (
        'class="menuopt is-active" role="menuitem"\n               href="/?filter=done&amp;sort=oldest'
        in html
    )


def test_the_records_root_carries_the_view_and_preferences(client, post, admin):
    html = page(client, filter="pinned", view="list")
    assert 'id="records-root" data-view="list" data-filter="pinned"' in html
    assert 'data-infinite="1"' in html
    post("/settings", {"infinite_scroll": False})
    assert 'data-infinite="0"' in page(client)
