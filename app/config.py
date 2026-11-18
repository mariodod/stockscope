"""Application settings, sourced from environment variables or .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "dev"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./stockscope.db"
    admin_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
