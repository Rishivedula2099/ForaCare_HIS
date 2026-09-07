from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import SessionLocal, engine, get_db


def test_engine_is_configured_from_settings():
    settings = get_settings()

    assert engine.url.render_as_string(hide_password=False) == settings.database_url
    assert engine.pool.size() == settings.db_pool_size


async def test_get_db_yields_an_async_session():
    generator = get_db()
    session = await generator.__anext__()

    try:
        assert isinstance(session, AsyncSession)
        assert session.bind is engine
    finally:
        await generator.aclose()


async def test_session_local_produces_independent_sessions():
    async with SessionLocal() as first, SessionLocal() as second:
        assert first is not second
