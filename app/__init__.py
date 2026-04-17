"""Application factory for the Instagram non-followers tracker."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask

from .models import db
from .routes import bp as main_bp


def create_app(config: dict | None = None) -> Flask:
    """Create and configure the Flask application.

    Parameters
    ----------
    config:
        Optional overrides for Flask config. Mainly useful for tests.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Make sure the instance folder exists so SQLite can write its file there.
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    default_db_path = Path(app.instance_path) / "tracker.sqlite"
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", f"sqlite:///{default_db_path}"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16 MB upload cap.
    )
    if config:
        app.config.update(config)

    db.init_app(app)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app
