from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import verify_api_key
from ..models import Note
from ..schemas import NoteCreate, NoteOut, NoteUpdate

router = APIRouter(prefix="/api/notes", tags=["notes"], dependencies=[Depends(verify_api_key)])


@router.get("/", response_model=list[NoteOut])
async def list_notes(
    project_id: UUID | None = Query(None),
    task_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Note).order_by(Note.created_at.desc())
    if project_id:
        query = query.where(Note.project_id == project_id)
    if task_id:
        query = query.where(Note.task_id == task_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=NoteOut, status_code=201)
async def create_note(data: NoteCreate, db: AsyncSession = Depends(get_db)):
    note = Note(**data.model_dump())
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.put("/{note_id}", response_model=NoteOut)
async def update_note(note_id: UUID, data: NoteUpdate, db: AsyncSession = Depends(get_db)):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    note.content = data.content
    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=204)
async def delete_note(note_id: UUID, db: AsyncSession = Depends(get_db)):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    await db.delete(note)
    await db.commit()
