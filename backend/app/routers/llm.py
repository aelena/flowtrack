from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..dependencies import verify_api_key
from ..models import LLMProvider, Project
from ..schemas import ChatMessage, LLMProviderCreate, LLMProviderOut

router = APIRouter(prefix="/api/llm", tags=["llm"], dependencies=[Depends(verify_api_key)])


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


@router.get("/providers", response_model=list[LLMProviderOut])
async def list_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).order_by(LLMProvider.name))
    return result.scalars().all()


@router.post("/providers", response_model=LLMProviderOut, status_code=201)
async def add_provider(data: LLMProviderCreate, db: AsyncSession = Depends(get_db)):
    provider = LLMProvider(**data.model_dump())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


@router.post("/generate/prd/{project_id}")
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


@router.post("/generate/brd/{project_id}")
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


@router.post("/generate/mrd/{project_id}")
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


@router.post("/generate/social/{project_id}")
async def generate_social(project_id: UUID, db: AsyncSession = Depends(get_db)):
    ctx = await _get_project_context(project_id, db)
    name = ctx["final_name"] or ctx["name"]
    desc = ctx["description"] or ctx["vision"] or ""
    return {
        "linkedin": f"Excited to share my latest project: {name}. {desc[:200]}",
        "twitter": f"{name} - {desc[:220]}" if len(desc) > 0 else f"Working on {name}!",
    }


@router.post("/chat/{project_id}")
async def chat(project_id: UUID, msg: ChatMessage, db: AsyncSession = Depends(get_db)):
    ctx = await _get_project_context(project_id, db)
    # Placeholder: returns context-aware echo. Real implementation would call configured LLM.
    return {
        "response": f"[LLM placeholder] Regarding '{ctx['name']}': {msg.message}\n\nProject context loaded with {len(ctx['tasks'])} tasks and {len(ctx['notes'])} notes.",
        "project_context": ctx["name"],
    }


@router.post("/suggest/{project_id}")
async def suggest(project_id: UUID, db: AsyncSession = Depends(get_db)):
    ctx = await _get_project_context(project_id, db)
    pending = [t for t in ctx["tasks"] if t["status"] != "done"]
    in_progress = [t for t in ctx["tasks"] if t["status"] == "in_progress"]
    suggestions = []
    if in_progress:
        suggestions.append(f"Continue working on: {in_progress[0]['title']}")
    if pending:
        suggestions.append(f"Next up: {pending[0]['title']}")
    if not ctx["description"]:
        suggestions.append("Add a project description to clarify scope")
    if not ctx["completion_criteria"]:
        suggestions.append("Define completion criteria to know when you're done")
    if not suggestions:
        suggestions.append("All tasks done! Consider reviewing and archiving this project.")
    return {"suggestions": suggestions}
