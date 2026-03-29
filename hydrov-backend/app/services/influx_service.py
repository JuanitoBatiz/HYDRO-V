# app/services/influx_service.py
from datetime import datetime, timezone, timedelta
from influxdb_client import Point
from app.db.influx_client import InfluxManager
from app.core.config import settings
from app.core.logger import logger


class InfluxService:
    """
    Servicio de lectura y escritura en InfluxDB.
    Usado por mqtt_service (escritura) y ml_service (lectura).
    """

    # ── Escritura ─────────────────────────────────────────────────

    async def write_telemetry(self, point: Point) -> None:
        """Escribe un punto de telemetría del ESP32."""
        write_api = InfluxManager.get_write_api()
        await write_api.write(
            bucket=settings.INFLUX_BUCKET_TELEMETRY,
            record=point,
        )

    async def write_nasa_points(self, points: list[Point]) -> None:
        """Escribe puntos de datos NASA POWER."""
        write_api = InfluxManager.get_write_api()
        await write_api.write(
            bucket=settings.INFLUX_BUCKET_NASA,
            record=points,
        )

    # ── Lectura ───────────────────────────────────────────────────

    async def get_avg_daily_consumption(
        self,
        node_id: str,
        days:    int = 7,
    ) -> float:
        """
        Calcula el consumo promedio diario en litros
        de los últimos N días para un nodo.
        """
        query_api = InfluxManager.get_query_api()
        query = f"""
            from(bucket: "{settings.INFLUX_BUCKET_TELEMETRY}")
              |> range(start: -{days}d)
              |> filter(fn: (r) => r._measurement == "sensor_telemetry")
              |> filter(fn: (r) => r.node_id == "{node_id}")
              |> filter(fn: (r) => r._field == "flow_total_liters")
              |> difference()
              |> mean()
        """
        try:
            tables = await query_api.query(query)
            for table in tables:
                for record in table.records:
                    val = record.get_value()
                    if val is not None:
                        return float(val)
        except Exception as e:
            logger.warning(f"[Influx] Error leyendo consumo de {node_id}: {e}")

        return 150.0  # default conservador litros/día familia promedio

    async def get_days_without_rain(self, node_id: str) -> int:
        """
        Retorna cuántos días consecutivos no ha habido flujo
        pluvial significativo en el nodo.
        """
        query_api = InfluxManager.get_query_api()
        query = f"""
            from(bucket: "{settings.INFLUX_BUCKET_TELEMETRY}")
              |> range(start: -30d)
              |> filter(fn: (r) => r._measurement == "sensor_telemetry")
              |> filter(fn: (r) => r.node_id == "{node_id}")
              |> filter(fn: (r) => r._field == "flow_lpm")
              |> filter(fn: (r) => r._value > 0.5)
              |> last()
        """
        try:
            tables = await query_api.query(query)
            for table in tables:
                for record in table.records:
                    last_flow = record.get_time()
                    if last_flow:
                        delta = datetime.now(timezone.utc) - last_flow
                        return delta.days
        except Exception as e:
            logger.warning(f"[Influx] Error leyendo días sin lluvia de {node_id}: {e}")

        return 0

    async def get_neighbor_nodes_data(self, node_id: str) -> list[dict]:
        """
        Obtiene los últimos datos de flujo y nivel de nodos vecinos.
        Por ahora retorna lista vacía — se implementa cuando
        haya múltiples nodos registrados.
        """
        # TODO: cuando haya múltiples nodos, consultar sus últimas
        # lecturas y retornarlas para alimentar la GNN de Emma
        return []

    async def get_latest_telemetry(self, node_id: str) -> dict | None:
        """Retorna la última lectura de telemetría de un nodo."""
        query_api = InfluxManager.get_query_api()
        query = f"""
            from(bucket: "{settings.INFLUX_BUCKET_TELEMETRY}")
              |> range(start: -1h)
              |> filter(fn: (r) => r._measurement == "sensor_telemetry")
              |> filter(fn: (r) => r.node_id == "{node_id}")
              |> last()
              |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
        """
        try:
            tables = await query_api.query(query)
            for table in tables:
                for record in table.records:
                    return dict(record.values)
        except Exception as e:
            logger.error(f"[Influx] Error leyendo última telemetría de {node_id}: {e}")

        return None


influx_service = InfluxService()