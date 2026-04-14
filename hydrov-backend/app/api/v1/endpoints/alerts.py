from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, join

from app.api.deps import get_db, get_current_user, get_current_superuser
from app.models.alert import Alert
from app.models.device import Device
from app.schemas.alert import AlertResponseSchema, AlertListSchema, AlertResolveSchema

router = APIRouter()

@router.get("/", response_model=AlertListSchema)
async def list_alerts(
    device_code: Optional[str] = Query(default=None),
    is_resolved: Optional[bool] = Query(default=None),
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    query = select(Alert)
    if device_code:
        query = query.join(Device).where(Device.device_code == device_code)
    if is_resolved is not None:
        query = query.where(Alert.is_resolved == is_resolved)
    
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    query = query.order_by(Alert.detected_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    items = result.scalars().all()

    return AlertListSchema(total=total, items=items)

@router.get("/{alert_id}", response_model=AlertResponseSchema)
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alerta no encontrada")
    return alert

@router.patch("/{alert_id}/resolve", response_model=AlertResponseSchema)
async def resolve_alert(
    alert_id: int,
    payload: AlertResolveSchema,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alerta no encontrada")

    alert.is_resolved = payload.is_resolved
    alert.resolved_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(alert)
    return alert
