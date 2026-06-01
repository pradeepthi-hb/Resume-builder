import os
from datetime import timedelta

from db_settings import get_sqlalchemy_database_uri, load_environment

load_environment()


def _parse_origins(raw_value):
    values = [origin.strip().strip("\"'") for origin in (raw_value or "").split(",")]
    normalized = []
    for origin in values:
        if not origin:
            continue
        if origin != "*":
            origin = origin.rstrip("/")
        if origin:
            normalized.append(origin)
    return normalized


LOCAL_DEV_ORIGIN_PATTERNS = [
    r"^https?://localhost(:\d+)?$",
    r"^https?://127\.0\.0\.1(:\d+)?$",
    r"^https?://\[::1\](:\d+)?$",
]

ENV_CORS_ORIGINS = _parse_origins(os.getenv("CORS_ALLOWED_ORIGINS", ""))
DEFAULT_CORS_ORIGINS = ENV_CORS_ORIGINS + [
    pattern for pattern in LOCAL_DEV_ORIGIN_PATTERNS if pattern not in ENV_CORS_ORIGINS
]

if not DEFAULT_CORS_ORIGINS:
    DEFAULT_CORS_ORIGINS = ["http://localhost:3000", *LOCAL_DEV_ORIGIN_PATTERNS]

class Config:

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "flask-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "THIS_IS_A_SUPER_LONG_32_CHAR_JWT_SECRET_KEY_123456")
    JWT_TOKEN_LOCATION = ["headers"]   
    JWT_COOKIE_CSRF_PROTECT = False    

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    SQLALCHEMY_DATABASE_URI = get_sqlalchemy_database_uri()
    CORS_ALLOWED_ORIGINS = DEFAULT_CORS_ORIGINS

    REDIS_URL = os.getenv("REDIS_URL", "")
    HIREYO_SESSION_TTL_SECONDS = int(os.getenv("HIREYO_SESSION_TTL_SECONDS", "1800"))
    HIREYO_SESSION_KEY_PREFIX = os.getenv("HIREYO_SESSION_KEY_PREFIX", "hireyo:session:")

    HIREYO_SHARED_SECRET = os.getenv("HIREYO_SHARED_SECRET", "")
    HIREYO_BUILDER_URL = os.getenv("HIREYO_BUILDER_URL", "")

    PARSER_API_URL = os.getenv("PARSER_API_URL", "http://localhost:8001")
    PARSER_CONNECT_TIMEOUT_SECONDS = float(os.getenv("PARSER_CONNECT_TIMEOUT_SECONDS", "5"))
    PARSER_READ_TIMEOUT_SECONDS = float(os.getenv("PARSER_READ_TIMEOUT_SECONDS", "45"))
    PARSER_MAX_RETRIES = int(os.getenv("PARSER_MAX_RETRIES", "2"))

