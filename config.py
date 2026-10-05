import os
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DEFAULT_SECRET = "dev-secret-change-me"


def _database_uri():
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    user = quote_plus(os.environ.get("DB_USER", "helpdesk_user"))
    password = quote_plus(os.environ.get("DB_PASSWORD", "HelpdeskPass@123"))
    host = os.environ.get("DB_HOST", "127.0.0.1")
    port = os.environ.get("DB_PORT", "3306")
    name = os.environ.get("DB_NAME", "helpdesk_db")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"


def _upload_folder():
    folder = os.environ.get("UPLOAD_FOLDER", "static/uploads")
    return folder if os.path.isabs(folder) else os.path.join(BASE_DIR, folder)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET)
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    UPLOAD_FOLDER = _upload_folder()
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_TIME_LIMIT = 8 * 3600
    PER_PAGE = 10


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "1") == "1"
    REMEMBER_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "1") == "1"


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
