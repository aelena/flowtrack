from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import verify_api_key
from ..inbox import INBOX_NAME, find_inbox_project, resolve_inbox_project
from ..models import Project, Snippet
from ..schemas import ExtensionProjectCreate, SnippetCreate, SnippetOut

router = APIRouter(prefix="/api/extension", tags=["extension"], dependencies=[Depends(verify_api_key)])


@router.get("/projects")
async def list_projects_simple(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.archived.is_(False)).order_by(Project.work_name))
    projects = result.scalars().all()
    return [{"id": str(p.id), "name": p.work_name} for p in projects]


@router.post("/project", status_code=201)
async def create_project_simple(data: ExtensionProjectCreate, db: AsyncSession = Depends(get_db)):
    """Start a project from the clipper, with only a name.

    An idea found on the web often is not a clip for an existing project — it is
    the start of a new one. Making the user open the app to create it first is
    how the idea gets lost. Everything else about the project is filled in later
    in FlowTrack proper.
    """
    name = data.name.strip()
    if not name:
        raise HTTPException(422, "Project name cannot be blank")

    project = Project(work_name=name)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return {"id": str(project.id), "name": project.work_name}


@router.get("/inbox")
async def get_inbox(db: AsyncSession = Depends(get_db)):
    """Where an unfiled clip lands, without creating it.

    A read stays a read: null means the inbox does not exist yet, which is the
    honest answer before anything has been clipped into it.
    """
    project = await find_inbox_project(db)
    if not project:
        return {"id": None, "name": INBOX_NAME, "exists": False}
    return {"id": str(project.id), "name": project.work_name, "exists": True}


@router.post("/snippet", response_model=SnippetOut, status_code=201)
async def save_snippet(data: SnippetCreate, db: AsyncSession = Depends(get_db)):
    if data.project_id is None:
        # Nothing chosen: the idea arrived before its project did. Park it in the
        # inbox rather than making the user pick a home for it at capture time.
        project_id = (await resolve_inbox_project(db)).id
    else:
        # The clipper remembers a project id between sessions, so it can outlive
        # the project. Without this check that arrives as a foreign key violation
        # and a 500, which the extension can only report as an opaque failure.
        if not await db.get(Project, data.project_id):
            raise HTTPException(404, "Project not found")
        project_id = data.project_id

    snippet = Snippet(
        project_id=project_id,
        snippet_type=data.type,
        content=data.content,
        source_url=data.source_url,
    )
    db.add(snippet)
    await db.commit()
    await db.refresh(snippet)
    return snippet
