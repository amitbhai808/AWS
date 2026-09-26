"""Consistent Hashing Engine for chunk placement.

Uses SHA-256 for ring position hashing and virtual nodes to ensure an even
distribution of chunks across physical storage nodes.
"""

from __future__ import annotations

import hashlib
from bisect import bisect_right, insort


class ConsistentHashRing:
    """Deterministic consistent-hash ring with configurable virtual nodes.

    Each physical node is mapped to ``virtual_nodes`` positions on the ring.
    Chunk placement walks clockwise from the chunk's hash to collect the
    requested number of *unique* physical nodes.
    """

    def __init__(self, virtual_nodes: int = 100) -> None:
        self._virtual_nodes = virtual_nodes
        self._ring: dict[int, str] = {}          # hash → physical node URL
        self._sorted_keys: list[int] = []        # sorted ring positions
        self._nodes: set[str] = set()             # registered physical nodes

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _hash(key: str) -> int:
        """Return a deterministic integer hash using SHA-256."""
        return int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)

    # ── Ring mutation ─────────────────────────────────────────────────────

    def add_node(self, node_url: str) -> None:
        """Insert a physical node (with all its virtual replicas) into the ring."""
        if node_url in self._nodes:
            return
        self._nodes.add(node_url)
        for i in range(self._virtual_nodes):
            h = self._hash(f"{node_url}#vnode-{i}")
            self._ring[h] = node_url
            insort(self._sorted_keys, h)

    def remove_node(self, node_url: str) -> None:
        """Remove a physical node and all its virtual replicas from the ring."""
        if node_url not in self._nodes:
            return
        self._nodes.discard(node_url)
        for i in range(self._virtual_nodes):
            h = self._hash(f"{node_url}#vnode-{i}")
            self._ring.pop(h, None)
            try:
                self._sorted_keys.remove(h)
            except ValueError:
                pass

    # ── Placement query ───────────────────────────────────────────────────

    def get_target_nodes(self, chunk_id: str, count: int) -> list[str]:
        """Walk clockwise from *chunk_id*'s hash and return up to *count*
        unique physical node URLs.

        Returns
        -------
        list[str]
            ``[primary_node, replica_1, replica_2, ...]``
        """
        if not self._sorted_keys:
            return []

        count = min(count, len(self._nodes))
        h = self._hash(chunk_id)
        start = bisect_right(self._sorted_keys, h) % len(self._sorted_keys)

        result: list[str] = []
        seen: set[str] = set()

        for offset in range(len(self._sorted_keys)):
            idx = (start + offset) % len(self._sorted_keys)
            node_url = self._ring[self._sorted_keys[idx]]
            if node_url not in seen:
                seen.add(node_url)
                result.append(node_url)
                if len(result) == count:
                    break

        return result

    # ── Introspection ─────────────────────────────────────────────────────

    @property
    def nodes(self) -> set[str]:
        """Return a copy of the set of registered physical node URLs."""
        return set(self._nodes)

    def __len__(self) -> int:
        return len(self._sorted_keys)

    def __repr__(self) -> str:
        return (
            f"ConsistentHashRing(physical_nodes={len(self._nodes)}, "
            f"virtual_nodes={self._virtual_nodes}, "
            f"ring_size={len(self._sorted_keys)})"
        )
