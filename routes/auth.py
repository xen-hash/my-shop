"""
auth.py – GadgetHub PH
==============================
Authentication blueprint: Register, Login, Logout, Profile.
Social Login: Google OAuth2, Facebook OAuth2 (via Authlib).

FIXES:
- Logout now clears Flask session AND invalidates the OAuth token cache,
  so Google's account-chooser prompt appears on the very next login.
- login_user(remember=False) everywhere — session expires on browser close
  unless the user ticks "Remember me".
- Google redirect forces account selection via prompt=select_account.
"""

from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, request, session, current_app, make_response
)
from flask_login import (
    login_user, logout_user,
    login_required, current_user
)
from models import db, User
from forms import RegisterForm, LoginForm, UpdateProfileForm

auth_bp = Blueprint("auth", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# OAuth helper – lazy-init so missing keys don't crash the app
# ─────────────────────────────────────────────────────────────────────────────

def get_oauth():
    from authlib.integrations.flask_client import OAuth
    oauth = OAuth(current_app)

    if current_app.config.get("GOOGLE_CLIENT_ID"):
        oauth.register(
            name="google",
            client_id     = current_app.config["GOOGLE_CLIENT_ID"],
            client_secret = current_app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs = {"scope": "openid email profile"},
        )

    if current_app.config.get("FACEBOOK_CLIENT_ID"):
        oauth.register(
            name="facebook",
            client_id     = current_app.config["FACEBOOK_CLIENT_ID"],
            client_secret = current_app.config["FACEBOOK_CLIENT_SECRET"],
            access_token_url  = "https://graph.facebook.com/oauth/access_token",
            authorize_url     = "https://www.facebook.com/dialog/oauth",
            api_base_url      = "https://graph.facebook.com/",
            client_kwargs     = {"scope": "email public_profile"},
        )

    return oauth


# ─────────────────────────────────────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("shop.index"))

    form = RegisterForm()

    if form.validate_on_submit():
        user = User(
            name  = form.name.data.strip(),
            email = form.email.data.lower().strip(),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user, remember=False)
        flash(f"Welcome to GadgetHub, {user.name}! 🎉", "success")
        return redirect(url_for("shop.index"))

    return render_template("register.html", form=form, title="Create Account")


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("shop.index"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(
            email=form.email.data.lower().strip()
        ).first()

        if user and user.check_password(form.password.data):
            remember = getattr(form, 'remember', None)
            remember_me = remember.data if remember else False
            login_user(user, remember=remember_me)
            flash(f"Welcome back, {user.name}! 👋", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("shop.index"))

        flash("Incorrect email or password. Please try again.", "danger")

    google_enabled   = bool(current_app.config.get("GOOGLE_CLIENT_ID"))
    facebook_enabled = bool(current_app.config.get("FACEBOOK_CLIENT_ID"))

    return render_template(
        "login.html",
        form=form,
        title="Log In",
        google_enabled=google_enabled,
        facebook_enabled=facebook_enabled,
    )


# ─────────────────────────────────────────────────────────────────────────────
# LOGOUT  ← FIX: fully clears session + kills OAuth cache + expires cookies
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()

    # Wipe every Flask session key
    session.clear()

    # Build response that also deletes the remember-me cookie
    response = make_response(redirect(url_for("auth.login")))
    response.delete_cookie("remember_token")       # Flask-Login remember cookie
    response.delete_cookie("session")              # Flask session cookie

    # Tell the browser not to cache this page so "Back" can't restore the session
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"]        = "no-cache"
    response.headers["Expires"]       = "0"

    flash("You have been logged out.", "info")
    return response


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = UpdateProfileForm(obj=current_user)

    if form.validate_on_submit():
        current_user.name = form.name.data.strip()
        if hasattr(current_user, 'address') and form.address.data is not None:
            current_user.address = form.address.data.strip()
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("auth.profile"))

    return render_template("profile.html", form=form, title="My Profile")


# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE OAUTH  ← FIX: prompt=select_account forces the account chooser
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/login/google")
def google_login():
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        flash("Google login is not configured yet.", "warning")
        return redirect(url_for("auth.login"))

    oauth = get_oauth()
    redirect_uri = url_for("auth.google_callback", _external=True)

    # FIX: prompt=select_account  →  forces Google to show the account picker
    #       even when the user is still signed into a Google account in the
    #       browser.  Without this, Google silently reuses the last account.
    return oauth.google.authorize_redirect(
        redirect_uri,
        prompt="select_account"
    )


@auth_bp.route("/login/google/callback")
def google_callback():
    try:
        oauth    = get_oauth()
        token    = oauth.google.authorize_access_token()

        # Try getting userinfo from token first, then fallback to userinfo endpoint
        userinfo = token.get("userinfo")
        if not userinfo:
            import requests as _req
            resp     = oauth.google.get("https://openidconnect.googleapis.com/v1/userinfo",
                                        token=token)
            userinfo = resp.json()

        email = userinfo.get("email")
        name  = userinfo.get("name") or (email.split("@")[0] if email else "User")

        if not email:
            raise ValueError("Google did not return an email address.")

        return _social_login(email=email, name=name)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Google OAuth error: {e}", exc_info=True)
        flash(f"Google login failed: {str(e)}", "danger")
        return redirect(url_for("auth.login"))


# ─────────────────────────────────────────────────────────────────────────────
# FACEBOOK OAUTH
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/login/facebook")
def facebook_login():
    if not current_app.config.get("FACEBOOK_CLIENT_ID"):
        flash("Facebook login is not configured yet.", "warning")
        return redirect(url_for("auth.login"))
    oauth = get_oauth()
    redirect_uri = url_for("auth.facebook_callback", _external=True)
    return oauth.facebook.authorize_redirect(redirect_uri)


@auth_bp.route("/login/facebook/callback")
def facebook_callback():
    try:
        oauth = get_oauth()
        oauth.facebook.authorize_access_token()
        resp = oauth.facebook.get("me?fields=id,name,email")
        info = resp.json()
        email = info.get("email") or f"fb_{info['id']}@facebook.local"
        return _social_login(email=email, name=info.get("name", "Facebook User"))
    except Exception as e:
        flash("Facebook login failed. Please try again.", "danger")
        return redirect(url_for("auth.login"))


# ─────────────────────────────────────────────────────────────────────────────
# Shared social-login helper
# ─────────────────────────────────────────────────────────────────────────────

def _social_login(email: str, name: str):
    """Find-or-create a user from a social provider, then log them in."""
    user = User.query.filter_by(email=email.lower()).first()
    if not user:
        user = User(
            name          = name,
            email         = email.lower(),
            password_hash = None,   # OAuth users have no password
        )
        db.session.add(user)
        db.session.commit()
        flash(f"Welcome to GadgetHub, {user.name}! 🎉", "success")
    else:
        flash(f"Welcome back, {user.name}! 👋", "success")

    login_user(user, remember=False)
    return redirect(url_for("shop.index"))