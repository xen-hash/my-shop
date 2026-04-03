"""
app.py – GadgetHub PH
======================
Application factory: configures Flask, extensions, and registers blueprints.
"""

import os
import logging
from flask import Flask
from flask_login import LoginManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Track whether migrations have already run this process lifetime
_migrations_done = False


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    # ── Configuration ─────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

    db_url = os.environ.get("DATABASE_URL", "sqlite:///gadgethub.db")
    # Render gives postgres:// but SQLAlchemy needs postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"]  = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": False,   # avoid extra ping on every connection
        "pool_recycle":  1800,    # recycle every 30 min instead of 5
        "pool_size":     3,
        "max_overflow":  2,
    }

    # OAuth
    app.config["GOOGLE_CLIENT_ID"]       = os.environ.get("GOOGLE_CLIENT_ID", "")
    app.config["GOOGLE_CLIENT_SECRET"]   = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    app.config["FACEBOOK_CLIENT_ID"]     = os.environ.get("FACEBOOK_CLIENT_ID", "")
    app.config["FACEBOOK_CLIENT_SECRET"] = os.environ.get("FACEBOOK_CLIENT_SECRET", "")

    # Mail
    app.config["MAIL_SERVER"]         = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"]           = int(os.environ.get("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"]        = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    app.config["MAIL_USERNAME"]       = os.environ.get("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"]       = os.environ.get("MAIL_PASSWORD", "")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get(
        "MAIL_DEFAULT_SENDER", app.config["MAIL_USERNAME"]
    )

    # ── Extensions ────────────────────────────────────────────
    from models import db, User
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view          = "auth.login"
    login_manager.login_message       = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ── DB setup + one-time migrations ────────────────────────
    with app.app_context():
        db.create_all()
        _run_migrations_once(db)

    # ── Blueprints ────────────────────────────────────────────
    from routes.shop   import shop_bp
    from routes.auth   import auth_bp
    from routes.cart   import cart_bp
    from routes.orders import orders_bp
    from routes.admin  import admin_bp

    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)

    logger.info("✅  GadgetHub PH app started successfully.")
    return app


def _run_migrations_once(db):
    """
    Runs ALTER TABLE migrations only once per process lifetime.
    The global flag prevents repeated DB round-trips on every request.
    """
    global _migrations_done
    if _migrations_done:
        return

    try:
        with db.engine.connect() as conn:
            conn.execute(db.text(
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancel_reason TEXT"
            ))
            conn.execute(db.text(
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL"
            ))
            conn.commit()
        logger.info("✅  Migrations done.")
    except Exception as e:
        logger.warning(f"⚠️  Migration warning (non-fatal): {e}")
    finally:
        _migrations_done = True   # never run again this process