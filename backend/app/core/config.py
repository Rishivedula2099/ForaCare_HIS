from functools import lru_cache

from pydantic import SecretStr, model_validator
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

    # P3-B06: HMAC key signing each OPD check-in QR reference, so a code's
    # authenticity can be checked structurally (mismatched/tampered
    # signature) before ever touching the database.
    # P7-B05: public origin printed into document QR codes (e.g.
    # https://his.example.com). Empty = use the host the request came in on.
    public_base_url: str = ""
    qr_signing_secret_key: str = "local-dev-only-insecure-qr-secret-change-me"

    cookie_domain: str | None = None
    session_cookie_samesite: str = "lax"

    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60

    # P7-B03: Chromium refuses to start as root / without user namespaces
    # (typical in containers) unless its sandbox is disabled. Safe here
    # because it only renders our own server-generated, autoescaped HTML.
    pdf_chromium_no_sandbox: bool = False

    file_storage_root: str = "./storage"
    file_upload_max_bytes: int = 5 * 1024 * 1024

    # P5-B04: selects the `PaymentAdapter` implementation
    # (app/modules/billing/payment_adapter.py). "mock" (the only
    # implementation today) settles every payment/refund immediately and
    # locally; a future production gateway integration registers its own
    # name there without any change to app/modules/billing/service.py.
    payment_adapter: str = "mock"

    # P8-B01: selects the `AbdmAdapter` implementation
    # (app/modules/abdm/factory.py): "mock" (offline), "sandbox" (NHA
    # sandbox) or "production". base_url defaults per mode when blank.
    abdm_adapter: str = "mock"
    abdm_base_url: str = ""
    abdm_client_id: str = ""
    # P8-B04: never committed - supplied only through the environment (or an
    # untracked .env). SecretStr keeps it out of repr()/logs/tracebacks;
    # read it with .get_secret_value() at the single point of use.
    abdm_client_secret: SecretStr = SecretStr("")
    abdm_timeout_seconds: float = 10.0
    abdm_max_retries: int = 2
    abdm_retry_backoff_seconds: float = 0.5
    # Mock adapter only: "" (normal) | "timeout" | "unavailable" | "rejected"
    # | "flaky" (every other OTP request fails, so a retry succeeds) - lets
    # the UI's pending/failed/timeout/retry states be exercised offline.
    abdm_mock_simulate: str = ""

    @model_validator(mode="after")
    def _reject_insecure_secrets_outside_local(self) -> "Settings":
        """P8-B04: the built-in dev defaults are public (they're in this
        repo), so any non-local environment must override every one."""
        if self.is_local:
            return self
        insecure = [
            name
            for name in (
                "jwt_access_secret_key",
                "jwt_refresh_secret_key",
                "qr_signing_secret_key",
            )
            if "local-dev-only" in getattr(self, name)
        ]
        if insecure:
            raise ValueError(
                f"ENVIRONMENT={self.environment!r} requires real values for: "
                + ", ".join(name.upper() for name in insecure)
            )
        return self

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
