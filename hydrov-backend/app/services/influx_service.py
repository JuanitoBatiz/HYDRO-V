# app/services/influx_service.py
from datetime import datetime, timezone, timedelta
from influxdb_client import Point
from app.db.influx_client import InfluxManager
from app.core.config import settings
from app.core.logger import logger
from app.schemas.mqtt import ESP32PayloadSchema


class InfluxService:
    """
    Servicio de lectura y escritura en InfluxDB.
    Usado por mqtt_service (escritura) y ml_service (lectura).
    """

    # ── Escritura ─────────────────────────────────────────────────

    async def write_telemetry(self, payload: ESP32PayloadSchema) -> None:
        """Escribe telemetría del ESP32 desnormalizada en dos measurements."""
        write_api = InfluxManager.get_write_api()
        
        device_code = payload.device_code
        now = payload.received_at

        # Measurement 1: sensor_reading
        p_sensor = (
            Point("sensor_reading")
            .tag("device_code", device_code)
            .field("turbidity_ntu", float(payload.sensors.turbidity_ntu))
            .field("distance_cm", float(payload.sensors.distance_cm))
            .field("flow_lpm", float(payload.sensors.flow_lpm))
            .field("flow_total_liters", float(payload.sensors.flow_total_liters))
            .time(now)
        )

        # Measurement 2: device_state
        p_state = (
            Point("device_state")
            .tag("device_code", device_code)
            .tag("fsm_state", payload.system_state.state)
            .field("state_duration_ms", payload.system_state.state_duration_ms)
            .field("intake_cycles", payload.system_state.intake_cycles)
            .field("reject_cycles", payload.system_state.reject_cycles)
            .field("error_count", payload.system_state.error_count)
            .time(now)
        )

        await write_api.write(
            bucket=settings.INFLUX_BUCKET_TELEMETRY,
            record=[p_sensor, p_state]
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
        device_code: str,
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
              |> filter(fn: (r) => r._measurement == "sensor_reading")
              |> filter(fn: (r) => r.device_code == "{device_code}")
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
            logger.warning(f"[Influx] Error leyendo consumo de {device_code}: {e}")

        return 150.0

    async def get_days_without_rain(self, device_code: str) -> int:
        """
        Retorna cuántos días consecutivos no ha habido flujo
        pluvial significativo en el nodo.
        """
        query_api = InfluxManager.get_query_api()
        query = f"""
            from(bucket: "{settings.INFLUX_BUCKET_TELEMETRY}")
              |> range(start: -30d)
              |> filter(fn: (r) => r._measurement == "sensor_reading")
              |> filter(fn: (r) => r.device_code == "{device_code}")
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
            logger.warning(f"[Influx] Error leyendo días sin lluvia de {device_code}: {e}")

        return 0

    async def get_neighbor_nodes_data(self, device_code: str) -> list[dict]:
        return []

    async def get_latest_telemetry(self, device_code: str) -> dict | None:
        """Retorna la última lectura de telemetría de un dispositivo."""
        query_api = InfluxManager.get_query_api()
        
        # Leemos ambas measurements para el dispositivo, ignorando las tablas múltiples si se separaron por measurement
        query = f"""
            from(bucket: "{settings.INFLUX_BUCKET_TELEMETRY}")
              |> range(start: -1h)
              |> filter(fn: (r) => r._measurement == "sensor_reading" or r._measurement == "device_state")
              |> filter(fn: (r) => r.device_code == "{device_code}")
              |> last()
        """
        try:
            tables = await query_api.query(query)
            result = {}
            for table in tables:
                for record in table.records:
                    # En una measurement con tags fsm_state por ejemplo, viene el tag
                    if "fsm_state" in record.values:
                        result["fsm_state"] = record.values["fsm_state"]
                    result[record.get_field()] = record.get_value()
            if result:
                return result
        except Exception as e:
            logger.error(f"[Influx] Error leyendo última telemetría de {device_code}: {e}")

        return None


influx_service = InfluxService()