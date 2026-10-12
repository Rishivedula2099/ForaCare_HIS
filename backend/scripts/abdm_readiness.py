"""Check this environment's ABDM configuration against a rollout stage.

    python scripts/abdm_readiness.py [--target sandbox|production] [--live]

Exits 0 when every requirement for the target stage is met, 1 otherwise.
`--live` additionally creates a real gateway session (no patient data is
sent). Secrets are never printed.
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import Settings  # noqa: E402
from app.modules.abdm.factory import get_abdm_adapter  # noqa: E402
from app.modules.abdm.readiness import ReadinessCheck, evaluate_readiness, is_ready  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", choices=["sandbox", "production"], default="production")
    parser.add_argument("--live", action="store_true", help="also attempt a real gateway session")
    args = parser.parse_args()

    try:
        settings = Settings()
    except ValueError as exc:  # e.g. non-local environment with public dev secrets
        print(f"[FAIL] configuration invalid: {exc}")
        return 1

    live = None
    if args.live and settings.abdm_adapter == args.target:  # a mock "connection" proves nothing
        live = asyncio.run(get_abdm_adapter().check_connection()).connected

    checks: list[ReadinessCheck] = evaluate_readiness(settings, args.target, live_connected=live)
    for c in checks:
        print(f"[{'ok' if c.ok else 'FAIL'}] {c.name}: {c.detail}")
    ready = is_ready(checks)
    print(f"\nABDM {args.target} readiness: {'READY' if ready else 'NOT READY'}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
