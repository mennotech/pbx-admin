"""Application factory for the PBX admin server.

The service currently routes/proxies to a small set of FreePBX hosts on Fly.io.
It is structured to grow into a control plane that launches, monitors, and
maintains PBX servers via the Fly.io API:

* ``config``      - environment-driven settings.
* ``db``          - SQLite access + schema/CLI wiring.
* ``auth``        - Cloudflare Access identity verification.
* ``repository``  - all SQL (servers, access control, audit log).
* ``metrics``     - upstream metrics URL building + reachability checks.
* ``proxy``       - reverse-proxy engine.
* ``blueprints``  - HTTP surface (control UI, gateway proxy). Future Fly.io
  automation should be added as a service module plus a dedicated blueprint.
"""

import secrets

from flask import Flask

from . import db
from .blueprints.control import control_bp
from .blueprints.gateway import gateway_bp
from .config import Config


def create_app(config_object=Config, overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)
    if overrides:
        app.config.update(overrides)

    if not app.config.get("SECRET_KEY"):
        app.logger.warning(
            "SESSION_SECRET is not set; generating an ephemeral secret. Sessions "
            "will not survive restarts and will break across multiple workers."
        )
        app.config["SECRET_KEY"] = secrets.token_hex(32)

    db.init_app(app)

    app.register_blueprint(control_bp, url_prefix=app.config["CONTROL_PREFIX"])
    app.register_blueprint(gateway_bp)

    return app
