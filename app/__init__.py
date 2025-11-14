from pathlib import Path
import os

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()


def create_app(test_config: dict | None = None) -> Flask:
    """Application factory so tests can create isolated instances."""
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder=str(Path(__file__).resolve().parent.parent / "static"),
        template_folder=str(Path(__file__).resolve().parent.parent / "templates"),
    )

    default_db_path = Path(app.instance_path) / "app.db"
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", f"sqlite:///{default_db_path}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"

    from . import models  # noqa: F401  # ensure models are registered for migrations
    from .cli import register_cli
    from .api import api_bp
    from .views import pages_bp

    register_cli(app)
    app.register_blueprint(api_bp)
    app.register_blueprint(pages_bp)

    @app.get("/health")
    def healthcheck():
        return {"status": "ok"}

    return app
