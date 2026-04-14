# app/services/redis_service.py
import json
import redis.asyncio as redis
from app.core.config import settings
from app.core.logger import logger
from app.schemas.mqtt import ESP32PayloadSchema

class RedisService:
    """
    Servicio centralizado para interacciones con Redis:
    - Caché del último estado de los dispositivos (con TTL obigatorio).
    - Publicación/Suscripción (PubSub) para WebSockets.
    """
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def update_device_state(self, payload: ESP32PayloadSchema, tank_level_pct: float | None = None) -> None:
        """
        Almacena el último estado del dispositivo bajo la nomenclatura V2:
        device:state:{device_code}
        TTL obligatorio de 300 segundos (5 minutos).
        """
        key = f"device:state:{payload.device_code}"
        try:
            data_dict = payload.model_dump(mode="json")
            if tank_level_pct is not None:
                data_dict["tank_level_pct"] = tank_level_pct
                
            await self.redis_client.setex(key, 300, json.dumps(data_dict))
        except Exception as e:
            logger.error(f"[Redis] Error actualizando estado de {payload.device_code}: {e}")

    async def publish_emergency(self, device_code: str, error_count: int, timestamp_iso: str) -> None:
        """
        Publica una alerta en el canal del dispositivo para que 
        los clientes WebSocket conectados la reciban.
        """
        # La variable settings la asume como format(node_id=...) por config antigua, la rehusamos.
        channel = settings.WS_ALERT_CHANNEL.format(node_id=device_code)
        message = json.dumps({
            "type":        "EMERGENCY",
            "device_code": device_code,
            "timestamp":   timestamp_iso,
            "error_count": error_count,
        })
        try:
            await self.redis_client.publish(channel, message)
            logger.info(f"[Redis] Canal {channel} -> Publicada EMERGENCIA")
        except Exception as e:
            logger.error(f"[Redis] Error publicando emergencia en {channel}: {e}")

    async def get_latest_state(self, device_code: str) -> dict | None:
        """
        Retorna el último estado reportado (caché rápida para API REST).
        Evita consultar PostgreSQL/Influx de forma intensiva.
        """
        key = f"device:state:{device_code}"
        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"[Redis] Error leyendo estado de {device_code}: {e}")
        return None

    async def close(self):
        await self.redis_client.aclose()


redis_service = RedisService()
