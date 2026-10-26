import asyncio
import sys

import pytest

if sys.platform == "win32":
    # The parent conftest selects the Selector loop for asyncpg; Playwright
    # spawns Chromium as a subprocess, which needs the Proactor loop. These
    # tests talk to a separately running stack and never touch asyncpg.
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@pytest.fixture(autouse=True)
def _clear_session_cookies():
    """Overrides the parent's autouse fixture, which needs the in-process
    app/database; browser tests keep their own cookie jar per context."""
    yield
