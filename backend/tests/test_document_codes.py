"""P7-B05: QR / barcode helpers (pure unit tests - no database or server)."""
import re
import uuid
from urllib.parse import parse_qs, urlparse

import pytest

from app.core.exceptions import AppError
from app.modules.documents import codes


def _decode_svg(svg: str) -> str:
    """Independent Code 128-B decoder working from the SVG's bar geometry."""
    rects = [(int(x), int(w)) for x, w in re.findall(r'<rect x="(\d+)" y="0" width="(\d+)"', str(svg))]
    # Rebuild the element-width sequence (bar, space, bar, ...) from positions.
    widths: list[int] = []
    cursor = rects[0][0]
    for x, w in rects:
        if x > cursor:
            widths.append(x - cursor)  # the gap is a space
        widths.append(w)
        cursor = x + w
    table = {pattern: value for value, pattern in enumerate(codes._PATTERNS)}
    symbols: list[int] = []
    pos = 0
    while pos + 6 <= len(widths):
        pattern = "".join(map(str, widths[pos : pos + 6]))
        if pos + 7 == len(widths):  # final 7-element stop pattern
            assert "".join(map(str, widths[pos:])) == codes._STOP_PATTERN
            break
        symbols.append(table[pattern])
        pos += 6
    start, *data, checksum = symbols
    assert start == codes.START_B
    assert checksum == (start + sum(v * (i + 1) for i, v in enumerate(data))) % 103
    return "".join(chr(v + 32) for v in data)


def test_pattern_table_is_well_formed():
    assert len(codes._PATTERNS) == 106
    assert all(len(p) == 6 and sum(map(int, p)) == 11 for p in codes._PATTERNS)
    assert sum(map(int, codes._STOP_PATTERN)) == 13
    assert len(set(codes._PATTERNS)) == 106  # no two symbols share a pattern


@pytest.mark.parametrize("reference", ["RCP-2026-000123", "INV/2026/0042", "A", "ADM 77~z", "x" * 40])
def test_barcode_round_trips(reference):
    assert _decode_svg(codes.code128_svg(reference)) == reference


def test_known_checksum():
    # Start B (104) + 'A' (33): (104 + 33*1) % 103 = 34
    assert codes.code128_values("A") == [104, 33, 34, 106]


@pytest.mark.parametrize("bad", ["", "   ", "x" * 41, "café", "line\nbreak", "tab\t"])
def test_invalid_references_are_rejected(bad):
    with pytest.raises(AppError) as exc:
        codes.validate_reference(bad)
    assert exc.value.code == "INVALID_DOCUMENT_REFERENCE"


def test_signature_binds_type_id_and_reference():
    doc_id = uuid.uuid4()
    sig = codes.sign_document("RECEIPT", doc_id, "RCP-1")
    assert len(sig) == 32
    assert codes.verify_signature("RECEIPT", doc_id, "RCP-1", sig)
    # Any change to what was signed must fail verification.
    assert not codes.verify_signature("INVOICE", doc_id, "RCP-1", sig)
    assert not codes.verify_signature("RECEIPT", uuid.uuid4(), "RCP-1", sig)
    assert not codes.verify_signature("RECEIPT", doc_id, "RCP-2", sig)
    assert not codes.verify_signature("RECEIPT", doc_id, "RCP-1", sig[:-1] + ("0" if sig[-1] != "0" else "1"))
    assert not codes.verify_signature("RECEIPT", doc_id, "RCP-1", "")


def test_verify_url_carries_a_valid_signature():
    doc_id = uuid.uuid4()
    url = codes.build_verify_url("https://his.example/", "INVOICE", doc_id, "INV-9")
    parsed = urlparse(url)
    assert parsed.path == "/api/v1/documents/verify"
    query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    assert query["t"] == "INVOICE" and query["id"] == str(doc_id)
    assert codes.verify_signature("INVOICE", doc_id, "INV-9", query["sig"])


def test_qr_is_a_png_data_uri():
    assert codes.qr_data_uri("hello").startswith("data:image/png;base64,")


# --- public verification (service logic; the lookup and audit write are stubbed) ---


def _summary(reference="RCP-1", issued=None):
    from datetime import datetime, timezone

    from app.modules.documents.base import DocumentSummary

    return DocumentSummary(
        reference, "Test Hospital", issued or datetime(2026, 10, 10, tzinfo=timezone.utc), uuid.uuid4(), uuid.uuid4()
    )


@pytest.fixture
def verify_env(monkeypatch):
    from dataclasses import replace

    from app.modules.documents import service

    known = {}
    audit_calls = []

    async def summarize(db, resource_id):
        return known.get(resource_id)

    async def fake_audit(db, **kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(service, "_REGISTRY", {"RECEIPT": replace(service._REGISTRY["RECEIPT"], summarize=summarize)})
    monkeypatch.setattr(service.audit_service, "record_event", fake_audit)
    return service, known, audit_calls


async def test_verify_accepts_a_genuine_signature(verify_env):
    service, known, audit_calls = verify_env
    doc_id = uuid.uuid4()
    known[doc_id] = _summary("RCP-1")
    result = await service.verify_document(None, "receipt", doc_id, codes.sign_document("RECEIPT", doc_id, "RCP-1"))
    assert result.valid and result.reference == "RCP-1" and result.facility_name == "Test Hospital"
    assert audit_calls and audit_calls[0]["action"] == "document.verified"


async def test_verify_rejects_everything_else_identically(verify_env):
    service, known, audit_calls = verify_env
    doc_id = uuid.uuid4()
    known[doc_id] = _summary("RCP-1")
    good = codes.sign_document("RECEIPT", doc_id, "RCP-1")
    bad_attempts = [
        (doc_id, "0" * 32),  # wrong signature
        (doc_id, ""),  # missing signature
        (uuid.uuid4(), good),  # id that does not exist
        (doc_id, codes.sign_document("RECEIPT", doc_id, "RCP-2")),  # signed for another reference
    ]
    results = [await service.verify_document(None, "RECEIPT", i, s) for i, s in bad_attempts]
    results.append(await service.verify_document(None, "NOT_A_TYPE", doc_id, good))
    results.append(await service.verify_document(None, "INVOICE", doc_id, good))  # type not registered here
    assert all(r.valid is False for r in results)
    # No information about *why* leaks: every failure is the same empty result.
    assert len({repr(r) for r in results}) == 1
    assert audit_calls == []


async def test_signature_for_another_document_type_does_not_verify(verify_env):
    service, known, _ = verify_env
    doc_id = uuid.uuid4()
    known[doc_id] = _summary("RCP-1")
    wrong_type_sig = codes.sign_document("INVOICE", doc_id, "RCP-1")
    assert not (await service.verify_document(None, "RECEIPT", doc_id, wrong_type_sig)).valid
