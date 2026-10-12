"""Application factory.

create_app() assembles the app from modules that each do one thing: the
SQLite connection (database), the session CSRF token and headers (security),
the first-run gate (setup), error pages (errors), what templates see
(templating), migrations, and the background worker. Blueprints hold the
routes.
"""

import logging

from flask import Flask

from . import database  # noqa: F401  (its SQLite connection listeners register on import)
from . import (
    account,
    admin,
    auth,
    cli,
    errors,
    health,
    main,
    migrations,
    security,
    setup,
    templating,
    turnstile,
    validation,
    worker,
)
from .config import Config
from .models import db

#: The single source of truth for the version. tools/bump-version.sh edits this
#: line; the About section, /healthz, the release scripts and the Docker tags all
#: read it from here.
__version__ = "1.0.0"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

BLUEPRINTS = (auth.bp, main.bp, setup.bp, account.bp, admin.bp, turnstile.bp, health.bp)


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    if app.config["TRUST_PROXY"] > 0:
        from werkzeug.middleware.proxy_fix import ProxyFix

        hops = app.config["TRUST_PROXY"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)

    db.init_app(app)
    auth.init_app(app)
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
    cli.register(app)

    # In this order: a fresh install goes to the wizard before CSRF is checked.
    setup.init_app(app)
    security.init_app(app)
    errors.init_app(app)
    validation.register(app)
    templating.init_app(app, __version__)

    with app.app_context():
        db.create_all()
        migrations.migrate(app)

    worker.start(app)
    return app
