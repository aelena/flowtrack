"""Deterministic document generation from project data.

No model is involved and none is planned: an agent driving the MCP server
has the whole project in context and can write something better than a
template ever would. These endpoints exist because a downloadable,
reproducible PRD/BRD/MRD is genuinely useful on its own.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..dependencies import verify_api_key
from ..models import Project

router = APIRouter(prefix="/api/documents", tags=["documents"], dependencies=[Depends(verify_api_key)])


async def _get_project_context(project_id: UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.tasks), selectinload(Project.notes))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    return {
        "name": project.work_name,
        "final_name": project.final_name,
        "description": project.description,
        "vision": project.vision,
        "goal": project.goal,
        "completion_criteria": project.completion_criteria,
        "tasks": [{"title": t.title, "status": t.status.value} for t in project.tasks],
        "notes": [n.content for n in project.notes],
    }


@router.post("/prd/{project_id}")
async def generate_prd(project_id: UUID, db: AsyncSession = Depends(get_db)):
    ctx = await _get_project_context(project_id, db)
    prd = {
        "title": f"PRD: {ctx['name']}",
        "overview": ctx["description"] or "",
        "vision": ctx["vision"] or "",
        "goals": ctx["goal"] or "",
        "success_criteria": ctx["completion_criteria"] or "",
        "features": [t["title"] for t in ctx["tasks"]],
        "notes": ctx["notes"],
        "status": {
            "total_tasks": len(ctx["tasks"]),
            "done": sum(1 for t in ctx["tasks"] if t["status"] == "done"),
            "in_progress": sum(1 for t in ctx["tasks"] if t["status"] == "in_progress"),
            "new": sum(1 for t in ctx["tasks"] if t["status"] == "new"),
        },
    }
    return prd


@router.post("/brd/{project_id}")
async def generate_brd(project_id: UUID, db: AsyncSession = Depends(get_db)):
    ctx = await _get_project_context(project_id, db)
    brd = {
        "title": f"BRD: {ctx['name']}",
        "business_objective": ctx["goal"] or "",
        "project_description": ctx["description"] or "",
        "scope": [t["title"] for t in ctx["tasks"]],
        "success_metrics": ctx["completion_criteria"] or "",
    }
    return brd


@router.post("/mrd/{project_id}")
async def generate_mrd(project_id: UUID, db: AsyncSession = Depends(get_db)):
    ctx = await _get_project_context(project_id, db)
    mrd = {
        "title": f"MRD: {ctx['name']}",
        "market_problem": ctx["goal"] or "",
        "product_vision": ctx["vision"] or "",
        "product_description": ctx["description"] or "",
        "key_features": [t["title"] for t in ctx["tasks"]],
    }
    return mrd
