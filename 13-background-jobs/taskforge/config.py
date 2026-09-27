from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TaskForge"
    environment: str = "development"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000

    database_url: str = "sqlite+aiosqlite:///./taskforge.db"

    default_queue: str = "default"
    default_max_retries: int = 3
    default_retry_delay_seconds: float = 5.0
    default_timeout_seconds: float = 60.0

    worker_poll_interval_seconds: float = 0.5
    worker_heartbeat_interval_seconds: float = 5.0
    worker_timeout_threshold_seconds: float = 30.0

    scheduler_poll_interval_seconds: float = 1.0

    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
