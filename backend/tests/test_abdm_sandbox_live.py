"""P8-B06 stage 2 (sandbox): live checks against the NHA sandbox gateway.

Opt-in - skipped unless credentials are supplied through the environment:

    ABDM_SANDBOX_CLIENT_ID=... ABDM_SANDBOX_CLIENT_SECRET=... \
        python -m pytest -m sandbox tests/test_abdm_sandbox_live.py

Only session creation is exercised: these tests send no patient data. Extend
them with OTP/ABHA flows once the sandbox adapter implements them.
"""
import os

import pytest

from app.modules.abdm.adapter import AbdmAuthError
from app.modules.abdm.factory import SANDBOX_URL
from app.modules.abdm.sandbox_adapter import SandboxAbdmAdapter

CLIENT_ID = os.environ.get("ABDM_SANDBOX_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("ABDM_SANDBOX_CLIENT_SECRET", "")
BASE_URL = os.environ.get("ABDM_SANDBOX_BASE_URL", SANDBOX_URL)

pytestmark = [
    pytest.mark.sandbox,
    pytest.mark.skipif(
        not (CLIENT_ID and CLIENT_SECRET),
        reason="ABDM_SANDBOX_CLIENT_ID / ABDM_SANDBOX_CLIENT_SECRET not set",
    ),
]


async def test_sandbox_accepts_our_credentials():
    adapter = SandboxAbdmAdapter(base_url=BASE_URL, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    status = await adapter.check_connection()
    assert status.mode == "sandbox"
    assert status.connected, status.message


async def test_sandbox_rejects_bad_credentials_without_retrying_forever():
    adapter = SandboxAbdmAdapter(
        base_url=BASE_URL, client_id=CLIENT_ID, client_secret="definitely-wrong-secret"
    )
    with pytest.raises(AbdmAuthError):
        await adapter._get_token()
