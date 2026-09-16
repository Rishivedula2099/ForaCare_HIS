#!/usr/bin/env python
"""Phase 1 Security Gate health check.

Exercises a *running* stack (defaults to the docker-compose stack behind
nginx on http://localhost) against every criterion in the Phase 1 gate and
prints a pass/fail table. Exits non-zero if anything fails.

Usage:
    python scripts/phase1_health_check.py [base_url]

    base_url defaults to http://localhost (i.e. through the nginx reverse
    proxy, at /api/v1). Pass http://localhost:8000 to hit the backend
    directly instead (bypassing the proxy check).
"""
import sys
import time
from dataclasses import dataclass, field

import httpx

DEMO_PASSWORD = "Demo@123"


@dataclass
class Results:
    checks: list[tuple[str, bool, str]] = field(default_factory=list)

    def record(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append((name, passed, detail))
        icon = "PASS" if passed else "FAIL"
        print(f"[{icon}] {name}" + (f" - {detail}" if detail and not passed else ""))

    @property
    def all_passed(self) -> bool:
        return all(passed for _, passed, _ in self.checks)


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost"
    api = f"{base_url}/api/v1"
    results = Results()

    print(f"Running Phase 1 health check against {api}\n")

    # --- Reverse proxy + health -------------------------------------------------
    try:
        health = httpx.get(f"{api}/health", timeout=10)
        results.record("Reverse proxy routes /api/* to backend", health.status_code == 200)
    except httpx.HTTPError as exc:
        results.record("Reverse proxy routes /api/* to backend", False, str(exc))

    try:
        frontend = httpx.get(base_url, timeout=10)
        results.record("Reverse proxy serves frontend at /", frontend.status_code == 200)
    except httpx.HTTPError as exc:
        results.record("Reverse proxy serves frontend at /", False, str(exc))

    client = httpx.Client(base_url=api, timeout=10)

    # --- Authentication -----------------------------------------------------
    wrong = client.post("/auth/login", json={"username": "dr.priya", "password": "wrong"})
    results.record(
        "Login rejects wrong password (no dev bypass)",
        wrong.status_code == 401,
        f"got {wrong.status_code}",
    )

    login = client.post("/auth/login", json={"username": "dr.priya", "password": DEMO_PASSWORD})
    results.record("Login succeeds with valid credentials", login.status_code == 200, login.text)

    access_cookie = client.cookies.get("access_token")
    refresh_cookie = client.cookies.get("refresh_token")
    results.record("Access + refresh cookies are set on login", bool(access_cookie and refresh_cookie))

    body = login.json().get("data", {})
    results.record("No JWT is present in the login response body", "access_token" not in str(body))

    set_cookie_headers = login.headers.get_list("set-cookie")
    httponly_ok = all("httponly" in h.lower() for h in set_cookie_headers if "token" in h.lower())
    results.record("Cookies are HttpOnly", httponly_ok)

    session_meta = body.get("session", {})
    results.record(
        "Access token lifetime is 15 minutes",
        session_meta.get("expires_in") == 15 * 60,
        f"got {session_meta.get('expires_in')}",
    )

    me = client.get("/auth/me")
    results.record("Authenticated /auth/me succeeds with session cookie", me.status_code == 200)

    # --- Refresh rotation + reuse detection ---------------------------------
    old_refresh = client.cookies.get("refresh_token")
    refreshed = client.post("/auth/refresh")
    results.record("Refresh rotates the token pair", refreshed.status_code == 200)
    new_refresh = client.cookies.get("refresh_token")
    results.record("Refresh cookie value changes on rotation", new_refresh != old_refresh)

    client.cookies.set("refresh_token", old_refresh)
    reused = client.post("/auth/refresh")
    results.record("Refresh reuse of a rotated token is rejected", reused.status_code == 401)

    client.cookies.set("refresh_token", new_refresh)
    after_reuse = client.post("/auth/refresh")
    results.record(
        "Reuse detection revokes the whole session (post-reuse refresh also fails)",
        after_reuse.status_code == 401,
    )

    # --- Logout / session revocation ----------------------------------------
    client.post("/auth/login", json={"username": "dr.priya", "password": DEMO_PASSWORD})
    logout = client.post("/auth/logout")
    results.record("Logout succeeds", logout.status_code == 200)
    me_after_logout = client.get("/auth/me")
    results.record("Session is dead server-side immediately after logout", me_after_logout.status_code == 401)

    # --- RBAC / permissions ---------------------------------------------------
    client.post("/auth/login", json={"username": "dr.priya", "password": DEMO_PASSWORD})
    forbidden = client.get("/tenants")
    results.record("RBAC blocks a DOCTOR from a SUPER_ADMIN-only endpoint (403)", forbidden.status_code == 403)

    client.post("/auth/login", json={"username": "super.admin", "password": DEMO_PASSWORD})
    allowed = client.get("/tenants")
    results.record("RBAC allows SUPER_ADMIN on the same endpoint (200)", allowed.status_code == 200)

    no_session_client = httpx.Client(base_url=api, timeout=10)
    unauthenticated = no_session_client.get("/auth/me")
    results.record("401 (not 403) when no session is present", unauthenticated.status_code == 401)

    # --- Facility / tenant isolation -----------------------------------------
    client.post("/auth/login", json={"username": "sunrise.admin", "password": DEMO_PASSWORD})
    sunrise_facilities = client.get("/facilities").json().get("data", [])
    if sunrise_facilities:
        sunrise_facility_id = sunrise_facilities[0]["id"]
        client.post("/auth/login", json={"username": "hospital.admin", "password": DEMO_PASSWORD})
        cross_tenant = client.get(f"/facilities/{sunrise_facility_id}")
        results.record("Cross-tenant facility access returns 404 (not 403)", cross_tenant.status_code == 404)
    else:
        results.record("Cross-tenant facility access returns 404 (not 403)", False, "no sunrise facilities found")

    # --- Audit -----------------------------------------------------------------
    client.post("/auth/login", json={"username": "auditor", "password": DEMO_PASSWORD})
    time.sleep(0.5)
    audit_logs = client.get("/audit/logs", params={"resource_type": "user"})
    has_login_event = any(
        log.get("action") == "auth.login.succeeded" for log in audit_logs.json().get("data", [])
    )
    results.record("Audit log captures login events", has_login_event)

    print("\n" + ("=" * 60))
    passed_count = sum(1 for _, ok, _ in results.checks if ok)
    print(f"{passed_count}/{len(results.checks)} checks passed")

    return 0 if results.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
