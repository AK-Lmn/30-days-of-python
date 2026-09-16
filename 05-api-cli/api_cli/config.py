import os
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS: float = 30.0
DEFAULT_DB_NAME: str = "api_cli.db"
USER_AGENT: str = "Universal-API-CLI/0.1.0"
DEFAULT_MAX_HISTORY: int = 500
SUPPORTED_FORMATS = ("json", "table", "raw", "headers")
SUPPORTED_EXPORTS = ("json", "csv", "md", "txt")


def get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def get_database_path() -> Path:
    env_db = os.getenv("API_CLI_DB")
    if env_db:
        return Path(env_db)
    return get_base_dir() / DEFAULT_DB_NAME
