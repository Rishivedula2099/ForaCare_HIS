"""P7-B05: QR codes and barcodes for printed documents.

- `code128_svg`: a Code 128 (subset B) barcode as an inline SVG, generated
  here so no extra dependency or image file is needed and it stays crisp at
  any print size.
- `sign_document` / `verify_signature`: the HMAC that makes a document's QR
  unforgeable. The signature covers the document type, id AND the printed
  reference number, so a QR cannot be lifted onto a document that shows a
  different number.
- `build_verify_url` / `qr_data_uri`: the public verification link and its QR.
"""
import base64
import hashlib
import hmac
import io
import re
import uuid
from urllib.parse import urlencode

import qrcode
from markupsafe import Markup

from app.core.config import get_settings
from app.core.exceptions import AppError

MAX_REFERENCE_LENGTH = 40
_SIGNATURE_HEX_LENGTH = 32  # 128 bits, matching the OPD/lab QR tokens

# --- Code 128 ---------------------------------------------------------------

# Bar/space element widths for symbol values 0..105 (six elements each) and
# the stop symbol (value 106, seven elements). Each six-element pattern sums
# to 11 modules; the stop pattern to 13.
_PATTERNS = (
    "212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 "
    "221312 231212 112232 122132 122231 113222 123122 123221 223211 221132 "
    "221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 "
    "212123 212321 232121 111323 131123 131321 112313 132113 132311 211313 "
    "231113 231311 112133 112331 132131 113123 113321 133121 313121 211331 "
    "231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 "
    "314111 221411 431111 111224 111422 121124 121421 141122 141221 112214 "
    "112412 122114 122411 142112 142211 241211 221114 413111 241112 134111 "
    "111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 "
    "214121 412121 111143 111341 131141 114113 114311 411113 411311 113141 "
    "114131 311141 411131 211412 211214 211232"
).split()
_STOP_PATTERN = "2331112"
START_B = 104

_PRINTABLE_ASCII = re.compile(r"^[\x20-\x7e]+$")


def validate_reference(reference: str) -> str:
    """A reference must be non-empty printable ASCII that fits the barcode."""
    if not reference or not reference.strip():
        raise AppError("A document reference is required.", code="INVALID_DOCUMENT_REFERENCE")
    if len(reference) > MAX_REFERENCE_LENGTH:
        raise AppError(
            f"Document reference is longer than {MAX_REFERENCE_LENGTH} characters.",
            code="INVALID_DOCUMENT_REFERENCE",
        )
    if not _PRINTABLE_ASCII.match(reference):
        raise AppError(
            "Document reference contains characters that cannot be barcoded.", code="INVALID_DOCUMENT_REFERENCE"
        )
    return reference


def code128_values(text: str) -> list[int]:
    """Symbol values for `text` in Code 128-B, including start, checksum and stop."""
    validate_reference(text)
    data = [ord(ch) - 32 for ch in text]
    checksum = (START_B + sum(value * (index + 1) for index, value in enumerate(data))) % 103
    return [START_B, *data, checksum, 106]


def code128_svg(text: str) -> Markup:
    """Inline SVG barcode, one unit per module, stretching to its container."""
    quiet = 10
    x = quiet
    bars: list[str] = []
    for value in code128_values(text):
        pattern = _STOP_PATTERN if value == 106 else _PATTERNS[value]
        for index, width in enumerate(int(c) for c in pattern):
            if index % 2 == 0:  # even positions are bars, odd are spaces
                bars.append(f'<rect x="{x}" y="0" width="{width}" height="40"/>')
            x += width
    total = x + quiet
    return Markup(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} 40" preserveAspectRatio="none" '
        f'class="barcode" role="img" aria-label="Barcode"><g fill="#000">{"".join(bars)}</g></svg>'
    )


# --- Signed verification QR -------------------------------------------------


def sign_document(doc_type: str, resource_id: uuid.UUID, reference: str) -> str:
    # "doc:v1" separates this from the OPD/lab QR tokens that share the key.
    message = f"doc:v1:{doc_type}:{resource_id}:{reference}".encode()
    secret = get_settings().qr_signing_secret_key.encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()[:_SIGNATURE_HEX_LENGTH]


def verify_signature(doc_type: str, resource_id: uuid.UUID, reference: str, signature: str) -> bool:
    expected = sign_document(doc_type, resource_id, reference)
    return hmac.compare_digest(expected, signature or "")


def build_verify_url(base_url: str, doc_type: str, resource_id: uuid.UUID, reference: str) -> str:
    """The URL a printed QR encodes; fails fast if it would not verify."""
    signature = sign_document(doc_type, resource_id, reference)
    if not verify_signature(doc_type, resource_id, reference, signature):  # defensive self-check
        raise AppError("Generated document signature failed validation.", code="INVALID_DOCUMENT_REFERENCE")
    query = urlencode({"t": doc_type, "id": str(resource_id), "sig": signature})
    return f"{base_url.rstrip('/')}/api/v1/documents/verify?{query}"


def qr_data_uri(text: str, *, box_size: int = 4, border: int = 1) -> str:
    buffer = io.BytesIO()
    qrcode.make(text, box_size=box_size, border=border).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
