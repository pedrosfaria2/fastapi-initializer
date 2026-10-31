"""Application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the generator."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FastAPI Initializr"
    environment: str = "development"
    max_generated_files: int = 200
    max_zip_bytes: int = 5_000_000


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
