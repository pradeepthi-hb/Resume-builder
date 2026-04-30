import os
from pathlib import Path
from urllib.parse import quote_plus

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
_ENV_LOADED = False


def load_environment():
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    if load_dotenv is not None:
        for env_path in (BACKEND_DIR / ".env", REPO_ROOT / ".env"):
            if env_path.exists():
                load_dotenv(env_path, override=False)

    _ENV_LOADED = True


def _require_env(name):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def get_db_name():
    load_environment()
    return _require_env("DB_NAME")


def get_mysql_config(include_database=True, allow_local_infile=False):
    load_environment()

    config = {
        "host": _require_env("DB_HOST"),
        "port": int(_require_env("DB_PORT")),
        "user": _require_env("DB_USER"),
        "password": os.getenv("DB_PASSWORD", ""),
    }

    if allow_local_infile:
        config["allow_local_infile"] = True

    if include_database:
        config["database"] = get_db_name()

    return config


def get_sqlalchemy_database_uri():
    config = get_mysql_config(include_database=True)
    user = quote_plus(config["user"])
    password = quote_plus(config["password"])
    host = config["host"]
    port = config["port"]
    database = config["database"]
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
