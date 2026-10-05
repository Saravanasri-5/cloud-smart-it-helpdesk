import os

import click
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError

from config import DEFAULT_SECRET, DevelopmentConfig, config_map
from extensions import csrf, db, login_manager
from models import CATEGORIES, PRIORITIES, ROLE_LABELS, STATUSES, User


def create_app(config_name=None):
    app = Flask(__name__)
    config_name = config_name or os.environ.get("APP_ENV", "development")
    app.config.from_object(config_map.get(config_name, DevelopmentConfig))

    if config_name == "production" and app.config["SECRET_KEY"] == DEFAULT_SECRET:
        raise RuntimeError("Set a strong SECRET_KEY environment variable for production.")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return jsonify(error="Authentication required."), 401
        from flask import flash
        flash(login_manager.login_message, login_manager.login_message_category)
        return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))

    from routes import register_blueprints
    register_blueprints(app)

    register_template_helpers(app)
    register_error_handlers(app)
    register_security_headers(app)
    register_cli(app)

    with app.app_context():
        db.create_all()
        bootstrap_admin()

    return app


def bootstrap_admin():
    """Create the first administrator when the database has no users."""
    if User.query.first() is not None:
        return
    admin = User(
        name=os.environ.get("ADMIN_NAME", "System Administrator"),
        email=os.environ.get("ADMIN_EMAIL", "admin@helpdesk.local").lower(),
        role="admin",
        department="IT",
    )
    admin.set_password(os.environ.get("ADMIN_PASSWORD", "Admin@12345"))
    db.session.add(admin)
    db.session.commit()


def register_template_helpers(app):
    @app.template_filter("dt")
    def fmt_datetime(value, fmt="%d %b %Y, %H:%M"):
        return value.strftime(fmt) if value else "—"

    @app.template_filter("filesize")
    def fmt_filesize(value):
        value = value or 0
        if value < 1024:
            return f"{value} B"
        if value < 1024 * 1024:
            return f"{value / 1024:.1f} KB"
        return f"{value / 1024 / 1024:.1f} MB"

    @app.context_processor
    def inject_constants():
        return {
            "CATEGORIES": CATEGORIES,
            "PRIORITIES": PRIORITIES,
            "STATUSES": STATUSES,
            "ROLE_LABELS": ROLE_LABELS,
        }


def register_error_handlers(app):
    def respond(code, title, message):
        if request.path.startswith("/api/"):
            return jsonify(error=message), code
        return render_template("errors/error.html", code=code, title=title, message=message), code

    @app.errorhandler(400)
    def bad_request(_):
        return respond(400, "Bad request", "The request could not be understood.")

    @app.errorhandler(CSRFError)
    def csrf_error(_):
        return respond(400, "Session expired", "Your form session expired or is invalid. Please go back, refresh the page and try again.")

    @app.errorhandler(403)
    def forbidden(_):
        return respond(403, "Access denied", "You do not have permission to access this resource.")

    @app.errorhandler(404)
    def not_found(_):
        return respond(404, "Page not found", "The page or record you requested does not exist.")

    @app.errorhandler(413)
    def too_large(_):
        return respond(413, "File too large", "Uploaded files must be 10 MB or smaller.")

    @app.errorhandler(500)
    def server_error(_):
        db.session.rollback()
        return respond(500, "Server error", "Something went wrong on our side. Please try again later.")


def register_security_headers(app):
    @app.after_request
    def headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'",
        )
        if request.endpoint and request.endpoint != "static":
            response.headers.setdefault("Cache-Control", "no-store")
        return response


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed")
    def seed_command():
        """Load sample users and tickets."""
        from seed import run_seed
        run_seed()


app = create_app()

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)))
