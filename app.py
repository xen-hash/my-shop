"""
app.py – GadgetHub PH
======================
Application factory: configures Flask, extensions, and registers blueprints.
"""

import os
import logging
from flask import Flask
from flask_login import LoginManager


# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# APPLICATION FACTORY
# ─────────────────────────────────────────────────────────────

def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    # ── Configuration ─────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///gadgethub.db"
    )
    # Render's Postgres URLs start with postgres:// — SQLAlchemy needs postgresql://
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config[
            "SQLALCHEMY_DATABASE_URI"
        ].replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # OAuth (optional – only needed if social login is configured)
    app.config["GOOGLE_CLIENT_ID"]     = os.environ.get("GOOGLE_CLIENT_ID", "")
    app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    app.config["FACEBOOK_CLIENT_ID"]     = os.environ.get("FACEBOOK_CLIENT_ID", "")
    app.config["FACEBOOK_CLIENT_SECRET"] = os.environ.get("FACEBOOK_CLIENT_SECRET", "")

    # Mail (used by email_utils)
    app.config["MAIL_SERVER"]   = os.environ.get("MAIL_SERVER",   "smtp.gmail.com")
    app.config["MAIL_PORT"]     = int(os.environ.get("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"]  = os.environ.get("MAIL_USE_TLS",  "true").lower() == "true"
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get(
        "MAIL_DEFAULT_SENDER",
        app.config["MAIL_USERNAME"]
    )

    # ── Extensions ────────────────────────────────────────────
    from models import db, User
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ── Database setup + auto-migrations ──────────────────────
    with app.app_context():
        db.create_all()
        _run_migrations()

    # ── Blueprints ────────────────────────────────────────────
    from shop   import shop_bp
    from auth   import auth_bp
    from cart   import cart_bp
    from orders import orders_bp
    from admin  import admin_bp

    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)

    logger.info("✅  GadgetHub PH app started successfully.")
    return app


# ─────────────────────────────────────────────────────────────
# AUTO-MIGRATIONS
# Runs on every startup — all statements use IF NOT EXISTS
# so they are completely safe to re-run.
# ─────────────────────────────────────────────────────────────

def _run_migrations():
    try:
        with db.engine.connect() as conn:
            # Migration 1: add cancel_reason to orders
            conn.execute(db.text("""
                ALTER TABLE orders
                ADD COLUMN IF NOT EXISTS cancel_reason TEXT
            """))

            # Migration 2: add is_deleted for soft deletes
            conn.execute(db.text("""
                ALTER TABLE orders
                ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL
            """))
            conn.commit()
            logger.info("✅  Migrations: cancel_reason + is_deleted columns ready.")
    except Exception as e:
        logger.warning(f"⚠️  Migration warning (non-fatal): {e}")