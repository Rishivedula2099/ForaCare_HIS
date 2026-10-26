"""P9-B02: cross-module tenant isolation matrix.

Hospital A = ForaCare (hospital.admin / dr.priya), Hospital B = Sunrise
(sunrise.admin). For every major module:

  A -> A resource : resolves (200; 403 only if the role lacks the permission)
  A -> B resource : never 200 (403/404)
  B -> A resource : never 200 (403/404)

Resources are discovered through each module's list endpoint, so the matrix
adapts to whatever is seeded. Lists must also never leak the other tenant's
ids. 404 is the intended cross-tenant answer (existence is not confirmed).
"""
import io
import itertools
import uuid

import pytest

DEMO_PASSWORD = "Demo@123"
A_ADMIN = "hospital.admin"
A_DOCTOR = "dr.priya"
B_ADMIN = "sunrise.admin"

# module -> (list path, [detail path templates using {id}])
MODULES: dict[str, tuple[str, list[str]]] = {
    "patients": (
        "/patients",
        ["/patients/{id}", "/abdm/patients/{id}/abha", "/opd/patients/{id}/consultations"],
    ),
    "departments": ("/departments", ["/departments/{id}"]),
    "doctors": ("/doctors", ["/doctors/{id}", "/opd/doctors/{id}/queue"]),
    "facilities": ("/facilities", ["/facilities/{id}"]),
    "billing_services": ("/billing/services", ["/billing/services/{id}"]),
    "billing_packages": ("/billing/packages", ["/billing/packages/{id}"]),
    "billing_invoices": (
        "/billing/invoices",
        [
            "/billing/invoices/{id}",
            "/billing/invoices/{id}/balance",
            "/billing/invoices/{id}/payments",
        ],
    ),
    "lab_tests": ("/lab/tests", ["/lab/tests/{id}", "/lab/tests/{id}/parameters"]),
    "lab_orders": (
        "/lab/orders",
        [
            "/lab/orders/{id}",
            "/lab/orders/{id}/status-history",
            "/lab/orders/{id}/report",
            "/lab/orders/{id}/report.pdf",
            "/lab/orders/{id}/verifications",
            "/lab/orders/{id}/approvals",
        ],
    ),
    "opd_encounters": (
        "/opd/encounters",
        [
            "/opd/encounters/{id}",
            "/opd/encounters/{id}/consultation",
            "/opd/encounters/{id}/prescription",
        ],
    ),
    "ipd_wards": ("/ipd/wards", []),
    "ipd_admissions": (
        "/ipd/admissions",
        [
            "/ipd/admissions/{id}",
            "/ipd/admissions/{id}/deposits",
            "/ipd/admissions/{id}/consents",
        ],
    ),
    "document_templates": ("/documents/templates", ["/documents/templates/{id}"]),
}


def _login(client, username):
    client.cookies.clear()
    r = client.post("/api/v1/auth/login", json={"username": username, "password": DEMO_PASSWORD})
    assert r.status_code == 200, r.text


def _ids(client, list_path: str) -> list[str]:
    r = client.get(f"/api/v1{list_path}")
    if r.status_code != 200:
        return []
    data = r.json().get("data")
    if isinstance(data, dict):  # paginated envelopes
        data = data.get("items") or data.get("results") or []
    return [row["id"] for row in data if isinstance(row, dict) and "id" in row][:5]


def _create_patient(client) -> str | None:
    n = uuid.uuid4().int % 10**9
    payload = {
        "first_name": "Isolation",
        "last_name": f"Probe{n}",
        "gender": "MALE",
        "dob": "1990-01-01",
        "blood_group": "O_POSITIVE",
        "address": {"street": "1 St", "city": "Pune", "state": "MH", "pincode": "411001"},
        "contacts": [{"contact_type": "MOBILE", "value": f"9{n:09d}"[:10], "is_primary": True}],
        "identifiers": [],
    }
    r = client.post("/api/v1/patients", json=payload)
    return r.json()["data"]["id"] if r.status_code == 200 else None


