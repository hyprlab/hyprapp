"""The admin routes: instance settings, registration, and user management.
Turnstile has its own file."""
import pytest

from hyprapp.models import Item, User, get_setting

from .conftest import token_for


def setting(app, key):
    with app.app_context():
        return get_setting(key)


def user(app, username) -> User | None:
    with app.app_context():
        return User.query.filter_by(username=username).first()


def signs_in(app, username, password) -> bool:
    other = app.test_client()
    token = token_for(other)
    return other.post("/login", data={"_csrf": token, "username": username,
                                      "password": password}).status_code == 302


# ———— instance ————

@pytest.mark.parametrize("body, error", [
    ({"worker_minutes": "x"}, "The background interval must be a number."),
    ({"worker_minutes": None}, "The background interval must be a number."),
    ({"worker_minutes": [1]}, "The background interval must be a number."),
    ({"worker_minutes": -1}, "The background interval must be between 0 and 1440."),
    ({"worker_minutes": 1441}, "The background interval must be between 0 and 1440."),
    ({"items_per_page": "abc"}, "The page size must be a number."),
    ({"items_per_page": 9}, "The page size must be between 10 and 500."),
    ({"items_per_page": 501}, "The page size must be between 10 and 500."),
])
def test_instance_settings_are_checked(app, post, admin, body, error):
    resp = post("/admin/instance", body)
    assert resp.status_code == 400 and resp.get_json() == {"error": error}


@pytest.mark.parametrize("body, key, stored", [
    ({"worker_minutes": 0}, "worker_minutes", "0"),
    ({"worker_minutes": 1440}, "worker_minutes", "1440"),
    ({"worker_minutes": "30"}, "worker_minutes", "30"),
    ({"items_per_page": 10}, "items_per_page", "10"),
    ({"items_per_page": 500}, "items_per_page", "500"),
    ({"items_per_page": 20.7}, "items_per_page", "20"),
])
def test_instance_settings_are_saved(app, post, admin, body, key, stored):
    assert post("/admin/instance", body).get_json() == {"ok": True}
    assert setting(app, key) == stored


def test_unknown_instance_keys_are_ignored(app, post, admin):
    assert post("/admin/instance", {"colour": "red"}).get_json() == {"ok": True}
    assert setting(app, "colour") is None


def test_a_valid_setting_before_an_invalid_one_is_still_saved(app, post, admin):
    resp = post("/admin/instance", {"worker_minutes": 30, "items_per_page": 5})
    assert resp.status_code == 400
    assert setting(app, "worker_minutes") == "30" and setting(app, "items_per_page") is None


def test_the_admin_section_shows_the_saved_values(client, post, admin):
    post("/admin/instance", {"worker_minutes": 45, "items_per_page": 60})
    html = client.get("/").data.decode()
    assert 'id="inst-worker" min="0" max="1440" step="1" value="45"' in html
    assert 'id="inst-perpage" min="10" max="500" step="10" value="60"' in html


def test_the_admin_section_defaults(client, admin):
    html = client.get("/").data.decode()
    # The wizard stored worker_minutes 0; nothing stored a page size.
    assert 'id="inst-worker" min="0" max="1440" step="1" value="0"' in html
    assert 'id="inst-perpage" min="10" max="500" step="10" value="40"' in html


# ———— registration ————

@pytest.mark.parametrize("body, is_open", [
    ({"open": True}, True), ({"open": False}, False), ({}, False), ({"open": "yes"}, True),
])
def test_registration(app, client, post, admin, body, is_open):
    assert post("/admin/registration", body).get_json() == {"ok": True, "open": is_open}
    assert setting(app, "registration_open") == ("1" if is_open else "0")
    assert ('id="reg-open" checked' in client.get("/").data.decode()) is is_open


def test_registration_falls_back_to_the_environment(app, client, csrf, admin):
    """The wizard stores a choice, which wins; with nothing stored,
    ALLOW_REGISTRATION decides."""
    from hyprapp.models import Setting, db
    client.post("/logout", headers={"X-CSRF": csrf})
    with app.app_context():
        db.session.delete(db.session.get(Setting, "registration_open"))
        db.session.commit()
    app.config["ALLOW_REGISTRATION"] = False
    assert b"Create an account" not in client.get("/login").data
    assert client.get("/register").status_code == 302
    app.config["ALLOW_REGISTRATION"] = True
    assert b"Create an account" in client.get("/login").data
    assert client.get("/register").status_code == 200


# ———— users ————

