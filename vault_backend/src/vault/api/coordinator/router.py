"""Maps upload/download/list endpoints for the Coordinator API Gateway."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from vault.api.coordinator.actions import (
    create_folder,
    delete_file,
    download_file,
    generate_share_link,
    get_cluster_status,
    get_shared_file_metadata,
    list_files,
    list_folders,
    rename_file,
    upload_file,
)
from vault.api.coordinator.auth import get_current_user_id
from vault.core.database import get_db

router = APIRouter(tags=["coordinator"])


# ── File operations ───────────────────────────────────────────────────────

@router.post("/files/upload", status_code=status.HTTP_201_CREATED)
async def handle_upload(
    file: UploadFile,
    folder_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_id),
) -> dict:
    """Accept a file, split it into chunks, distribute across the cluster,
    and persist metadata."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    try:
        return await upload_file(
            filename=file.filename,
            file_bytes=file_bytes,
            db=db,
            owner_id=user_id,
            folder_id=folder_id,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )


@router.get("/files/{file_id}/download")
async def handle_download(
    file_id: str,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Reassemble and stream a file from its distributed chunks."""
    try:
        return StreamingResponse(
            download_file(file_id, db),
            media_type="application/octet-stream",
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def handle_delete(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_id),
):
    # DEBUG: Try to fetch the file to see why delete_file fails
    from sqlalchemy import select
    from vault.models.file import FileRecord
    stmt = select(FileRecord).where(FileRecord.file_id == file_id)
    if user_id:
        stmt = stmt.where(FileRecord.owner_id == user_id)
    file_result = await db.execute(stmt)
    file_record = file_result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(status_code=404, detail=f"DEBUG: Not found. Passed user_id: {user_id}. DB matched: {bool(file_record)}")
        
    success = await delete_file(file_id, db, owner_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found or not owned by user")
    return None

class RenameRequest(BaseModel):
    name: str

@router.patch("/files/{file_id}/rename")
async def handle_rename(
    file_id: str,
    req: RenameRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_id),
) -> dict:
    success = await rename_file(file_id, req.name, db, owner_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found or not owned by user")
    return {"status": "ok", "new_name": req.name}

@router.get("/files/")
async def handle_list_files(
    folder_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_id),
) -> dict:
    """Return a listing of uploaded files."""
    return await list_files(db, owner_id=user_id, folder_id=folder_id)

@router.post("/files/{file_id}/share")
async def handle_share_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_id),
) -> dict:
    share_id = await generate_share_link(file_id, db, owner_id=user_id)
    if not share_id:
        raise HTTPException(status_code=404, detail="File not found or not owned by user")
    return {"share_id": share_id, "share_url": f"/share/{share_id}"}

@router.get("/share/{share_id}/download")
async def handle_shared_download(
    share_id: str,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    file_record = await get_shared_file_metadata(share_id, db)
    if not file_record:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
        
    try:
        return StreamingResponse(
            download_file(file_record.file_id, db),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{file_record.filename}"'}
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

# ── Folder operations ───────────────────────────────────────────────────────

from pydantic import BaseModel

class CreateFolderRequest(BaseModel):
    name: str
    parent_id: str | None = None

@router.post("/folders/", status_code=status.HTTP_201_CREATED)
async def handle_create_folder(
    req: CreateFolderRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_id),
) -> dict:
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await create_folder(req.name, db, owner_id=user_id, parent_id=req.parent_id)

@router.get("/folders/")
async def handle_list_folders(
    parent_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_id),
) -> dict:
    return await list_folders(db, owner_id=user_id, parent_id=parent_id)


# ── Cluster operations ───────────────────────────────────────────────────

@router.get("/cluster/status")
async def handle_cluster_status(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return aggregate cluster health metrics."""
    return await get_cluster_status(db)
