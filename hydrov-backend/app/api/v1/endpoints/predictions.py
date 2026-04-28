# app/api/v1/endpoints/predictions.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user, verify_grafana_or_user
from app.models.user import User
from app.models.device import Device
from app.services.ml_service import ml_service
from app.core.logger import logger

router = APIRouter()


# ─────────────────────────────────────────────────────────────────
#  GET /predictions/{node_id}/autonomy
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/{node_id}/autonomy",
    summary="Predicción de días de autonomía hídrica",
)
async def predict_autonomy(
    node_id:   str,
    level_pct: float = Query(
        None, ge=0.0, le=100.0,
        description="Nivel actual de la cisterna en porcentaje (0-100). Si no se envía, usa Redis."
    ),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_grafana_or_user),
) -> dict:
    """
    Predice cuántos días de agua le quedan al nodo combinando:
    - Nivel actual de cisterna (`level_pct`)
    - Consumo promedio diario de los últimos 7 días (InfluxDB)
    - Pronóstico de precipitaciones NASA POWER próximas 72h
    - Temperatura, humedad y días sin lluvia

    Retorna:
    ```json
    {
      "node_id": "HYDRO-V-001",
      "days_autonomy": 4.3,
      "confidence": 0.85,
      "alert": false
    }
    ```
    """
    # Verificar que el nodo existe
    result = await db.execute(select(Device).where(Device.device_code == node_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nodo '{node_id}' no encontrado",
        )
    if device.status != 'active':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Nodo '{node_id}' está inactivo",
        )

    if level_pct is None:
        import json
        from app.services.redis_service import redis_service
        data = await redis_service.redis_client.get(f"sensor:latest:{node_id}")
        if not data:
            raise HTTPException(400, "level_pct no proveído por querystring y sin registro en Redis")
        sensors = json.loads(data).get("sensors", {})
        distance = float(sensors.get("distance_cm", 0))
        computed = (1.0 - (distance / 200.0)) * 100.0
        level_pct = max(0.0, min(100.0, computed))

    try:
        prediction = await ml_service.get_autonomy_prediction(
            node_id=node_id,
            level_pct=level_pct,
            lat=device.latitude,
            lon=device.longitude,
        )
    except Exception as e:
        logger.error(f"[Predictions] Error en autonomy para {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de predicción no está disponible temporalmente",
        )

    return {"node_id": node_id, **prediction}


# ─────────────────────────────────────────────────────────────────
#  GET /predictions/{node_id}/leaks
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/{node_id}/leaks",
    summary="Detección de fugas en el nodo",
)
async def detect_leaks(
    node_id:   str,
    flow_lpm:  float = Query(None, ge=0.0, description="Flujo actual en litros/minuto"),
    level_pct: float = Query(None, ge=0.0, le=100.0, description="Nivel actual en %"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """
    Ejecuta la GNN de detección de anomalías de flujo.
    Cuando hay múltiples nodos activos, correlaciona con nodos vecinos.

    Retorna:
    ```json
    {
      "node_id": "HYDRO-V-001",
      "leak_detected": false,
      "anomaly_score": 0.12,
      "confidence": 0.80
    }
    ```
    Un `anomaly_score` > 0.75 indica fuga probable.
    """
    result = await db.execute(select(Device).where(Device.device_code == node_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nodo '{node_id}' no encontrado",
        )

    if level_pct is None or flow_lpm is None:
        import json
        from app.services.redis_service import redis_service
        data = await redis_service.redis_client.get(f"sensor:latest:{node_id}")
        if not data:
            raise HTTPException(400, "level_pct o flow_lpm no proveídos y sin registro en Redis")
        sensors = json.loads(data).get("sensors", {})
        if level_pct is None:
            distance = float(sensors.get("distance_cm", 0))
            computed = (1.0 - (distance / 200.0)) * 100.0
            level_pct = max(0.0, min(100.0, computed))
        if flow_lpm is None:
            flow_lpm = float(sensors.get("flow_lpm", 0))

    try:
        detection = await ml_service.get_leak_detection(
            node_id=node_id,
            flow_lpm=flow_lpm,
            level_pct=level_pct,
        )
    except Exception as e:
        logger.error(f"[Predictions] Error en leak detection para {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de detección no está disponible temporalmente",
        )

    return detection


# ─────────────────────────────────────────────────────────────────
#  GET /predictions/{node_id}/full  — autonomía + fugas en una sola llamada
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/{node_id}/full",
    summary="Predicción completa: autonomía + detección de fugas",
)
async def full_prediction(
    node_id:   str,
    level_pct: float = Query(None, ge=0.0, le=100.0),
    flow_lpm:  float = Query(None, ge=0.0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """
    Combina autonomía hídrica + detección de fugas en una sola petición.
    Diseñado para el widget de estado del dashboard que necesita ambas métricas.
    """
    result = await db.execute(select(Device).where(Device.device_code == node_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail=f"Nodo '{node_id}' no encontrado")

    if level_pct is None or flow_lpm is None:
        import json
        from app.services.redis_service import redis_service
        data = await redis_service.redis_client.get(f"sensor:latest:{node_id}")
        if not data:
            raise HTTPException(400, "level_pct o flow_lpm no proveídos y sin registro en Redis")
        sensors = json.loads(data).get("sensors", {})
        if level_pct is None:
            distance = float(sensors.get("distance_cm", 0))
            computed = (1.0 - (distance / 200.0)) * 100.0
            level_pct = max(0.0, min(100.0, computed))
        if flow_lpm is None:
            flow_lpm = float(sensors.get("flow_lpm", 0))

    autonomy = await ml_service.get_autonomy_prediction(
        node_id=node_id, level_pct=level_pct, lat=device.latitude, lon=device.longitude,
    )
    leaks = await ml_service.get_leak_detection(
        node_id=node_id, flow_lpm=flow_lpm, level_pct=level_pct,
    )

    return {
        "node_id":  node_id,
        "autonomy": autonomy,
        "leaks":    leaks,
    }
