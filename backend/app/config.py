from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    stake_session_token: str | None = None
    stake_username: str | None = None
    stake_password: str | None = None
    fmp_api_key: str | None = None
    database_url: str = "postgresql+asyncpg://stake:stake@db:5432/stake_dashboard"
    redis_url: str = "redis://redis:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
