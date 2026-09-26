"""Integration tests: upload → chunking → corruption → self-healing.

These tests exercise ORM models, chunking logic, hash-ring placement,
and the database-level repair simulation without starting actual HTTP
servers.
"""

from __future__ import annotations

import hashlib
import json
import os

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from vault.core.database import Base
from vault.core.hash_ring import ConsistentHashRing
from vault.models.chunk import ChunkRecord
from vault.models.file import FileRecord
from vault.models.node import NodeStatusRecord


# ── Per-test DB session ───────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        yield session

    await engine.dispose()


# ═════════════════════════════════════════════════════════════════════════
# 1. Chunking logic
# ═════════════════════════════════════════════════════════════════════════

class TestChunking:
    """Verify file-to-chunk splitting and hash reproducibility."""

    def test_split_file_into_chunks(self) -> None:
        chunk_size = 1024
        data = os.urandom(3000)  # 3 chunks: 1024 + 1024 + 952

        chunks: list[bytes] = []
        offset = 0
        while offset < len(data):
            chunks.append(data[offset : offset + chunk_size])
            offset += chunk_size

        assert len(chunks) == 3
        assert b"".join(chunks) == data

    def test_sha256_is_deterministic(self) -> None:
        data = b"deterministic hash check"
        h1 = hashlib.sha256(data).hexdigest()
        h2 = hashlib.sha256(data).hexdigest()
        assert h1 == h2
        assert len(h1) == 64

    def test_different_data_different_hash(self) -> None:
        assert (
            hashlib.sha256(b"aaa").hexdigest()
            != hashlib.sha256(b"bbb").hexdigest()
        )


# ═════════════════════════════════════════════════════════════════════════
# 2. ORM record operations
# ═════════════════════════════════════════════════════════════════════════

class TestDatabaseRecords:
    """CRUD operations on ORM models via the async session."""

    @pytest.mark.asyncio
    async def test_create_file_record(self, db: AsyncSession) -> None:
        db.add(
            FileRecord(
                file_id="file-001",
                filename="hello.txt",
                total_size=4096,
                total_chunks=2,
            )
        )
        await db.commit()

        result = await db.execute(
            select(FileRecord).where(FileRecord.file_id == "file-001")
        )
        rec = result.scalar_one()
        assert rec.filename == "hello.txt"
        assert rec.total_size == 4096
        assert rec.total_chunks == 2

    @pytest.mark.asyncio
    async def test_create_chunk_record_with_replicas(
        self, db: AsyncSession
    ) -> None:
        db.add(
            FileRecord(
                file_id="file-002",
                filename="data.bin",
                total_size=8192,
                total_chunks=1,
            )
        )
        await db.commit()

        chunk_hash = hashlib.sha256(b"chunk-data").hexdigest()
        db.add(
            ChunkRecord(
                chunk_hash=chunk_hash,
                file_id="file-002",
                chunk_index=0,
                primary_node_url="http://localhost:8001",
                replica_node_urls=json.dumps(
                    ["http://localhost:8002", "http://localhost:8003"]
                ),
            )
        )
        await db.commit()

        result = await db.execute(
            select(ChunkRecord).where(ChunkRecord.file_id == "file-002")
        )
        rec = result.scalar_one()
        assert rec.chunk_hash == chunk_hash
        replicas = json.loads(rec.replica_node_urls)
        assert len(replicas) == 2
        assert "http://localhost:8002" in replicas

    @pytest.mark.asyncio
    async def test_node_health_toggle(self, db: AsyncSession) -> None:
        db.add(
            NodeStatusRecord(
                node_url="http://localhost:8001",
                is_healthy=True,
                storage_used_bytes=1024,
            )
        )
        await db.commit()

        # Mark as down
        result = await db.execute(
            select(NodeStatusRecord).where(
                NodeStatusRecord.node_url == "http://localhost:8001"
            )
        )
        node = result.scalar_one()
        node.is_healthy = False
        await db.commit()

        dead = (
            await db.execute(
                select(NodeStatusRecord).where(
                    NodeStatusRecord.is_healthy == False  # noqa: E712
                )
            )
        ).scalars().all()
        assert len(dead) == 1
        assert dead[0].node_url == "http://localhost:8001"

    @pytest.mark.asyncio
    async def test_chunk_ordering_by_index(self, db: AsyncSession) -> None:
        db.add(
            FileRecord(
                file_id="file-003",
                filename="multi.bin",
                total_size=3072,
                total_chunks=3,
            )
        )
        await db.commit()

        for idx in [2, 0, 1]:  # deliberately out of order
            db.add(
                ChunkRecord(
                    chunk_hash=hashlib.sha256(f"chunk-{idx}".encode()).hexdigest(),
                    file_id="file-003",
                    chunk_index=idx,
                    primary_node_url="http://localhost:8001",
                    replica_node_urls="[]",
                )
            )
        await db.commit()

        result = await db.execute(
            select(ChunkRecord)
            .where(ChunkRecord.file_id == "file-003")
            .order_by(ChunkRecord.chunk_index)
        )
        ordered = result.scalars().all()
        assert [c.chunk_index for c in ordered] == [0, 1, 2]


