"""File response metadata DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    """Returned after a successful file upload."""

    file_id: str
    filename: str
    total_size: int
    total_chunks: int
    status: str = "uploaded"


class FileInfo(BaseModel):
    """Single file entry used in listings."""

    file_id: str
    filename: str
    total_size: int
    total_chunks: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FileListResponse(BaseModel):
    """Wrapper for paginated file listings."""

    files: list[FileInfo]
    total: int
