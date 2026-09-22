from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///nexuspg.db"
    app_name: str = "NexusPG Feature Flag Platform"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False
    echo_sql: bool = False
    pool_size: int = 10
    max_overflow: int = 20


settings = Settings()
