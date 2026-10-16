#!/usr/bin/env python3
"""P10-S02: operational checks for a ForaCare HIS deployment.

Run from cron every few minutes (or from any monitoring agent). Standard library
only, so it works on the host without the app's virtualenv.

    python infra/ops/ops_check.py \
        --api https://his.example.org --backup-dir /opt/foracare/backups \
        --storage-dir /var/lib/docker/volumes/foracare_his_prod_his_file_storage/_data \
        --cert-host his.example.org --alert

Checks (each is OK / WARN / CRIT):

  api_ready        GET /api/v1/health/ready - database, migrations, storage
  backup_fresh     newest backup is recent, last run did not fail
  backup_integrity newest backup has a non-empty dump and checksums
  backup_verified  a restore test passed recently
  disk             free space on the backup and storage volumes
  tls_cert         days until the TLS certificate expires
  auth_activity    (needs --metrics-url) NEW security alerts, abnormal failed-login
                   volume, unhandled errors and 5xx since the previous run

Exit status follows the Nagios convention: 0 OK, 1 WARN, 2 CRIT.

`--alert` posts to $ALERT_WEBHOOK_URL (incoming-webhook JSON `{"text": ...}`) only
when a check CHANGES state (OK -> bad, bad -> worse, bad -> OK), tracked in
`--state-file`, so a standing problem pages once, not every five minutes. Messages
name checks and counts only - never data.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

OK, WARN, CRIT = "OK", "WARN", "CRIT"
EXIT_CODE = {OK: 0, WARN: 1, CRIT: 2}
RANK = {OK: 0, WARN: 1, CRIT: 2}


@dataclass
class Result:
    name: str
    status: str
    message: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(text: str) -> datetime | None:
    text = text.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- api


def check_api_ready(
    base_url: str, *, timeout: float = 5.0, verify_tls: bool = True, host_header: str | None = None
) -> Result:
    url = base_url.rstrip("/") + "/api/v1/health/ready"
    context = None if verify_tls else ssl._create_unverified_context()  # noqa: S323 - opt-in, for self-signed test stacks
    request = urllib.request.Request(url)
    if host_header:  # reach the proxy by address while presenting the public host name
        request.add_header("Host", host_header)
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context):  # noqa: S310
            pass
        return Result("api_ready", OK, "all readiness checks pass")
    except urllib.error.HTTPError as exc:
        if exc.code == 503:
            try:
                checks = json.loads(exc.read().decode("utf-8", "replace"))["data"]["checks"]
                failing = ", ".join(f"{n}:{c.get('reason', 'fail')}" for n, c in checks.items() if c.get("status") != "ok")
            except Exception:  # noqa: BLE001
                failing = "unknown"
            return Result("api_ready", CRIT, f"not ready ({failing})")
        return Result("api_ready", CRIT, f"unexpected HTTP {exc.code}")
    except (urllib.error.URLError, socket.timeout, ConnectionError, ssl.SSLError, OSError) as exc:
        return Result("api_ready", CRIT, f"unreachable ({type(exc).__name__})")


# ------------------------------------------------------------------------ backups


def _backups(backup_dir: Path) -> list[Path]:
    return sorted(p for p in backup_dir.glob("forahis_*T*Z") if p.is_dir()) if backup_dir.is_dir() else []


def check_backup_fresh(backup_dir: Path, *, max_age_hours: float, now: datetime | None = None) -> Result:
    now = now or _utcnow()
    if not backup_dir.is_dir():
        return Result("backup_fresh", CRIT, f"backup directory {backup_dir} does not exist")
    failure = backup_dir / ".last_failure"
    success = backup_dir / ".last_success"
    failed_at = None
    if failure.exists():
        parts = failure.read_text(encoding="utf8").split()
        failed_at = _parse_utc(parts[0]) if parts else None
        stage = parts[1] if len(parts) > 1 else "backup"
    succeeded_at = _parse_utc(success.read_text(encoding="utf8")) if success.exists() else None
    if failed_at and (not succeeded_at or failed_at > succeeded_at):
        return Result("backup_fresh", CRIT, f"the last backup run FAILED at {failed_at:%Y-%m-%d %H:%M}Z (stage: {stage})")

    backups = _backups(backup_dir)
    if not backups:
        return Result("backup_fresh", CRIT, "no backups exist")
    newest = _parse_utc(backups[-1].name.removeprefix("forahis_"))
    if newest is None:
        return Result("backup_fresh", WARN, f"cannot read the timestamp of {backups[-1].name}")
    age = now - newest
    if age > timedelta(hours=max_age_hours):
        return Result("backup_fresh", CRIT, f"newest backup is {age.total_seconds() / 3600:.1f}h old (limit {max_age_hours:g}h)")
    return Result("backup_fresh", OK, f"newest backup {age.total_seconds() / 3600:.1f}h old")


def check_backup_integrity(backup_dir: Path) -> Result:
    backups = _backups(backup_dir)
    if not backups:
        return Result("backup_integrity", CRIT, "no backups exist")
    latest = backups[-1]
    dump = latest / "db.dump"
    if not dump.exists() or dump.stat().st_size == 0:
        return Result("backup_integrity", CRIT, f"{latest.name}: db.dump is missing or empty")
    if not (latest / "SHA256SUMS").exists() or not (latest / "manifest.json").exists():
        return Result("backup_integrity", CRIT, f"{latest.name}: checksums or manifest missing")
    return Result("backup_integrity", OK, f"{latest.name} has a dump, manifest and checksums")


def check_backup_verified(backup_dir: Path, *, max_age_days: float, now: datetime | None = None) -> Result:
    now = now or _utcnow()
    marker = backup_dir / ".last_verified"
    verified = _parse_utc(marker.read_text(encoding="utf8")) if marker.exists() else None
    if verified is None:
        return Result("backup_verified", WARN, "no restore test has ever passed (run infra/backup/verify.sh)")
    age = now - verified
    if age > timedelta(days=max_age_days):
        return Result("backup_verified", WARN, f"last restore test was {age.days} days ago (limit {max_age_days:g})")
    return Result("backup_verified", OK, f"restore test passed {age.days} day(s) ago")


# --------------------------------------------------------------------------- disk


def check_disk(label: str, path: Path | None, *, min_free_pct: float) -> Result:
    name = f"disk_{label}"
    if path is None:
        return Result(name, OK, "not configured (skipped)")
    if not path.exists():
        return Result(name, CRIT, f"{path} does not exist")
    usage = shutil.disk_usage(path)
    free_pct = usage.free / usage.total * 100
    msg = f"{free_pct:.0f}% free ({usage.free / 1e9:.1f} GB)"
    if free_pct < min_free_pct:
        return Result(name, CRIT, msg + f", below {min_free_pct:g}%")
    if free_pct < min_free_pct * 1.5:
        return Result(name, WARN, msg + ", getting low")
    return Result(name, OK, msg)


# ---------------------------------------------------------------------------- TLS


def cert_days_left(not_after: str, now: datetime | None = None) -> float:
    expiry = datetime.fromtimestamp(ssl.cert_time_to_seconds(not_after), tz=timezone.utc)
    return ((now or _utcnow()) - expiry).total_seconds() / -86400


def check_tls_cert(host: str | None, port: int = 443, *, warn_days: float = 21, crit_days: float = 7) -> Result:
    if not host:
        return Result("tls_cert", OK, "not configured (skipped)")
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=8) as sock, context.wrap_socket(sock, server_hostname=host) as tls:
            days = cert_days_left(tls.getpeercert()["notAfter"])
    except ssl.SSLCertVerificationError as exc:
        return Result("tls_cert", CRIT, f"certificate does not verify ({exc.verify_message})")
    except (OSError, ssl.SSLError) as exc:
        return Result("tls_cert", CRIT, f"cannot read the certificate ({type(exc).__name__})")
    if days < crit_days:
        return Result("tls_cert", CRIT, f"certificate expires in {days:.0f} day(s)")
    if days < warn_days:
        return Result("tls_cert", WARN, f"certificate expires in {days:.0f} day(s)")
    return Result("tls_cert", OK, f"certificate valid for {days:.0f} more days")


# ------------------------------------------------------------------ auth activity


def parse_prometheus(text: str) -> dict[str, float]:
    """`name{labels} value` -> {"name{labels}": value} (histograms ignored)."""
    series: dict[str, float] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        key, _, value = line.rpartition(" ")
        if "_bucket" in key or key.endswith("_sum") or key.endswith("_count"):
            continue
        try:
            series[key] = float(value)
        except ValueError:
            continue
    return series


def _sum(series: dict[str, float], prefix: str, contains: str = "") -> float:
    return sum(v for k, v in series.items() if k.startswith(prefix) and contains in k)


def check_auth_activity(
    current: dict[str, float], previous: dict[str, float] | None, *, failed_login_warn: float = 50, error_crit: float = 5
) -> Result:
    if previous is None:
        return Result("auth_activity", OK, "baseline recorded; deltas start next run")
    # A counter that went DOWN means the API restarted: treat the new value as the delta.
    def delta(prefix: str, contains: str = "") -> float:
        now, before = _sum(current, prefix, contains), _sum(previous, prefix, contains)
        return now if now < before else now - before

    alerts = delta("his_security_alerts_total")
    reuse = delta("his_auth_events_total", 'event="refresh_token_reuse"')
    failed = delta("his_auth_events_total", 'event="login_failed"')
    denied = delta("his_auth_events_total", 'event="permission_denied"')
    crossed = delta("his_auth_events_total", 'event="cross_tenant_access"') + delta(
        "his_auth_events_total", 'event="cross_facility_access"'
    )
    unhandled = delta("his_unhandled_exceptions_total")
    server_errors = delta("his_http_requests_total", 'status="5xx"')
    detail = (
        f"since last run: {failed:g} failed sign-ins, {denied:g} permission denials, {alerts:g} security alerts, "
        f"{unhandled:g} unhandled errors, {server_errors:g} 5xx"
    )
    if alerts or reuse or crossed:
        return Result("auth_activity", CRIT, f"SECURITY: {alerts:g} alert(s), {reuse:g} token reuse, {crossed:g} cross-tenant/facility attempts; " + detail)
    if unhandled >= error_crit or server_errors >= error_crit * 4:
        return Result("auth_activity", CRIT, "application errors: " + detail)
    if failed >= failed_login_warn or unhandled or server_errors:
        return Result("auth_activity", WARN, detail)
    return Result("auth_activity", OK, detail)


def fetch_metrics(url: str, token: str | None, *, host_header: str | None = None, timeout: float = 5.0) -> dict[str, float]:
    request = urllib.request.Request(url)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    if host_header:
        request.add_header("Host", host_header)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return parse_prometheus(response.read().decode("utf-8", "replace"))


# -------------------------------------------------------------------------- alerts


def transitions(results: list[Result], previous: dict[str, str]) -> list[str]:
    """Human-readable lines for checks whose state changed since the last run."""
    lines = []
    for r in results:
        before = previous.get(r.name, OK)
        if RANK[r.status] != RANK[before]:
            kind = "RECOVERED" if r.status == OK else r.status
            lines.append(f"{kind} {r.name}: {r.message}")
    return lines


def send_webhook(url: str, text: str, timeout: float = 10.0) -> bool:
    data = json.dumps({"text": text}).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout):  # noqa: S310
            return True
    except (urllib.error.URLError, OSError):
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", help="base URL, e.g. https://his.example.org")
    parser.add_argument("--insecure", action="store_true", help="skip TLS verification of --api (test stacks only)")
    parser.add_argument("--host-header", help="send this Host header to --api (reach the proxy by address)")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--max-backup-age-hours", type=float, default=26)
    parser.add_argument("--max-verify-age-days", type=float, default=8)
    parser.add_argument("--storage-dir", type=Path)
    parser.add_argument("--min-free-pct", type=float, default=15)
    parser.add_argument("--cert-host")
    parser.add_argument("--cert-port", type=int, default=443)
    parser.add_argument("--metrics-url", help="e.g. http://localhost:8000/internal/metrics")
    parser.add_argument("--metrics-token-env", default="METRICS_TOKEN", help="env var holding the bearer token")
    parser.add_argument("--metrics-host-header", default="localhost")
    parser.add_argument("--state-file", type=Path, default=Path(".ops_check_state.json"))
    parser.add_argument("--alert", action="store_true", help="post state changes to $ALERT_WEBHOOK_URL")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    state: dict = {}
    if args.state_file.exists():
        try:
            state = json.loads(args.state_file.read_text(encoding="utf8"))
        except (OSError, ValueError):
            state = {}

    results: list[Result] = []
    if args.api:
        results.append(check_api_ready(args.api, verify_tls=not args.insecure, host_header=args.host_header))
    if args.backup_dir:
        results += [
            check_backup_fresh(args.backup_dir, max_age_hours=args.max_backup_age_hours),
            check_backup_integrity(args.backup_dir),
            check_backup_verified(args.backup_dir, max_age_days=args.max_verify_age_days),
            check_disk("backups", args.backup_dir, min_free_pct=args.min_free_pct),
        ]
    if args.storage_dir:
        results.append(check_disk("storage", args.storage_dir, min_free_pct=args.min_free_pct))
    if args.cert_host:
        results.append(check_tls_cert(args.cert_host, args.cert_port))
    new_counters = None
    if args.metrics_url:
        try:
            new_counters = fetch_metrics(args.metrics_url, os.environ.get(args.metrics_token_env), host_header=args.metrics_host_header)
            results.append(check_auth_activity(new_counters, state.get("counters")))
        except (urllib.error.URLError, OSError) as exc:
            results.append(Result("auth_activity", CRIT, f"cannot read metrics ({type(exc).__name__})"))

    worst = max((r.status for r in results), key=RANK.__getitem__, default=OK)
    if args.json:
        print(json.dumps({"status": worst, "checks": [asdict(r) for r in results]}, indent=2))
    else:
        for r in results:
            print(f"{r.status:<4} {r.name}: {r.message}")
        print(f"-- overall: {worst}")

    if args.alert:
        webhook = os.environ.get("ALERT_WEBHOOK_URL", "")
        changes = transitions(results, state.get("statuses", {}))
        if changes and webhook:
            host = socket.gethostname()
            if not send_webhook(webhook, f"[{host}] ForaCare HIS ops check: " + " | ".join(changes)):
                print("warning: alert webhook delivery failed", file=sys.stderr)
        elif changes and not webhook:
            print("warning: state changed but ALERT_WEBHOOK_URL is not set", file=sys.stderr)

    try:
        args.state_file.write_text(
            json.dumps(
                {"updated": time.time(), "statuses": {r.name: r.status for r in results}, "counters": new_counters or state.get("counters")}
            ),
            encoding="utf8",
        )
    except OSError:
        print("warning: could not write the state file", file=sys.stderr)
    return EXIT_CODE[worst]


if __name__ == "__main__":
    raise SystemExit(main())
