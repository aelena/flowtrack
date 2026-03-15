import os
import re
import uuid as uuid_mod
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..dependencies import verify_api_key
from ..models import ProjectFile
from ..schemas import FileOut

router = APIRouter(prefix="/api/projects/{project_id}/files", tags=["files"], dependencies=[Depends(verify_api_key)])

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


def _sanitize_folder(folder: str | None) -> str | None:
    if not folder:
        return None
    folder = folder.replace("\\", "/")
    parts = [p for p in folder.split("/") if p and p != "." and p != ".."]
    if not parts:
        return None
    sanitized = "/".join(parts)
    if re.search(r"[<>:\"|?*\x00-\x1f]", sanitized):
        raise HTTPException(400, "Folder name contains invalid characters")
    return sanitized


@router.get("/", response_model=list[FileOut])
async def list_files(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id).order_by(ProjectFile.created_at)
    )
    return result.scalars().all()


@router.post("/", response_model=FileOut, status_code=201)
async def upload_file(
    project_id: UUID,
    file: UploadFile = File(...),
    folder: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    ext = os.path.splitext(file.filename)[1].lstrip(".").lower() if file.filename else "bin"

    safe_folder = _sanitize_folder(folder)

    store_dir = os.path.join(settings.storage_path, str(project_id))
    if safe_folder:
        store_dir = os.path.join(store_dir, safe_folder)

    resolved = os.path.realpath(store_dir)
    storage_root = os.path.realpath(settings.storage_path)
    if not resolved.startswith(storage_root + os.sep) and resolved != storage_root:
        raise HTTPException(400, "Invalid folder path")

    os.makedirs(store_dir, exist_ok=True)

    unique_name = f"{uuid_mod.uuid4().hex}_{file.filename}"
    full_path = os.path.join(store_dir, unique_name)

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(413, f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB")

    # Relative path for DB
    rel_path = os.path.relpath(full_path, settings.storage_path)

    pf = ProjectFile(
        project_id=project_id,
        filename=file.filename,
        file_type=ext,
        file_path=rel_path,
        folder=safe_folder,
    )
    db.add(pf)
    await db.commit()
    await db.refresh(pf)
    return pf


@router.get("/{file_id}/download")
async def download_file(project_id: UUID, file_id: UUID, db: AsyncSession = Depends(get_db)):
    pf = await db.get(ProjectFile, file_id)
    if not pf or pf.project_id != project_id:
        raise HTTPException(404, "File not found")
    full_path = os.path.realpath(os.path.join(settings.storage_path, pf.file_path))
    storage_root = os.path.realpath(settings.storage_path)
    if not full_path.startswith(storage_root + os.sep):
        raise HTTPException(403, "Access denied")
    if not os.path.exists(full_path):
        raise HTTPException(404, "File missing from storage")
    return FileResponse(full_path, filename=pf.filename)


@router.delete("/{file_id}", status_code=204)
async def delete_file(project_id: UUID, file_id: UUID, db: AsyncSession = Depends(get_db)):
    pf = await db.get(ProjectFile, file_id)
    if not pf or pf.project_id != project_id:
        raise HTTPException(404, "File not found")
    full_path = os.path.join(settings.storage_path, pf.file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
    await db.delete(pf)
    await db.commit()
