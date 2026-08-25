"""
Centralized application configuration.

Why pydantic-settings: it reads environment variables (and a .env file)
into a typed, validated Python object. Every other module imports `settings`
from here instead of calling os.environ.get(...) scattered across the code.
This is the single source of truth for configuration.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str

    # --- Auth ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- App ---
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Cached so we only parse environment variables once per process,
    not on every import / request.
    """
    return Settings()


settings = get_settings()
