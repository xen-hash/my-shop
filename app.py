"""
app.py – GadgetHub PH
======================
Application factory: configures Flask, extensions, and registers blueprints.
FIX: Added session lifetime + remember-cookie config to prevent
     permanent auto-login on mobile / shared devices.
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

    # ── FIX: Session lifetime – session expires when browser closes
    #         unless user explicitly ticks "Remember me".
    app.config["SESSION_PERMANENT"]        = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

    # ── FIX: Remember-me cookie – only 1 day even when ticked.
    #         Default Flask-Login value is 365 days which caused the
    #         "mobile always shows admin" bug.
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

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    is_sqlite = db_url.startswith("sqlite")
    if is_sqlite:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
    else:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            # pool_pre_ping: tests every connection before use —
            # if the connection was dropped by Supabase it gets
            # replaced automatically instead of raising an error.
            "pool_pre_ping":    True,
            "pool_recycle":     120,   # recycle connections every 2 min (Supabase drops idle ones)
            "pool_size":        3,     # keep fewer persistent connections on free tier
            "max_overflow":     5,
            "pool_timeout":     20,
            "pool_use_lifo":    True,
            "connect_args": {
                "connect_timeout":        15,
                "keepalives":             1,
                "keepalives_idle":        10,   # send keepalive after 10s idle
                "keepalives_interval":    5,
                "keepalives_count":       5,
                "sslmode":                "require",
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
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view             = "auth.login"
    login_manager.login_message          = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ── DB setup ─────────────────────────────────────────────
    with app.app_context():
        _maybe_init_db(db)

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
    finally:
        _migrations_done = True


def _run_migrations_once(db):
    try:
        with db.engine.connect() as conn:
            # ── users table ───────────────────────────────────
            conn.execute(db.text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(256)"
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