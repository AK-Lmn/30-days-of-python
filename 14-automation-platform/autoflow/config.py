from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AutoFlow Platform"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./autoflow.db"
    cors_origins: list[str] = ["*"]
    scheduler_interval_seconds: float = 2.0
    action_timeout_seconds: float = 30.0
    max_concurrent_runs: int = 10

    model_config = SettingsConfigDict(
        env_prefix="AUTOFLOW_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
