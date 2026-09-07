import asyncio
import sys

import pytest
from fastapi.testclient import TestClient

from app.main import app

if sys.platform == "win32":
    # asyncpg's connection I/O is incompatible with the default Windows
    # ProactorEventLoop when bridged through TestClient's sync-over-async
    # portal.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def client():
    # TestClient opens a fresh anyio portal (and event loop) per request
    # unless used as a context manager, in which case one portal/loop is
    # kept alive for its whole lifetime. The async DB engine's pooled
    # asyncpg connections are bound to the loop they were created on, so
    # without this a second request's fresh loop fails to reuse a
    # connection pooled by a first request's now-closed loop.
    with TestClient(app) as test_client:
        yield test_client
