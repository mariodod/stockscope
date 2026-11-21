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
    stale_after_days: int = 90
    quote_retention_days: int = 5 * 365
    history_years: int = 5
    redis_url: str = ""
    fmp_api_key: str = ""
    sec_user_agent: str = "Stockscope research contact@example.com"
    quote_refresh_cron: str = "0 22 * * 1-5"
    fundamentals_refresh_cron: str = "0 3 * * 0"
    universe_refresh_cron: str = "0 4 * * 0"
    history_refresh_cron: str = "0 5 * * 0"
    dividends_refresh_cron: str = "0 6 * * 0"
    filings_refresh_cron: str = "0 7 * * *"
    prune_cron: str = "0 8 1 * *"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
