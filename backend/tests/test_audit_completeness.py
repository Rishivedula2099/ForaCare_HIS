"""P9-B03: audit completeness across auth, PHI reads, ABHA and security
failures. Mutation audits already have per-module tests; this file covers the
cross-cutting gaps closed in P9 and guards the action catalog."""
import re
import uuid
from pathlib import Path

import pytest

DEMO_PASSWORD = "Demo@123"
APP = Path(__file__).resolve().parents[1] / "app"


def _login(client, username, password=DEMO_PASSWORD):
    client.cookies.clear()
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _logs(client, action: str, **params) -> list[dict]:
    """Audit rows for `action`, newest first, read as a tenant admin."""
    _login(client, "hospital.admin")
    rows = client.get("/api/v1/audit/logs", params={"limit": 200, **params}).json()["data"]
    return [row for row in rows if row["action"] == action]


# --- auth / security failures ------------------------------------------------


def test_failed_login_is_audited_without_the_password(client):
    secret = f"Wrong-{uuid.uuid4().hex}"
    assert _login(client, "dr.priya", secret).status_code == 401

    rows = _logs(client, "auth.login.failed")
    mine = [r for r in rows if r["actor_username"] == "dr.priya"]
    assert mine, "failed login was not audited"
    assert mine[0]["after"]["reason"] == "bad_password"
    assert secret not in str(rows)


def test_failed_login_audit_is_tenant_scoped(client):
    assert _login(client, "sunrise.admin", "nope-nope").status_code == 401
    # hospital.admin (another tenant) must not see sunrise's failure.
    rows = _logs(client, "auth.login.failed")
    assert all(r["actor_username"] != "sunrise.admin" for r in rows)


