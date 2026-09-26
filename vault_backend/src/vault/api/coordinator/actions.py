"""Coordinates chunking & network orchestration.

Houses the core business logic consumed by the coordinator router:

* ``upload_file``   – slice → hash → distribute → persist metadata
* ``download_file`` – reassemble with automatic replica failover
* ``list_files``    – paginated file index
* ``get_cluster_status`` – aggregate health metrics
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from collections.abc import AsyncGenerator

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vault.core.config import get_settings
from vault.core.hash_ring import ConsistentHashRing
from vault.models.chunk import ChunkRecord
from vault.models.file import FileRecord
from vault.models.node import NodeStatusRecord

logger = logging.getLogger("vault.coordinator.actions")
settings = get_settings()

# ── Module-level hash ring ────────────────────────────────────────────────
hash_ring = ConsistentHashRing(virtual_nodes=settings.VIRTUAL_NODES)
for _url in settings.node_urls:
    hash_ring.add_node(_url)


# ── Upload flow ───────────────────────────────────────────────────────────

async def upload_file(
    filename: str,
    file_bytes: bytes,
    db: AsyncSession,
    owner_id: str | None = None,
    folder_id: str | None = None,
) -> dict:
    """Chunk a file, replicate each chunk across the ring, and record
    all metadata in the database.

    Returns a summary dict suitable for JSON serialisation.
    """
    file_id = str(uuid.uuid4())
    total_size = len(file_bytes)
    chunk_size = settings.CHUNK_SIZE

    # ── 1. Slice into chunks & compute hashes ─────────────────────────
    chunks: list[tuple[int, str, bytes]] = []
    offset = 0
    index = 0
    while offset < total_size:
        chunk_data = file_bytes[offset : offset + chunk_size]
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()
        chunks.append((index, chunk_hash, chunk_data))
        offset += chunk_size
        index += 1

    total_chunks = len(chunks)

    # ── 2. Persist file record ────────────────────────────────────────
    db.add(
        FileRecord(
            file_id=file_id,
            filename=filename,
            owner_id=owner_id,
            folder_id=folder_id,
            total_size=total_size,
            total_chunks=total_chunks,
        )
    )

    # ── 3. Distribute each chunk ──────────────────────────────────────
    async with httpx.AsyncClient(timeout=30.0) as client:
        for chunk_index, chunk_hash, chunk_data in chunks:
            target_nodes = hash_ring.get_target_nodes(
                chunk_hash, settings.REPLICATION_FACTOR
            )
            if not target_nodes:
                raise RuntimeError("No storage nodes available on the hash ring")

            # Upload to all targets in parallel
            tasks = [
                _upload_chunk_to_node(client, node, chunk_hash, chunk_data)
                for node in target_nodes
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful: list[str] = []
            for node_url, result in zip(target_nodes, results):
                if isinstance(result, Exception):
                    logger.error(
                        "Upload chunk %s → %s failed: %s",
                        chunk_hash[:12],
                        node_url,
                        result,
                    )
                else:
                    successful.append(node_url)

            if not successful:
                raise RuntimeError(
                    f"All {len(target_nodes)} uploads failed for chunk {chunk_hash[:12]}"
                )

            db.add(
                ChunkRecord(
                    chunk_hash=chunk_hash,
                    file_id=file_id,
                    chunk_index=chunk_index,
                    primary_node_url=successful[0],
                    replica_node_urls=json.dumps(successful[1:]),
                )
            )

    await db.commit()

    logger.info(
        "Uploaded %s (%s bytes, %d chunks) → file_id=%s",
        filename,
        f"{total_size:,}",
        total_chunks,
        file_id,
    )
    return {
        "file_id": file_id,
        "filename": filename,
        "total_size": total_size,
        "total_chunks": total_chunks,
        "status": "uploaded",
    }


async def _upload_chunk_to_node(
    client: httpx.AsyncClient,
    node_url: str,
    chunk_hash: str,
    chunk_data: bytes,
) -> None:
    """POST a chunk's raw bytes to a single storage node."""
    resp = await client.post(
        f"{node_url}/chunks/{chunk_hash}",
        files={"file": (f"{chunk_hash}.bin", chunk_data, "application/octet-stream")},
    )
    resp.raise_for_status()


