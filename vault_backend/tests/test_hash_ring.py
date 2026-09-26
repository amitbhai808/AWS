"""Ring distribution validation tests.

Verifies:
- Basic add / remove operations
- Deterministic, repeatable placement
- Roughly even distribution across nodes
- Minimal key redistribution when a node is added
- Edge cases (empty ring, single node, idempotent operations)
"""

from __future__ import annotations

import pytest

from vault.core.hash_ring import ConsistentHashRing


class TestAddRemove:
    """Node lifecycle on the ring."""

    def test_add_node(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=10)
        ring.add_node("http://localhost:8001")
        assert "http://localhost:8001" in ring.nodes
        assert len(ring.nodes) == 1

    def test_remove_node(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=10)
        ring.add_node("http://localhost:8001")
        ring.remove_node("http://localhost:8001")
        assert len(ring.nodes) == 0
        assert len(ring) == 0

    def test_add_is_idempotent(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=10)
        ring.add_node("http://localhost:8001")
        ring.add_node("http://localhost:8001")
        assert len(ring.nodes) == 1

    def test_remove_nonexistent_is_safe(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=10)
        ring.remove_node("http://localhost:9999")  # must not raise
        assert len(ring.nodes) == 0


class TestPlacement:
    """Chunk → node placement queries."""

    def test_empty_ring_returns_empty(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=10)
        assert ring.get_target_nodes("anything", count=3) == []

    def test_single_node_caps_at_one(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=10)
        ring.add_node("http://localhost:8001")
        targets = ring.get_target_nodes("chunk-xyz", count=3)
        assert targets == ["http://localhost:8001"]

    def test_returns_unique_nodes(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=50)
        for port in [8001, 8002, 8003, 8004]:
            ring.add_node(f"http://localhost:{port}")

        targets = ring.get_target_nodes("chunk-abc", count=3)
        assert len(targets) == 3
        assert len(set(targets)) == 3

    def test_deterministic(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=50)
        for port in [8001, 8002, 8003]:
            ring.add_node(f"http://localhost:{port}")

        assert (
            ring.get_target_nodes("my-chunk", count=2)
            == ring.get_target_nodes("my-chunk", count=2)
        )

    def test_count_exceeds_nodes(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=10)
        ring.add_node("http://localhost:8001")
        ring.add_node("http://localhost:8002")
        targets = ring.get_target_nodes("chunk", count=5)
        assert len(targets) == 2


class TestDistribution:
    """Statistical distribution quality."""

    def test_roughly_even(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=150)
        nodes = [f"http://localhost:{p}" for p in range(8001, 8005)]
        for n in nodes:
            ring.add_node(n)

        counts: dict[str, int] = {n: 0 for n in nodes}
        total = 2000
        for i in range(total):
            primary = ring.get_target_nodes(f"chunk-{i}", count=1)[0]
            counts[primary] += 1

        expected = total / len(nodes)
        for node, count in counts.items():
            deviation = abs(count - expected) / expected
            assert deviation < 0.30, (
                f"{node}: {count}/{total} — {deviation:.0%} deviation exceeds 30%"
            )

    def test_minimal_redistribution_on_add(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=100)
        for port in [8001, 8002, 8003]:
            ring.add_node(f"http://localhost:{port}")

        before = {
            f"c-{i}": ring.get_target_nodes(f"c-{i}", 1)[0] for i in range(200)
        }

        ring.add_node("http://localhost:8004")

        after = {
            f"c-{i}": ring.get_target_nodes(f"c-{i}", 1)[0] for i in range(200)
        }

        moved = sum(1 for k in before if before[k] != after[k])
        # Adding 1 node to a 3-node ring should move ~25% of keys
        assert moved < 100, f"{moved}/200 keys moved — too many"


class TestRepr:
    """Smoke tests for __repr__ and __len__."""

    def test_repr(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=5)
        ring.add_node("http://localhost:8001")
        r = repr(ring)
        assert "physical_nodes=1" in r
        assert "virtual_nodes=5" in r
        assert "ring_size=5" in r

    def test_len(self) -> None:
        ring = ConsistentHashRing(virtual_nodes=10)
        ring.add_node("http://localhost:8001")
        ring.add_node("http://localhost:8002")
        assert len(ring) == 20
