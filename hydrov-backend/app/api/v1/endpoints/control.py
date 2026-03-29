# app/api/v1/endpoints/control.py
"""
Endpoints de control remoto — envían comandos al ESP32 via MQTT.
Solo usuarios autenticados pueden enviar comandos.
Los comandos llegan al ESP32 en el topic: hydrov/{node_id}/commands
"""
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import aiomqtt

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.core.logger import logger
from app.models.user import User
from app.models.device import Device

router = APIRouter()


# ── Schemas de control (internos a este endpoint) ─────────────────

class CommandPayload(BaseModel):
    action: Literal[
        "FORCE_HARVEST",    # Forzar apertura de válvula de captación
        "FORCE_IDLE",       # Forzar estado IDLE (detener operación)
        "RESET_ERRORS",     # Limpiar contador de errores del ESP32
        "REQUEST_TELEMETRY", # Solicitar telemetría inmediata fuera de ciclo
        "REBOOT",           # Reiniciar el ESP32 remotamente
    ]
    notes: str | None = None


class CommandResponse(BaseModel):
    node_id:    str
    action:     str
    topic:      str
    published_at: datetime
    status:     str


# ─────────────────────────────────────────────────────────────────
#  POST /control/{node_id}/command
# ─────────────────────────────────────────────────────────────────

@router.post(
    "/{node_id}/command",
    response_model=CommandResponse,
    summary="Enviar comando al ESP32 via MQTT",
)
async def send_command(
    node_id: str,
    payload: CommandPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommandResponse:
    """
    Publica un comando MQTT en el topic `hydrov/{node_id}/commands`.
    El ESP32 (net_mqtt.cpp) escucha este topic y ejecuta la acción.

    **Acciones disponibles:**
    - `FORCE_HARVEST` — Abre la válvula de captación manualmente
    - `FORCE_IDLE` — Detiene todas las operaciones del nodo
    - `RESET_ERRORS` — Limpia el contador de errores del FSM
    - `REQUEST_TELEMETRY` — Solicita telemetría inmediata
    - `REBOOT` — Reinicia el microcontrolador remotamente ⚠️

    > **Nota:** `REBOOT` causa una interrupción temporal del nodo.
    """
    # Verificar que el nodo existe y está activo
    result = await db.execute(select(Device).where(Device.device_id == node_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nodo '{node_id}' no encontrado",
        )
    if not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Nodo '{node_id}' está inactivo — no se pueden enviar comandos",
        )

    topic = settings.MQTT_TOPIC_COMMANDS.format(node_id=node_id)
    now   = datetime.now(timezone.utc)

    command_msg = json.dumps({
        "action":     payload.action,
        "from":       "hydrov-backend",
        "user_id":    current_user.id,
        "timestamp":  now.isoformat(),
        "notes":      payload.notes,
    })

    try:
        async with aiomqtt.Client(
            hostname=settings.MQTT_HOST,
            port=settings.MQTT_PORT,
            username=settings.MQTT_USER,
            password=settings.MQTT_PASSWORD,
            tls_params=aiomqtt.TLSParameters(),
        ) as client:
            await client.publish(topic, command_msg, qos=1)

        logger.info(
            f"[Control] Comando '{payload.action}' enviado a {node_id} "
            f"por user_id={current_user.id}"
        )
    except Exception as e:
        logger.error(f"[Control] Error publicando comando MQTT: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo publicar el comando en MQTT: {e}",
        )

    return CommandResponse(
        node_id=node_id,
        action=payload.action,
        topic=topic,
        published_at=now,
        status="published",
    )


# ─────────────────────────────────────────────────────────────────
#  GET /control/{node_id}/status
#  Acceso rápido al último estado FSM conocido del nodo
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/{node_id}/status",
    summary="Estado FSM actual del nodo (desde InfluxDB)",
)
async def get_node_status(
    node_id: str,
    _: User = Depends(get_current_user),
) -> dict:
    """
    Retorna el último estado FSM del ESP32 conocido por el backend.
    Más rápido que el endpoint de telemetría completo — solo returns el estado.
    """
    from app.services.influx_service import InfluxService

    influx = InfluxService()
    data   = await influx.get_latest_telemetry(node_id)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hay datos recientes para el nodo '{node_id}'",
        )

    return {
        "node_id":          node_id,
        "fsm_state":        data.get("fsm_state", "UNKNOWN"),
        "flow_lpm":         data.get("flow_lpm", 0.0),
        "distance_cm":      data.get("distance_cm", 0.0),
        "turbidity_ntu":    data.get("turbidity_ntu", 0.0),
        "error_count":      data.get("error_count", 0),
        "last_seen":        data.get("_time"),
    }
