# app/api/v1/endpoints/devices.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user, get_current_superuser
from app.models.user import User
from app.models.device import Device
from app.schemas.device import (
    DeviceCreateSchema,
    DeviceUpdateSchema,
    DeviceResponseSchema,
)
from app.services.nasa_ingestion import ingest_climatology
from app.core.logger import logger

router = APIRouter()


# ─────────────────────────────────────────────────────────────────
#  GET /devices/
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[DeviceResponseSchema],
    summary="Listar todos los nodos Hydro-V registrados",
)
async def list_devices(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> List[DeviceResponseSchema]:
    """Retorna todos los nodos registrados, tanto activos como inactivos."""
    result = await db.execute(select(Device).order_by(Device.created_at.desc()))
    return result.scalars().all()


# ─────────────────────────────────────────────────────────────────
#  GET /devices/{device_id}
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/{device_id}",
    response_model=DeviceResponseSchema,
    summary="Obtener detalle de un nodo",
)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DeviceResponseSchema:
    """Retorna el detalle de un nodo por su device_id (ej: HYDRO-V-001)."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nodo '{device_id}' no encontrado",
        )
    return device


# ─────────────────────────────────────────────────────────────────
#  POST /devices/
# ─────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=DeviceResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo nodo Hydro-V",
)
async def create_device(
    payload: DeviceCreateSchema,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> DeviceResponseSchema:
    """
    Registra un nuevo nodo en el sistema (solo admins).
    Al registrar, dispara automáticamente la ingesta de climatología
    histórica de NASA POWER para las coordenadas del nodo.
    """
    # Verificar device_id único
    existing = await db.execute(
        select(Device).where(Device.device_id == payload.device_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El nodo '{payload.device_id}' ya existe",
        )

    device = Device(**payload.model_dump())
    db.add(device)
    await db.flush()
    await db.refresh(device)

    # Disparar ingesta de climatología NASA POWER en background
    # (no bloqueamos la respuesta por esto)
    try:
        logger.info(
            f"[Devices] Iniciando ingesta de climatología para {payload.device_id} "
            f"lat={payload.lat} lon={payload.lon}"
        )
        await ingest_climatology(lat=payload.lat, lon=payload.lon)
    except Exception as e:
        logger.warning(
            f"[Devices] No se pudo ingestar climatología para {payload.device_id}: {e}"
        )

    return device


# ─────────────────────────────────────────────────────────────────
#  PATCH /devices/{device_id}
# ─────────────────────────────────────────────────────────────────

@router.patch(
    "/{device_id}",
    response_model=DeviceResponseSchema,
    summary="Actualizar datos de un nodo",
)
async def update_device(
    device_id: str,
    payload: DeviceUpdateSchema,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> DeviceResponseSchema:
    """Actualiza campos editables de un nodo (solo admins)."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nodo '{device_id}' no encontrado",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)

    await db.flush()
    await db.refresh(device)
    return device


# ─────────────────────────────────────────────────────────────────
#  DELETE /devices/{device_id}
# ─────────────────────────────────────────────────────────────────

@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un nodo (soft delete → is_active=False)",
)
async def deactivate_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> None:
    """
    Desactiva un nodo (soft delete). No elimina los datos históricos.
    Solo admins pueden hacer esto.
    """
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nodo '{device_id}' no encontrado",
        )

    device.is_active = False
    await db.flush()
