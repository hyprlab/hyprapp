"""The home page and the worked example's JSON API.

Two shapes of route live here:

* ``index`` renders the shell (sidebar, topbar, records, dialogs) for a page
  load. The filter, sort and view are query parameters, so every screen has a
  URL and the back button works. With ``partial=1`` it returns only the record
  list, which is how "Load more" and infinite scroll page: one renderer for the
  list, not a second one in JavaScript.
* Everything else answers JSON to ``fetch`` calls from ``static/js/``, behind
  the session CSRF check. Failures refuse with ``{"error": "..."}`` and a 4xx
  status, written for the person reading it; the client shows it as a toast
  or an inline form error.

This module and ``Item`` are the part a new app replaces (docs/TEMPLATE.md).
"""

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from . import admin
from .models import VIEWS, Item, db, int_setting
from .validation import json_body, refuse

bp = Blueprint("main", __name__)

FILTERS = ("open", "all", "pinned", "done")
SORTS = {
    "newest": ("Newest first", lambda: Item.created_at.desc()),
    "oldest": ("Oldest first", lambda: Item.created_at.asc()),
    "title": ("Title, A to Z", lambda: func.lower(Item.title).asc()),
}


# ———— The shell ————


def _choice(name: str, allowed, default: str) -> str:
    value = request.args.get(name) or default
    return value if value in allowed else default


def _items_query(filter_name: str, sort: str):
    query = Item.query.filter(Item.user_id == current_user.id)
    if filter_name == "open":
        query = query.filter(Item.done.is_(False))
    elif filter_name == "pinned":
        query = query.filter(Item.pinned.is_(True))
    elif filter_name == "done":
        query = query.filter(Item.done.is_(True))
    # Pinned records lead every list, whatever the sort.
    return query.order_by(Item.pinned.desc(), SORTS[sort][1](), Item.id.desc())


@bp.route("/")
@login_required
def index():
    filter_name = _choice("filter", FILTERS, "open")
    sort = _choice("sort", SORTS, "newest")
    view = request.args.get("view") or current_user.view_mode
    if view not in VIEWS:
        view = "cards"

    page = max(1, request.args.get("page", type=int) or 1)
    per_page = int_setting("items_per_page", 40)
    items = _items_query(filter_name, sort).limit(per_page + 1).offset((page - 1) * per_page).all()
    context = dict(
        items=items[:per_page],
        filter=filter_name,
        sort=sort,
        view=view,
        page=page,
        has_more=len(items) > per_page,
    )
    if request.args.get("partial") == "1":
        return render_template("partials/records.html", **context)

    mine = Item.query.filter_by(user_id=current_user.id)
    counts = {
        "open": mine.filter_by(done=False).count(),
        "pinned": mine.filter_by(pinned=True).count(),
        "done": mine.filter_by(done=True).count(),
    }
    return render_template("app.html", counts=counts, sorts=SORTS, **context, **admin.pane_context())


# ———— Records ————


def _own_item(item_id: int) -> Item:
    """404, not 403, for someone else's record: its existence is not theirs to
    learn either."""
    item = db.session.get(Item, item_id)
    if item is None or item.user_id != current_user.id:
        abort(404)
    return item


def _item_json(item: Item) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "body": item.body,
        "summary": item.summary,
        "pinned": item.pinned,
        "done": item.done,
        "created_at": item.created_at.isoformat() + "Z",
        "updated_at": item.updated_at.isoformat() + "Z",
    }


def _title(data: dict) -> str:
    title = (data.get("title") or "").strip()
    if not title:
        refuse("Give it a title.")
    if len(title) > 300:
        refuse("Titles are limited to 300 characters.")
    return title


def _body(data: dict) -> str:
    return (data.get("body") or "").strip()


@bp.route("/items", methods=["POST"])
@login_required
def item_create():
    data = json_body()
    item = Item(user_id=current_user.id, title=_title(data), body=_body(data))
    db.session.add(item)
    db.session.commit()
    return jsonify(ok=True, item=_item_json(item))


@bp.route("/items/<int:item_id>")
@login_required
def item_detail(item_id):
    return jsonify(ok=True, item=_item_json(_own_item(item_id)))


@bp.route("/items/<int:item_id>", methods=["POST"])
@login_required
def item_update(item_id):
    item = _own_item(item_id)
    data = json_body()
    if "title" in data:
        item.title = _title(data)
    if "body" in data:
        item.body = _body(data)
    if "pinned" in data:
        item.pinned = bool(data["pinned"])
    if "done" in data:
        item.done = bool(data["done"])
    db.session.commit()
    return jsonify(ok=True, item=_item_json(item))


@bp.route("/items/<int:item_id>/delete", methods=["POST"])
@login_required
def item_delete(item_id):
    item = _own_item(item_id)
    snapshot = _item_json(item)
    db.session.delete(item)
    db.session.commit()
    # The client keeps the snapshot to offer Undo, which re-creates it.
    return jsonify(ok=True, item=snapshot)


@bp.route("/items/restore", methods=["POST"])
@login_required
def item_restore():
    """Undo for a delete: re-create a record from the snapshot the delete
    returned. Only the user's own fields come back; the id is new."""
    data = json_body()
    title = (data.get("title") or "").strip()[:300]
    if not title:
        refuse("Nothing to restore.")
    item = Item(
        user_id=current_user.id,
        title=title,
        body=_body(data),
        pinned=bool(data.get("pinned")),
        done=bool(data.get("done")),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(ok=True, item=_item_json(item))


@bp.route("/search")
@login_required
def search():
    """Backs the Ctrl/Cmd+K palette: a case-insensitive substring match over
    the user's own records, newest first, capped so a broad query stays cheap."""
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return jsonify(results=[])
    like = "%" + query.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    rows = (
        Item.query.filter(Item.user_id == current_user.id)
        .filter(
            or_(func.lower(Item.title).like(like, escape="\\"), func.lower(Item.body).like(like, escape="\\"))
        )
        .order_by(Item.created_at.desc())
        .limit(20)
        .all()
    )
    return jsonify(
        results=[
            {"id": r.id, "title": r.title, "done": r.done, "when": r.created_at.strftime("%b %-d")}
            for r in rows
        ]
    )
