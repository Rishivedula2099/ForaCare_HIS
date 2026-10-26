"""P10-S02: operational checks (infra/ops/ops_check.py) and backup failure alerts
(infra/backup/common.sh)."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ops_check", REPO / "infra" / "ops" / "ops_check.py")
ops = importlib.util.module_from_spec(spec)
sys.modules["ops_check"] = ops  # @dataclass resolves annotations through sys.modules
spec.loader.exec_module(ops)

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)


def stamp(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def make_backup(root: Path, when: datetime, *, dump=b"PGDMP", sums=True, manifest=True) -> Path:
    d = root / f"forahis_{stamp(when)}"
    d.mkdir(parents=True)
    (d / "db.dump").write_bytes(dump)
    if sums:
        (d / "SHA256SUMS").write_text("x")
    if manifest:
        (d / "manifest.json").write_text("{}")
    return d


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================================ backups


def test_a_recent_backup_is_ok(tmp_path):
    make_backup(tmp_path, NOW - timedelta(hours=3))
    r = ops.check_backup_fresh(tmp_path, max_age_hours=26, now=NOW)
    assert r.status == ops.OK and "3.0h" in r.message


def test_a_stale_backup_is_critical_even_though_nothing_failed(tmp_path):
    """The scheduler silently stopping is as bad as a failing backup."""
    make_backup(tmp_path, NOW - timedelta(hours=60))
    r = ops.check_backup_fresh(tmp_path, max_age_hours=26, now=NOW)
    assert r.status == ops.CRIT and "60.0h old" in r.message


def test_no_backups_and_a_missing_directory_are_critical(tmp_path):
    assert ops.check_backup_fresh(tmp_path, max_age_hours=26, now=NOW).status == ops.CRIT
    assert ops.check_backup_fresh(tmp_path / "nope", max_age_hours=26, now=NOW).status == ops.CRIT


def test_a_failed_run_is_critical_until_a_later_success(tmp_path):
    make_backup(tmp_path, NOW - timedelta(hours=2))
    (tmp_path / ".last_success").write_text(iso(NOW - timedelta(hours=2)))
    (tmp_path / ".last_failure").write_text(f"{iso(NOW - timedelta(hours=1))} backup exit=1")
    r = ops.check_backup_fresh(tmp_path, max_age_hours=26, now=NOW)
    assert r.status == ops.CRIT and "FAILED" in r.message and "stage: backup" in r.message
    (tmp_path / ".last_success").write_text(iso(NOW - timedelta(minutes=5)))  # a later success clears it
    assert ops.check_backup_fresh(tmp_path, max_age_hours=26, now=NOW).status == ops.OK


def test_a_failed_recovery_test_is_reported_as_a_failed_backup(tmp_path):
    make_backup(tmp_path, NOW - timedelta(hours=2))
    (tmp_path / ".last_failure").write_text(f"{iso(NOW)} backup verification exit=1")
    r = ops.check_backup_fresh(tmp_path, max_age_hours=26, now=NOW)
    assert r.status == ops.CRIT and "backup" in r.message


def test_backup_integrity_needs_a_dump_manifest_and_checksums(tmp_path):
    assert ops.check_backup_integrity(tmp_path).status == ops.CRIT
    make_backup(tmp_path, NOW - timedelta(hours=1))
    assert ops.check_backup_integrity(tmp_path).status == ops.OK
    shutil.rmtree(tmp_path / f"forahis_{stamp(NOW - timedelta(hours=1))}")
    make_backup(tmp_path, NOW, dump=b"")
    assert "empty" in ops.check_backup_integrity(tmp_path).message
    shutil.rmtree(tmp_path / f"forahis_{stamp(NOW)}")
    make_backup(tmp_path, NOW, sums=False)
    assert ops.check_backup_integrity(tmp_path).status == ops.CRIT


def test_an_unverified_or_old_restore_test_warns(tmp_path):
    assert ops.check_backup_verified(tmp_path, max_age_days=8, now=NOW).status == ops.WARN
    (tmp_path / ".last_verified").write_text(iso(NOW - timedelta(days=2)))
    assert ops.check_backup_verified(tmp_path, max_age_days=8, now=NOW).status == ops.OK
    (tmp_path / ".last_verified").write_text(iso(NOW - timedelta(days=20)))
    assert ops.check_backup_verified(tmp_path, max_age_days=8, now=NOW).status == ops.WARN


# ================================================================================ disk


def test_disk_thresholds(tmp_path, monkeypatch):
    def usage(free_pct):
        return shutil._ntuple_diskusage(1000, int(1000 * (1 - free_pct / 100)), int(1000 * free_pct / 100))

    for free, expected in ((40, ops.OK), (20, ops.WARN), (10, ops.CRIT)):
        monkeypatch.setattr(ops.shutil, "disk_usage", lambda p, f=free: usage(f))
        assert ops.check_disk("storage", tmp_path, min_free_pct=15).status == expected, free
    assert ops.check_disk("storage", None, min_free_pct=15).status == ops.OK  # not configured
    assert ops.check_disk("storage", tmp_path / "gone", min_free_pct=15).status == ops.CRIT


# ================================================================================= TLS


def test_certificate_expiry_arithmetic():
    assert round(ops.cert_days_left("Nov 15 12:00:00 2026 GMT", now=NOW), 1) == 30.0
    assert ops.cert_days_left("Oct 10 12:00:00 2026 GMT", now=NOW) < 0  # already expired


def test_tls_check_is_skipped_without_a_host_and_critical_when_unreachable():
    assert ops.check_tls_cert(None).status == ops.OK
    assert ops.check_tls_cert("127.0.0.1", 1).status == ops.CRIT


# ============================================================================ API ready


def test_api_ready_critical_when_unreachable():
    r = ops.check_api_ready("http://127.0.0.1:1", timeout=1)
    assert r.status == ops.CRIT and "unreachable" in r.message


def test_api_ready_reports_which_check_failed_from_a_503(monkeypatch):
    import io
    import urllib.error

    body = json.dumps({"data": {"checks": {"database": {"status": "ok"}, "storage": {"status": "fail", "reason": "low_disk"}}}})

    def fake_open(url, timeout=None, context=None):
        raise urllib.error.HTTPError(url, 503, "NA", {}, io.BytesIO(body.encode()))

    monkeypatch.setattr(ops.urllib.request, "urlopen", fake_open)
    r = ops.check_api_ready("https://his.example.org")
    assert r.status == ops.CRIT and "storage:low_disk" in r.message and "database" not in r.message


# ================================================================ authentication activity


METRICS = """\
# HELP his_auth_events_total x
# TYPE his_auth_events_total counter
his_auth_events_total{event="login_failed"} 10
his_auth_events_total{event="permission_denied"} 2
his_unhandled_exceptions_total 0
his_http_requests_total{method="GET",route="/x",status="2xx"} 500
his_http_requests_total{method="GET",route="/x",status="5xx"} 1
his_http_request_duration_seconds_bucket{route="/x",le="0.1"} 5
his_http_request_duration_seconds_sum{route="/x"} 1.5
"""


def counters(text=METRICS):
    return ops.parse_prometheus(text)


def test_prometheus_parser_ignores_comments_and_histograms():
    series = counters()
    assert series['his_auth_events_total{event="login_failed"}'] == 10
    assert not any("_bucket" in k or k.endswith("_sum") for k in series)


def test_first_run_only_records_a_baseline():
    assert ops.check_auth_activity(counters(), None).status == ops.OK


def test_quiet_period_is_ok():
    assert ops.check_auth_activity(counters(), counters()).status == ops.OK


def test_a_new_security_alert_is_critical():
    after = counters(METRICS + 'his_security_alerts_total{type="failed_logins_per_ip"} 1\n')
    r = ops.check_auth_activity(after, counters())
    assert r.status == ops.CRIT and r.message.startswith("SECURITY")


def test_refresh_token_reuse_and_cross_tenant_attempts_are_critical():
    reuse = counters(METRICS + 'his_auth_events_total{event="refresh_token_reuse"} 1\n')
    assert ops.check_auth_activity(reuse, counters()).status == ops.CRIT
    cross = counters(METRICS + 'his_auth_events_total{event="cross_tenant_access"} 3\n')
    assert ops.check_auth_activity(cross, counters()).status == ops.CRIT


def test_a_spike_of_failed_logins_warns_and_unhandled_errors_escalate():
    spike = counters(METRICS.replace('login_failed"} 10', 'login_failed"} 90'))
    assert ops.check_auth_activity(spike, counters()).status == ops.WARN
    one_error = counters(METRICS.replace("his_unhandled_exceptions_total 0", "his_unhandled_exceptions_total 1"))
    assert ops.check_auth_activity(one_error, counters()).status == ops.WARN
    many = counters(METRICS.replace("his_unhandled_exceptions_total 0", "his_unhandled_exceptions_total 9"))
    assert ops.check_auth_activity(many, counters()).status == ops.CRIT


def test_an_api_restart_resets_counters_without_hiding_new_events():
    before = counters(METRICS.replace('login_failed"} 10', 'login_failed"} 1000'))
    after_restart = counters(METRICS.replace('login_failed"} 10', 'login_failed"} 60'))  # counter went DOWN
    assert ops.check_auth_activity(after_restart, before).status == ops.WARN  # 60 failures since restart


def test_only_state_changes_are_alerted():
    prev = {"api_ready": "OK", "disk_backups": "WARN"}
    results = [
        ops.Result("api_ready", ops.CRIT, "down"),  # OK -> CRIT: alert
        ops.Result("disk_backups", ops.WARN, "low"),  # unchanged: silent
        ops.Result("backup_fresh", ops.OK, "fine"),  # unchanged (absent = OK): silent
    ]
    assert ops.transitions(results, prev) == ["CRIT api_ready: down"]
    recovered = ops.transitions([ops.Result("api_ready", ops.OK, "up")], {"api_ready": "CRIT"})
    assert recovered == ["RECOVERED api_ready: up"]


# ================================================================================ main()


def run_main(tmp_path, *extra):
    # Disk thresholds are pinned low so the exit codes under test do not depend on how
    # full the machine running the tests happens to be.
    return ops.main(["--state-file", str(tmp_path / "state.json"), "--min-free-pct", "0.1", *extra])


def test_main_exit_codes_follow_the_nagios_convention(tmp_path, capsys):
    backups = tmp_path / "b"
    make_backup(backups, datetime.now(timezone.utc) - timedelta(hours=1))
    (backups / ".last_verified").write_text(iso(datetime.now(timezone.utc)))
    assert run_main(tmp_path, "--backup-dir", str(backups)) == 0
    (backups / ".last_verified").unlink()
    assert run_main(tmp_path, "--backup-dir", str(backups)) == 1  # WARN: never verified
    shutil.rmtree(backups)
    backups.mkdir()
    assert run_main(tmp_path, "--backup-dir", str(backups)) == 2  # CRIT: no backups
    assert "overall: CRIT" in capsys.readouterr().out


def test_main_json_output(tmp_path, capsys):
    backups = tmp_path / "b"
    backups.mkdir()
    run_main(tmp_path, "--backup-dir", str(backups), "--json")
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "CRIT" and {c["name"] for c in data["checks"]} >= {"backup_fresh", "backup_integrity"}


def test_main_alerts_once_per_change_with_no_data_in_the_message(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(ops, "send_webhook", lambda url, text, timeout=10: sent.append(text) or True)
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://hooks.example.org/x")
    backups = tmp_path / "b"
    backups.mkdir()  # no backups -> CRIT
    for _ in range(3):
        run_main(tmp_path, "--backup-dir", str(backups), "--alert")
    assert len(sent) == 1 and "backup_fresh" in sent[0]  # three runs, one page
    make_backup(backups, datetime.now(timezone.utc) - timedelta(minutes=5))
    run_main(tmp_path, "--backup-dir", str(backups), "--alert")
    assert len(sent) == 2 and "RECOVERED backup_fresh" in sent[1]


def test_main_tracks_metric_deltas_between_runs(tmp_path, monkeypatch, capsys):
    scrapes = [counters(), counters(METRICS + 'his_security_alerts_total{type="failed_logins_per_ip"} 1\n')]
    monkeypatch.setattr(ops, "fetch_metrics", lambda *a, **k: scrapes.pop(0))
    assert run_main(tmp_path, "--metrics-url", "http://x/internal/metrics") == 0  # baseline
    assert run_main(tmp_path, "--metrics-url", "http://x/internal/metrics") == 2  # new security alert
    assert "SECURITY" in capsys.readouterr().out


# ===================================================== backup failure alerts (common.sh)


def _bash():
    found = shutil.which("bash")
    return None if (not found or "system32" in found.lower()) else found


needs_bash = pytest.mark.skipif(_bash() is None, reason="needs a real bash (Git Bash / Linux)")


def _run_common(tmp_path, snippet, *, webhook=True):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(exist_ok=True)
    log = tmp_path / "curl.log"
    curl = fake_bin / "curl"
    curl.write_text(f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "{log.as_posix()}"\n')
    curl.chmod(0o755)
    backups = tmp_path / "backups"
    env = {**os.environ, "PATH": f"{fake_bin.as_posix()}{os.pathsep}{os.environ['PATH']}", "BACKUP_DIR": str(backups)}
    env.pop("ALERT_WEBHOOK_URL", None)
    if webhook:
        env["ALERT_WEBHOOK_URL"] = "https://hooks.example.org/T0K3N"
    result = subprocess.run(
        [_bash(), "-c", f'source "{(REPO / "infra/backup/common.sh").as_posix()}"; {snippet}'],
        capture_output=True, text=True, env=env, cwd=REPO,
    )
    return result, backups, log


@needs_bash
def test_a_backup_failure_writes_a_marker_and_pages_the_webhook(tmp_path):
    result, backups, log = _run_common(tmp_path, "record_failure backup 3")
    assert result.returncode == 0, result.stderr
    marker = (backups / ".last_failure").read_text()
    assert " backup exit=3" in marker
    posted = log.read_text()
    assert "hooks.example.org/T0K3N" in posted and "FAILED (exit 3)" in posted
    assert "password" not in posted.lower() and "postgres" not in posted.lower()  # status only, no data


@needs_bash
def test_a_backup_success_clears_the_failure_marker(tmp_path):
    result, backups, log = _run_common(tmp_path, "record_failure backup 1; record_success success; record_success verified")
    assert result.returncode == 0, result.stderr
    assert not (backups / ".last_failure").exists()
    assert (backups / ".last_success").read_text().strip().endswith("Z")
    assert (backups / ".last_verified").exists()


@needs_bash
def test_without_a_webhook_a_failure_is_still_recorded_and_nothing_is_posted(tmp_path):
    result, backups, log = _run_common(tmp_path, "record_failure backup 2", webhook=False)
    assert result.returncode == 0, result.stderr
    assert (backups / ".last_failure").exists()
    assert not log.exists()


@needs_bash
def test_a_marker_written_by_the_script_is_what_ops_check_understands(tmp_path):
    _run_common(tmp_path, "record_failure backup 1", webhook=False)
    backups = tmp_path / "backups"
    make_backup(backups, datetime.now(timezone.utc) - timedelta(hours=1))
    r = ops.check_backup_fresh(backups, max_age_hours=26)
    assert r.status == ops.CRIT and "FAILED" in r.message
    _run_common(tmp_path, "record_success success", webhook=False)
    assert ops.check_backup_fresh(backups, max_age_hours=26).status == ops.OK


# ============================================================ alert rules and secrets


def test_example_alert_rules_parse_and_only_use_metrics_the_api_exports():
    import re

    import yaml

    from app.core import metrics

    rules_file = REPO / "infra" / "ops" / "prometheus-alerts.example.yml"
    doc = yaml.safe_load(rules_file.read_text(encoding="utf8"))
    exprs = [rule["expr"] for group in doc["groups"] for rule in group["rules"]]
    assert len(exprs) >= 10
    exported = set(metrics.HELP)
    for expr in exprs:
        used = set(re.findall(r"\bhis_[a-z_]+", str(expr)))
        base = {re.sub(r"_(bucket|sum|count)$", "", name) for name in used}
        assert base <= exported, (expr, base - exported)
    # every alert points at a runbook anchor that exists
    incident = (REPO / "docs" / "incident-response.md").read_text(encoding="utf8").lower()
    for group in doc["groups"]:
        for rule in group["rules"]:
            anchor = rule["annotations"]["runbook"].split("#")[1].replace("-", " ")
            assert anchor in incident, (rule["alert"], anchor)


def test_the_secret_generator_creates_the_metrics_token_and_an_empty_webhook_secret(tmp_path):
    out = tmp_path / "secrets"
    result = subprocess.run(
        [os.sys.executable, str(REPO / "backend" / "scripts" / "generate_secrets.py"), "--out", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert len((out / "metrics_token").read_text()) >= 32
    assert (out / "alert_webhook_url").read_text() == ""
    assert "alert_webhook_url" in result.stdout  # reminded to fill in by hand


def test_production_compose_wires_observability_secrets_and_log_rotation():
    compose = (REPO / "docker-compose.prod.yml").read_text(encoding="utf8")
    assert "metrics_token" in compose and "alert_webhook_url" in compose
    assert "max-size" in compose and "max-file" in compose
    assert "/api/v1/health/ready" in compose  # the edge reports readiness, not just liveness
    proxy = (REPO / "infra" / "nginx" / "prod" / "proxy_params.conf").read_text(encoding="utf8")
    assert "X-Request-ID $request_id" in proxy
