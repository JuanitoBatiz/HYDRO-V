import json
import asyncpg
import redis.asyncio as redis
from app.core.config import settings
from app.core.logger import logger

class DeviceCache:
    def __init__(self, pg_pool: asyncpg.Pool):
        self.pg_pool = pg_pool
        # decode_responses=True permite que redis devuelva strings en lugar de bytes
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get_device_metadata(self, device_code: str) -> dict | None:
        """
        Obtiene la metadata del dispositivo desde Redis (caché).
        Si no existe en caché, la consulta en PostgreSQL y la cachea.
        """
        cache_key = f"hydrov:device_meta:{device_code}"
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"[Cache] Error leyendo de Redis para {device_code}: {e}")

        # Si no está en caché o falló Redis, consultar PostgreSQL
        try:
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT d.id, d.cistern_capacity_liters, d.cistern_height_cm,
                           z.zone_code
                    FROM devices d
                    LEFT JOIN zones z ON z.id = d.zone_id
                    WHERE d.device_code = $1 AND d.status != 'inactive'
                    """,
                    device_code
                )

            if row:
                metadata = {
                    "id": row["id"],
                    "cistern_capacity_liters": row["cistern_capacity_liters"],
                    "cistern_height_cm": row["cistern_height_cm"],
                    "zone_code": row["zone_code"],  # puede ser None si no tiene zona
                }
                # Guardar en Redis con TTL de 1 hora
                try:
                    await self.redis_client.setex(cache_key, 3600, json.dumps(metadata))
                except Exception as e:
                    logger.warning(f"[Cache] Error cacheando metadata en Redis para {device_code}: {e}")

                return metadata
        except Exception as e:
            logger.error(f"[Cache] Error consultando PostgreSQL para {device_code}: {e}")

        return None

    async def get_zone_code(self, device_code: str) -> str | None:
        """
        Atajo para obtener solo el zone_code de un dispositivo.
        Reutiliza la metadata completa (que ya incluye zone_code tras la mejora I-02).
        """
        meta = await self.get_device_metadata(device_code)
        return meta.get("zone_code") if meta else None

    async def close(self):
        """Cierra la conexión al cliente de Redis."""
        await self.redis_client.aclose()
