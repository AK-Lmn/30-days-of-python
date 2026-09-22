from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FLAGFORGE_",
        env_file=".env",
        extra="ignore",
    )

    api_title: str = "FlagForge API"
    api_version: str = "0.1.0"
    api_description: str = "Dynamic feature flag and remote configuration management REST engine."
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    debug: bool = False
    storage_file: str = "data/flags.json"

    def get_storage_path(self) -> Path:
        return Path(self.storage_file)


settings = Settings()
