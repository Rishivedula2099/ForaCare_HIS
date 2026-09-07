from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"
    debug: bool = False

    app_name: str = "ForaCare HIS API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    cors_origins: str = "http://localhost:3000"

    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "postgresql+asyncpg://forahis:forahis@localhost:5432/forahis"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    jwt_secret_key: str = "local-dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_local(self) -> bool:
        return self.environment.lower() == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
