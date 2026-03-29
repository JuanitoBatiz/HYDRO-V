# app/api/v1/endpoints/alerts.py
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_db, get_current_user, get_current_superuser
from app.models.user import User
from app.models.alert import EmergencyAlert
from app.schemas.alert import (
    EmergencyAlertResponseSchema,
    AlertListSchema,
    AlertResolveSchema,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────
#  GET /alerts/
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=AlertListSchema,
    summary="Listar alertas de emergencia",
)
async def list_alerts(
    node_id:  Optional[str]  = Query(default=None, description="Filtrar por nodo"),
    resolved: Optional[bool] = Query(default=None, description="True=resueltas, False=pendientes"),
    limit:  int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AlertListSchema:
    """
    Retorna el historial de alertas de emergencia.
    - Filtrar por nodo con `?node_id=HYDRO-V-001`
    - Filtrar pendientes con `?resolved=false`
    - Filtrar resueltas con `?resolved=true`
    """
    query = select(EmergencyAlert)

    if node_id:
        query = query.where(EmergencyAlert.node_id == node_id)
    if resolved is not None:
        query = query.where(EmergencyAlert.resolved == resolved)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    query = query.order_by(EmergencyAlert.timestamp.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    items = result.scalars().all()

    return AlertListSchema(total=total, items=items)


# ─────────────────────────────────────────────────────────────────
#  GET /alerts/{alert_id}
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/{alert_id}",
    response_model=EmergencyAlertResponseSchema,
    summary="Detalle de una alerta",
)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> EmergencyAlertResponseSchema:
    """Retorna el detalle completo de una alerta incluyendo el payload_snapshot del ESP32."""
    result = await db.execute(
        select(EmergencyAlert).where(EmergencyAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerta #{alert_id} no encontrada",
        )
    return alert


# ─────────────────────────────────────────────────────────────────
#  PATCH /alerts/{alert_id}/resolve
# ─────────────────────────────────────────────────────────────────

@router.patch(
    "/{alert_id}/resolve",
    response_model=EmergencyAlertResponseSchema,
    summary="Marcar alerta como resuelta",
)
async def resolve_alert(
    alert_id: int,
    payload: AlertResolveSchema,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> EmergencyAlertResponseSchema:
    """
    Marca una alerta de emergencia como resuelta.
    Se puede incluir notas opcionales explicando cómo se resolvió.
    """
    result = await db.execute(
        select(EmergencyAlert).where(EmergencyAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerta #{alert_id} no encontrada",
        )
    if alert.resolved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La alerta #{alert_id} ya está marcada como resuelta",
        )

    alert.resolved       = payload.resolved
    alert.resolved_notes = payload.notes
    alert.resolved_at    = datetime.utcnow()

    await db.flush()
    await db.refresh(alert)
    return alert


# ─────────────────────────────────────────────────────────────────
#  GET /alerts/stats  — métricas para el dashboard
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/stats/summary",
    summary="Resumen de alertas por nodo para el dashboard",
)
async def alert_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """
    Retorna conteos de alertas pendientes y resueltas agrupadas por nodo.
    Útil para el widget de estado del dashboard.
    """
    result = await db.execute(
        select(
            EmergencyAlert.node_id,
            func.count(EmergencyAlert.id).label("total"),
            func.sum(
                func.cast(EmergencyAlert.resolved == False, Integer)  # noqa
            ).label("pending"),
        ).group_by(EmergencyAlert.node_id)
    )
    from sqlalchemy import Integer
    rows = result.all()

    return {
        "nodes": [
            {
                "node_id": r.node_id,
                "total":   r.total,
                "pending": r.pending or 0,
                "resolved": r.total - (r.pending or 0),
            }
            for r in rows
        ]
    }
