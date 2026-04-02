# app/services/mqtt_service.py
import asyncio
import json
import uuid
import asyncpg
import aiomqtt
from datetime import datetime
from app.core.config import settings
from app.core.logger import logger
from app.schemas.mqtt import ESP32PayloadSchema
from app.services.influx_service import influx_service
from app.services.redis_service import redis_service
from app.services.device_cache import DeviceCache


async def handle_emergency(
    payload:   ESP32PayloadSchema,
    pg_pool:   asyncpg.Pool,
    device_cache: DeviceCache,
    mqtt_client: aiomqtt.Client,
) -> None:
    """
    Cascada de 3 acciones ante estado EMERGENCY:
    1. PostgreSQL  → registro permanente en tabla 'alerts' (nueva arquitectura v2)
    2. MQTT        → ACK de vuelta al ESP32
    3. Redis       → notificación al frontend via WebSocket
    """
    device_code = payload.device_code
    timestamp   = payload.received_at

    # Para meter una alerta en PostgreSQL V2 necesitamos el device_id numérico PK
    meta = await device_cache.get_device_metadata(device_code)
    db_device_id = meta["id"] if meta else None

    if not db_device_id:
        logger.error(f"[MQTT] No se encontró el device_id para {device_code}. Imposible crear alerta en PG.")
    else:
        # 1. PostgreSQL (Tabla alerts) ───────────────────────────────────────────────
        try:
            # Obtenemos el alert_type_id de la emergencia (name='emergency' en el Seed)
            async with pg_pool.acquire() as conn:
                alert_type_id = await conn.fetchval("SELECT id FROM alert_types WHERE name = 'emergency'")
                
                if alert_type_id:
                    await conn.execute(
                        """
                        INSERT INTO alerts
                            (device_id, alert_type_id, severity, confidence_score, description, payload_snapshot, detected_at)
                        VALUES ($1, $2, 'critical', 1.0, 'Estado EMERGENCY detectado en FSM del ESP32', $3::jsonb, $4)
                        """,
                        db_device_id,
                        alert_type_id,
                        payload.model_dump_json(),
                        timestamp
                    )
                    logger.info(f"[MQTT] Emergency guardada en PostgreSQL | device={device_code}")
                else:
                    logger.error(f"[MQTT] Missing 'emergency' AlertType in DB catalog.")
        except Exception as e:
            logger.error(f"[MQTT] Error guardando emergency en PostgreSQL: {e}")

    # 2. MQTT ACK al ESP32 ────────────────────────────────────────
    try:
        ack_topic   = settings.MQTT_TOPIC_COMMANDS.format(node_id=device_code) # Usa el mismo topic que V1
        ack_payload = json.dumps({
            "action":    "EMERGENCY_ACK",
            "timestamp": timestamp.isoformat(),
            "from":      "hydrov-backend",
        })
        await mqtt_client.publish(ack_topic, ack_payload, qos=1)
        logger.info(f"[MQTT] Emergency ACK enviado a {ack_topic}")
    except Exception as e:
        logger.error(f"[MQTT] Error enviando ACK: {e}")

    # 3. Redis → WebSocket frontend ───────────────────────────────
    try:
        await redis_service.publish_emergency(
            device_code=device_code,
            error_count=payload.system_state.error_count,
            timestamp_iso=timestamp.isoformat()
        )
    except Exception as e:
        logger.error(f"[MQTT] Error publicando en Redis via WS: {e}")


async def process_message(
    message:     aiomqtt.Message,
    pg_pool:     asyncpg.Pool,
    device_cache: DeviceCache,
    mqtt_client: aiomqtt.Client,
) -> None:
    """
    Procesa cada mensaje MQTT del ESP32 de acuerdo a Pipeline V2.
    """
    try:
        raw     = json.loads(message.payload.decode())
        payload = ESP32PayloadSchema(**raw)
        
        device_code = payload.device_code

        # ── 1. Update Latest State Cache in Redis ───────────────
        await redis_service.update_device_state(payload)

        # ── 2. Escribe en InfluxDB (measurements separadas) ──────
        await influx_service.write_telemetry(payload)
        
        # Opcional log debug
        # logger.debug(f"[MQTT] Telemetría procesada | device={device_code} state={payload.system_state.state}")

        # ── 3. Handler de emergencia ─────────────────────────────
        if payload.system_state.state == "EMERGENCY":
            await handle_emergency(payload, pg_pool, device_cache, mqtt_client)

        # ── 4. Actualizar last_seen_at en PG (Opcional pero útil) ──
        # Lo haremos en backend job o de manera menos intensiva que un update per-packet.

    except Exception as e:
        logger.error(f"[MQTT] Error procesando mensaje: {e}")
        logger.debug(f"[MQTT] Payload raw devuelto error: {message.payload}")


async def mqtt_to_influx_loop(pg_pool: asyncpg.Pool) -> None:
    """
    Loop permanente que escucha MQTT y procesa la telemetría.
    """
    device_cache = DeviceCache(pg_pool)

    while True:
        try:
            base_id = settings.MQTT_CLIENT_ID or "hydrov_backend"
            unique_client_id = f"{base_id}_{uuid.uuid4().hex[:8]}"

            async with aiomqtt.Client(
                hostname=settings.MQTT_HOST,
                port=settings.MQTT_PORT,
                username=settings.MQTT_USER,
                password=settings.MQTT_PASSWORD,
                tls_params=aiomqtt.TLSParameters(),
                client_id=unique_client_id,
            ) as client:
                await client.subscribe(settings.MQTT_TOPIC_TELEMETRY, qos=1)
                logger.info(f"[MQTT] Conectado y suscrito a {settings.MQTT_TOPIC_TELEMETRY} con ID {unique_client_id}")

                async with client.messages() as messages:
                    async for message in messages:
                        await process_message(message, pg_pool, device_cache, client)

        except Exception as e:
            logger.warning(f"[MQTT] Conexión pérdida: {e}. Reintentando en 5s...")
            await asyncio.sleep(5)