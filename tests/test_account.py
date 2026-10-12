"""Per-user preferences (POST /settings) and changing one's own password."""
import pytest

from hyprapp.models import User


def me(app) -> User:
    with app.app_context():
        return User.query.filter_by(username="admin@example.com").one()


def test_settings_answers_ok_and_an_empty_body_changes_nothing(app, post, admin):
    before = me(app)
    assert post("/settings").get_json() == {"ok": True}
    after = me(app)
    assert (after.name, after.theme, after.view_mode, after.infinite_scroll) == \
        (before.name, before.theme, before.view_mode, before.infinite_scroll)


@pytest.mark.parametrize("sent, stored", [
    ("  Ada Lovelace  ", "Ada Lovelace"),
    ("x" * 130, "x" * 120),
    ("", None),
    ("   ", None),
    (None, None),
])
def test_name(app, post, admin, sent, stored):
    post("/settings", {"name": sent})
    assert me(app).name == stored


def test_a_cleared_name_shows_the_email(client, post, admin):
    post("/settings", {"name": ""})
    html = client.get("/").data.decode()
    assert '<span class="user-name" id="user-name">admin@example.com</span>' in html
    assert '<span class="avatar" id="user-avatar">A</span>' in html
    assert 'id="user-email" hidden>' in html


@pytest.mark.parametrize("theme, stored", [
    ("dark", "dark"), ("light", "light"), ("system", "system"), ("blue", "system"), (None, "system"),
])
def test_theme(app, client, post, admin, theme, stored):
    post("/settings", {"theme": theme})
    assert me(app).theme == stored
    assert f'data-theme-pref="{stored}"' in client.get("/").data.decode()


@pytest.mark.parametrize("view, stored", [("list", "list"), ("cards", "cards"), ("grid", "cards")])
def test_view_mode(app, post, admin, view, stored):
    post("/settings", {"view_mode": view})
    assert me(app).view_mode == stored


@pytest.mark.parametrize("sent, stored", [(False, False), (0, False), ("", False), (True, True), ("no", True)])
def test_infinite_scroll(app, post, admin, sent, stored):
    post("/settings", {"infinite_scroll": sent})
    assert me(app).infinite_scroll is stored


def test_preferences_render_in_the_appearance_section(client, post, admin):
    post("/settings", {"theme": "dark", "view_mode": "list", "infinite_scroll": False})
    html = client.get("/").data.decode()
    assert '<input type="radio" name="theme" value="dark" checked>' in html
    assert '<input type="radio" name="view_mode" value="list" checked>' in html
    assert '<input type="checkbox" id="infinite-scroll" >' in html


# ———— password ————

def sign_in(app, username, password) -> int:
    from .conftest import token_for
    other = app.test_client()
    token = token_for(other)
    return other.post("/login", data={"_csrf": token, "username": username,
                                      "password": password}).status_code


@pytest.mark.parametrize("body", [{"current": "wrong", "new": "password2"}, {"new": "password2"}])
def test_the_current_password_must_be_right(post, admin, body):
    resp = post("/account/password", body)
    assert resp.status_code == 403
    assert resp.get_json() == {"error": "Current password is wrong."}


@pytest.mark.parametrize("new", ["", "short", "1234567"])
def test_a_new_password_needs_eight_characters(post, admin, new):
    resp = post("/account/password", {"current": "password1", "new": new})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "New passwords need at least 8 characters."}


def test_a_missing_new_password_is_too_short(post, admin):
    resp = post("/account/password", {"current": "password1"})
    assert resp.status_code == 400


def test_changing_the_password(app, post, admin):
    assert post("/account/password", {"current": "password1", "new": "password2"}).get_json() == {"ok": True}
    assert sign_in(app, "admin@example.com", "password1") == 401
    assert sign_in(app, "admin@example.com", "password2") == 302


def test_a_remembered_session_stays_remembered(app, csrf):
    from .conftest import token_for
    client = app.test_client()
    token = token_for(client)
    client.post("/setup", json={"username": "admin@example.com", "password": "password1"},
                headers={"X-CSRF": token})
    assert client.get_cookie("remember_token") is not None
    resp = client.post("/account/password", json={"current": "password1", "new": "password2"},
                       headers={"X-CSRF": token})
    assert resp.status_code == 200
    client.delete_cookie("session")
    # The new remember-me cookie alone signs the browser back in.
    assert client.get("/", headers={"Accept": "text/html"}).status_code == 200


def test_a_session_without_remember_me_gets_no_cookie(app, client, csrf, admin):
    client.post("/logout", headers={"X-CSRF": csrf})
    token = csrf
    client.post("/login", data={"_csrf": token, "username": "admin@example.com", "password": "password1"})
    client.delete_cookie("remember_token")
    resp = client.post("/account/password", json={"current": "password1", "new": "password2"},
                       headers={"X-CSRF": token})
    assert resp.status_code == 200
    assert client.get_cookie("remember_token") is None
