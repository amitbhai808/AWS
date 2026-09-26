"""Maps 'files' table."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from vault.core.database import Base


class FileRecord(Base):
    """Stores metadata for every uploaded file."""

    __tablename__ = "files"

    file_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String, nullable=True)
    folder_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    total_size: Mapped[int] = mapped_column(Integer, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<FileRecord file_id={self.file_id!r} "
            f"filename={self.filename!r} size={self.total_size}>"
        )
