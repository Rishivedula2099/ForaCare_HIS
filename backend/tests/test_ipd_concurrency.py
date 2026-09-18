"""P4-B03 concurrency tests: two admit/transfer requests racing for the same
bed (or the same patient) must never both succeed - the loser gets a 409
CONFLICT and the DB is left with exactly one winner. Exercises the
`SELECT ... FOR UPDATE` row locks and the per-patient advisory lock added in
app/modules/ipd/service.py, against the real Postgres test database (row
locking can't be demonstrated against an in-memory/mocked DB). Mirrors
test_ipd_security.py's conventions - demo-seeded fixed UUIDs, shared DB, no
per-test rollback.
"""

import threading

DEMO_PASSWORD = "Demo@123"

HOSPITAL_ADMIN = "hospital.admin"

# Seeded by 20260918_0902_f83c5a1e6d92_seed_demo_ipd_data.py
BED_101_A_ID = "99999999-9999-9999-9999-999999999901"
BED_101_B_ID = "99999999-9999-9999-9999-999999999902"

# Seeded by 20260908_1101_b8d1e4f6a209_seed_demo_patients.py
PATIENT_1_ID = "44444444-4444-4444-4444-444444444401"
PATIENT_2_ID = "44444444-4444-4444-4444-444444444402"


def _login(client, username: str, password: str = DEMO_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _find_bed(client, bed_id: str) -> dict:
    beds = client.get("/api/v1/ipd/beds").json()["data"]
    return next(bed for bed in beds if bed["id"] == bed_id)


def _ensure_bed_available(client, bed_id: str) -> None:
    bed = _find_bed(client, bed_id)
    occupant = bed.get("current_occupant")
    if occupant:
        client.post(f"/api/v1/ipd/admissions/{occupant['admission_id']}/discharge", json={"discharge_type": "NORMAL"})
        bed = _find_bed(client, bed_id)
    if bed["status"] != "AVAILABLE":
        client.patch(f"/api/v1/ipd/beds/{bed_id}", json={"status": "AVAILABLE"})


def _admit_concurrently(client, requests: list[dict]) -> list:
    """Fires every admission POST in `requests` from its own thread at
    (as close to) the same instant, so their transactions actually overlap
    in Postgres rather than running one after another."""
    results: list = [None] * len(requests)
    barrier = threading.Barrier(len(requests))

    def _run(index: int, payload: dict) -> None:
        barrier.wait()
        results[index] = client.post("/api/v1/ipd/admissions", json=payload)

    threads = [threading.Thread(target=_run, args=(i, r)) for i, r in enumerate(requests)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def test_two_patients_racing_for_the_same_bed_only_one_wins(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)

    responses = _admit_concurrently(
        client,
        [
            {"patient_id": PATIENT_1_ID, "bed_id": BED_101_A_ID, "admission_type": "ELECTIVE"},
            {"patient_id": PATIENT_2_ID, "bed_id": BED_101_A_ID, "admission_type": "ELECTIVE"},
        ],
    )

    statuses = sorted(r.status_code for r in responses)
    assert statuses == [200, 409], [r.text for r in responses]

    conflict = next(r for r in responses if r.status_code == 409)
    assert conflict.json()["error"]["code"] == "CONFLICT"

    # The bed must be OCCUPIED by exactly the winner, never left AVAILABLE
    # or double-assigned.
    bed = _find_bed(client, BED_101_A_ID)
    assert bed["status"] == "OCCUPIED"
    winner = next(r for r in responses if r.status_code == 200).json()["data"]
    assert bed["current_occupant"]["admission_id"] == winner["id"]

    client.post(f"/api/v1/ipd/admissions/{winner['id']}/discharge", json={"discharge_type": "NORMAL"})


def test_independent_concurrent_admissions_get_distinct_admission_numbers(client):
    """Two admits for different patients into different beds don't contend
    on the patient lock or either bed's row lock, so this specifically
    exercises `_lock_admission_number_sequence` - without it, both requests
    can compute the same `admission_number` and one fails with a raw 500
    (unique constraint violation) instead of succeeding.
    """
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    _ensure_bed_available(client, BED_101_B_ID)

    responses = _admit_concurrently(
        client,
        [
            {"patient_id": PATIENT_1_ID, "bed_id": BED_101_A_ID, "admission_type": "ELECTIVE"},
            {"patient_id": PATIENT_2_ID, "bed_id": BED_101_B_ID, "admission_type": "ELECTIVE"},
        ],
    )

    assert [r.status_code for r in responses] == [200, 200], [r.text for r in responses]
    admissions = [r.json()["data"] for r in responses]
    assert admissions[0]["admission_number"] != admissions[1]["admission_number"]

    for admission in admissions:
        client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})
    _ensure_bed_available(client, BED_101_A_ID)
    _ensure_bed_available(client, BED_101_B_ID)


def test_one_patient_racing_for_two_different_beds_only_one_admission_wins(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    _ensure_bed_available(client, BED_101_B_ID)

    responses = _admit_concurrently(
        client,
        [
            {"patient_id": PATIENT_1_ID, "bed_id": BED_101_A_ID, "admission_type": "ELECTIVE"},
            {"patient_id": PATIENT_1_ID, "bed_id": BED_101_B_ID, "admission_type": "ELECTIVE"},
        ],
    )

    statuses = sorted(r.status_code for r in responses)
    assert statuses == [200, 409], [r.text for r in responses]

    admissions = client.get(f"/api/v1/ipd/admissions?patient_id={PATIENT_1_ID}&status=ADMITTED").json()["data"]
    assert len(admissions) == 1

    # Whichever bed lost the race must have been left untouched (still
    # AVAILABLE), not partially allocated.
    bed_a, bed_b = _find_bed(client, BED_101_A_ID), _find_bed(client, BED_101_B_ID)
    occupied = [b for b in (bed_a, bed_b) if b["status"] == "OCCUPIED"]
    available = [b for b in (bed_a, bed_b) if b["status"] == "AVAILABLE"]
    assert len(occupied) == 1
    assert len(available) == 1

    client.post(f"/api/v1/ipd/admissions/{admissions[0]['id']}/discharge", json={"discharge_type": "NORMAL"})
    _ensure_bed_available(client, BED_101_A_ID)
    _ensure_bed_available(client, BED_101_B_ID)
