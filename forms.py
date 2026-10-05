import re

from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, Optional, ValidationError
from models import CATEGORIES, PRIORITIES, ROLES, ROLE_LABELS, STATUSES, User

MAX_UPLOAD = 10 * 1024 * 1024
def valid_email(form, field):
    value = (field.data or "").strip()

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        raise ValidationError("Please enter a valid email address.")


def strong_password(form, field):
    value = field.data or ""
    if not (re.search(r"[A-Za-z]", value) and re.search(r"\d", value)):
        raise ValidationError("Password must contain at least one letter and one number.")


def _unique_email(email, exclude_id=None):
    existing = User.query.filter(User.email == (email or "").strip().lower()).first()
    if existing and existing.id != exclude_id:
        raise ValidationError("This email address is already registered.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), valid_email, Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign in")


class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email", validators=[DataRequired(), valid_email, Length(max=120)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    department = StringField("Department", validators=[Optional(), Length(max=100)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128), strong_password])
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password", "Passwords must match.")])
    submit = SubmitField("Create account")

    def validate_email(self, field):
        _unique_email(field.data)


class ProfileForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email", validators=[DataRequired(), valid_email, Length(max=120)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    department = StringField("Department", validators=[Optional(), Length(max=100)])
    submit = SubmitField("Save profile")

    def validate_email(self, field):
        _unique_email(field.data, current_user.id)


class PasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=8, max=128), strong_password])
    confirm = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("new_password", "Passwords must match.")])
    submit = SubmitField("Change password")


class TicketForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(min=5, max=200)])
    category = SelectField("Category", choices=[(c, c) for c in CATEGORIES], validators=[DataRequired()])
    priority = SelectField("Priority", choices=[(p, p) for p in PRIORITIES], default="Medium", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired(), Length(min=10, max=5000)])
    attachment = FileField("Screenshot / attachment", validators=[
        Optional(),
        FileAllowed(["png", "jpg", "jpeg", "pdf"], "Only PNG, JPG, JPEG or PDF files are allowed."),
        FileSize(max_size=MAX_UPLOAD, message="File must be 10 MB or smaller."),
    ])
    submit = SubmitField("Submit ticket")


class CommentForm(FlaskForm):
    body = TextAreaField("Comment", validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField("Add comment")


class AttachmentForm(FlaskForm):
    attachment = FileField("Attachment", validators=[
        DataRequired(),
        FileAllowed(["png", "jpg", "jpeg", "pdf"], "Only PNG, JPG, JPEG or PDF files are allowed."),
        FileSize(max_size=MAX_UPLOAD, message="File must be 10 MB or smaller."),
    ])
    submit = SubmitField("Upload")


class StatusForm(FlaskForm):
    status = SelectField("Status", choices=[(s, s) for s in STATUSES], validators=[DataRequired()])
    resolution = TextAreaField("Resolution details", validators=[Optional(), Length(max=5000)])
    submit = SubmitField("Update ticket")


class AssignForm(FlaskForm):
    assignee = SelectField("Assign to", coerce=int, validate_choice=False)
    submit = SubmitField("Assign")


class EmptyForm(FlaskForm):
    """CSRF-only form for POST actions (delete, toggle, logout)."""


class UserAdminForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email", validators=[DataRequired(), valid_email, Length(max=120)])
    role = SelectField("Role", choices=[(r, ROLE_LABELS[r]) for r in ROLES], validators=[DataRequired()])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    department = StringField("Department", validators=[Optional(), Length(max=100)])
    password = PasswordField("Password", validators=[Optional(), Length(min=8, max=128), strong_password])
    active = BooleanField("Account active", default=True)
    submit = SubmitField("Save user")

    def __init__(self, *args, user_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = user_id

    def validate_email(self, field):
        _unique_email(field.data, self.user_id)
