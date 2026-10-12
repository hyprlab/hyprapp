"""Cloudflare Turnstile: a challenge on the sign-in and sign-up pages.

Configured in Settings > Security. The TURNSTILE_* environment variables are
the fresh-install default, as for every admin setting: once an admin turns
Turnstile on or off in the app, the stored choice wins. Removing the feature
is removing this module and its blueprint, the two verify_form() calls in
auth.py, the Security pane, turnstile.js and the blocks in the auth templates.
"""

import requests
from flask import Blueprint, current_app, jsonify, request

from .models import get_setting, set_setting
from .security import admin_required
from .validation import json_body, refuse

bp = Blueprint("turnstile", __name__)

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
ERRORS = {
    "invalid-input-secret": "Cloudflare doesn't recognize that secret key.",
    "missing-input-secret": "Enter the secret key.",
    "invalid-input-response": "The challenge answer was not accepted. Try again.",
    "missing-input-response": "Complete the challenge first.",
    "timeout-or-duplicate": "The challenge expired. Complete it again.",
    "internal-error": "Cloudflare had an internal error. Try again.",
}


def config() -> dict | None:
    """The keys in force, or None when Turnstile is off.

    Returns {"site_key", "secret_key", "source"}, source being "settings" or
    "environment".
    """
    enabled = get_setting("turnstile_enabled")
    if enabled == "0":
        return None
    if enabled == "1":
        site, secret = get_setting("turnstile_site_key"), get_setting("turnstile_secret_key")
        if site and secret:
            return {"site_key": site, "secret_key": secret, "source": "settings"}
    site = current_app.config["TURNSTILE_SITE_KEY"]
    secret = current_app.config["TURNSTILE_SECRET_KEY"]
    if site and secret:
        return {"site_key": site, "secret_key": secret, "source": "environment"}
    return None


def siteverify(secret: str, token: str) -> tuple[bool, str | None]:
    """Ask Cloudflare whether a challenge token is good. Returns (ok, why not),
    the reason written for a person."""
    if not token:
        return False, ERRORS["missing-input-response"]
    try:
        resp = requests.post(
            VERIFY_URL,
            # remote_addr, not a CF-Connecting-IP header a client could set:
            # behind a proxy, TRUST_PROXY makes remote_addr the real address.
            data={"secret": secret, "response": token, "remoteip": request.remote_addr},
            timeout=10,
        )
        data = resp.json()
    except (requests.RequestException, ValueError):
        return False, "Couldn't reach Cloudflare to check the challenge."
    if data.get("success"):
        return True, None
    codes = data.get("error-codes") or []
    for code in codes:
        if code in ERRORS:
            return False, ERRORS[code]
    return False, "Cloudflare refused the challenge" + (f" ({', '.join(codes)})." if codes else ".")


def verify_form() -> bool:
    """Check the sign-in or sign-up form's challenge, if Turnstile is on."""
    keys = config()
    if keys is None:
        return True
    ok, _ = siteverify(keys["secret_key"], request.form.get("cf-turnstile-response", ""))
    return ok


def status() -> dict:
    """What the Security section shows. The secret never leaves the server;
    only its last four characters do, so an admin can tell which one is saved."""
    keys = config()
    stored_site = get_setting("turnstile_site_key") or ""
    stored_secret = get_setting("turnstile_secret_key") or ""
    return {
        "on": keys is not None,
        "source": keys["source"] if keys else None,
        "site_key": keys["site_key"] if keys else stored_site,
        "secret_hint": (keys["secret_key"] if keys else stored_secret)[-4:],
    }


@bp.post("/admin/turnstile")
@admin_required
def enable():
    """Turn Turnstile on, or change its keys.

    Only after the admin has passed a challenge rendered with the new site key
    and Cloudflare has accepted the answer with the new secret. That proves the
    two keys belong together and that this address is allowed for the widget;
    a wrong pair saved blindly would lock everyone, the admin included, out of
    sign-in.
    """
    data = json_body()
    site_key = (data.get("site_key") or "").strip()
    secret_key = (data.get("secret_key") or "").strip()
    if not site_key:
        refuse("Enter the site key.")
    if not secret_key:
        # Blank keeps the secret already in force, so changing only the site
        # key doesn't mean pasting the secret again.
        secret_key = (config() or {}).get("secret_key") or get_setting("turnstile_secret_key") or ""
        if not secret_key:
            refuse("Enter the secret key.")
    if len(site_key) > 200 or len(secret_key) > 200:
        refuse("That doesn't look like a Turnstile key.")
    ok, why = siteverify(secret_key, data.get("token") or "")
    if not ok:
        refuse(why)
    set_setting("turnstile_site_key", site_key)
    set_setting("turnstile_secret_key", secret_key)
    set_setting("turnstile_enabled", "1")
    return jsonify(ok=True, status=status())


@bp.post("/admin/turnstile/disable")
@admin_required
def disable():
    """Turn Turnstile off. The keys stay saved, so turning it back on is one
    challenge away. The stored "off" also overrides TURNSTILE_* variables."""
    set_setting("turnstile_enabled", "0")
    return jsonify(ok=True, status=status())
