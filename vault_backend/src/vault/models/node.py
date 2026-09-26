"""Maps 'node_status' table."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from vault.core.database import Base


class NodeStatusRecord(Base):
    """Tracks the health and disk usage of every storage node.

    Updated periodically by the repair worker's heartbeat loop.
    """

    __tablename__ = "node_status"

    node_url: Mapped[str] = mapped_column(String(256), primary_key=True)
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    storage_used_bytes: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    def __repr__(self) -> str:
        status = "UP" if self.is_healthy else "DOWN"
        return f"<NodeStatusRecord {self.node_url} [{status}]>"
