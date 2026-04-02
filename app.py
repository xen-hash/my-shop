"""
app.py – GadgetHub PH (application factory)

FIX: Route files live in the project ROOT (auth.py, shop.py, etc.)
     NOT in a routes/ sub-package.  Import them directly.
"""

from flask import Flask
from config import config
from models import db, bcrypt
from flask_login import LoginManager
import os


def create_app(env=None):
    app = Flask(__name__)

    env = env or os.environ.get("FLASK_ENV", "default")
    app.config.from_object(config[env])

    db.init_app(app)
    bcrypt.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view             = "auth.login"
    login_manager.login_message          = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return db.session.get(User, int(user_id))

    # ── Blueprints ────────────────────────────────────────────
    # IMPORTANT: import from root, not from routes.*
    from auth   import auth_bp
    from shop   import shop_bp
    from cart   import cart_bp
    from orders import orders_bp
    from admin  import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True)