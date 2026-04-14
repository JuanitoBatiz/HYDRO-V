# app/api/v1/endpoints/devices.py
from typing import List, Optional
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, join
from pydantic import BaseModel
import aiomqtt

from datetime import datetime, timezone

from app.api.deps import get_db, get_current_user, get_current_superuser
from app.models.user import User
from app.models.device import Device
from app.models.zone import Zone
from app.models.alert import Alert
from app.schemas.device import (
    DeviceCreateSchema,
    DeviceUpdateSchema,
    DeviceResponseSchema,
)
from app.services.nasa_ingestion import ingest_climatology
from app.services.redis_service import redis_service
from app.core.logger import logger
from app.core.config import settings

router = APIRouter()

class CommandSchema(BaseModel):
    action: str
    payload: Optional[dict] = {}


@router.get("/", response_model=List[DeviceResponseSchema])
async def list_devices(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(select(Device).order_by(Device.created_at.desc()))
    return result.scalars().all()


@router.get("/{device_code}", response_model=DeviceResponseSchema)
async def get_device(
    device_code: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(select(Device).where(Device.device_code == device_code))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")
    return device


@router.post("/", response_model=DeviceResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_device(
    payload: DeviceCreateSchema,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_superuser),
):
    existing = await db.execute(select(Device).where(Device.device_code == payload.device_code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El nodo ya existe")

    device_data = payload.model_dump()
    device_data["installed_at"] = datetime.now(timezone.utc)
    device = Device(**device_data)
    db.add(device)
    await db.flush()
    await db.refresh(device)

    try:
        await ingest_climatology(lat=payload.latitude, lon=payload.longitude)
    except Exception as e:
        logger.warning(f"No se pudo ingestar climatologia para {payload.device_code}: {e}")

    return device


@router.patch("/{device_code}", response_model=DeviceResponseSchema)
async def update_device(
    device_code: str,
    payload: DeviceUpdateSchema,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_superuser),
):
    result = await db.execute(select(Device).where(Device.device_code == device_code))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)

    await db.flush()
    await db.refresh(device)
    return device


@router.delete("/{device_code}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_device(
    device_code: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_superuser),
):
    result = await db.execute(select(Device).where(Device.device_code == device_code))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")

    device.status = 'inactive'
    await db.flush()


@router.get("/{device_code}/status")
async def get_device_status(device_code: str, _: dict = Depends(get_current_user)):
    data = await redis_service.redis_client.get(f"device:state:{device_code}")
    if not data:
        raise HTTPException(404, detail="Status no disponible")
    return json.loads(data)


@router.get("/{device_code}/latest")
async def get_device_latest(device_code: str, _: dict = Depends(get_current_user)):
    data = await redis_service.redis_client.get(f"sensor:latest:{device_code}")
    if not data:
        raise HTTPException(404, detail="Sensores no disponibles")
    return json.loads(data)


@router.get("/{device_code}/predict")
async def get_device_predict(device_code: str, _: dict = Depends(get_current_user)):
    data = await redis_service.redis_client.get(f"autonomy:pred:{device_code}")
    if not data:
        raise HTTPException(404, detail="Predicción no disponible")
    return json.loads(data)


@router.get("/{device_code}/alerts")
async def get_device_alerts(
    device_code: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    result = await db.execute(
        select(Alert).join(Device, Alert.device_id == Device.id)
        .where(Device.device_code == device_code)
        .order_by(Alert.detected_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.post("/{device_code}/command")
async def post_device_command(
    device_code: str,
    cmd: CommandSchema,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    result = await db.execute(
        select(Zone.zone_code)
        .join(Device, Device.zone_id == Zone.id)
        .where(Device.device_code == device_code)
    )
    zone_code = result.scalar_one_or_none()
    if not zone_code:
        raise HTTPException(404, detail="Dispositivo o zona no encontrado")

    topic = f"hydrov/{zone_code}/{device_code}/commands"
    msg = {"action": cmd.action, "payload": cmd.payload}
    
    try:
        async with aiomqtt.Client(
            hostname=settings.MQTT_HOST,
            port=settings.MQTT_PORT,
            username=settings.MQTT_USER,
            password=settings.MQTT_PASSWORD,
            tls_params=aiomqtt.TLSParameters()
        ) as client:
            await client.publish(topic, json.dumps(msg), qos=1)
    except Exception as e:
        logger.error(f"Error publishing command: {e}")
        raise HTTPException(500, detail="No se pudo publicar el comando MQTT")

    return {"status": "ok", "topic": topic}
