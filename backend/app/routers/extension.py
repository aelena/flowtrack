from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import verify_api_key
from ..models import Project, Snippet
from ..schemas import SnippetCreate, SnippetOut

router = APIRouter(prefix="/api/extension", tags=["extension"], dependencies=[Depends(verify_api_key)])


@router.get("/projects")
async def list_projects_simple(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.archived.is_(False)).order_by(Project.work_name))
    projects = result.scalars().all()
    return [{"id": str(p.id), "name": p.work_name} for p in projects]


@router.post("/snippet", response_model=SnippetOut, status_code=201)
async def save_snippet(data: SnippetCreate, db: AsyncSession = Depends(get_db)):
    snippet = Snippet(
        project_id=data.project_id,
        snippet_type=data.type,
        content=data.content,
        source_url=data.source_url,
    )
    db.add(snippet)
    await db.commit()
    await db.refresh(snippet)
    return snippet
