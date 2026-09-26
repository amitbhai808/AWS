"""Cluster status response DTOs."""

from __future__ import annotations

from pydantic import BaseModel


class NodeInfo(BaseModel):
    """Health snapshot for a single storage node."""

    node_url: str
    is_healthy: bool
    last_seen: str
    storage_used_bytes: int


class ClusterStatusResponse(BaseModel):
    """Aggregate cluster health and metrics."""

    total_files: int
    total_chunks: int
    active_nodes: int
    dead_nodes: int
    replication_factor: int
    nodes: list[NodeInfo]
