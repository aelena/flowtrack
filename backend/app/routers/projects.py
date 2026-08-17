import io
import json
import os
import zipfile
from datetime import UTC
from datetime import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..database import get_db
from ..dependencies import verify_api_key
from ..models import Project, Snippet, TaskStatus
from ..schemas import CollaboratorCreate, ProjectCreate, ProjectListOut, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"], dependencies=[Depends(verify_api_key)])


def compute_task_completion(tasks):
    if not tasks:
        return 0.0
    done = sum(1 for t in tasks if t.status == TaskStatus.done)
    return round((done / len(tasks)) * 100, 1)


@router.get("/", response_model=list[ProjectListOut])
async def list_projects(
    search: str | None = None,
    area_id: UUID | None = None,
    tag: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    archived: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = select(Project).options(selectinload(Project.tasks)).where(Project.archived == archived)

    if search:
        query = query.where(Project.work_name.ilike(f"%{search}%") | Project.final_name.ilike(f"%{search}%"))
    if area_id:
        query = query.where(Project.area_id == area_id)
    if tag:
        query = query.where(Project.tags.contains([tag]))

    ALLOWED_SORT = {"created_at", "work_name", "star_rating", "updated_at", "subjective_completion"}
    sort_col = getattr(Project, sort_by) if sort_by in ALLOWED_SORT else Project.created_at
    query = query.order_by(sort_col.asc() if sort_order == "asc" else sort_col.desc())

    result = await db.execute(query)
    projects = result.scalars().all()

    out = []
    for p in projects:
        data = ProjectListOut.model_validate(p)
        data.task_completion = compute_task_completion(p.tasks)
        out.append(data)
    return out


@router.get("/tags/all", response_model=list[str])
async def get_all_tags(db: AsyncSession = Depends(get_db)):
    """Get all unique tags across all projects."""
    result = await db.execute(
        text(
            "SELECT DISTINCT jsonb_array_elements_text(tags) AS tag FROM projects WHERE tags IS NOT NULL AND tags != '[]'::jsonb ORDER BY tag"
        )
    )
    return [row[0] for row in result.fetchall()]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).options(selectinload(Project.tasks)).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    out = ProjectOut.model_validate(project)
    out.task_completion = compute_task_completion(project.tasks)
    return out


@router.post("/", response_model=ProjectOut, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(**data.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ProjectOut.model_validate(project)


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: UUID, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).options(selectinload(Project.tasks)).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    out = ProjectOut.model_validate(project)
    out.task_completion = compute_task_completion(project.tasks)
    return out


async def _set_archived(project_id: UUID, archived: bool, db: AsyncSession) -> ProjectOut:
    result = await db.execute(
        select(Project).options(selectinload(Project.tasks)).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    project.archived = archived
    await db.commit()
    await db.refresh(project)
    out = ProjectOut.model_validate(project)
    out.task_completion = compute_task_completion(project.tasks)
    return out


@router.post("/{project_id}/archive", response_model=ProjectOut)
async def archive_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    return await _set_archived(project_id, True, db)


@router.post("/{project_id}/unarchive", response_model=ProjectOut)
async def unarchive_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Archiving was one-way: there was no route back out of the archive."""
    return await _set_archived(project_id, False, db)


@router.get("/{project_id}/export")
async def export_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.tasks), selectinload(Project.notes), selectinload(Project.files))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    snippets_result = await db.execute(
        select(Snippet).where(Snippet.project_id == project_id).order_by(Snippet.created_at)
    )
    snippets = snippets_result.scalars().all()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        meta = {
            "work_name": project.work_name,
            "final_name": project.final_name,
            "description": project.description,
            "vision": project.vision,
            "goal": project.goal,
            "completion_criteria": project.completion_criteria,
            "abandonment_criteria": project.abandonment_criteria,
            "desired_end_date": str(project.desired_end_date) if project.desired_end_date else None,
            "github_repo": project.github_repo,
            "website": project.website,
            "star_rating": project.star_rating,
            "subjective_completion": project.subjective_completion,
            "collaborators": project.collaborators,
        }
        zf.writestr("project.json", json.dumps(meta, indent=2))

        tasks_data = [
            {"title": t.title, "description": t.description, "status": t.status.value} for t in project.tasks
        ]
        zf.writestr("tasks.json", json.dumps(tasks_data, indent=2))

        notes_data = [
            {"content": n.content, "task_id": str(n.task_id) if n.task_id else None} for n in project.notes
        ]
        zf.writestr("notes.json", json.dumps(notes_data, indent=2))

        snippets_data = [
            {
                "snippet_type": s.snippet_type,
                "content": s.content,
                "source_url": s.source_url,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in snippets
        ]
        zf.writestr("snippets.json", json.dumps(snippets_data, indent=2))

        for f in project.files:
            full_path = os.path.join(settings.storage_path, f.file_path)
            if os.path.exists(full_path):
                arcname = f"files/{f.folder + '/' if f.folder else ''}{f.filename}"
                zf.write(full_path, arcname)

    buf.seek(0)
    name = project.work_name.replace(" ", "_")
    ts = dt.now(UTC).strftime("%Y%m%d-%H%M%S")
    filename = f"{name}-{ts}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{project_id}/pending")
async def get_pending(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.tasks), selectinload(Project.notes))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    pending_tasks = [
        {"id": str(t.id), "title": t.title, "status": t.status.value}
        for t in project.tasks
        if t.status != TaskStatus.done
    ]
    return {
        "project": project.work_name,
        "pending_tasks": pending_tasks,
        "total_tasks": len(project.tasks),
        "done_tasks": len(project.tasks) - len(pending_tasks),
        "notes_count": len(project.notes),
    }


@router.post("/{project_id}/collaborators", response_model=ProjectOut)
async def add_collaborator(
    project_id: UUID, collaborator: CollaboratorCreate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project).options(selectinload(Project.tasks)).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    collabs = list(project.collaborators or [])
    collabs.append(collaborator.model_dump())
    project.collaborators = collabs
    await db.commit()
    await db.refresh(project)
    out = ProjectOut.model_validate(project)
    out.task_completion = compute_task_completion(project.tasks)
    return out
