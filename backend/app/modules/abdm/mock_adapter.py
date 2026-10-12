"""Offline `AbdmAdapter` for local development, tests and demos. Accepts any
6-digit OTP and derives a deterministic ABHA profile from the identifier."""

from __future__ import annotations

import hashlib
import uuid

from app.modules.abdm.adapter import (
    AbdmAdapter,
    AbdmConnectionStatus,
    AbdmError,
    AbdmOtpChallenge,
    AbdmRejectedError,
    AbdmTimeoutError,
    AbdmUnavailableError,
    AbhaProfile,
)


class MockAbdmAdapter(AbdmAdapter):
    mode = "mock"

    def __init__(self) -> None:
        self._pending: dict[str, str] = {}
        self._otp_requests = 0

    def _maybe_fail(self, *, flaky_applies: bool = False) -> None:
        """Raises the failure named by `Settings.abdm_mock_simulate`."""
        from app.core.config import get_settings

        settings = get_settings()
        # Failure simulation is a dev/UAT aid - ignored outside local.
        mode = settings.abdm_mock_simulate if settings.is_local else ""
        if mode == "timeout":
            raise AbdmTimeoutError()
        if mode == "unavailable":
            raise AbdmUnavailableError()
        if mode == "rejected":
            raise AbdmRejectedError()
        if mode == "flaky" and flaky_applies and self._otp_requests % 2 == 1:
            raise AbdmUnavailableError()

    async def check_connection(self) -> AbdmConnectionStatus:
        return AbdmConnectionStatus(
            mode=self.mode, connected=True, message="Mock ABDM adapter (no live gateway)."
        )

    async def request_otp(self, *, auth_method: str, identifier: str) -> AbdmOtpChallenge:
        self._otp_requests += 1
        self._maybe_fail(flaky_applies=True)
        transaction_id = f"MOCK-TXN-{uuid.uuid4().hex[:12].upper()}"
        self._pending[transaction_id] = identifier
        return AbdmOtpChallenge(transaction_id=transaction_id, message="Mock OTP sent.")

    async def verify_otp(self, *, transaction_id: str, otp: str) -> AbhaProfile:
        self._maybe_fail()
        identifier = self._pending.pop(transaction_id, None)
        if identifier is None:
            raise AbdmError("Unknown or expired transaction.", code="ABDM_INVALID_TRANSACTION")
        if not (otp.isdigit() and len(otp) == 6):
            raise AbdmError("OTP must be 6 digits.", code="ABDM_INVALID_OTP")
        digits = f"{int(hashlib.sha256(identifier.encode()).hexdigest(), 16) % 10**14:014d}"
        return AbhaProfile(
            abha_number=f"{digits[:2]}-{digits[2:6]}-{digits[6:10]}-{digits[10:]}",
            abha_address=f"user{digits[-6:]}@sbx",
        )
