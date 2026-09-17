"""Signed QR check-in references (P3-B06).

A reference is `<nonce>.<signature>` where `nonce` is a random, unguessable
value and `signature` is an HMAC-SHA256 of the nonce keyed by
`settings.qr_signing_secret_key`, truncated to 32 hex chars (128 bits -
still computationally infeasible to forge, and keeps the QR payload small).

This is deliberately the *only* thing ever encoded in a check-in QR - no
patient name, MRN, diagnosis, or other clinical data ever goes into the
value rendered as a QR code (see `EncounterOut`/the frontend `QRCodeSVG`
usage, which is always given exactly this string and nothing else).

The signature lets `verify_qr_code` reject a malformed/tampered/guessed
code immediately, without a database round trip - the database lookup
(by the full reference, which must also exist and be unrevoked/unexpired)
is a second, independent layer on top of this.
"""

import hashlib
import hmac
import secrets

from app.core.config import get_settings

_NONCE_BYTES = 18
_SIGNATURE_HEX_LENGTH = 32


def _sign(nonce: str) -> str:
    secret = get_settings().qr_signing_secret_key.encode()
    return hmac.new(secret, nonce.encode(), hashlib.sha256).hexdigest()[:_SIGNATURE_HEX_LENGTH]


def generate_qr_reference() -> str:
    nonce = secrets.token_urlsafe(_NONCE_BYTES)
    return f"{nonce}.{_sign(nonce)}"


def verify_qr_signature(reference: str) -> bool:
    if "." not in reference:
        return False
    nonce, _, signature = reference.rpartition(".")
    if not nonce or not signature:
        return False
    expected = _sign(nonce)
    return hmac.compare_digest(expected, signature)
