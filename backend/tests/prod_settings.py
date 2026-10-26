"""A fully valid production configuration for tests (P10-S01). Tests override
single fields to prove each one is enforced."""
import secrets

PROD = dict(
    environment="production",
    debug=False,
    database_url="postgresql+asyncpg://his_app:Zq7-pT4mXw9LkR2vNc8@db.internal:5432/his",
    jwt_access_secret_key=secrets.token_urlsafe(48),
    jwt_refresh_secret_key=secrets.token_urlsafe(48),
    qr_signing_secret_key=secrets.token_urlsafe(48),
    cors_origins="https://his.example.com",
    public_base_url="https://his.example.com",
    frontend_base_url="https://his.example.com",
    allowed_hosts="his.example.com,localhost",
    trusted_proxy_cidrs="172.16.0.0/12",
    file_storage_root="/app/storage",
    # pinned so the test process environment (conftest turns rate limiting off) cannot leak in
    rate_limit_enabled=True,
    seed_demo_data=False,
    db_echo=False,
    abdm_adapter="mock",
    abdm_mock_simulate="",
    session_cookie_samesite="lax",
    smtp_host="",
)


def prod_kwargs(**overrides):
    return {**PROD, **overrides, "_env_file": None}
