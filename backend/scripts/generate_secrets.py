#!/usr/bin/env python
"""P10-S01: create the Docker secret files for docker-compose.prod.yml.

    python backend/scripts/generate_secrets.py [--out secrets] [--db-user his_app] [--db-name his]

Writes high-entropy values (secrets.token_urlsafe) to one file per secret:

    db_password, database_url, jwt_access_secret_key, jwt_refresh_secret_key,
    qr_signing_secret_key                       <- generated
    smtp_password, abdm_client_secret           <- created empty; fill in by hand

Existing files are NEVER overwritten (replacing db_password would lock you out of
the database; replacing a JWT key signs everyone out), unless you pass
--rotate NAME. Values are not printed. The output directory must stay out of
git and backups of it must be encrypted.
"""
import argparse
import os
import secrets
import stat
import sys
from pathlib import Path

GENERATED = ("db_password", "jwt_access_secret_key", "jwt_refresh_secret_key", "qr_signing_secret_key")
MANUAL = ("smtp_password", "abdm_client_secret")


def write_secret(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")
    # Docker bind-mounts secret files with their host mode, and the container's
    # user is not the host user, so the file must be world-readable; the
    # directory (0700) is what keeps other host users out.
    path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="secrets", help="output directory (default: ./secrets)")
    parser.add_argument("--db-user", default="his_app")
    parser.add_argument("--db-name", default="his")
    parser.add_argument("--db-host", default="postgres")
    parser.add_argument("--rotate", action="append", default=[], metavar="NAME", help="regenerate this secret")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        out.chmod(0o700)
    except OSError:
        pass  # Windows: rely on the profile ACLs

    created, kept = [], []

    def put(name: str, value: str) -> None:
        path = out / name
        if path.exists() and name not in args.rotate:
            kept.append(name)
            return
        write_secret(path, value)
        created.append(name)

    for name in GENERATED:
        put(name, secrets.token_urlsafe(48 if name != "db_password" else 32))
    password = (out / "db_password").read_text(encoding="utf-8")
    # token_urlsafe uses only [A-Za-z0-9_-], all legal unescaped in a URL password.
    put("database_url", f"postgresql+asyncpg://{args.db_user}:{password}@{args.db_host}:5432/{args.db_name}")
    if "db_password" in args.rotate:
        write_secret(out / "database_url", f"postgresql+asyncpg://{args.db_user}:{password}@{args.db_host}:5432/{args.db_name}")
        print("NOTE: db_password rotated - also run ALTER USER in PostgreSQL, or the app cannot connect.", file=sys.stderr)
    for name in MANUAL:
        put(name, "")

    if created:
        print("created: " + ", ".join(created))
    if kept:
        print("kept (already exist): " + ", ".join(kept))
    empty = [n for n in MANUAL if not (out / n).read_text(encoding="utf-8")]
    if empty:
        print("fill in if you use them: " + ", ".join(empty))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
