"""ABDM gateway abstraction (P8-B01).

`AbdmAdapter` is the seam between ForaCare's domain code and the National
Health Authority's ABDM gateway (docs/integrations.md section 2). Domain
services only ever call this interface, so switching between the offline
`MockAbdmAdapter`, the NHA `SandboxAbdmAdapter` and the live
`ProductionAbdmAdapter` is a configuration change (`Settings.abdm_adapter`),
never a code change - the same pattern as billing's `PaymentAdapter`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


class AbdmError(Exception):
    """Raised by an adapter when the gateway call can't be completed."""

    def __init__(self, message: str, *, code: str = "ABDM_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status: int | None = None  # set when the gateway answered


class AbdmTimeoutError(AbdmError):
    """The gateway did not answer in time (transient - safe to retry)."""

    def __init__(self, message: str = "The ABDM gateway timed out."):
        super().__init__(message, code="ABDM_TIMEOUT")


class AbdmUnavailableError(AbdmError):
    """The gateway is unreachable, overloaded or erroring (transient)."""

    def __init__(self, message: str = "The ABDM gateway is currently unavailable."):
        super().__init__(message, code="ABDM_UNAVAILABLE")


class AbdmAuthError(AbdmError):
    """Our client credentials were rejected - retrying will not help."""

    def __init__(self, message: str = "ABDM rejected the configured credentials."):
        super().__init__(message, code="ABDM_AUTH_FAILED")


class AbdmRejectedError(AbdmError):
    """The gateway rejected the request itself (4xx) - retrying will not help."""

    def __init__(self, message: str = "ABDM rejected the request."):
        super().__init__(message, code="ABDM_REJECTED")


class AbdmNotConfiguredError(AbdmError):
    def __init__(self, message: str):
        super().__init__(message, code="ABDM_NOT_CONFIGURED")


class AbdmNotImplementedError(AbdmError):
    def __init__(self, message: str):
        super().__init__(message, code="ABDM_NOT_IMPLEMENTED")


@dataclass(frozen=True)
class AbdmConnectionStatus:
    """What the UI shows as the ABDM "connection status"."""

    mode: str  # "mock" | "sandbox" | "production"
    connected: bool
    message: str | None = None


@dataclass(frozen=True)
class AbdmOtpChallenge:
    transaction_id: str
    message: str | None = None


@dataclass(frozen=True)
class AbhaProfile:
    abha_number: str  # 14 digits, formatted XX-XXXX-XXXX-XXXX
    abha_address: str
    first_name: str | None = None
    last_name: str | None = None
    gender: str | None = None
    dob: date | None = None


class AbdmAdapter(ABC):
    """ABDM Milestone 1 operations (ABHA identity verification)."""

    mode: str

    @abstractmethod
    async def check_connection(self) -> AbdmConnectionStatus:
        """Reports whether the gateway is reachable with valid credentials.
        Never raises for an unreachable/unconfigured gateway - that is
        reported as `connected=False` with a message."""

    @abstractmethod
    async def request_otp(self, *, auth_method: str, identifier: str) -> AbdmOtpChallenge:
        """Starts Aadhaar/mobile OTP auth (`auth_method` is "AADHAAR_OTP" or
        "MOBILE_OTP") and returns the transaction to verify against."""

    @abstractmethod
    async def verify_otp(self, *, transaction_id: str, otp: str) -> AbhaProfile:
        """Completes the OTP challenge and returns the verified ABHA profile."""