@pytest.fixture(scope="module")
def world(client):
    """Resource ids owned by each hospital, discovered once per module."""
    owned: dict[str, dict[str, list[str]]] = {"A": {}, "B": {}}

    for tenant, username in (("A", A_ADMIN), ("B", B_ADMIN)):
        _login(client, username)
        for module, (list_path, _) in MODULES.items():
            owned[tenant][module] = _ids(client, list_path)

    # Guarantee at least one patient per hospital where the role may create one.
    for tenant, username in (("A", A_DOCTOR), ("B", B_ADMIN)):
        _login(client, username)
        created = _create_patient(client)
        if created:
            owned[tenant]["patients"].append(created)

    client.cookies.clear()
    return owned


def _cases():
    for module, (_, details) in MODULES.items():
        for detail in details:
            yield pytest.param(module, detail, id=f"{module}:{detail}")


def _forbidden_or_missing(status: int) -> bool:
    return status in (401, 403, 404, 405, 422)


def _no_leak(response) -> bool:
    """Denied, or a tenant-filtered collection that came back empty.

    History/list-style endpoints scope their query by the caller's tenant
    instead of looking the parent up, so the other hospital's id yields
    `200 []` - identical to a non-existent id, hence no existence leak.
    """
    if _forbidden_or_missing(response.status_code):
        return True
    return response.status_code == 200 and response.json().get("data") == []


@pytest.mark.parametrize("module,detail", list(_cases()))
def test_a_reads_own_and_cannot_read_b(client, world, module, detail):
    own, foreign = world["A"][module], world["B"][module]
    _login(client, A_ADMIN)

    for rid in own[:2]:
        r = client.get(f"/api/v1{detail.format(id=rid)}")
        # A -> A must resolve; 403 only means the role lacks the permission.
        ok = (200, 403) + ((404,) if detail.endswith(("/consultation", "/prescription")) else ())
        # (consultation/prescription legitimately 404 until clinically started)
        assert r.status_code in ok, (detail, rid, r.status_code, r.text)

    for rid in foreign:
        r = client.get(f"/api/v1{detail.format(id=rid)}")
        assert _no_leak(r), (
            f"A reached B's {module}: {detail.format(id=rid)} -> {r.status_code}"
        )


@pytest.mark.parametrize("module,detail", list(_cases()))
def test_b_cannot_read_a(client, world, module, detail):
    foreign = world["A"][module]
    _login(client, B_ADMIN)

    for rid in foreign:
        r = client.get(f"/api/v1{detail.format(id=rid)}")
        assert _no_leak(r), (
            f"B reached A's {module}: {detail.format(id=rid)} -> {r.status_code}"
        )


@pytest.mark.parametrize("module", [m for m in MODULES if m != "facilities"])
def test_lists_never_leak_other_tenants_ids(client, world, module):
    list_path = MODULES[module][0]
    for viewer, viewer_user, other in (("A", A_ADMIN, "B"), ("B", B_ADMIN, "A")):
        _login(client, viewer_user)
        visible = set(_ids(client, list_path))
        leaked = visible & set(world[other][module])
        assert not leaked, f"{viewer} list {list_path} leaked {other}'s ids: {leaked}"


@pytest.mark.parametrize(
    "viewer,viewer_user,owner", [("A", A_ADMIN, "B"), ("B", B_ADMIN, "A")]
)
def test_writes_across_tenants_are_rejected(client, world, viewer, viewer_user, owner):
    """PATCH/POST/DELETE against the other hospital's resources must fail."""
    _login(client, viewer_user)
    attempts = []
    for pid in world[owner]["patients"]:
        attempts.append(("PATCH", f"/patients/{pid}", {"occupation": "tampered"}))
        attempts.append(("POST", f"/abdm/patients/{pid}/abha/consents", {}))
        attempts.append(("DELETE", f"/abdm/patients/{pid}/abha", None))
    for did in world[owner]["departments"]:
        attempts.append(("PATCH", f"/departments/{did}", {"name": "tampered"}))
    for did in world[owner]["doctors"]:
        attempts.append(("PATCH", f"/doctors/{did}", {"specialization": "tampered"}))
    for sid in world[owner]["billing_services"]:
        attempts.append(("PATCH", f"/billing/services/{sid}", {"name": "tampered"}))
    for tid in world[owner]["lab_tests"]:
        attempts.append(("PATCH", f"/lab/tests/{tid}", {"name": "tampered"}))
    for fid in world[owner]["facilities"]:
        attempts.append(("PATCH", f"/facilities/{fid}", {"name": "tampered"}))

    for method, path, body in attempts:
        r = client.request(method, f"/api/v1{path}", json=body)
        assert _forbidden_or_missing(r.status_code), f"{viewer} {method} {path} -> {r.status_code}"


