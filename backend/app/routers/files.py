import os
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
    # Determine file type from extension
    ext = os.path.splitext(file.filename)[1].lstrip(".").lower() if file.filename else "bin"

    # Create storage directory
    store_dir = os.path.join(settings.storage_path, str(project_id))
    if folder:
        store_dir = os.path.join(store_dir, folder)
    os.makedirs(store_dir, exist_ok=True)

    # Save file with unique name
    unique_name = f"{uuid_mod.uuid4().hex}_{file.filename}"
    full_path = os.path.join(store_dir, unique_name)

    content = await file.read()
    with open(full_path, "wb") as f:
        f.write(content)

    # Relative path for DB
    rel_path = os.path.relpath(full_path, settings.storage_path)

    pf = ProjectFile(
        project_id=project_id,
        filename=file.filename,
        file_type=ext,
        file_path=rel_path,
        folder=folder,
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
    full_path = os.path.join(settings.storage_path, pf.file_path)
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
