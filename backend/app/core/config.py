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

    jwt_access_secret_key: str = "local-dev-only-insecure-access-secret-change-me"
    jwt_refresh_secret_key: str = "local-dev-only-insecure-refresh-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 3

    cookie_domain: str | None = None
    session_cookie_samesite: str = "lax"

    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_local(self) -> bool:
        return self.environment.lower() == "local"

    @property
    def cookie_secure(self) -> bool:
        return not self.is_local


@lru_cache
def get_settings() -> Settings:
    return Settings()
