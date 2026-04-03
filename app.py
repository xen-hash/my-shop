"""
app.py – GadgetHub PH
======================
Application factory: configures Flask, extensions, and registers blueprints.
FIXED: Supabase-optimised connection pool + fast startup.
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
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # ── SUPABASE FIX: Use pgBouncer transaction-mode URL if available ──────
    # In Supabase dashboard → Settings → Database → Connection pooling
    # Use the "Transaction" mode URL (port 6543) for best performance on Render
    # Set env var SUPABASE_DB_URL to that URL to override DATABASE_URL
    supabase_url = os.environ.get("SUPABASE_DB_URL", "")
    if supabase_url:
        if supabase_url.startswith("postgres://"):
            supabase_url = supabase_url.replace("postgres://", "postgresql://", 1)
        db_url = supabase_url

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ── FIXED: Supabase-optimised pool settings ─────────────────────────────
    # Supabase free tier allows ~60 direct connections.
    # With pgBouncer (port 6543) you can use NullPool for serverless safety.
    is_sqlite = db_url.startswith("sqlite")
    if is_sqlite:
        # SQLite has no pool concept
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
    else:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            # CRITICAL: must be True for Supabase — connections go stale after
            # the Supabase idle timeout and need to be recycled automatically.
            "pool_pre_ping":    True,

            # Recycle connections every 5 minutes to avoid Supabase's idle
            # connection timeout (which is ~5 min on the free tier).
            "pool_recycle":     300,

            # Keep a small pool — Supabase free tier has limited connections.
            # If using pgBouncer URL (port 6543), you can raise this safely.
            "pool_size":        5,
            "max_overflow":     10,

            # Wait up to 10 s for a connection before raising an error.
            "pool_timeout":     10,

            # Silence the "pool size X exceeded" log spam.
            "pool_use_lifo":    True,

            # PostgreSQL-specific: keep connections alive at the TCP layer.
            "connect_args": {
                "connect_timeout":        10,
                "keepalives":             1,
                "keepalives_idle":        30,
                "keepalives_interval":    5,
                "keepalives_count":       3,
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
    # FIXED: Only run create_all + migrations if tables don't already exist.
    # On Supabase this avoids a slow schema-inspection round-trip on every
    # cold start after the tables have already been created.
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
    """
    Fast startup: check if the 'users' table exists first.
    Only run create_all() and migrations if it doesn't — avoids the slow
    full schema introspection on every Render cold start.
    """
    global _migrations_done
    if _migrations_done:
        return

    try:
        with db.engine.connect() as conn:
            # Quick existence check — very fast (single query)
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

        # Run migrations regardless (they're idempotent with IF NOT EXISTS)
        _run_migrations_once(db)

    except Exception as e:
        # SQLite fallback (dev) — always run create_all
        logger.warning(f"⚠️  Schema check failed ({e}), running create_all as fallback.")
        try:
            db.create_all()
            _run_migrations_once(db)
        except Exception as e2:
            logger.error(f"❌  DB init error: {e2}")
    finally:
        _migrations_done = True


def _run_migrations_once(db):
    """Idempotent ALTER TABLE migrations."""
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