"""The worked example's JSON API: create, read, update, delete, restore and
search. The list it feeds is test_listing.py.

Characterization: each test pins what the routes do today, error texts
included, since the client shows them to people verbatim.
"""

import re

import pytest
from werkzeug.exceptions import NotFound

from hyprapp.models import Item, User, db

from .conftest import make

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
    resp = client.post("/items", data="title=x", headers={"X-CSRF": csrf}, content_type="text/plain")
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


@pytest.mark.parametrize(
    "title, error",
    [
        ("", "Give it a title."),
        ("   ", "Give it a title."),
        (None, "Give it a title."),
        ("x" * 301, "Titles are limited to 300 characters."),
    ],
)
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


def test_someone_else_s_record_cannot_be_deleted(post, second_user):
    item = make(post, "Mine")
    other, token = second_user
    assert other.post(f"/items/{item['id']}/delete", json={}, headers={"X-CSRF": token}).status_code == 404
    assert post(f"/items/{item['id']}", {}).get_json()["item"]["title"] == "Mine"


def test_restore_makes_a_new_record_from_the_snapshot(post, admin):
    item = make(post, "Back", body="Body")
    newer = make(post, "Newer")
    post(f"/items/{item['id']}", {"pinned": True, "done": True})
    snapshot = post(f"/items/{item['id']}/delete").get_json()["item"]
    resp = post("/items/restore", {**snapshot, "id": 777})
    restored = resp.get_json()["item"]
    assert resp.get_json()["ok"] is True
    assert restored["id"] == newer["id"] + 1  # the snapshot's id is ignored
    assert (restored["title"], restored["body"], restored["pinned"], restored["done"]) == (
        "Back",
        "Body",
        True,
        True,
    )


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
    assert [r["title"] for r in results] == ["Milkshake recipe", "Groceries"]  # newest first
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
