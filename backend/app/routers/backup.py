from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..dependencies import verify_api_key
from ..models import Area, Note, Project, ProjectStatus, Snippet, Task, TaskStatus

router = APIRouter(prefix="/api/backup", tags=["backup"], dependencies=[Depends(verify_api_key)])


def _safe_uuid(val):
    if not val:
        return None
    try:
        return UUID(str(val))
    except (ValueError, AttributeError):
        return None


def _safe_dt(val):
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None


def _safe_date(val):
    if not val:
        return None
    try:
        return date.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None


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
        "tags": p.tags or [],
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
    areas_result = await db.execute(select(Area).order_by(Area.name))
    areas = [
        {"id": str(a.id), "name": a.name, "created_at": a.created_at.isoformat() if a.created_at else None}
        for a in areas_result.scalars().all()
    ]

    projects_result = await db.execute(
        select(Project)
        .options(selectinload(Project.tasks).selectinload(Task.notes), selectinload(Project.notes))
        .order_by(Project.created_at)
    )
    projects = [_project_to_dict(p) for p in projects_result.scalars().all()]

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
        "exported_at": datetime.now(UTC).isoformat(),
        "areas": areas,
        "projects": projects,
        "snippets": snippets,
    }


@router.post("/import")
async def import_all(data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Import areas, projects (with tasks, notes), and snippets from JSON.

    Merges data: existing records with matching IDs are skipped,
    new records are inserted.
    """
    imported = {"areas": 0, "projects": 0, "tasks": 0, "notes": 0, "snippets": 0}
    # Records whose id already exists are left untouched. Count them so the
    # caller can tell "nothing to do" apart from "nothing happened".
    skipped = {"areas": 0, "projects": 0, "tasks": 0, "notes": 0, "snippets": 0}

    try:
        # Import areas first
        for a_data in data.get("areas", []):
            area_id = _safe_uuid(a_data.get("id"))
            if area_id:
                existing = await db.get(Area, area_id)
                if existing:
                    skipped["areas"] += 1
                    continue
            area = Area(name=a_data["name"])
            if area_id:
                area.id = area_id
            created_at = _safe_dt(a_data.get("created_at"))
            if created_at:
                area.created_at = created_at
            db.add(area)
            imported["areas"] += 1

        await db.flush()

        # Import projects
        for p_data in data.get("projects", []):
            project_id = _safe_uuid(p_data.get("id"))
            if project_id:
                existing = await db.get(Project, project_id)
                if existing:
                    skipped["projects"] += 1
                    skipped["tasks"] += len(p_data.get("tasks", []))
                    skipped["notes"] += len(p_data.get("notes", []))
                    continue

            status_val = p_data.get("status", "active")
            try:
                status_enum = ProjectStatus(status_val)
            except ValueError:
                status_enum = ProjectStatus.active

            project = Project(
                work_name=p_data["work_name"],
                final_name=p_data.get("final_name"),
                description=p_data.get("description"),
                vision=p_data.get("vision"),
                goal=p_data.get("goal"),
                completion_criteria=p_data.get("completion_criteria"),
                abandonment_criteria=p_data.get("abandonment_criteria"),
                desired_end_date=_safe_date(p_data.get("desired_end_date")),
                github_repo=p_data.get("github_repo"),
                website=p_data.get("website"),
                star_rating=p_data.get("star_rating"),
                subjective_completion=p_data.get("subjective_completion", 0),
                local_dir=p_data.get("local_dir"),
                area_id=_safe_uuid(p_data.get("area_id")),
                archived=p_data.get("archived", False),
                status=status_enum,
                tags=p_data.get("tags", []),
                collaborators=p_data.get("collaborators", []),
            )
            if project_id:
                project.id = project_id
            created_at = _safe_dt(p_data.get("created_at"))
            if created_at:
                project.created_at = created_at
            updated_at = _safe_dt(p_data.get("updated_at"))
            if updated_at:
                project.updated_at = updated_at

            db.add(project)
            await db.flush()
            imported["projects"] += 1

            # Import tasks for this project
            for t_data in p_data.get("tasks", []):
                task_id = _safe_uuid(t_data.get("id"))
                if task_id:
                    existing_task = await db.get(Task, task_id)
                    if existing_task:
                        skipped["tasks"] += 1
                        continue

                status_str = t_data.get("status", "new")
                try:
                    task_status = TaskStatus(status_str)
                except ValueError:
                    task_status = TaskStatus.new

                task = Task(
                    project_id=project.id,
                    title=t_data["title"],
                    description=t_data.get("description"),
                    status=task_status,
                )
                if task_id:
                    task.id = task_id
                created_at = _safe_dt(t_data.get("created_at"))
                if created_at:
                    task.created_at = created_at
                updated_at = _safe_dt(t_data.get("updated_at"))
                if updated_at:
                    task.updated_at = updated_at
                db.add(task)
                imported["tasks"] += 1

            # Import notes for this project
            for n_data in p_data.get("notes", []):
                note_id = _safe_uuid(n_data.get("id"))
                if note_id:
                    existing_note = await db.get(Note, note_id)
                    if existing_note:
                        skipped["notes"] += 1
                        continue

                note = Note(
                    project_id=project.id,
                    task_id=_safe_uuid(n_data.get("task_id")),
                    content=n_data["content"],
                )
                if note_id:
                    note.id = note_id
                created_at = _safe_dt(n_data.get("created_at"))
                if created_at:
                    note.created_at = created_at
                updated_at = _safe_dt(n_data.get("updated_at"))
                if updated_at:
                    note.updated_at = updated_at
                db.add(note)
                imported["notes"] += 1

        await db.flush()

        # Import snippets
        for s_data in data.get("snippets", []):
            snippet_project_id = _safe_uuid(s_data.get("project_id"))
            if not snippet_project_id:
                continue
            snippet_id = _safe_uuid(s_data.get("id"))
            if snippet_id:
                existing_snippet = await db.get(Snippet, snippet_id)
                if existing_snippet:
                    skipped["snippets"] += 1
                    continue

            snippet = Snippet(
                project_id=snippet_project_id,
                snippet_type=s_data.get("snippet_type", "snippet"),
                content=s_data.get("content", ""),
                source_url=s_data.get("source_url"),
            )
            if snippet_id:
                snippet.id = snippet_id
            created_at = _safe_dt(s_data.get("created_at"))
            if created_at:
                snippet.created_at = created_at
            db.add(snippet)
            imported["snippets"] += 1

        await db.commit()

    except Exception:
        await db.rollback()
        # `from None`: the internal error is deliberately not surfaced to the
        # client, only logged by the generic handler.
        raise HTTPException(
            status_code=400,
            detail="Import failed: the uploaded data contains invalid or conflicting records",
        ) from None

    return {"status": "ok", "imported": imported, "skipped": skipped}
