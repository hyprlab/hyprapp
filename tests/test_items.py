"""The worked example's JSON API and the record list it feeds.

Characterization: each test pins what the routes do today, error texts
included, since the client shows them to people verbatim.
"""
import re
from datetime import timedelta

import pytest
from werkzeug.exceptions import NotFound

from hyprapp.models import Item, User, db, utcnow


def make(post, title="Record", **extra) -> dict:
    resp = post("/items", {"title": title, **extra})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["item"]


def titles(html: str) -> list[str]:
    return re.findall(r'class="(?:card|row)-title">([^<]*)<', html)


def page(client, **params) -> str:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return client.get(f"/?{query}").data.decode()


# ———— create ————

def test_create_returns_the_whole_record(post, admin):
    resp = post("/items", {"title": "  Title  ", "body": "  Line one\n\nline   two  "})
    data = resp.get_json()
    assert resp.status_code == 200 and data["ok"] is True
    item = data["item"]
    assert set(item) == {"id", "title", "body", "summary", "pinned", "done", "created_at", "updated_at"}
    assert item["title"] == "Title"
    assert item["body"] == "Line one\n\nline   two"
    assert item["summary"] == "Line one line two"
    assert item["pinned"] is False and item["done"] is False
    assert item["created_at"].endswith("Z") and item["updated_at"].endswith("Z")


@pytest.mark.parametrize("body", [{}, {"title": ""}, {"title": "   "}, {"title": None}])
def test_create_needs_a_title(post, admin, body):
    resp = post("/items", body)
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Give it a title."}


def test_create_limits_the_title(post, admin):
    resp = post("/items", {"title": "x" * 301})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Titles are limited to 300 characters."}
    assert post("/items", {"title": "x" * 300}).status_code == 200


def test_create_ignores_pinned_and_done(post, admin):
    item = make(post, "Fresh", pinned=True, done=True)
    assert item["pinned"] is False and item["done"] is False


def test_a_body_that_is_not_json_counts_as_empty(client, csrf, admin):
    resp = client.post("/items", data="title=x", headers={"X-CSRF": csrf},
                       content_type="text/plain")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Give it a title."}


# ———— read ————

def test_detail(client, csrf, post, admin):
    item = make(post, "Mine")
    resp = client.get(f"/items/{item['id']}", headers={"X-CSRF": csrf})
    assert resp.get_json() == {"ok": True, "item": item}


def test_a_missing_record_is_a_json_404(client, csrf, admin):
    resp = client.get("/items/999", headers={"X-CSRF": csrf})
    assert resp.status_code == 404
    assert resp.get_json() == {"error": NotFound.description}


# ———— update ————

def test_update_changes_only_what_it_is_sent(client, csrf, post, admin):
    item = make(post, "Before", body="Body")
    url = f"/items/{item['id']}"

    updated = post(url, {"title": "  After  "}).get_json()["item"]
    assert updated["title"] == "After" and updated["body"] == "Body"
    assert updated["updated_at"] != item["updated_at"]

    updated = post(url, {"body": "  New body  "}).get_json()["item"]
    assert updated["body"] == "New body" and updated["title"] == "After"

    updated = post(url, {"pinned": 1}).get_json()["item"]
    assert updated["pinned"] is True and updated["done"] is False
    updated = post(url, {"done": "yes"}).get_json()["item"]
    assert updated["done"] is True and updated["pinned"] is True
    updated = post(url, {"pinned": 0, "done": None}).get_json()["item"]
    assert updated["pinned"] is False and updated["done"] is False

    updated = post(url, {"body": None}).get_json()["item"]
    assert updated["body"] == ""


@pytest.mark.parametrize("title, error", [
    ("", "Give it a title."),
    ("   ", "Give it a title."),
    (None, "Give it a title."),
    ("x" * 301, "Titles are limited to 300 characters."),
])
def test_update_refuses_a_bad_title_and_saves_nothing(client, csrf, post, admin, title, error):
    item = make(post, "Kept")
    resp = post(f"/items/{item['id']}", {"title": title, "body": "changed", "pinned": True})
    assert resp.status_code == 400 and resp.get_json() == {"error": error}
    now = client.get(f"/items/{item['id']}", headers={"X-CSRF": csrf}).get_json()["item"]
    assert now == item


def test_update_of_a_missing_record_is_404(post, admin):
    assert post("/items/999", {"title": "x"}).status_code == 404


# ———— delete and restore ————

def test_delete_returns_a_snapshot(client, csrf, post, admin):
    item = make(post, "Doomed", body="Gone soon")
    post(f"/items/{item['id']}", {"pinned": True})
    snapshot_before = client.get(f"/items/{item['id']}", headers={"X-CSRF": csrf}).get_json()["item"]
    resp = post(f"/items/{item['id']}/delete")
    assert resp.get_json() == {"ok": True, "item": snapshot_before}
    assert client.get(f"/items/{item['id']}", headers={"X-CSRF": csrf}).status_code == 404
    assert post(f"/items/{item['id']}/delete").status_code == 404


