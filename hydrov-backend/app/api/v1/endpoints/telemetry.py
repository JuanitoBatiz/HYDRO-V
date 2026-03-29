# app/api/v1/endpoints/telemetry.py
from typing import Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import WebSocket

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.device import Device
from app.models.telemetry import TelemetryEvent
from app.schemas.telemetry import TelemetryResponseSchema, TelemetryListSchema
from app.services.websocketservice import handle_websocket
from app.services.influx_service import InfluxService

router = APIRouter()


# ─────────────────────────────────────────────────────────────────
#  WebSocket /telemetry/ws/{node_id}
# ─────────────────────────────────────────────────────────────────

@router.websocket("/ws/{node_id}")
async def websocket_telemetry(websocket: WebSocket, node_id: str):
    """
    Conexión WebSocket por nodo.
    El frontend se conecta aquí y recibe alertas de EMERGENCY en tiempo real
    vía Redis pub/sub → WebSocket.

    No requiere JWT (WebSocket no soporta headers estándar de auth).
    Considerar query param ?token=... si se necesita autenticación futura.
    """
    await handle_websocket(websocket, node_id)


# ─────────────────────────────────────────────────────────────────
#  GET /telemetry/{node_id}  — histórico desde PostgreSQL
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/{node_id}",
    response_model=TelemetryListSchema,
    summary="Histórico de telemetría de un nodo (PostgreSQL)",
)
async def get_telemetry_history(
    node_id: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Máximo de registros"),
    offset: int = Query(default=0, ge=0),
    start: Optional[datetime] = Query(default=None, description="Desde (ISO 8601)"),
    end: Optional[datetime]   = Query(default=None, description="Hasta (ISO 8601)"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TelemetryListSchema:
    """
    Retorna el histórico paginado de telemetría de un nodo.
    - Rango de fechas opcional con `start` y `end`.
    - Por defecto retorna los últimos 100 eventos ordenados por fecha desc.
    - Para datos de alta frecuencia (minutales) usar el endpoint de InfluxDB.
    """
    query = select(TelemetryEvent).where(TelemetryEvent.device_id == node_id)

    if start:
        query = query.where(TelemetryEvent.received_at >= start)
    if end:
        query = query.where(TelemetryEvent.received_at <= end)

    # Total para paginación
    count_q = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    # Datos paginados
    query = query.order_by(TelemetryEvent.received_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    items = result.scalars().all()

    return TelemetryListSchema(total=total, items=items)


# ─────────────────────────────────────────────────────────────────
#  GET /telemetry/{node_id}/latest  — último dato en tiempo real
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/{node_id}/latest",
    response_model=TelemetryResponseSchema,
    summary="Última lectura de telemetría de un nodo",
)
async def get_latest_telemetry(
    node_id: str,
    _: User = Depends(get_current_user),
) -> TelemetryResponseSchema:
    """
    Retorna la lectura más reciente directamente desde InfluxDB
    (más fresco que PostgreSQL para datos en tiempo real).
    """
    influx = InfluxService()
    data = await influx.get_latest_telemetry(node_id)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hay telemetría reciente para el nodo '{node_id}'",
        )
    return data


# ─────────────────────────────────────────────────────────────────
#  GET /telemetry/{node_id}/summary  — resumen del día
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/{node_id}/summary",
    summary="Resumen diario de telemetría de un nodo",
)
async def get_daily_summary(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """
    Retorna un resumen del día: promedio de turbidez, total de litros
    cosechados, ciclos de ingesta/rechazo, número de errores.
    Útil para el widget de resumen del dashboard.
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    result = await db.execute(
        select(
            func.avg(TelemetryEvent.turbidity_ntu).label("avg_turbidity"),
            func.max(TelemetryEvent.flow_total_liters).label("total_liters"),
            func.min(TelemetryEvent.flow_total_liters).label("min_liters"),
            func.sum(TelemetryEvent.intake_cycles).label("total_intake"),
            func.sum(TelemetryEvent.reject_cycles).label("total_reject"),
            func.sum(TelemetryEvent.error_count).label("total_errors"),
            func.count(TelemetryEvent.id).label("total_records"),
        ).where(
            TelemetryEvent.device_id == node_id,
            TelemetryEvent.received_at >= today_start,
        )
    )
    row = result.one()

    return {
        "node_id":        node_id,
        "date":           today_start.date().isoformat(),
        "avg_turbidity_ntu": round(row.avg_turbidity or 0.0, 2),
        "liters_harvested": round((row.total_liters or 0.0) - (row.min_liters or 0.0), 2),
        "intake_cycles":  row.total_intake or 0,
        "reject_cycles":  row.total_reject or 0,
        "total_errors":   row.total_errors or 0,
        "total_records":  row.total_records or 0,
    }
