import os
from datetime import timedelta

from db_settings import get_sqlalchemy_database_uri, load_environment

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_environment()

class Config:

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "flask-secret-key"
    JWT_SECRET_KEY = "THIS_IS_A_SUPER_LONG_32_CHAR_JWT_SECRET_KEY_123456"
    JWT_TOKEN_LOCATION = ["headers"]   
    JWT_COOKIE_CSRF_PROTECT = False    

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    SQLALCHEMY_DATABASE_URI = get_sqlalchemy_database_uri()
    HIREYO_SHARED_SECRET = os.getenv("HIREYO_SHARED_SECRET", "")
    HIREYO_BUILDER_URL = os.getenv("HIREYO_BUILDER_URL", "")
    HIREYO_STORAGE_DIR = os.getenv("HIREYO_STORAGE_DIR", os.path.join(BASE_DIR, "storage", "hireyo_sessions"))