@pytest.mark.parametrize("username", ["", "nope", "a@b", "a b@c.de", "x" * 75 + "@e.com", None])
def test_new_users_need_an_email(post, admin, username):
    resp = post("/admin/users", {"username": username, "password": "password1"})
    assert resp.status_code == 400 and resp.get_json() == {"error": "Enter a valid email address."}


def test_the_email_is_checked_before_the_password(post, admin):
    resp = post("/admin/users", {"username": "bad", "password": "x"})
    assert resp.get_json() == {"error": "Enter a valid email address."}


@pytest.mark.parametrize("password", ["", "1234567", None])
def test_new_users_need_a_long_password(post, admin, password):
    resp = post("/admin/users", {"username": "b@example.com", "password": password})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Passwords need at least 8 characters."}


def test_emails_are_unique_whatever_the_case(post, admin):
    resp = post("/admin/users", {"username": "  ADMIN@Example.com ", "password": "password1"})
    assert resp.status_code == 409
    assert resp.get_json() == {"error": "An account with that email already exists."}


def test_creating_a_user(app, post, admin):
    resp = post("/admin/users", {"username": "  New@Example.COM ", "password": "password1",
                                 "name": "  " + "n" * 130, "is_admin": 1})
    body = resp.get_json()
    assert resp.status_code == 200 and body["ok"] is True
    created = user(app, "new@example.com")
    assert body["id"] == created.id
    assert created.name == "n" * 120 and created.is_admin is True
    assert signs_in(app, "new@example.com", "password1")


def test_a_created_user_without_a_name_or_admin_flag(app, post, admin):
    post("/admin/users", {"username": "plain@example.com", "password": "password1", "name": "  "})
    created = user(app, "plain@example.com")
    assert created.name is None and created.is_admin is False


def test_the_user_list(client, post, second_user):
    other, token = second_user
    other.post("/items", json={"title": "One"}, headers={"X-CSRF": token})
    html = client.get("/").data.decode()
    assert 'data-user="2" data-username="other@example.com"' in html
    assert "other@example.com · joined" in html and "· 1 record</span>" in html
    assert '<span class="chip chip--muted">you</span>' in html
    assert 'aria-label="Make admin"' in html and 'aria-label="Delete user"' in html


# ———— reset a password ————

def test_resetting_a_password(app, post, second_user):
    other, token = second_user
    assert post("/admin/users/2/password", {"new": "password9"}).get_json() == {"ok": True}
    assert signs_in(app, "other@example.com", "password9")
    # The user's own session ends with the old password.
    assert other.get("/search?q=ab", headers={"Accept": "application/json"}).status_code == 401


@pytest.mark.parametrize("body", [{"new": "short"}, {}])
def test_a_reset_password_needs_eight_characters(post, second_user, body):
    resp = post("/admin/users/2/password", body)
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Passwords need at least 8 characters."}


def test_resetting_your_own_password_here_signs_you_out(client, post, admin):
    """Unlike Settings > Account, the admin route does not sign the session back in."""
    assert post("/admin/users/1/password", {"new": "password2"}).status_code == 200
    assert client.get("/search?q=ab", headers={"Accept": "application/json"}).status_code == 401


# ———— admin flag and deletion ————

def test_toggling_admin(app, post, second_user):
    assert post("/admin/users/2/toggle-admin").get_json() == {"ok": True, "is_admin": True}
    assert user(app, "other@example.com").is_admin is True
    assert post("/admin/users/2/toggle-admin").get_json() == {"ok": True, "is_admin": False}


def test_an_admin_cannot_change_their_own_flag(post, admin):
    resp = post("/admin/users/1/toggle-admin")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "You can't change your own admin status."}


def test_an_admin_cannot_delete_themselves(post, admin):
    resp = post("/admin/users/1/delete")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "You can't delete your own account from here."}


def test_deleting_a_user(app, post, second_user):
    other, token = second_user
    other.post("/items", json={"title": "Theirs"}, headers={"X-CSRF": token})
    assert post("/admin/users/2/delete").get_json() == {"ok": True}
    assert user(app, "other@example.com") is None
    with app.app_context():
        assert Item.query.count() == 0
    assert other.get("/", headers={"Accept": "text/html"}).status_code == 302


@pytest.mark.parametrize("url", ["/admin/users/99/password", "/admin/users/99/toggle-admin",
                                 "/admin/users/99/delete"])
def test_a_missing_user_is_404(post, admin, url):
    assert post(url, {"new": "password1"}).status_code == 404
