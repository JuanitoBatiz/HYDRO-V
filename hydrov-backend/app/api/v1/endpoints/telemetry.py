# app/api/v1/endpoints/telemetry.py
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi import WebSocket

from app.api.deps import get_current_user
from app.services.websocketservice import handle_websocket
from app.services.influx_service import influx_service

router = APIRouter()

@router.websocket("/ws/{device_code}")
async def websocket_telemetry(websocket: WebSocket, device_code: str):
    await handle_websocket(websocket, device_code)

@router.get("/{device_code}/history")
async def get_telemetry_history(
    device_code: str,
    hours: int = Query(default=1, ge=1, le=168, description="Horas de historial"),
    _: dict = Depends(get_current_user),
):
    items = await influx_service.get_history(device_code, hours)
    return {"total": len(items), "items": items}

@router.get("/{device_code}/latest")
async def get_latest_telemetry(
    device_code: str,
    _: dict = Depends(get_current_user),
):
    data = await influx_service.get_latest_telemetry(device_code)
    if not data:
        raise HTTPException(status_code=404, detail="No data available")
    return data
