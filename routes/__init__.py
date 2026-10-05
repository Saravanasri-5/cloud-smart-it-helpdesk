def register_blueprints(app):
    from routes.admin import bp as admin_bp
    from routes.api import bp as api_bp
    from routes.auth import bp as auth_bp
    from routes.main import bp as main_bp
    from routes.tickets import bp as tickets_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
