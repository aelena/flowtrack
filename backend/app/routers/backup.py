import json
from datetime import datetime, date
from uuid import UUID

from fastapi import APIRouter, Depends, Body
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..dependencies import verify_api_key
from ..models import Area, Project, Task, Note, Snippet, TaskStatus, ProjectStatus

router = APIRouter(prefix="/api/backup", tags=["backup"], dependencies=[Depends(verify_api_key)])


def _serialize_dt(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Not serializable: {type(obj)}")


def _project_to_dict(p):
    return {
        "id": str(p.id),
        "work_name": p.work_name,
        "final_name": p.final_name,
        "description": p.description,
        "vision": p.vision,
        "goal": p.goal,
        "completion_criteria": p.completion_criteria,
        "abandonment_criteria": p.abandonment_criteria,
        "desired_end_date": p.desired_end_date.isoformat() if p.desired_end_date else None,
        "github_repo": p.github_repo,
        "website": p.website,
        "star_rating": p.star_rating,
        "subjective_completion": p.subjective_completion,
        "local_dir": p.local_dir,
        "area_id": str(p.area_id) if p.area_id else None,
        "archived": p.archived,
        "status": p.status.value if p.status else "active",
        "collaborators": p.collaborators or [],
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "status": t.status.value if t.status else "new",
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in (p.tasks or [])
        ],
        "notes": [
            {
                "id": str(n.id),
                "content": n.content,
                "task_id": str(n.task_id) if n.task_id else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "updated_at": n.updated_at.isoformat() if n.updated_at else None,
            }
            for n in (p.notes or [])
        ],
    }


@router.get("/export")
async def export_all(db: AsyncSession = Depends(get_db)):
    """Export all areas, projects (with tasks, notes), and snippets as JSON."""
    # Areas
    areas_result = await db.execute(select(Area).order_by(Area.name))
    areas = [
        {"id": str(a.id), "name": a.name, "created_at": a.created_at.isoformat() if a.created_at else None}
        for a in areas_result.scalars().all()
    ]

    # Projects with tasks and notes
    projects_result = await db.execute(
        select(Project)
        .options(selectinload(Project.tasks).selectinload(Task.notes), selectinload(Project.notes))
        .order_by(Project.created_at)
    )
    projects = [_project_to_dict(p) for p in projects_result.scalars().all()]

    # Snippets
    snippets_result = await db.execute(select(Snippet).order_by(Snippet.created_at))
    snippets = [
        {
            "id": str(s.id),
            "project_id": str(s.project_id),
            "snippet_type": s.snippet_type,
            "content": s.content,
            "source_url": s.source_url,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in snippets_result.scalars().all()
    ]

    return {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "areas": areas,
        "projects": projects,
        "snippets": snippets,
    }


@router.post("/import")
async def import_all(data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Import areas, projects (with tasks, notes), and snippets from JSON.

    This merges data: existing records with matching IDs are skipped,
    new records are inserted. To do a full replace, clear the database first.
    """
    imported = {"areas": 0, "projects": 0, "tasks": 0, "notes": 0, "snippets": 0}

    # Import areas
    for a_data in data.get("areas", []):
        area_id = UUID(a_data["id"]) if a_data.get("id") else None
        existing = await db.get(Area, area_id) if area_id else None
        if existing:
            continue
        area = Area(
            id=area_id,
            name=a_data["name"],
        )
        if a_data.get("created_at"):
            area.created_at = datetime.fromisoformat(a_data["created_at"])
        db.add(area)
        imported["areas"] += 1

    await db.flush()

    # Import projects
    for p_data in data.get("projects", []):
        project_id = UUID(p_data["id"]) if p_data.get("id") else None
        existing = await db.get(Project, project_id) if project_id else None
        if existing:
            continue

        project = Project(
            id=project_id,
            work_name=p_data["work_name"],
            final_name=p_data.get("final_name"),
            description=p_data.get("description"),
            vision=p_data.get("vision"),
            goal=p_data.get("goal"),
            completion_criteria=p_data.get("completion_criteria"),
            abandonment_criteria=p_data.get("abandonment_criteria"),
            desired_end_date=date.fromisoformat(p_data["desired_end_date"]) if p_data.get("desired_end_date") else None,
            github_repo=p_data.get("github_repo"),
            website=p_data.get("website"),
            star_rating=p_data.get("star_rating"),
            subjective_completion=p_data.get("subjective_completion", 0),
            local_dir=p_data.get("local_dir"),
            area_id=UUID(p_data["area_id"]) if p_data.get("area_id") else None,
            archived=p_data.get("archived", False),
            status=ProjectStatus(p_data.get("status", "active")),
            collaborators=p_data.get("collaborators", []),
        )
        if p_data.get("created_at"):
            project.created_at = datetime.fromisoformat(p_data["created_at"])
        if p_data.get("updated_at"):
            project.updated_at = datetime.fromisoformat(p_data["updated_at"])
        db.add(project)
        imported["projects"] += 1

        await db.flush()

        # Import tasks for this project
        for t_data in p_data.get("tasks", []):
            task_id = UUID(t_data["id"]) if t_data.get("id") else None
            existing_task = await db.get(Task, task_id) if task_id else None
            if existing_task:
                continue
            task = Task(
                id=task_id,
                project_id=project.id,
                title=t_data["title"],
                description=t_data.get("description"),
                status=TaskStatus(t_data.get("status", "new")),
            )
            if t_data.get("created_at"):
                task.created_at = datetime.fromisoformat(t_data["created_at"])
            if t_data.get("updated_at"):
                task.updated_at = datetime.fromisoformat(t_data["updated_at"])
            db.add(task)
            imported["tasks"] += 1

        # Import notes for this project
        for n_data in p_data.get("notes", []):
            note_id = UUID(n_data["id"]) if n_data.get("id") else None
            existing_note = await db.get(Note, note_id) if note_id else None
            if existing_note:
                continue
            note = Note(
                id=note_id,
                project_id=project.id,
                task_id=UUID(n_data["task_id"]) if n_data.get("task_id") else None,
                content=n_data["content"],
            )
            if n_data.get("created_at"):
                note.created_at = datetime.fromisoformat(n_data["created_at"])
            if n_data.get("updated_at"):
                note.updated_at = datetime.fromisoformat(n_data["updated_at"])
            db.add(note)
            imported["notes"] += 1

    await db.flush()

    # Import snippets
    for s_data in data.get("snippets", []):
        snippet_id = UUID(s_data["id"]) if s_data.get("id") else None
        existing_snippet = await db.get(Snippet, snippet_id) if snippet_id else None
        if existing_snippet:
            continue
        snippet = Snippet(
            id=snippet_id,
            project_id=UUID(s_data["project_id"]),
            snippet_type=s_data["snippet_type"],
            content=s_data["content"],
            source_url=s_data.get("source_url"),
        )
        if s_data.get("created_at"):
            snippet.created_at = datetime.fromisoformat(s_data["created_at"])
        db.add(snippet)
        imported["snippets"] += 1

    await db.commit()

    return {"status": "ok", "imported": imported}
