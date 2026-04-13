"""
app.py – GadgetHub PH
======================
Lean factory — zero DB calls at startup or on requests.
Tables and migrations already exist on Neon. pool_pre_ping
handles dead connections silently per-query.
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


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    # ── Config ────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    app.config["SESSION_PERMANENT"]          = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
    app.config["REMEMBER_COOKIE_DURATION"]   = timedelta(days=1)
    app.config["REMEMBER_COOKIE_SECURE"]     = os.environ.get("FLASK_ENV") == "production"
    app.config["REMEMBER_COOKIE_HTTPONLY"]   = True
    app.config["REMEMBER_COOKIE_SAMESITE"]   = "Lax"

    db_url = os.environ.get("DATABASE_URL", "sqlite:///gadgethub.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"]        = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if db_url.startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
    else:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping":  True,   # silently replaces dead connections per-query
            "pool_recycle":   300,
            "pool_size":      2,
            "max_overflow":   2,
            "pool_timeout":   20,
            "pool_use_lifo":  True,
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

    logger.info("✅  GadgetHub PH started.")
    return app