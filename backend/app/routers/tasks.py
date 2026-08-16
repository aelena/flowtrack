import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import verify_api_key
from ..models import Task
from ..schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(
    prefix="/api/projects/{project_id}/tasks", tags=["tasks"], dependencies=[Depends(verify_api_key)]
)


def parse_task_list(content: str) -> list[str]:
    """Parse bullet or ordered list into individual task titles."""
    lines = content.strip().splitlines()
    tasks = []
    for line in lines:
        stripped = line.strip()
        # Match bullet lists (- or * or +) or ordered lists (1. 2. etc.)
        match = re.match(r"^(?:[-*+]|\d+[.)]) +(.+)", stripped)
        if match:
            tasks.append(match.group(1).strip())
        elif stripped and not tasks:
            # If no list format detected yet, treat entire content as single task
            return [content.strip()]
    return tasks if tasks else [content.strip()]


@router.get("/", response_model=list[TaskOut])
async def list_tasks(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.project_id == project_id).order_by(Task.created_at))
    return result.scalars().all()


@router.post("/", response_model=list[TaskOut], status_code=201)
async def create_tasks(project_id: UUID, data: TaskCreate, db: AsyncSession = Depends(get_db)):
    titles = parse_task_list(data.content)
    created = []
    for title in titles:
        task = Task(project_id=project_id, title=title, description=data.description)
        db.add(task)
        created.append(task)
    await db.commit()
    for t in created:
        await db.refresh(t)
    return created


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(project_id: UUID, task_id: UUID, data: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(404, "Task not found")
    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.status is not None:
        task.status = data.status
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(project_id: UUID, task_id: UUID, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(404, "Task not found")
    await db.delete(task)
    await db.commit()