# ── Download flow ─────────────────────────────────────────────────────────

async def download_file(
    file_id: str,
    db: AsyncSession,
) -> AsyncGenerator[bytes, None]:
    """Yield reassembled file bytes chunk-by-chunk.

    For each chunk the primary node is tried first; on failure or hash
    mismatch (corruption), replicas are tried in order.
    """
    # Verify file exists
    file_result = await db.execute(
        select(FileRecord).where(FileRecord.file_id == file_id)
    )
    file_record = file_result.scalar_one_or_none()
    if file_record is None:
        raise FileNotFoundError(f"File {file_id} not found")

    # Fetch ordered chunks
    chunk_result = await db.execute(
        select(ChunkRecord)
        .where(ChunkRecord.file_id == file_id)
        .order_by(ChunkRecord.chunk_index)
    )
    chunk_records = chunk_result.scalars().all()
    if not chunk_records:
        raise FileNotFoundError(f"No chunks found for file {file_id}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for chunk in chunk_records:
            all_nodes = [chunk.primary_node_url] + json.loads(
                chunk.replica_node_urls
            )
            data = await _download_chunk_with_failover(
                client, chunk.chunk_hash, all_nodes
            )
            yield data


async def _download_chunk_with_failover(
    client: httpx.AsyncClient,
    chunk_hash: str,
    node_urls: list[str],
) -> bytes:
    """Try each node in order; validate SHA-256 integrity before returning."""
    last_error: Exception | None = None

    for node_url in node_urls:
        try:
            resp = await client.get(f"{node_url}/chunks/{chunk_hash}")
            resp.raise_for_status()
            data = resp.content

            if hashlib.sha256(data).hexdigest() == chunk_hash:
                return data

            logger.warning(
                "Corruption detected for chunk %s on %s — trying next replica",
                chunk_hash[:12],
                node_url,
            )
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            last_error = exc
            logger.warning(
                "Node %s unreachable for chunk %s: %s — trying next replica",
                node_url,
                chunk_hash[:12],
                exc,
            )

    raise RuntimeError(
        f"All nodes exhausted for chunk {chunk_hash[:12]}: {last_error}"
    )


# ── Deletion & Rename ───────────────────────────────────────────────────────

async def delete_file(file_id: str, db: AsyncSession, owner_id: str | None = None) -> bool:
    print(f"DEBUG DELETE: file_id='{file_id}', owner_id='{owner_id}'")
    stmt = select(FileRecord).where(FileRecord.file_id == file_id)
    if owner_id:
        stmt = stmt.where(FileRecord.owner_id == owner_id)
    file_result = await db.execute(stmt)
    file_record = file_result.scalar_one_or_none()
    print(f"DEBUG DELETE: file_record={file_record}")
    if not file_record:
        return False
    
    # In a full implementation, we would also call nodes to delete the physical chunks.
    # For now, we delete metadata and chunks from DB, letting a garbage collector clean nodes.
    await db.delete(file_record)
    
    # Also delete chunks metadata
    chunk_stmt = select(ChunkRecord).where(ChunkRecord.file_id == file_id)
    chunk_result = await db.execute(chunk_stmt)
    chunks = chunk_result.scalars().all()
    for c in chunks:
        await db.delete(c)
        
    await db.commit()
    return True

async def rename_file(file_id: str, new_name: str, db: AsyncSession, owner_id: str | None = None) -> bool:
    stmt = select(FileRecord).where(FileRecord.file_id == file_id)
    if owner_id:
        stmt = stmt.where(FileRecord.owner_id == owner_id)
    file_result = await db.execute(stmt)
    file_record = file_result.scalar_one_or_none()
    if not file_record:
        return False
        
    file_record.filename = new_name
    await db.commit()
    return True

from vault.models.share import ShareLinkRecord

async def generate_share_link(file_id: str, db: AsyncSession, owner_id: str | None = None) -> str | None:
    # Check ownership
    stmt = select(FileRecord).where(FileRecord.file_id == file_id)
    if owner_id:
        stmt = stmt.where(FileRecord.owner_id == owner_id)
    file_record = (await db.execute(stmt)).scalar_one_or_none()
    if not file_record:
        return None
        
    share_record = ShareLinkRecord(file_id=file_id, owner_id=owner_id)
    db.add(share_record)
    await db.commit()
    await db.refresh(share_record)
    return share_record.share_id

async def get_shared_file_metadata(share_id: str, db: AsyncSession) -> FileRecord | None:
    stmt = select(ShareLinkRecord).where(ShareLinkRecord.share_id == share_id)
    share_record = (await db.execute(stmt)).scalar_one_or_none()
    if not share_record:
        return None
        
    file_stmt = select(FileRecord).where(FileRecord.file_id == share_record.file_id)
    return (await db.execute(file_stmt)).scalar_one_or_none()

# ── Listing & status ─────────────────────────────────────────────────────

async def list_files(
    db: AsyncSession, 
    owner_id: str | None = None,
    folder_id: str | None = None,
) -> dict:
    """Return all uploaded files ordered by creation time (newest first)."""
    stmt = select(FileRecord)
    if owner_id:
        stmt = stmt.where(FileRecord.owner_id == owner_id)
    if folder_id:
        stmt = stmt.where(FileRecord.folder_id == folder_id)
    elif owner_id:
        # If no folder requested, default to root for this user
        stmt = stmt.where(FileRecord.folder_id == None)

    stmt = stmt.order_by(FileRecord.created_at.desc())
    result = await db.execute(stmt)
    files = result.scalars().all()
    return {
        "files": [
            {
                "file_id": f.file_id,
                "filename": f.filename,
                "total_size": f.total_size,
                "total_chunks": f.total_chunks,
                "created_at": f.created_at.isoformat() if f.created_at else "",
            }
            for f in files
        ],
        "total": len(files),
    }

from vault.models.folder import FolderRecord

async def create_folder(name: str, db: AsyncSession, owner_id: str | None = None, parent_id: str | None = None) -> dict:
    folder = FolderRecord(name=name, owner_id=owner_id, parent_id=parent_id)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return {
        "folder_id": folder.folder_id,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "created_at": folder.created_at.isoformat() if folder.created_at else "",
    }

async def list_folders(db: AsyncSession, owner_id: str | None = None, parent_id: str | None = None) -> dict:
    stmt = select(FolderRecord)
    if owner_id:
        stmt = stmt.where(FolderRecord.owner_id == owner_id)
    if parent_id:
        stmt = stmt.where(FolderRecord.parent_id == parent_id)
    elif owner_id:
        stmt = stmt.where(FolderRecord.parent_id == None)

    stmt = stmt.order_by(FolderRecord.created_at.desc())
    result = await db.execute(stmt)
    folders = result.scalars().all()
    return {
        "folders": [
            {
                "folder_id": f.folder_id,
                "name": f.name,
                "parent_id": f.parent_id,
                "created_at": f.created_at.isoformat() if f.created_at else "",
            }
            for f in folders
        ]
    }


async def get_cluster_status(db: AsyncSession) -> dict:
    """Aggregate cluster health: file count, chunk count, node statuses."""
    total_files = (
        await db.execute(select(func.count(FileRecord.file_id)))
    ).scalar() or 0

    total_chunks = (
        await db.execute(select(func.count(ChunkRecord.id)))
    ).scalar() or 0

    node_result = await db.execute(select(NodeStatusRecord))
    nodes = node_result.scalars().all()

    return {
        "total_files": total_files,
        "total_chunks": total_chunks,
        "active_nodes": sum(1 for n in nodes if n.is_healthy),
        "dead_nodes": sum(1 for n in nodes if not n.is_healthy),
        "replication_factor": settings.REPLICATION_FACTOR,
        "nodes": [
            {
                "node_url": n.node_url,
                "is_healthy": n.is_healthy,
                "last_seen": n.last_seen.isoformat() if n.last_seen else "",
                "storage_used_bytes": n.storage_used_bytes,
            }
            for n in nodes
        ],
    }
