from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PipeForge"
    app_version: str = "0.1.0"
    metadata_database_url: str = "sqlite:///pipeforge_audit.db"
    default_batch_size: int = 500
    quarantine_directory: Path = Path("quarantine")
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    model_config = SettingsConfigDict(
        env_prefix="PIPEFORGE_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
