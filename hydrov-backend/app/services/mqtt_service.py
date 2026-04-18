# app/services/mqtt_service.py
import asyncio
import json
import uuid
import asyncpg
# import aioredis
import redis.asyncio as aioredis
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
                            (device_id, alert_type_id, severity, confidence_score, description, payload_snapshot, detected_at, is_resolved)
                        VALUES ($1, $2, 'critical', 1.0, 'Estado EMERGENCY detectado en FSM del ESP32', $3::jsonb, $4, FALSE)
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

        # --- Cálculo de nivel de Cisterna para Redis (G-07) ---
        meta = await device_cache.get_device_metadata(device_code)
        tank_height = meta["cistern_height_cm"] if meta else 125.0
        zone_code   = meta.get("zone_code") if meta else None  # I-02

        water_level = max(0.0, tank_height - payload.sensors.distance_cm)
        percent = (water_level / tank_height) * 100.0
        tank_level_pct = max(0.0, min(100.0, round(percent, 2)))

        # ── 1. Update Latest State Cache in Redis ───────────────
        await redis_service.update_device_state(payload, tank_level_pct=tank_level_pct)

        # ── 2. Escribe en InfluxDB — con zone_code como tag (I-02) ──
        await influx_service.write_telemetry(payload, zone_code=zone_code)

        # ── 3. Handler de emergencia ─────────────────────────────
        if payload.system_state.state == "EMERGENCY":
            await handle_emergency(payload, pg_pool, device_cache, mqtt_client)

        # ── 4. Actualizar last_seen_at en PG con throttle de 60 s (I-03) ──
        throttle_key = f"pg:last_seen_update:{device_code}"
        try:
            already_updated = await redis_service.redis_client.exists(throttle_key)
            if not already_updated:
                # Han pasado más de 60 s (o nunca se actualizó): ejecutar UPDATE
                async with pg_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE devices SET last_seen_at = $1 WHERE device_code = $2",
                        payload.received_at,
                        device_code,
                    )
                # Marcar timer en Redis con TTL de 60 segundos
                await redis_service.redis_client.setex(throttle_key, 60, "1")
                logger.debug(f"[MQTT] last_seen_at actualizado en PG | device={device_code}")
        except Exception as e:
            logger.warning(f"[MQTT] Error en throttle last_seen_at para {device_code}: {e}")

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
                client_id=unique_client_id,   # aiomqtt >= 0.9: 'identifier' fue renombrado a 'client_id'
            ) as client:
                await client.subscribe(settings.MQTT_TOPIC_TELEMETRY, qos=1)
                logger.info(f"[MQTT] Conectado y suscrito a {settings.MQTT_TOPIC_TELEMETRY} con ID {unique_client_id}")

                async with client.messages() as messages:
                    async for message in messages:
                        await process_message(message, pg_pool, device_cache, client)

        except Exception as e:
            logger.warning(f"[MQTT] Conexión pérdida: {e}. Reintentando en 5s...")
            await asyncio.sleep(5)