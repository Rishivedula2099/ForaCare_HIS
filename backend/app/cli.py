"""P10-B01: operator command line.

    python -m app.cli bootstrap-admin \
        --tenant-name "Sunrise Hospitals" --tenant-code SUNRISE \
        --facility-name "Sunrise General" --facility-code SUN-MAIN-01 \
        --username jane.admin --email jane@example.org --full-name "Jane Doe"

Creates (or reuses) the tenant and facility, creates the first administrator
with NO password, and prints a one-time activation link. Add `--role
SUPER_ADMIN` for a platform operator. Run it inside the backend container:
    docker compose exec backend python -m app.cli bootstrap-admin ...
"""
import argparse
import asyncio
import sys


# Heavy imports (database engine, models) are deferred into the commands: they
# read Settings at import time, and `check-config` must be able to report an
# invalid configuration instead of dying in an import traceback.


async def _bootstrap(args: argparse.Namespace) -> int:
    from app.core.database import SessionLocal
    from app.core.exceptions import AppError
    from app.modules.auth import mailer, user_tokens
    from app.modules.auth.provisioning import provision_admin

    async with SessionLocal() as db:
        try:
            result = await provision_admin(
                db,
                tenant_name=args.tenant_name,
                tenant_code=args.tenant_code,
                facility_name=args.facility_name,
                facility_code=args.facility_code,
                username=args.username,
                email=args.email,
                full_name=args.full_name,
                role_code=args.role,
            )
        except AppError as exc:
            print(f"error: {exc.message}", file=sys.stderr)
            return 1

    link = user_tokens.build_link(user_tokens.ACTIVATION, result.activation_token)
    emailed = False
    if args.send_email:
        emailed = await mailer.send_email(
            to=result.user.email,
            subject="Activate your ForaCare HIS account",
            body=f"Hello {result.user.full_name},\n\nChoose your password to activate your account:\n\n{link}\n",
        )
    print(f"tenant   : {result.tenant.code} ({'created' if result.tenant_created else 'existing'})")
    print(f"facility : {result.facility.facility_code} ({'created' if result.facility_created else 'existing'})")
    print(f"user     : {result.user.username} <{result.user.email}> role={args.role}")
    if emailed:
        print("An activation email was sent.")
    else:
        print("Give this one-time activation link to the administrator (it is not stored anywhere):")
        print(link)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    boot = sub.add_parser("bootstrap-admin", help="Create a tenant/facility and its first administrator")
    boot.add_argument("--tenant-name", required=True)
    boot.add_argument("--tenant-code", required=True)
    boot.add_argument("--facility-name", required=True)
    boot.add_argument("--facility-code", required=True)
    boot.add_argument("--username", required=True)
    boot.add_argument("--email", required=True)
    boot.add_argument("--full-name", required=True)
    boot.add_argument("--role", default="HOSPITAL_ADMIN", choices=["HOSPITAL_ADMIN", "SUPER_ADMIN"])
    boot.add_argument("--send-email", action="store_true", help="Email the link instead of printing it")

    sub.add_parser(
        "check-config",
        help="Validate the configuration for production without starting the API (exit 1 if unsafe)",
    )
    args = parser.parse_args()

    if args.command == "check-config":
        return _check_config()

    async def run() -> int:
        from app.core.database import dispose_engine

        try:
            return await _bootstrap(args)
        finally:
            await dispose_engine()

    return asyncio.run(run())


def _check_config() -> int:
    """Run before a deployment: `docker compose run --rm backend python -m app.cli check-config`."""
    from pydantic import ValidationError

    from app.core.config import Settings

    try:
        settings = Settings()
    except ValidationError as exc:
        print("CONFIGURATION IS NOT SAFE TO START:", file=sys.stderr)
        for error in exc.errors():
            print(str(error["msg"]).removeprefix("Value error, "), file=sys.stderr)
        return 1
    if settings.is_local:
        problems = settings.production_config_problems()
        print(f"ENVIRONMENT={settings.environment}: development defaults are allowed here.")
        print(f"Production readiness: {len(problems)} item(s) would block a production start.")
        for problem in problems:
            print(f"  - {problem}")
        return 0
    print(f"ENVIRONMENT={settings.environment}: configuration is valid for production.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
