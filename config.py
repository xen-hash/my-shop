import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "gadgethub-super-secret-key-change-in-prod")

    # ── Database ──────────────────────────────────────────────────────────────
    BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Flask-Login ───────────────────────────────────────────────────────────
    LOGIN_VIEW       = "auth.login"
    LOGIN_MESSAGE    = "Please log in to access this page."
    LOGIN_MSG_CAT    = "warning"

    # ── Stripe (optional) ─────────────────────────────────────────────────────
    STRIPE_SECRET_KEY      = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")

    # ── Pagination ────────────────────────────────────────────────────────────
    PRODUCTS_PER_PAGE = 12

    # ── Admin ─────────────────────────────────────────────────────────────────
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@gadgethub.ph")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}