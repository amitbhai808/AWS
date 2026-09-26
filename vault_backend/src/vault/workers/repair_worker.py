"""Background self-healing loop & node heartbeats.

The :class:`RepairWorker` runs as an ``asyncio`` task inside the coordinator
process.  Each cycle it:

1. Pings every registered storage node (``GET /health``).
2. Marks unreachable nodes as unhealthy in the ``node_status`` table.
3. Scans chunk metadata for under-replicated data on dead nodes.
4. Re-replicates affected chunks to new healthy targets.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from vault.core.config import get_settings
from vault.core.database import async_session_factory
from vault.core.hash_ring import ConsistentHashRing
from vault.models.chunk import ChunkRecord
from vault.models.node import NodeStatusRecord

logger = logging.getLogger("vault.repair_worker")
settings = get_settings()


class RepairWorker:
    """Autonomous background worker for cluster health & self-healing."""

    def __init__(self) -> None:
        self._running = True
        self._hash_ring = ConsistentHashRing(virtual_nodes=settings.VIRTUAL_NODES)
        for url in settings.node_urls:
            self._hash_ring.add_node(url)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def stop(self) -> None:
        """Signal the run-loop to exit gracefully."""
        self._running = False

    async def run(self) -> None:
        """Main loop: heartbeat → repair → sleep → repeat."""
        logger.info(
            "Repair worker started (heartbeat every %ds)",
            settings.HEARTBEAT_INTERVAL_SECONDS,
        )
        # Give storage nodes a moment to boot
        await asyncio.sleep(2)

        while self._running:
            try:
                await self.heartbeat_check()
                await self.self_healing_routine()
            except Exception:
                logger.exception("Repair worker cycle error")
            await asyncio.sleep(settings.HEARTBEAT_INTERVAL_SECONDS)

        logger.info("Repair worker stopped.")

    # ── Heartbeat ─────────────────────────────────────────────────────────

    async def heartbeat_check(self) -> None:
        """Probe every storage node and upsert its health record."""
        async with httpx.AsyncClient(
            timeout=settings.NODE_TIMEOUT_SECONDS,
        ) as client:
            async with async_session_factory() as db:
                for node_url in settings.node_urls:
                    is_healthy = False
                    storage_used = 0

                    try:
                        resp = await client.get(f"{node_url}/health")
                        resp.raise_for_status()
                        body = resp.json()
                        is_healthy = body.get("status") == "healthy"
                        storage_used = body.get("storage_used_bytes", 0)
                    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                        logger.warning("Node %s unreachable: %s", node_url, exc)

                    # Upsert
                    result = await db.execute(
                        select(NodeStatusRecord).where(
                            NodeStatusRecord.node_url == node_url
                        )
                    )
                    record = result.scalar_one_or_none()

                    now = datetime.now(timezone.utc)
                    if record is not None:
                        record.is_healthy = is_healthy
                        record.storage_used_bytes = storage_used
                        if is_healthy:
                            record.last_seen = now
                    else:
                        db.add(
                            NodeStatusRecord(
                                node_url=node_url,
                                is_healthy=is_healthy,
                                storage_used_bytes=storage_used,
                                last_seen=now,
                            )
                        )

                await db.commit()

    # ── Self-healing ──────────────────────────────────────────────────────

    async def self_healing_routine(self) -> None:
        """Find chunks sitting on dead nodes and replicate them to healthy
        replacements, restoring the target replication factor."""
        async with async_session_factory() as db:
            # Collect dead / alive sets
            dead_result = await db.execute(
                select(NodeStatusRecord.node_url).where(
                    NodeStatusRecord.is_healthy == False  # noqa: E712
                )
            )
            dead_urls: set[str] = set(dead_result.scalars().all())
            if not dead_urls:
                return

            alive_result = await db.execute(
                select(NodeStatusRecord.node_url).where(
                    NodeStatusRecord.is_healthy == True  # noqa: E712
                )
            )
            alive_urls: set[str] = set(alive_result.scalars().all())
            if not alive_urls:
                logger.error("No healthy nodes — cannot repair!")
                return

            # Scan every chunk for dead-node references
            all_chunks = (
                (await db.execute(select(ChunkRecord))).scalars().all()
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
                for chunk in all_chunks:
                    all_nodes = [chunk.primary_node_url] + json.loads(
                        chunk.replica_node_urls
                    )
                    dead_holders = [n for n in all_nodes if n in dead_urls]
                    if not dead_holders:
                        continue

                    alive_holders = [n for n in all_nodes if n in alive_urls]
                    if not alive_holders:
                        logger.error(
                            "Chunk %s has NO healthy holders — potential data loss!",
                            chunk.chunk_hash[:12],
                        )
                        continue

                    for dead_node in dead_holders:
                        current_set = set(all_nodes)
                        candidates = [
                            n for n in alive_urls if n not in current_set
                        ]
                        if not candidates:
                            logger.warning(
                                "No candidate nodes for chunk %s repair",
                                chunk.chunk_hash[:12],
                            )
                            continue

                        new_node = candidates[0]
                        source = alive_holders[0]

                        try:
                            # Download from healthy source
                            dl = await client.get(
                                f"{source}/chunks/{chunk.chunk_hash}"
                            )
                            dl.raise_for_status()

                            # Upload to new target
                            ul = await client.post(
                                f"{new_node}/chunks/{chunk.chunk_hash}",
                                files={
                                    "file": (
                                        f"{chunk.chunk_hash}.bin",
                                        dl.content,
                                        "application/octet-stream",
                                    )
                                },
                            )
                            ul.raise_for_status()

                            # Swap dead → new in the node list
                            all_nodes = [
                                new_node if n == dead_node else n
                                for n in all_nodes
                            ]
                            chunk.primary_node_url = all_nodes[0]
                            chunk.replica_node_urls = json.dumps(all_nodes[1:])

                            logger.info(
                                "[REPAIR WORKER] Self-healing complete: "
                                "Chunk %s replicated from %s to %s "
                                "(replaced dead node %s)",
                                chunk.chunk_hash[:12],
                                source,
                                new_node,
                                dead_node,
                            )
                        except (
                            httpx.RequestError,
                            httpx.HTTPStatusError,
                        ) as exc:
                            logger.error(
                                "Repair failed for chunk %s (%s → %s): %s",
                                chunk.chunk_hash[:12],
                                source,
                                new_node,
                                exc,
                            )

            await db.commit()
