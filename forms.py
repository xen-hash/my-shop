"""
forms.py – GadgetHub PH
=======================
WTForms form classes for user authentication.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, ValidationError
)
from models import User


class RegisterForm(FlaskForm):
    name = StringField("Full Name", validators=[
        DataRequired(),
        Length(min=2, max=120, message="Name must be 2–120 characters.")
    ])
    email = StringField("Email Address", validators=[
        DataRequired(),
        Email(message="Enter a valid email address.")
    ])
    password = PasswordField("Password", validators=[
        DataRequired(),
        Length(min=6, message="Password must be at least 6 characters.")
    ])
    confirm_password = PasswordField("Confirm Password", validators=[
        DataRequired(),
        EqualTo("password", message="Passwords must match.")
    ])
    address = TextAreaField("Shipping Address (optional)", validators=[])
    submit = SubmitField("Create Account")

    def validate_email(self, field):
        """Ensure the email is not already registered."""
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError("That email is already registered. Please log in.")


class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[
        DataRequired(),
        Email(message="Enter a valid email address.")
    ])
    password = PasswordField("Password", validators=[
        DataRequired()
    ])
    submit = SubmitField("Log In")


class UpdateProfileForm(FlaskForm):
    name = StringField("Full Name", validators=[
        DataRequired(),
        Length(min=2, max=120)
    ])
    address = TextAreaField("Shipping Address", validators=[])
    submit = SubmitField("Save Changes")