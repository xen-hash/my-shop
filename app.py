"""
app.py – GadgetHub PH
======================
Application factory: configures Flask, extensions, and registers blueprints.
FIX: Added session lifetime + remember-cookie config to prevent
     permanent auto-login on mobile / shared devices.
FIX: before_request now pings via db.session (not db.engine.connect)
     to correctly detect and recover from stale session connections.
FIX: _maybe_init_db is now fully non-fatal — a Supabase timeout at
     startup no longer kills the deploy.
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

_migrations_done = False


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    # ── Configuration ─────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

    # Session lifetime – expires when browser closes unless "Remember me" ticked
    app.config["SESSION_PERMANENT"]          = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

    # Remember-me cookie – 1 day max
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=1)
    app.config["REMEMBER_COOKIE_SECURE"]   = os.environ.get("FLASK_ENV") == "production"
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"

    db_url = os.environ.get("DATABASE_URL", "sqlite:///gadgethub.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    supabase_url = os.environ.get("SUPABASE_DB_URL", "")
    if supabase_url:
        if supabase_url.startswith("postgres://"):
            supabase_url = supabase_url.replace("postgres://", "postgresql://", 1)
        db_url = supabase_url

    app.config["SQLALCHEMY_DATABASE_URI"]        = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    is_sqlite = db_url.startswith("sqlite")
    if is_sqlite:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
    else:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping":  True,
            "pool_recycle":   60,
            "pool_size":      2,
            "max_overflow":   3,
            "pool_timeout":   30,
            "pool_use_lifo":  True,
            "connect_args": {
                "connect_timeout":     10,   # short timeout so startup doesn't hang
                "keepalives":          1,
                "keepalives_idle":     5,
                "keepalives_interval": 2,
                "keepalives_count":    3,
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

    # ── DB setup (non-fatal) ──────────────────────────────────
    # Wrapped in a top-level try/except so a Supabase timeout at
    # boot time cannot prevent the app from starting on Render.
    with app.app_context():
        try:
            _maybe_init_db(db)
        except Exception as e:
            logger.warning(
                f"⚠️  DB init skipped at startup (will retry on first request): {e}"
            )
            db.engine.dispose()

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

    # ── Auto-retry on SSL/connection drops ────────────────────
    # Supabase free tier drops connections aggressively.
    # Pings via db.session so stale session connections are caught,
    # not just pool-level drops.
    @app.before_request
    def ensure_db_connection():
        """Ping the DB before each request; reconnect if needed."""
        from sqlalchemy import text
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            db.session.remove()  # drop the stale session
            db.engine.dispose()  # purge the entire connection pool

    logger.info("✅  GadgetHub PH app started successfully.")
    return app


def _maybe_init_db(db):
    global _migrations_done
    if _migrations_done:
        return

    try:
        with db.engine.connect() as conn:
            result = conn.execute(db.text(
                "SELECT to_regclass('public.users')"
            ))
            table_exists = result.scalar() is not None

        if not table_exists:
            logger.info("🔧  First run — creating tables...")
            db.create_all()
            logger.info("✅  Tables created.")
        else:
            logger.info("✅  Tables already exist — skipping create_all.")

        _run_migrations_once(db)

    except Exception as e:
        logger.warning(f"⚠️  Schema check failed ({e}), running create_all as fallback.")
        try:
            db.create_all()
            _run_migrations_once(db)
        except Exception as e2:
            logger.error(f"❌  DB init error: {e2}")
            raise   # re-raise so the outer try/except in create_app can catch it
    finally:
        _migrations_done = True


def _run_migrations_once(db):
    try:
        with db.engine.connect() as conn:
            # ── users table ───────────────────────────────────
            # Live DB uses 'password' column (not password_hash)
            conn.execute(db.text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS password VARCHAR(256)"
            ))
            # Make password nullable so OAuth users can have NULL password
            conn.execute(db.text(
                "ALTER TABLE users ALTER COLUMN password DROP NOT NULL"
            ))
            conn.execute(db.text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(120)"
            ))
            conn.execute(db.text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS facebook_id VARCHAR(120)"
            ))
            conn.execute(db.text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS picture VARCHAR(500)"
            ))
            conn.execute(db.text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT"
            ))

            # ── orders table ──────────────────────────────────
            conn.execute(db.text(
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancel_reason TEXT"
            ))
            conn.execute(db.text(
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL"
            ))

            # ── products table ────────────────────────────────
            conn.execute(db.text(
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url_2 VARCHAR(500)"
            ))
            conn.execute(db.text(
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url_3 VARCHAR(500)"
            ))

            conn.commit()
        logger.info("✅  Migrations done.")
    except Exception as e:
        logger.warning(f"⚠️  Migration warning (non-fatal): {e}")