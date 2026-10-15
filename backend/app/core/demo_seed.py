"""P10-B01: single switch for prototype/demo fixtures.

Demo data (shared-password logins, sample patients, demo tenants) must never
reach a real deployment. Migrations that create it call `demo_seed_enabled()`;
it is true only when SEED_DEMO_DATA=true AND ENVIRONMENT=local (Settings
refuses to start with SEED_DEMO_DATA=true in any other environment).
"""
from app.core.config import get_settings


def demo_seed_enabled() -> bool:
    settings = get_settings()
    return settings.seed_demo_data and settings.is_local
