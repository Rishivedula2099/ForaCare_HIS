import ipaddress
import os
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# P10-S01: values that must never guard a real deployment.
_WEAK_DB_PASSWORDS = {
    "", "forahis", "postgres", "password", "passw0rd", "admin", "root", "changeme", "change-me",
    "secret", "123456", "12345678", "letmein",
}
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _is_strong_secret(value: str) -> bool:
    lowered = value.lower()
    return (
        len(value) >= 32
        and len(set(value)) >= 10
        and "local-dev-only" not in lowered
        and "change-me" not in lowered
        and "changeme" not in lowered
    )


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / .env."""

    # P10-S01: besides the environment, each setting can be supplied as a file
    # named after it (e.g. `$SECRETS_DIR/jwt_access_secret_key`) - the Docker /
    # Kubernetes secrets convention - so credentials need never sit in an env
    # file or `docker inspect`. Precedence: init args > environment > .env > files.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        secrets_dir=os.environ.get("SECRETS_DIR") or None,
    )

    environment: str = "local"
    debug: bool = False

    app_name: str = "ForaCare HIS API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    cors_origins: str = "http://localhost:3000"
    # P10-S01: Host headers the API answers to (comma separated; "*" = any,
    # local only) and the reverse proxies whose X-Forwarded-* headers are
    # believed (CIDRs; the peer must be inside one for the headers to count).
    allowed_hosts: str = "*"
    trusted_proxy_cidrs: str = ""
    # Reject request bodies larger than this (413) before they are read. Must
    # cover the largest upload (file_upload_max_bytes) plus multipart framing.
    max_request_body_bytes: int = 6 * 1024 * 1024

    # P9-B01: in-process rate limits (app/core/rate_limit.py), per client IP.
    rate_limit_enabled: bool = True
    rate_limit_login_per_minute: int = 10
    rate_limit_sensitive_per_minute: int = 10
    rate_limit_public_per_minute: int = 30

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

    # P10-B01: creates the shared-password demo tenant/users/patients when
    # migrations run. Local development only - rejected in every other
    # environment (see the validator below).
    seed_demo_data: bool = False

    # P10-B01: how long an account-activation / password-reset link stays valid.
    user_token_activation_hours: int = 72
    user_token_reset_minutes: int = 30
    # Origin used to build activation/reset links (falls back to public_base_url).
    frontend_base_url: str = ""

    # P10-B01: outbound email for activation / reset links (stdlib smtplib).
    # Blank host = no transport: links are then only surfaced to the operator
    # (bootstrap CLI) or, in local dev, as `debug_token` in the API response.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = ""
    smtp_starttls: bool = True

    # P10-S02: observability and operational controls.
    # Bearer token for GET /internal/metrics. Outside local the endpoint does not
    # exist unless this is set (it is never reachable through the public proxy).
    metrics_token: SecretStr = SecretStr("")
    # Incoming-webhook URL (Slack/Teams/Mattermost style `{"text": ...}`) for
    # security and error alerts. It embeds a credential, so it is a secret.
    alert_webhook_url: SecretStr = SecretStr("")
    alert_cooldown_seconds: int = 900
    # Readiness fails when the storage volume has less free space than this.
    storage_min_free_mb: int = 200
    # Abnormal-authentication detector (app/core/security_monitor.py): a
    # `security_alert` is raised when, inside the window, one client IP causes
    # this many failed sign-ins, tries this many distinct usernames, or one
    # username collects this many failures.
    auth_alert_window_seconds: int = 300
    auth_alert_failed_logins_per_ip: int = 20
    auth_alert_distinct_users_per_ip: int = 8
    auth_alert_failed_logins_per_user: int = 6

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
    def _reject_unsafe_configuration_outside_local(self) -> "Settings":
        """P8-B04 / P10-S01: the built-in dev defaults are public (they are in
        this repo), so any non-local environment must override every one and
        be configured for the production topology (HTTPS behind a trusted
        proxy). Every problem is reported at once so an operator fixes the
        whole file in one pass; startup fails if there are any."""
        if self.is_local:
            return self
        problems = self.production_config_problems()
        if problems:
            raise ValueError(
                f"Unsafe configuration for ENVIRONMENT={self.environment!r}:\n  - " + "\n  - ".join(problems)
            )
        return self

    def production_config_problems(self) -> list[str]:
        problems: list[str] = []
        if self.debug:
            problems.append("DEBUG must be false")
        if self.db_echo:
            # echo logs every statement with its bound values (PHI, hashes).
            problems.append("DB_ECHO must be false (it logs patient data)")
        if self.seed_demo_data:
            problems.append("SEED_DEMO_DATA must be false (it creates shared-password demo logins)")

        secrets_by_name = {
            "JWT_ACCESS_SECRET_KEY": self.jwt_access_secret_key,
            "JWT_REFRESH_SECRET_KEY": self.jwt_refresh_secret_key,
            "QR_SIGNING_SECRET_KEY": self.qr_signing_secret_key,
        }
        for name, value in secrets_by_name.items():
            if not _is_strong_secret(value):
                problems.append(
                    f"{name} must be a real secret of at least 32 characters "
                    '(generate: python -c "import secrets; print(secrets.token_urlsafe(48))")'
                )
        if len(set(secrets_by_name.values())) != len(secrets_by_name):
            problems.append("JWT_ACCESS_SECRET_KEY, JWT_REFRESH_SECRET_KEY and QR_SIGNING_SECRET_KEY must all differ")
        if self.jwt_algorithm not in {"HS256", "HS384", "HS512"}:
            problems.append("JWT_ALGORITHM must be HS256, HS384 or HS512")
        if self.access_token_expire_minutes > 60:
            problems.append("ACCESS_TOKEN_EXPIRE_MINUTES must be 60 or less")
        if self.refresh_token_expire_days > 30:
            problems.append("REFRESH_TOKEN_EXPIRE_DAYS must be 30 or less")

        problems.extend(self._database_problems())
        problems.extend(self._origin_problems())
        problems.extend(self._proxy_problems())

        if self.session_cookie_samesite.lower() not in {"lax", "strict", "none"}:
            problems.append("SESSION_COOKIE_SAMESITE must be lax, strict or none")
        if self.cookie_domain and "://" in self.cookie_domain:
            problems.append("COOKIE_DOMAIN must be a bare domain, not a URL")
        if not self.rate_limit_enabled:
            problems.append("RATE_LIMIT_ENABLED must be true")
        if self.abdm_adapter not in {"mock", "sandbox", "production"}:
            problems.append("ABDM_ADAPTER must be mock, sandbox or production")
        if self.abdm_adapter != "mock" and not (
            self.abdm_client_id and self.abdm_client_secret.get_secret_value()
        ):
            problems.append(f"ABDM_CLIENT_ID and ABDM_CLIENT_SECRET are required when ABDM_ADAPTER={self.abdm_adapter}")
        if self.abdm_mock_simulate:
            problems.append("ABDM_MOCK_SIMULATE must be empty (it fakes gateway failures)")
        webhook = self.alert_webhook_url.get_secret_value()
        if webhook and not webhook.startswith("https://"):
            problems.append("ALERT_WEBHOOK_URL must be an https URL")
        if self.alert_cooldown_seconds < 60:
            problems.append("ALERT_COOLDOWN_SECONDS must be at least 60 (alerts must not flood the channel)")
        if self.smtp_host and not self.smtp_from:
            problems.append("SMTP_FROM is required when SMTP_HOST is set")
        if self.smtp_username and not self.smtp_password.get_secret_value():
            problems.append("SMTP_PASSWORD is required when SMTP_USERNAME is set")
        if not os.path.isabs(self.file_storage_root):
            problems.append("FILE_STORAGE_ROOT must be an absolute path on a persistent volume")
        if self.max_request_body_bytes < self.file_upload_max_bytes:
            problems.append("MAX_REQUEST_BODY_BYTES must be at least FILE_UPLOAD_MAX_BYTES")
        return problems

    def _database_problems(self) -> list[str]:
        from sqlalchemy.engine import make_url

        try:
            url = make_url(self.database_url)
        except Exception:  # noqa: BLE001
            return ["DATABASE_URL is not a valid URL"]
        problems = []
        password = url.password or ""
        if password.lower() in _WEAK_DB_PASSWORDS or len(password) < 12:
            problems.append("DATABASE_URL must carry a strong password (12+ characters, not a default)")
        if not url.host or url.host in {"localhost", "127.0.0.1"} and self.environment.lower() == "production":
            problems.append("DATABASE_URL must point at the production database host, not localhost")
        return problems

    def _origin_problems(self) -> list[str]:
        problems = []
        origins = self.cors_origin_list
        if not origins:
            problems.append("CORS_ORIGINS must list the https origin(s) of the web app")
        for origin in origins:
            parsed = urlparse(origin)
            if origin == "*" or parsed.scheme != "https" or not parsed.hostname:
                problems.append(f"CORS_ORIGINS entry {origin!r} must be an https origin (no wildcards)")
            elif parsed.hostname in _LOOPBACK_HOSTS or parsed.path not in {"", "/"}:
                problems.append(f"CORS_ORIGINS entry {origin!r} must be a public https origin without a path")
        for name, value in (("PUBLIC_BASE_URL", self.public_base_url), ("FRONTEND_BASE_URL", self.frontend_base_url)):
            if name == "PUBLIC_BASE_URL" and not value:
                problems.append("PUBLIC_BASE_URL is required (printed into document QR codes)")
            elif value and urlparse(value).scheme != "https":
                problems.append(f"{name} must be an https URL")
        hosts = self.allowed_host_list
        if not hosts or "*" in hosts or any("://" in h for h in hosts):
            problems.append("ALLOWED_HOSTS must list the exact host name(s) served (no '*', no scheme)")
        return problems

    def _proxy_problems(self) -> list[str]:
        cidrs = [c.strip() for c in self.trusted_proxy_cidrs.split(",") if c.strip()]
        if not cidrs:
            return [
                "TRUSTED_PROXY_CIDRS is required: the API only accepts requests relayed over HTTPS by "
                "your reverse proxy (e.g. the Docker network range 172.16.0.0/12)"
            ]
        problems = []
        for cidr in cidrs:
            try:
                network = ipaddress.ip_network(cidr, strict=False)
            except ValueError:
                problems.append(f"TRUSTED_PROXY_CIDRS entry {cidr!r} is not a valid CIDR")
                continue
            if network.prefixlen == 0:
                problems.append("TRUSTED_PROXY_CIDRS must not trust the whole internet (0.0.0.0/0)")
        return problems

    def __repr_args__(self):
        """Keep credentials out of repr()/str() and of pydantic's validation
        error text (P9-B04); `database_url` carries the DB password."""
        masked = {
            "jwt_access_secret_key", "jwt_refresh_secret_key", "qr_signing_secret_key", "database_url",
            "metrics_token", "alert_webhook_url",
        }
        for name, value in super().__repr_args__():
            yield name, "***" if name in masked else value

    @property
    def database_password(self) -> str:
        from sqlalchemy.engine import make_url

        try:
            return make_url(self.database_url).password or ""
        except Exception:
            return ""

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def trusted_proxy_networks(self) -> list:
        return [
            ipaddress.ip_network(c.strip(), strict=False)
            for c in self.trusted_proxy_cidrs.split(",")
            if c.strip()
        ]

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_local(self) -> bool:
        return self.environment.lower() == "local"

    @property
    def cookie_secure(self) -> bool:
        return not self.is_local

    @property
    def https_enforced(self) -> bool:
        return not self.is_local


@lru_cache
def get_settings() -> Settings:
    return Settings()
