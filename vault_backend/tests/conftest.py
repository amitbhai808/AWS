"""Global fixtures (mock database, mock storage nodes).

All test modules can request ``db_session`` for an in-memory async SQLite
session and ``temp_data_dir`` for a throwaway chunk-storage directory.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ── Override settings BEFORE any vault imports ────────────────────────────
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["NODE_PORTS"] = "[8001,8002,8003,8004]"

from vault.core.database import Base  # noqa: E402
from vault.models import ChunkRecord, FileRecord, NodeStatusRecord  # noqa: E402, F401


# ── Event loop ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Provide a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Database session ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh in-memory async session with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ── Temp storage directory ────────────────────────────────────────────────

@pytest.fixture
def temp_data_dir() -> Path:
    """Provide a temporary directory for chunk storage tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
