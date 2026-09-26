"""SQLAlchemy engine, sessions, and tables definition."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from vault.core.config import get_settings

# ── Declarative base ──────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Declarative base class shared by every ORM model."""


# ── Engine & session factory ──────────────────────────────────────────────

_settings = get_settings()

engine = create_async_engine(
    _settings.async_database_url,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Bootstrap helpers ─────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables that are registered with ``Base.metadata``.

    Models are imported here so their table definitions are discovered
    regardless of import order elsewhere in the application.
    """
    import vault.models.file   # noqa: F401
    import vault.models.chunk  # noqa: F401
    import vault.models.node   # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency – yields an async DB session and handles commit /
    rollback lifecycle automatically."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