def test_unknown_user_failure_records_attempted_username_only(monkeypatch):
    import asyncio

    from app.core.exceptions import UnauthorizedError
    from app.modules.audit import service as audit_service
    from app.modules.auth import service

    captured = {}

    async def fake_record_event(db, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(audit_service, "record_event", fake_record_event)
    error = service._login_failure("Invalid username or password.", "unknown_user")
    assert isinstance(error, UnauthorizedError)
    asyncio.run(service.record_login_failure(None, "x" * 500, error, ip_address="10.0.0.1"))

    assert captured["action"] == "auth.login.failed"
    assert captured["tenant_id"] is None and captured["actor_user_id"] is None
    assert len(captured["actor_username"]) == 100
    assert captured["after"] == {"reason": "unknown_user", "ip_address": "10.0.0.1"}


def test_permission_denial_is_audited(client):
    _login(client, "dr.priya")
    assert client.get("/api/v1/audit/logs").status_code == 403

    rows = _logs(client, "security.permission_denied")
    hit = [r for r in rows if r["actor_username"] == "dr.priya" and r["after"]["path"] == "/api/v1/audit/logs"]
    assert hit, "403 was not audited"
    assert hit[0]["after"]["required"] == ["audit.view_logs"]


def test_failed_otp_verification_is_audited(client):
    _login(client, "dr.priya")
    r = client.post(
        "/api/v1/auth/phone/change/verify", json={"new_phone": "9000000001", "code": "000000"}
    )
    assert r.status_code == 401
    rows = _logs(client, "auth.otp.verification_failed")
    assert any(row["after"]["purpose"] == "phone_change" for row in rows)


# --- ABHA ----------------------------------------------------------------------


def _first_patient_id(client) -> str:
    return client.get("/api/v1/patients").json()["data"][0]["id"]


def test_abha_otp_request_is_audited_without_the_identifier(client):
    _login(client, "hospital.admin")
    identifier = "9123456780"
    r = client.post("/api/v1/abdm/otp", json={"auth_method": "MOBILE_OTP", "identifier": identifier})
    assert r.status_code == 200, r.text
    txn = r.json()["data"]["transaction_id"]

    rows = _logs(client, "abha.otp_requested")
    mine = [row for row in rows if row["resource_id"] == txn]
    assert mine and mine[0]["after"] == {"auth_method": "MOBILE_OTP"}
    assert identifier not in str(rows)


def test_abha_failed_verification_is_audited(client):
    _login(client, "hospital.admin")
    pid = _first_patient_id(client)
    r = client.post(
        f"/api/v1/abdm/patients/{pid}/abha/verify", json={"transaction_id": "nope", "otp": "123456"}
    )
    assert r.status_code == 400
    rows = _logs(client, "abha.verification_failed")
    assert any(row["resource_id"] == pid for row in rows)


# --- PHI / financial read access -------------------------------------------------

READS = [
    # (list path, detail path, audit action, role able to read it)
    ("/opd/encounters", "/opd/encounters/{id}/consultation", "opd.consultations.viewed", "hospital.admin"),
    ("/opd/encounters", "/opd/encounters/{id}/prescription", "opd.prescriptions.viewed", "hospital.admin"),
    ("/ipd/admissions", "/ipd/admissions/{id}", "ipd.admission_viewed", "hospital.admin"),
    ("/billing/invoices", "/billing/invoices/{id}", "billing.invoice_viewed", "hospital.admin"),
    ("/lab/orders", "/lab/orders/{id}", "lab.order_viewed", "hospital.admin"),
]


@pytest.mark.parametrize("list_path,detail,action,role", READS, ids=[r[2] for r in READS])
def test_record_reads_are_audited(client, list_path, detail, action, role):
    _login(client, role)
    items = client.get(f"/api/v1{list_path}").json()["data"]
    if isinstance(items, dict):
        items = items.get("items", [])
    if not items:
        pytest.skip(f"no seeded data under {list_path}")
    rid = items[0]["id"]

    response = client.get(f"/api/v1{detail.format(id=rid)}")
    if response.status_code == 404:
        pytest.skip("record has no sub-resource yet (e.g. consultation not started)")
    assert response.status_code == 200, response.text

    assert any(r["resource_id"] == rid for r in _logs(client, action)), f"{action} not recorded"


def test_denied_reads_are_not_recorded_as_views(client):
    _login(client, "sunrise.admin")
    other = str(uuid.uuid4())
    assert client.get(f"/api/v1/billing/invoices/{other}").status_code == 404
    assert not any(r["resource_id"] == other for r in _logs(client, "billing.invoice_viewed"))


def test_reading_the_audit_log_is_itself_audited(client):
    _login(client, "auditor")
    assert client.get("/api/v1/audit/logs").status_code == 200
    rows = _logs(client, "audit.logs_viewed")
    assert any(r["actor_user_id"] for r in rows)


# --- catalog guard ------------------------------------------------------------------

# Every category the P9-B03 brief names, with the actions that must keep existing.
EXPECTED_ACTIONS = {
    "auth": ["auth.login.succeeded", "auth.login.failed", "auth.logout", "auth.logout_all",
             "auth.password_changed", "auth.otp.verification_failed",
             "auth.security.refresh_reuse_detected"],
    "patient": ["patients.created", "patients.updated", "patients.viewed", "patients.photo_uploaded",
                "patients.photo_accessed"],
    "opd": ["opd.encounters.registered", "opd.tokens.called", "opd.consultations.created",
            "opd.consultations.viewed", "opd.prescriptions.created", "opd.prescriptions.viewed"],
    "ipd": ["ipd.admission_created", "ipd.admission_viewed", "ipd.transfer_created",
            "ipd.discharge_created", "ipd.deposit_recorded", "ipd.consent_recorded"],
    "billing": ["billing.invoice_created", "billing.invoice_viewed", "billing.payment_recorded",
                "billing.refund_created", "billing.deposit_recorded", "billing.access_denied"],
    "lab": ["lab.results_entered", "lab.results_verified", "lab.results_approved", "lab.result_amended",
            "lab.order_viewed", "lab.report_viewed"],
    "documents": ["document.generated", "document.generation_failed", "document.verified"],
    "abha": ["abha.otp_requested", "abha.verified", "abha.verification_failed", "abha.linked",
             "abha.unlinked", "abha.consent_granted", "abha.consent_revoked"],
    "administrative": ["facilities.created", "departments.updated", "doctors.updated",
                       "rbac.role.permissions_updated", "document_template.version_activated",
                       "audit.logs_viewed"],
    "security": ["security.permission_denied", "auth.login.failed", "abha.verification_failed",
                 "billing.access_denied"],
}


def _source_actions() -> str:
    return "\n".join(p.read_text(encoding="utf8") for p in APP.rglob("*.py"))


@pytest.mark.parametrize("category", sorted(EXPECTED_ACTIONS))
def test_audit_action_catalog_is_complete(category):
    source = _source_actions()
    missing = [a for a in EXPECTED_ACTIONS[category] if not re.search(rf'["\']{re.escape(a)}["\']', source)]
    assert not missing, f"{category}: audit actions no longer emitted anywhere: {missing}"