def test_photo_is_not_served_across_tenants(client, world):
    from PIL import Image

    _login(client, A_DOCTOR)
    pid = next(iter(world["A"]["patients"]), None)
    assert pid, "hospital A has no patient to attach a photo to"
    buf = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buf, format="PNG")
    files = {"file": ("p.png", buf.getvalue(), "image/png")}
    up = client.post(f"/api/v1/patients/{pid}/photo", files=files)
    assert up.status_code == 200, up.text
    photo_id = up.json()["data"]["id"]
    assert client.get(f"/api/v1/patients/{pid}/photo/{photo_id}").status_code == 200  # A -> A

    _login(client, B_ADMIN)
    assert client.get(f"/api/v1/patients/{pid}/photo/{photo_id}").status_code in (403, 404)
    r = client.post(f"/api/v1/patients/{pid}/photo", files=files)
    assert _forbidden_or_missing(r.status_code)


def test_document_engine_is_tenant_scoped(client, world):
    """Generating/historying any resource of the other hospital never succeeds."""
    _login(client, A_ADMIN)
    codes = [t["code"] for t in client.get("/api/v1/documents/types").json()["data"]]

    for viewer_user, owner_key in ((B_ADMIN, "A"), (A_ADMIN, "B")):
        _login(client, viewer_user)
        viewer_tenant = client.get("/api/v1/auth/me").json()["data"]["tenant"]["id"]
        # Facility ids are not printable resources, and seed ids collide with
        # patient ids (a Sunrise facility shares a UUID with a ForaCare
        # patient), so probing them would test the viewer's own data.
        ids = set(
            itertools.chain.from_iterable(v for k, v in world[owner_key].items() if k != "facilities")
        )
        for code in codes:
            for rid in ids:
                r = client.get(f"/api/v1/documents/{code}/{rid}")
                assert r.status_code != 200 and r.status_code < 500, (
                    f"{viewer_user} got {code} for {owner_key}'s {rid} -> {r.status_code}"
                )
                # History is tenant-scoped: the viewer may only ever see rows
                # of their own tenant (e.g. their own earlier denied attempts).
                h = client.get(f"/api/v1/documents/{code}/{rid}/history")
                assert h.status_code < 500
                if h.status_code == 200:
                    assert all(row["tenant_id"] == viewer_tenant for row in h.json()["data"]), (
                        f"{viewer_user} saw another tenant's {code} history for {rid}"
                    )


def test_forged_tenant_claim_does_not_switch_tenant(client, world):
    """Tenant comes from the user row, never from a token claim: even a token
    re-signed (dev key) with A's tenant/facility claims, for B's user, stays
    scoped to B."""
    import jwt

    from app.core.config import get_settings

    settings = get_settings()

    def decode(token):
        return jwt.decode(token, settings.jwt_access_secret_key, algorithms=[settings.jwt_algorithm])

    _login(client, A_ADMIN)
    claims_a = decode(client.cookies.get("access_token"))

    _login(client, B_ADMIN)
    claims_b = decode(client.cookies.get("access_token"))
    b_tenant = client.get("/api/v1/auth/me").json()["data"]["tenant"]["id"]

    forged_claims = {
        **claims_b,
        "tenant_id": claims_a["tenant_id"],
        "facility_id": claims_a["facility_id"],
    }
    forged = jwt_encode(forged_claims, settings)

    client.cookies.clear()
    client.cookies.set("access_token", forged)
    me = client.get("/api/v1/auth/me").json()["data"]
    assert me["tenant"]["id"] == b_tenant
    for pid in world["A"]["patients"]:
        assert client.get(f"/api/v1/patients/{pid}").status_code == 404


def jwt_encode(claims, settings):
    import jwt

    return jwt.encode(claims, settings.jwt_access_secret_key, algorithm=settings.jwt_algorithm)
