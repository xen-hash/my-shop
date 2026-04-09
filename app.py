"""
app.py – GadgetHub PH
======================
Application factory: configures Flask, extensions, and registers blueprints.
Works with Neon PostgreSQL on Render free tier.
- No blocking DB calls at startup — gunicorn binds instantly
- db.create_all() + migrations run lazily on first request
- pool_pre_ping handles stale connection recovery automatically
"""

import os
import logging
from datetime import timedelta
from flask import Flask
from flask_login import LoginManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

_tables_checked = False


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    # ── Configuration ─────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

    app.config["SESSION_PERMANENT"]          = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=1)
    app.config["REMEMBER_COOKIE_SECURE"]   = os.environ.get("FLASK_ENV") == "production"
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"

    db_url = os.environ.get("DATABASE_URL", "sqlite:///gadgethub.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"]        = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    is_sqlite = db_url.startswith("sqlite")
    if is_sqlite:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
    else:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping":  True,
            "pool_recycle":   300,
            "pool_size":      2,
            "max_overflow":   3,
            "pool_timeout":   30,
            "pool_use_lifo":  True,
            # NOTE: sslmode is NOT here — it's already in the Neon URL (?sslmode=require)
            # Adding it here too causes psycopg2 to throw a conflict error on startup
            "connect_args": {
                "connect_timeout":     10,
                "keepalives":          1,
                "keepalives_idle":     10,
                "keepalives_interval": 2,
                "keepalives_count":    5,
            },
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
    from email_utils import mail
    db.init_app(app)
    mail.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view             = "auth.login"
    login_manager.login_message          = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

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

    # ── Lazy table init ───────────────────────────────────────
    # Runs once on the very first request — keeps startup instant.
    # Retries automatically if the first attempt fails.
    @app.before_request
    def ensure_tables():
        global _tables_checked
        if _tables_checked:
            return
        _tables_checked = True
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db.create_all()
            _run_migrations(db)
            logger.info("✅  DB tables ready.")
        except Exception as e:
            logger.warning(f"⚠️  DB init on first request failed (non-fatal): {e}")
            _tables_checked = False  # retry on next request

    logger.info("✅  GadgetHub PH app started successfully.")
    return app


def _run_migrations(db):
    """Safely add any missing columns. Each ALTER is wrapped individually."""
    try:
        with db.engine.connect() as conn:
            for stmt in [
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS password VARCHAR(256)",
                "ALTER TABLE users ALTER COLUMN password DROP NOT NULL",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(120)",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS facebook_id VARCHAR(120)",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS picture VARCHAR(500)",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancel_reason TEXT",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL",
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url_2 VARCHAR(500)",
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url_3 VARCHAR(500)",
            ]:
                try:
                    conn.execute(db.text(stmt))
                except Exception:
                    pass  # column already exists — safe to ignore
            conn.commit()
        logger.info("✅  Migrations done.")
    except Exception as e:
        logger.warning(f"⚠️  Migration warning (non-fatal): {e}")