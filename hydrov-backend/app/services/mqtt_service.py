# app/services/mqtt_service.py
import asyncio
import json
import asyncpg
import aioredis
import aiomqtt
from datetime import datetime, timezone
from influxdb_client import Point
from app.core.config import settings
from app.core.logger import logger
from app.schemas.telemetry import ESP32PayloadSchema
from app.schemas.alert import EmergencyAlertCreateSchema
from app.services.influx_service import InfluxService


async def handle_emergency(
    payload:   ESP32PayloadSchema,
    pg_pool:   asyncpg.Pool,
    mqtt_client: aiomqtt.Client,
) -> None:
    """
    Cascada de 3 acciones ante estado EMERGENCY:
    1. PostgreSQL  → registro permanente de auditoría
    2. MQTT        → ACK de vuelta al ESP32
    3. Redis       → notificación al frontend via WebSocket
    """
    node_id   = payload.device_id
    timestamp = payload.received_at

    # 1. PostgreSQL ───────────────────────────────────────────────
    try:
        await pg_pool.execute(
            """
            INSERT INTO emergency_alerts
                (node_id, timestamp, error_count, state_duration_ms, payload_snapshot)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
            node_id,
            timestamp,
            payload.system_state.error_count,
            payload.system_state.state_duration_ms,
            payload.model_dump_json(),
        )
        logger.info(f"[MQTT] Emergency guardada en PostgreSQL | node={node_id}")
    except Exception as e:
        logger.error(f"[MQTT] Error guardando emergency en PostgreSQL: {e}")

    # 2. MQTT ACK al ESP32 ────────────────────────────────────────
    try:
        ack_topic   = settings.MQTT_TOPIC_COMMANDS.format(node_id=node_id)
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
        redis = aioredis.from_url(settings.REDIS_URL)
        channel = settings.WS_ALERT_CHANNEL.format(node_id=node_id)
        await redis.publish(
            channel,
            json.dumps({
                "type":        "EMERGENCY",
                "node_id":     node_id,
                "timestamp":   timestamp.isoformat(),
                "error_count": payload.system_state.error_count,
            })
        )
        await redis.aclose()
        logger.info(f"[MQTT] Emergency publicada en Redis canal {channel}")
    except Exception as e:
        logger.error(f"[MQTT] Error publicando en Redis: {e}")


async def process_message(
    message:     aiomqtt.Message,
    influx_svc:  InfluxService,
    pg_pool:     asyncpg.Pool,
    mqtt_client: aiomqtt.Client,
) -> None:
    """
    Procesa cada mensaje MQTT del ESP32:
    1. Valida con Pydantic
    2. Escribe en InfluxDB
    3. Si es EMERGENCY → cascada de alertas
    """
    try:
        raw     = json.loads(message.payload.decode())
        payload = ESP32PayloadSchema(**raw)
        node_id = payload.device_id
        now     = payload.received_at  # timestamp del backend, no del ESP32

        # ── Construir Point de InfluxDB ───────────────────────────
        point = (
            Point("sensor_telemetry")
            .tag("node_id",   node_id)
            .tag("fsm_state", payload.system_state.state)
            # Sensores
            .field("turbidity_ntu",      payload.sensors.turbidity_ntu)
            .field("distance_cm",        payload.sensors.distance_cm)
            .field("flow_lpm",           payload.sensors.flow_lpm)
            .field("flow_total_liters",  payload.sensors.flow_total_liters)
            # Estado FSM
            .field("state_duration_ms",  payload.system_state.state_duration_ms)
            .field("intake_cycles",      payload.system_state.intake_cycles)
            .field("reject_cycles",      payload.system_state.reject_cycles)
            .field("error_count",        payload.system_state.error_count)
            # Uptime del ESP32 (millis())
            .field("esp32_uptime_ms",    payload.timestamp)
            .time(now)
        )

        await influx_svc.write_telemetry(point)
        logger.debug(f"[MQTT] Telemetría guardada | node={node_id} state={payload.system_state.state}")

        # ── Handler de emergencia ─────────────────────────────────
        if payload.system_state.state == "EMERGENCY":
            await handle_emergency(payload, pg_pool, mqtt_client)

    except Exception as e:
        logger.error(f"[MQTT] Error procesando mensaje: {e}")
        logger.debug(f"[MQTT] Payload raw: {message.payload}")


async def mqtt_to_influx_loop(pg_pool: asyncpg.Pool) -> None:
    """
    Loop permanente que escucha MQTT y escribe en InfluxDB.
    Se lanza como background task en el lifespan de main.py.
    Reconecta automáticamente si pierde conexión.
    """
    influx_svc = InfluxService()

    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.MQTT_HOST,
                port=settings.MQTT_PORT,
                username=settings.MQTT_USER,
                password=settings.MQTT_PASSWORD,
                tls_params=aiomqtt.TLSParameters(),
                client_id=settings.MQTT_CLIENT_ID,
            ) as client:
                await client.subscribe(settings.MQTT_TOPIC_TELEMETRY, qos=1)
                logger.info(f"[MQTT] Conectado y suscrito a {settings.MQTT_TOPIC_TELEMETRY}")

                async for message in client.messages:
                    await process_message(message, influx_svc, pg_pool, client)

        except Exception as e:
            logger.warning(f"[MQTT] Conexión perdida: {e}. Reintentando en 5s...")
            await asyncio.sleep(5)