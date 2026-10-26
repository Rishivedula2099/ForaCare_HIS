"""P10-F02 browser tests: the first-run wizard, run against a live stack
(set E2E_BASE_URL like test_security_browser.py)."""
import os
import re
import subprocess
import uuid

import pytest

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect

BASE = os.environ.get("E2E_BASE_URL")
API = os.environ.get("E2E_API_URL", "http://localhost:8000/api/v1")
PASSWORD = "Demo@123"
PG_CONTAINER = os.environ.get("E2E_PG_CONTAINER", "backend-postgres-1")

pytestmark = pytest.mark.skipif(not BASE, reason="set E2E_BASE_URL to run browser tests")


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context()
    ctx.set_default_timeout(20_000)
    yield ctx.new_page()
    ctx.close()


def _psql(sql: str) -> None:
    subprocess.run(
        ["docker", "exec", PG_CONTAINER, "psql", "-U", "forahis", "-d", "forahis", "-c", sql],
        check=True,
        capture_output=True,
    )


def _purge(code: str) -> None:
    t = f"(SELECT id FROM tenants WHERE code = '{code}')"
    for sql in (
        f"DELETE FROM user_tokens WHERE user_id IN (SELECT id FROM users WHERE tenant_id = {t})",
        f"DELETE FROM user_sessions WHERE user_id IN (SELECT id FROM users WHERE tenant_id = {t})",
        f"DELETE FROM audit_logs WHERE tenant_id = {t} OR resource_id = CAST({t} AS text)",
        f"DELETE FROM user_facility_memberships WHERE user_id IN (SELECT id FROM users WHERE tenant_id = {t})",
        f"DELETE FROM users WHERE tenant_id = {t}",
        f"DELETE FROM facilities WHERE tenant_id = {t}",
        f"DELETE FROM tenants WHERE code = '{code}'",
    ):
        _psql(sql)


def sign_in(page, username):
    page.goto(f"{BASE}/login")
    page.get_by_label("Username or Email").fill(username)
    page.get_by_label("Password", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Sign In").click()
    page.wait_for_url(lambda url: "/login" not in url)


def test_anonymous_visitor_is_sent_to_login_and_the_api_refuses(page):
    page.goto(f"{BASE}/setup")
    page.wait_for_url(re.compile(r"/login\?redirect=%2Fsetup"))
    assert page.request.post(f"{API}/platform/tenants", data={}).status == 401


def test_a_hospital_admin_cannot_open_the_wizard_or_call_the_api(page):
    sign_in(page, "hospital.admin")
    expect(page.locator("aside").get_by_role("link", name="Hospital Setup")).to_have_count(0)
    page.goto(f"{BASE}/setup")
    page.wait_for_url(re.compile(r"/forbidden"))
    assert page.request.get(f"{API}/platform/setup-options").status == 403


def test_operator_completes_the_wizard_and_the_new_admin_can_activate(page):
    suffix = uuid.uuid4().hex[:6].upper()
    code = f"E2E{suffix}"
    try:
        sign_in(page, "super.admin")
        expect(page.locator("aside").get_by_role("link", name="Hospital Setup")).to_be_visible()
        page.goto(f"{BASE}/setup")

        # Step 1: validation first
        page.get_by_role("button", name="Continue").click()
        expect(page.get_by_text("Organisation name is required.")).to_be_visible()
        page.get_by_label("Organisation name").fill(f"E2E Hospital {suffix}")
        page.get_by_label("Organisation code").fill(code)
        page.get_by_role("button", name="Continue").click()

        # Step 2: a code that already exists is caught before moving on
        page.get_by_label("Facility name").fill("E2E Main")
        page.get_by_label("Facility code").fill("FC-MAIN-01")
        page.get_by_role("button", name="Continue").click()
        expect(page.get_by_text("A facility with this code already exists.")).to_be_visible()
        page.get_by_label("Facility code").fill(f"{code}-01")
        page.get_by_role("button", name="Continue").click()

        # Step 3-5
        page.get_by_label("Phone").fill("+91 98765 43210")
        page.get_by_label("Contact email").fill(f"info.{suffix.lower()}@e2e.example")
        page.get_by_label("Address line 1").fill("1 Test Road")
        page.get_by_label("City").fill("Pune")
        page.get_by_label("State / province").fill("Maharashtra")
        page.get_by_label("Postal / PIN code").fill("411001")
        page.get_by_role("button", name="Continue").click()
        expect(page.get_by_role("heading", name="Operational settings")).to_be_visible()
        page.get_by_role("button", name="Continue").click()
        page.get_by_label("Full name").fill("E2E Admin")
        page.get_by_label("Username").fill(f"e2e.admin.{suffix.lower()}")
        page.get_by_label("Email").fill(f"admin.{suffix.lower()}@e2e.example")
        page.get_by_role("button", name="Continue").click()

        # Review, create
        expect(page.get_by_role("heading", name="Review & create")).to_be_visible()
        expect(page.get_by_text(f"E2E Hospital {suffix} ({code})")).to_be_visible()
        page.get_by_role("button", name="Create hospital").click()
        expect(page.get_by_text(f"E2E Hospital {suffix} is set up")).to_be_visible()

        link = page.get_by_label("Activation link").input_value()
        assert "/activate-account?token=" in link

        # The new administrator activates and signs in; the platform operator's own page is not theirs.
        ctx2 = page.context.browser.new_context()
        try:
            admin_page = ctx2.new_page()
            admin_page.goto(link)
            admin_page.get_by_label("New password").fill("Str0ng!Passw0rd#42")
            admin_page.get_by_label("Confirm password").fill("Str0ng!Passw0rd#42")
            admin_page.get_by_role("button", name="Set password").click()
            admin_page.wait_for_url(re.compile(r"/login\?reason=activated"))
            admin_page.get_by_label("Username or Email").fill(f"e2e.admin.{suffix.lower()}")
            admin_page.get_by_label("Password", exact=True).fill("Str0ng!Passw0rd#42")
            admin_page.get_by_role("button", name="Sign In").click()
            admin_page.wait_for_url(re.compile(r"/dashboard"))
            expect(admin_page.get_by_text("E2E Main").first).to_be_visible()
            expect(admin_page.locator("aside").get_by_role("link", name="Hospital Setup")).to_have_count(0)
        finally:
            ctx2.close()

        # Setting up again with the same details is refused and creates nothing new.
        page.get_by_role("button", name="Set up another hospital").click()
        assert page.get_by_label("Organisation name").input_value() == ""
    finally:
        _purge(code)
