"""Async SQLAlchemy database lifecycle and request sessions."""

import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import settings
from database.models import Base

logger = logging.getLogger(__name__)


def _async_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


_db_url = _async_database_url(settings.DATABASE_URL)

engine = create_async_engine(
    _db_url,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def _try_connect_and_create_tables() -> None:
    """Try to connect and create all tables."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def init_db() -> None:
    """Create tables, with automatic SQLite fallback if PostgreSQL is unreachable."""
    global engine, AsyncSessionLocal

    try:
        await _try_connect_and_create_tables()
        db_display = _db_url.split("@")[-1] if "@" in _db_url else _db_url
        logger.info(f"✅ Database connected: {db_display}")

    except Exception as e:
        logger.warning(
            f"⚠️  Could not connect to PostgreSQL ({type(e).__name__}: {e})\n"
            "🔄 Falling back to local SQLite database (security_os.db) ..."
        )
        sqlite_url = "sqlite+aiosqlite:///./security_os.db"
        engine = create_async_engine(sqlite_url, echo=settings.DATABASE_ECHO, future=True)
        AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Local SQLite fallback database ready (security_os.db)")


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield one short-lived session per request or background operation."""
    async with AsyncSessionLocal() as session:
        yield session