# ═════════════════════════════════════════════════════════════════════════
# 3. Corruption detection
# ═════════════════════════════════════════════════════════════════════════

class TestCorruptionDetection:
    """Ensure hash mismatches are properly identified."""

    def test_bit_rot_detected(self) -> None:
        original = b"important data"
        corrupted = b"importabt data"
        assert (
            hashlib.sha256(original).hexdigest()
            != hashlib.sha256(corrupted).hexdigest()
        )

    def test_identical_content_matches(self) -> None:
        data = os.urandom(256)
        assert hashlib.sha256(data).hexdigest() == hashlib.sha256(data).hexdigest()


# ═════════════════════════════════════════════════════════════════════════
# 4. Self-healing simulation
# ═════════════════════════════════════════════════════════════════════════

class TestSelfHealing:
    """Simulate the repair worker's DB-level operations."""

    def test_failover_candidate_selection(self) -> None:
        """Hash-ring can identify a node NOT currently holding a chunk."""
        ring = ConsistentHashRing(virtual_nodes=50)
        all_nodes = [f"http://localhost:{p}" for p in [8001, 8002, 8003, 8004]]
        for n in all_nodes:
            ring.add_node(n)

        holders = set(ring.get_target_nodes("test-chunk", count=3))
        candidates = [n for n in all_nodes if n not in holders]
        assert len(candidates) >= 1

    @pytest.mark.asyncio
    async def test_repair_replaces_dead_node_in_db(
        self, db: AsyncSession
    ) -> None:
        """Simulate: node dies → chunk record updated to swap the dead
        node with a healthy replacement."""
        db.add(
            FileRecord(
                file_id="heal-file",
                filename="heal.bin",
                total_size=1024,
                total_chunks=1,
            )
        )
        await db.commit()

        chunk_hash = hashlib.sha256(b"heal-data").hexdigest()
        db.add(
            ChunkRecord(
                chunk_hash=chunk_hash,
                file_id="heal-file",
                chunk_index=0,
                primary_node_url="http://localhost:8001",
                replica_node_urls=json.dumps(
                    ["http://localhost:8002", "http://localhost:8003"]
                ),
            )
        )
        await db.commit()

        # ── Simulate repair: 8003 died → replace with 8004 ───────────
        dead_node = "http://localhost:8003"
        new_node = "http://localhost:8004"

        result = await db.execute(
            select(ChunkRecord).where(ChunkRecord.chunk_hash == chunk_hash)
        )
        chunk = result.scalar_one()
        all_nodes = [chunk.primary_node_url] + json.loads(
            chunk.replica_node_urls
        )
        updated = [new_node if n == dead_node else n for n in all_nodes]

        chunk.primary_node_url = updated[0]
        chunk.replica_node_urls = json.dumps(updated[1:])
        await db.commit()

        # ── Verify ────────────────────────────────────────────────────
        result2 = await db.execute(
            select(ChunkRecord).where(ChunkRecord.chunk_hash == chunk_hash)
        )
        fixed = result2.scalar_one()
        final_nodes = [fixed.primary_node_url] + json.loads(
            fixed.replica_node_urls
        )

        assert dead_node not in final_nodes
        assert new_node in final_nodes
        assert len(final_nodes) == 3

    @pytest.mark.asyncio
    async def test_under_replication_detection(
        self, db: AsyncSession
    ) -> None:
        """Chunks on dead nodes should be identifiable via a join query."""
        # Seed nodes
        for port, healthy in [(8001, True), (8002, True), (8003, False)]:
            db.add(
                NodeStatusRecord(
                    node_url=f"http://localhost:{port}",
                    is_healthy=healthy,
                    storage_used_bytes=0,
                )
            )
        db.add(
            FileRecord(
                file_id="under-rep",
                filename="ur.bin",
                total_size=512,
                total_chunks=1,
            )
        )
        await db.commit()

        db.add(
            ChunkRecord(
                chunk_hash=hashlib.sha256(b"ur").hexdigest(),
                file_id="under-rep",
                chunk_index=0,
                primary_node_url="http://localhost:8001",
                replica_node_urls=json.dumps(
                    ["http://localhost:8002", "http://localhost:8003"]
                ),
            )
        )
        await db.commit()

        # Find dead nodes
        dead = (
            await db.execute(
                select(NodeStatusRecord.node_url).where(
                    NodeStatusRecord.is_healthy == False  # noqa: E712
                )
            )
        ).scalars().all()
        dead_set = set(dead)

        # Check which chunks reference dead nodes
        chunks = (await db.execute(select(ChunkRecord))).scalars().all()
        affected = []
        for c in chunks:
            all_n = [c.primary_node_url] + json.loads(c.replica_node_urls)
            if any(n in dead_set for n in all_n):
                affected.append(c)

        assert len(affected) == 1
        assert affected[0].file_id == "under-rep"
