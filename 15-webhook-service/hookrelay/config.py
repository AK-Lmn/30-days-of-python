from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HookRelay"
    app_version: str = "0.1.0"
    database_url: str = "sqlite+aiosqlite:///hookrelay.db"
    default_timeout_seconds: float = 10.0
    default_max_retries: int = 3
    default_backoff_base_seconds: float = 2.0
    max_payload_size_bytes: int = 10 * 1024 * 1024
    server_host: str = "127.0.0.1"
    server_port: int = 8000

    model_config = SettingsConfigDict(
        env_prefix="HOOKRELAY_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
