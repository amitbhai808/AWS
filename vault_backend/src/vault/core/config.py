"""Cluster configuration (Replication factor N, etc.)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global system parameters for Vault v0.1-beta."""

    # ── Chunking ──────────────────────────────────────────────────────────
    CHUNK_SIZE: int = Field(
        default=4 * 1024 * 1024,
        description="Chunk size in bytes (default 4 MB)",
    )

    # ── Replication ───────────────────────────────────────────────────────
    REPLICATION_FACTOR: int = Field(
        default=3,
        description="Number of copies per chunk across storage nodes",
    )

    # ── Consistent hashing ────────────────────────────────────────────────
    VIRTUAL_NODES: int = Field(
        default=100,
        description="Virtual nodes per physical node on the hash ring",
    )

    # ── Health checks ─────────────────────────────────────────────────────
    HEARTBEAT_INTERVAL_SECONDS: int = Field(
        default=3,
        description="Seconds between heartbeat pings to storage nodes",
    )
    NODE_TIMEOUT_SECONDS: float = Field(
        default=2.0,
        description="HTTP timeout when probing node health",
    )

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./vault_metadata.db",
        description="Async database connection URL (SQLite or PostgreSQL)",
    )

    # ── Storage nodes ─────────────────────────────────────────────────────
    NODE_PORTS: list[int] = Field(
        default=[8001, 8002, 8003, 8004],
        description="Ports for locally-spawned storage nodes",
    )
    NODE_HOST: str = Field(
        default="localhost",
        description="Hostname / IP for storage nodes",
    )
    STORAGE_NODES: list[str] | None = Field(
        default=None,
        description="Explicit list of storage-node base URLs (overrides NODE_HOST + NODE_PORTS)",
    )

    # ── Coordinator ───────────────────────────────────────────────────────
    COORDINATOR_PORT: int = Field(
        default=8000,
        description="Port for the coordinator API gateway",
    )

    # ── Derived helpers ───────────────────────────────────────────────────
    @property
    def node_urls(self) -> list[str]:
        """Return the full list of storage-node base URLs."""
        if self.STORAGE_NODES:
            return self.STORAGE_NODES
        return [f"http://{self.NODE_HOST}:{port}" for port in self.NODE_PORTS]

    @property
    def async_database_url(self) -> str:
        """Return DATABASE_URL formatted for async drivers.

        Handles two Neon-specific quirks that trip up asyncpg:
        1. Rewrites ``postgresql://`` → ``postgresql+asyncpg://``.
        2. Strips ``channel_binding`` (unsupported by asyncpg).
        3. Translates ``sslmode`` → ``ssl`` (asyncpg's parameter name).
        """
        import urllib.parse

        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        else:
            return url  # sqlite — no query-param mangling needed

        parsed = urllib.parse.urlsplit(url)
        qs = urllib.parse.parse_qs(parsed.query)
        qs.pop("channel_binding", None)
        if "sslmode" in qs:
            qs["ssl"] = qs.pop("sslmode")
        new_query = urllib.parse.urlencode(qs, doseq=True)
        return urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment)
        )

    model_config = {
        "env_file": [".env.local", ".env"],
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()
