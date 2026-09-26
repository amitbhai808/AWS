"""Maps local disk IO endpoints (/chunks/{id}).

Each storage node runs its own instance of this router. The ``configure()``
function must be called at startup to set the data directory and port before
any requests are served.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["storage"])

# ── Module-level state (set via configure()) ──────────────────────────────
DATA_DIR: Path = Path("./data")
NODE_PORT: int = 8001


def configure(data_dir: str, port: int) -> None:
    """Initialise storage directory and advertised port.

    Called once by :func:`vault.daemon_main.create_app` during startup.
    """
    global DATA_DIR, NODE_PORT
    DATA_DIR = Path(data_dir)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    NODE_PORT = port


# ── Chunk CRUD endpoints ─────────────────────────────────────────────────

@router.post("/chunks/{chunk_id}", status_code=status.HTTP_201_CREATED)
async def store_chunk(chunk_id: str, file: UploadFile) -> dict[str, str]:
    """Write uploaded bytes to disk after verifying the SHA-256 digest
    matches the requested ``chunk_id``."""
    raw_bytes = await file.read()
    computed_hash = hashlib.sha256(raw_bytes).hexdigest()

    if computed_hash != chunk_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hash mismatch: expected {chunk_id}, computed {computed_hash}",
        )

    chunk_path = DATA_DIR / f"{chunk_id}.bin"
    chunk_path.write_bytes(raw_bytes)
    return {"status": "stored", "chunk_id": chunk_id}


@router.get("/chunks/{chunk_id}")
async def retrieve_chunk(chunk_id: str) -> StreamingResponse:
    """Stream a chunk from local disk back to the caller."""
    chunk_path = DATA_DIR / f"{chunk_id}.bin"

    if not chunk_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk {chunk_id} not found",
        )

    def _iter_file():
        with open(chunk_path, "rb") as fh:
            while block := fh.read(8192):
                yield block

    return StreamingResponse(_iter_file(), media_type="application/octet-stream")


@router.post("/chunks/{chunk_id}/verify")
async def verify_chunk(chunk_id: str) -> dict[str, str]:
    """Re-compute the SHA-256 of the stored chunk and compare it against
    ``chunk_id``.  Returns 409 on corruption (bit rot)."""
    chunk_path = DATA_DIR / f"{chunk_id}.bin"

    if not chunk_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk {chunk_id} not found",
        )

    computed_hash = hashlib.sha256(chunk_path.read_bytes()).hexdigest()

    if computed_hash == chunk_id:
        return {"chunk_id": chunk_id, "status": "valid"}

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Chunk {chunk_id} is corrupted (got {computed_hash})",
    )


@router.delete("/chunks/{chunk_id}")
async def delete_chunk(chunk_id: str) -> dict[str, str]:
    """Remove a chunk file from local disk."""
    chunk_path = DATA_DIR / f"{chunk_id}.bin"

    if not chunk_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk {chunk_id} not found",
        )

    chunk_path.unlink()
    return {"status": "deleted", "chunk_id": chunk_id}


# ── Health probe ──────────────────────────────────────────────────────────

@router.get("/health")
async def health_check() -> dict[str, object]:
    """Return node readiness status and cumulative disk usage."""
    used_bytes = (
        sum(f.stat().st_size for f in DATA_DIR.iterdir() if f.is_file())
        if DATA_DIR.exists()
        else 0
    )
    return {
        "status": "healthy",
        "port": NODE_PORT,
        "storage_used_bytes": used_bytes,
    }
