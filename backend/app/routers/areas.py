from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import verify_api_key
from ..models import Area, Project
from ..schemas import AreaCreate, AreaUpdate, AreaOut

router = APIRouter(prefix="/api/areas", tags=["areas"], dependencies=[Depends(verify_api_key)])


@router.get("/", response_model=list[AreaOut])
async def list_areas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Area).order_by(Area.name))
    return result.scalars().all()


@router.post("/", response_model=AreaOut, status_code=201)
async def create_area(data: AreaCreate, db: AsyncSession = Depends(get_db)):
    area = Area(name=data.name)
    db.add(area)
    await db.commit()
    await db.refresh(area)
    return area


@router.put("/{area_id}", response_model=AreaOut)
async def update_area(area_id: UUID, data: AreaUpdate, db: AsyncSession = Depends(get_db)):
    area = await db.get(Area, area_id)
    if not area:
        raise HTTPException(404, "Area not found")
    area.name = data.name
    await db.commit()
    await db.refresh(area)
    return area


@router.delete("/{area_id}", status_code=204)
async def delete_area(area_id: UUID, db: AsyncSession = Depends(get_db)):
    area = await db.get(Area, area_id)
    if not area:
        raise HTTPException(404, "Area not found")
    # Ungroup projects instead of deleting them
    result = await db.execute(select(Project).where(Project.area_id == area_id))
    for project in result.scalars().all():
        project.area_id = None
    await db.delete(area)
    await db.commit()
