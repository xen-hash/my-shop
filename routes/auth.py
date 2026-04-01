"""
routes/auth.py – GadgetHub PH
==============================
Authentication blueprint: Register, Login, Logout, Profile.
"""

from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, request
)
from flask_login import (
    login_user, logout_user,
    login_required, current_user
)
from models import db, User
from forms import RegisterForm, LoginForm, UpdateProfileForm

auth_bp = Blueprint("auth", __name__)


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
            name    = form.name.data.strip(),
            email   = form.email.data.lower().strip(),
            address = form.address.data.strip() if form.address.data else None,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)
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
            login_user(user, remember=True)
            flash(f"Welcome back, {user.name}! 👋", "success")

            # Redirect to the page the user originally wanted
            next_page = request.args.get("next")
            return redirect(next_page or url_for("shop.index"))

        flash("Incorrect email or password. Please try again.", "danger")

    return render_template("login.html", form=form, title="Log In")


# ─────────────────────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = UpdateProfileForm(obj=current_user)

    if form.validate_on_submit():
        current_user.name    = form.name.data.strip()
        current_user.address = form.address.data.strip()
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("auth.profile"))

    return render_template("profile.html", form=form, title="My Profile")