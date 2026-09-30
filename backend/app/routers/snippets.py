from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import verify_api_key
from ..models import Project, Snippet
from ..schemas import SnippetOut, SnippetUpdate

router = APIRouter(prefix="/api/snippets", tags=["snippets"], dependencies=[Depends(verify_api_key)])


@router.get("/", response_model=list[SnippetOut])
async def list_snippets(
    project_id: UUID | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Newest first, because a clip is read to triage it, not to re-read the oldest.

    The clipper could only write until now: snippets were reachable through the
    project export zip and the whole-database backup, and nowhere else.
    """
    query = select(Snippet).order_by(Snippet.created_at.desc()).limit(limit)
    if project_id:
        query = query.where(Snippet.project_id == project_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.put("/{snippet_id}", response_model=SnippetOut)
async def move_snippet(snippet_id: UUID, data: SnippetUpdate, db: AsyncSession = Depends(get_db)):
    """Re-file a clip.

    Clipping happens before you know where the idea belongs, so the project
    picked at capture time is a guess. Without this the guess is permanent.
    """
    snippet = await db.get(Snippet, snippet_id)
    if not snippet:
        raise HTTPException(404, "Snippet not found")
    if not await db.get(Project, data.project_id):
        raise HTTPException(404, "Project not found")
    snippet.project_id = data.project_id
    await db.commit()
    await db.refresh(snippet)
    return snippet


@router.delete("/{snippet_id}", status_code=204)
async def delete_snippet(snippet_id: UUID, db: AsyncSession = Depends(get_db)):
    snippet = await db.get(Snippet, snippet_id)
    if not snippet:
        raise HTTPException(404, "Snippet not found")
    await db.delete(snippet)
    await db.commit()
