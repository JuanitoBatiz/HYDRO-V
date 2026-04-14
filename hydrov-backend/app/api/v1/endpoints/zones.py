from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user, get_current_superuser
from app.models.zone import Zone
from app.schemas.zone import ZoneSchema, ZoneCreateSchema
from app.services.redis_service import redis_service

router = APIRouter()

@router.get("/", response_model=List[ZoneSchema])
async def list_zones(db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user)):
    result = await db.execute(select(Zone).order_by(Zone.name))
    return result.scalars().all()

@router.get("/{zone_code}", response_model=ZoneSchema)
async def get_zone(zone_code: str, db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user)):
    result = await db.execute(select(Zone).where(Zone.zone_code == zone_code))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(404, "Zona no encontrada")
    return zone

@router.post("/", response_model=ZoneSchema, status_code=201)
async def create_zone(payload: ZoneCreateSchema, db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_superuser)):
    existing = await db.execute(select(Zone).where(Zone.zone_code == payload.zone_code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="La zona ya existe")

    zone = Zone(**payload.model_dump())
    db.add(zone)
    await db.flush()
    await db.refresh(zone)
    return zone

@router.get("/{zone_code}/alerts/active")
async def get_active_alerts(zone_code: str, _: dict = Depends(get_current_user)):
    # Read from redis alerts:active:{zone_code} set
    members = await redis_service.redis_client.smembers(f"alerts:active:{zone_code}")
    return {"zone_code": zone_code, "active_alert_ids": list(members)}