def test_restore_makes_a_new_record_from_the_snapshot(post, admin):
    item = make(post, "Back", body="Body")
    newer = make(post, "Newer")
    post(f"/items/{item['id']}", {"pinned": True, "done": True})
    snapshot = post(f"/items/{item['id']}/delete").get_json()["item"]
    resp = post("/items/restore", {**snapshot, "id": 777})
    restored = resp.get_json()["item"]
    assert resp.get_json()["ok"] is True
    assert restored["id"] == newer["id"] + 1   # the snapshot's id is ignored
    assert (restored["title"], restored["body"], restored["pinned"], restored["done"]) == \
        ("Back", "Body", True, True)


def test_restore_trims_and_truncates_the_title(post, admin):
    restored = post("/items/restore", {"title": "  " + "y" * 350, "body": "  b  "}).get_json()["item"]
    assert restored["title"] == "y" * 300 and restored["body"] == "b"
    assert restored["pinned"] is False and restored["done"] is False


@pytest.mark.parametrize("body", [{}, {"title": "  "}, {"title": None}])
def test_restore_needs_a_title(post, admin, body):
    resp = post("/items/restore", body)
    assert resp.status_code == 400 and resp.get_json() == {"error": "Nothing to restore."}


# ———— search ————

def test_search_needs_two_characters(client, post, admin):
    make(post, "Alpha")
    assert client.get("/search").get_json() == {"results": []}
    assert client.get("/search?q=%20a%20").get_json() == {"results": []}
    assert len(client.get("/search?q=al").get_json()["results"]) == 1


def test_search_matches_title_or_body_case_insensitively(client, post, admin):
    make(post, "Groceries", body="Buy MILK")
    make(post, "Milkshake recipe")
    make(post, "Unrelated")
    results = client.get("/search?q=milk").get_json()["results"]
    assert [r["title"] for r in results] == ["Milkshake recipe", "Groceries"]   # newest first
    assert set(results[0]) == {"id", "title", "done", "when"}
    assert re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}", results[0]["when"])


def test_search_reports_done_and_escapes_backslashes(client, post, admin):
    item = make(post, r"C:\temp folder")
    post(f"/items/{item['id']}", {"done": True})
    results = client.get("/search?q=" + "%3A%5Ct").get_json()["results"]
    assert len(results) == 1 and results[0]["done"] is True


def test_search_returns_at_most_twenty(app, client, admin):
    with app.app_context():
        owner = User.query.one()
        db.session.add_all(Item(user_id=owner.id, title=f"Match {n}") for n in range(25))
        db.session.commit()
    assert len(client.get("/search?q=match").get_json()["results"]) == 20


# ———— the list ————

@pytest.fixture()
def records(post, admin):
    """One record in each state, created oldest first."""
    made = {name: make(post, title) for name, title in [
        ("open", "banana open"), ("pinned", "Apple pinned"), ("done", "cherry done"),
        ("both", "Date pinned and done")]}
    post(f"/items/{made['pinned']['id']}", {"pinned": True})
    post(f"/items/{made['done']['id']}", {"done": True})
    post(f"/items/{made['both']['id']}", {"pinned": True, "done": True})
    return made


@pytest.mark.parametrize("filter_name, expected", [
    ("open", ["Apple pinned", "banana open"]),
    ("all", ["Date pinned and done", "Apple pinned", "cherry done", "banana open"]),
    ("pinned", ["Date pinned and done", "Apple pinned"]),
    ("done", ["Date pinned and done", "cherry done"]),
    ("nonsense", ["Apple pinned", "banana open"]),
])
def test_filters(client, records, filter_name, expected):
    assert titles(page(client, filter=filter_name, partial=1)) == expected


def test_no_filter_means_open(client, records):
    assert titles(page(client, partial=1)) == ["Apple pinned", "banana open"]


@pytest.mark.parametrize("sort, expected", [
    ("newest", ["Date pinned and done", "Apple pinned", "cherry done", "banana open"]),
    ("oldest", ["Apple pinned", "Date pinned and done", "banana open", "cherry done"]),
    ("title", ["Apple pinned", "Date pinned and done", "banana open", "cherry done"]),
    ("sideways", ["Date pinned and done", "Apple pinned", "cherry done", "banana open"]),
])
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
        db.session.add_all(Item(user_id=owner.id, title=f"Item {n:02d}",
                                created_at=start + timedelta(seconds=n)) for n in range(12))
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


@pytest.mark.parametrize("filter_name, heading, onboard", [
    ("open", "Nothing here yet", True),
    ("pinned", "Nothing pinned", False),
    ("done", "Nothing done yet", False),
    ("all", "Nothing to show", False),
])
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
    assert 'class="menuopt is-active" role="menuitem"\n               href="/?filter=done&amp;sort=oldest' in html


def test_the_records_root_carries_the_view_and_preferences(client, post, admin):
    html = page(client, filter="pinned", view="list")
    assert 'id="records-root" data-view="list" data-filter="pinned"' in html
    assert 'data-infinite="1"' in html
    post("/settings", {"infinite_scroll": False})
    assert 'data-infinite="0"' in page(client)
