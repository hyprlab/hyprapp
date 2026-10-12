"""/healthz: whether the app can serve, for Docker and any proxy in front."""
from flask import Blueprint, jsonify

from .models import db

bp = Blueprint("health", __name__)


@bp.route("/healthz")
def healthz():
    """Outside @login_required and outside the setup gate, and it touches the
    database, so a healthy answer means the app can serve, not just that the
    port is open."""
    from . import __version__

    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception:
        return jsonify(ok=False), 503
    return jsonify(ok=True, version=__version__)
