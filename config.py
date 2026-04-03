import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "gadgethub-super-secret-key-change-in-prod")
    WTF_CSRF_SECRET_KEY = os.environ.get("SECRET_KEY", "gadgethub-super-secret-key-change-in-prod")

    # ── Database ──────────────────────────────────────────────────────────────
    BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
    )
    # Render gives postgres:// but SQLAlchemy needs postgresql://
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── OAuth – Google ────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # ── OAuth – Facebook ──────────────────────────────────────────────────────
    FACEBOOK_CLIENT_ID     = os.environ.get("FACEBOOK_CLIENT_ID", "")
    FACEBOOK_CLIENT_SECRET = os.environ.get("FACEBOOK_CLIENT_SECRET", "")

    # ── Admin ─────────────────────────────────────────────────────────────────
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@gadgethub.ph")

    # ── Pagination ────────────────────────────────────────────────────────────
    PRODUCTS_PER_PAGE = 12

    # ── Flask-Mail ────────────────────────────────────────────────────────────
    MAIL_SERVER         = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT           = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS        = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_USE_SSL        = False
    MAIL_USERNAME       = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD       = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER",
        "GadgetHub PH <noreply@gadgethub.ph>"
    )


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}