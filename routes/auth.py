import time
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from forms import EmptyForm, LoginForm, PasswordForm, ProfileForm, RegisterForm
from models import User

bp = Blueprint("auth", __name__)

MAX_ATTEMPTS = 5
LOCK_SECONDS = 300
_attempts = {}


def _attempt_key(email):
    return f"{request.remote_addr}:{(email or '').lower()}"


def _is_locked(key):
    record = _attempts.get(key)
    if not record:
        return False
    count, stamp = record
    if time.time() - stamp > LOCK_SECONDS:
        _attempts.pop(key, None)
        return False
    return count >= MAX_ATTEMPTS


def _register_failure(key):
    count, _ = _attempts.get(key, (0, 0))
    _attempts[key] = (count + 1, time.time())


def _safe_next(target):
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    return target


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        key = _attempt_key(email)
        if _is_locked(key):
            flash("Too many failed attempts. Please try again in a few minutes.", "danger")
            return render_template("login.html", form=form), 429
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(form.password.data):
            if not user.active:
                flash("Your account has been deactivated. Contact an administrator.", "danger")
                return render_template("login.html", form=form)
            _attempts.pop(key, None)
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(_safe_next(request.args.get("next")) or url_for("main.dashboard"))
        _register_failure(key)
        flash("Invalid email or password.", "danger")
    return render_template("login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(name=form.name.data.strip(), email=form.email.data.strip().lower(),
                    phone=(form.phone.data or "").strip() or None,
                    department=(form.department.data or "").strip() or None, role="user")
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully. Please sign in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    if EmptyForm().validate_on_submit():
        logout_user()
        flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    profile_form = ProfileForm(obj=current_user)
    password_form = PasswordForm()
    if request.method == "POST":
        which = request.form.get("form")
        if which == "profile" and profile_form.validate_on_submit():
            current_user.name = profile_form.name.data.strip()
            current_user.email = profile_form.email.data.strip().lower()
            current_user.phone = (profile_form.phone.data or "").strip() or None
            current_user.department = (profile_form.department.data or "").strip() or None
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("auth.profile"))
        if which == "password" and password_form.validate_on_submit():
            if not current_user.check_password(password_form.current_password.data):
                flash("Current password is incorrect.", "danger")
            else:
                current_user.set_password(password_form.new_password.data)
                db.session.commit()
                flash("Password changed successfully.", "success")
                return redirect(url_for("auth.profile"))
    return render_template("profile.html", profile_form=profile_form, password_form=password_form,
                           submitted=request.form.get("form") if request.method == "POST" else None)
