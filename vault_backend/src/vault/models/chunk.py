"""Maps 'chunk_metadata' table."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from vault.core.database import Base


class ChunkRecord(Base):
    """Tracks where each chunk is stored across the cluster.

    ``chunk_hash`` is the SHA-256 digest of the raw chunk bytes and doubles
    as the filename on storage nodes (``{chunk_hash}.bin``).

    ``replica_node_urls`` is a JSON-encoded ``list[str]`` of node base URLs
    holding additional copies beyond the primary.
    """

    __tablename__ = "chunk_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("files.file_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_node_url: Mapped[str] = mapped_column(String(256), nullable=False)
    replica_node_urls: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )

    def __repr__(self) -> str:
        return (
            f"<ChunkRecord hash={self.chunk_hash[:12]}… "
            f"file={self.file_id} idx={self.chunk_index}>"
        )
