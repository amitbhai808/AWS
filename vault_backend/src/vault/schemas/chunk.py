"""Chunk mapping response DTOs."""

from __future__ import annotations

from pydantic import BaseModel


class ChunkPlacement(BaseModel):
    """Placement details for a single chunk."""

    chunk_hash: str
    chunk_index: int
    primary_node_url: str
    replica_node_urls: list[str]


class ChunkVerifyResponse(BaseModel):
    """Result of a chunk integrity check."""

    chunk_id: str
    status: str  # "valid" | "corrupted"


class ChunkHealthResponse(BaseModel):
    """Storage-node health probe response."""

    status: str
    port: int
    storage_used_bytes: int
