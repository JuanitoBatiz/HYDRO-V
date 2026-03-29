# app/services/ml_service.py
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from app.core.logger import logger
from app.core.config import settings

# ── Agregar hydrov-ml al path para importar sus módulos ──────────
ML_PATH = Path(__file__).parent.parent.parent.parent / "hydrov-ml" / "src"
sys.path.insert(0, str(ML_PATH))

from inference.predict_autonomy import predict_autonomy
from inference.detect_leaks import detect_leak


class MLService:
    """
    Puente entre el backend FastAPI y los modelos de Emma.
    Consume influx_service para obtener datos históricos
    y nasa_service para el forecast meteorológico.
    """

    async def get_autonomy_prediction(
        self,
        node_id:       str,
        level_pct:     float,
        lat:           float = None,
        lon:           float = None,
    ) -> dict:
        """
        Calcula los días de autonomía hídrica para un nodo.
        Combina telemetría del nodo + datos NASA POWER.

        Retorna dict con days_autonomy, confidence y alert.
        """
        from app.services.influx_service import InfluxService
        from app.services.nasa_service import fetch_nasa_power, HYDROV_PARAMS, NASATemporality

        lat = lat or settings.NASA_DEFAULT_LAT
        lon = lon or settings.NASA_DEFAULT_LON

        influx = InfluxService()

        # ── Consumo promedio últimos 7 días ───────────────────────
        avg_consumption = await influx.get_avg_daily_consumption(node_id, days=7)

        # ── Forecast NASA POWER próximas 72h ─────────────────────
        today = datetime.now(timezone.utc)
        try:
            nasa_data = await fetch_nasa_power(
                temporality=NASATemporality.DAILY,
                params=HYDROV_PARAMS["daily"],
                lat=lat,
                lon=lon,
                start=today.strftime("%Y%m%d"),
                end=(today + timedelta(days=3)).strftime("%Y%m%d"),
            )
            params = nasa_data["properties"]["parameter"]
            # Sumar precipitación de los próximos 3 días
            precip_values = list(params.get("PRECTOTCORR", {}).values())
            forecast_precip = sum(
                v for v in precip_values if v != -999
            )
            temp_values = [v for v in params.get("T2M", {}).values() if v != -999]
            temperature  = sum(temp_values) / len(temp_values) if temp_values else 20.0
            hum_values   = [v for v in params.get("RH2M", {}).values() if v != -999]
            humidity     = sum(hum_values) / len(hum_values) if hum_values else 50.0
        except Exception as e:
            logger.warning(f"[ML] NASA POWER no disponible, usando defaults: {e}")
            forecast_precip = 0.0
            temperature     = 20.0
            humidity        = 50.0

        # ── Días sin lluvia (desde InfluxDB) ─────────────────────
        days_without_rain = await influx.get_days_without_rain(node_id)

        result = predict_autonomy(
            level_pct=level_pct,
            avg_consumption_lpd=avg_consumption,
            forecast_precip_mm=forecast_precip,
            temperature_c=temperature,
            humidity_pct=humidity,
            days_without_rain=days_without_rain,
            month=today.month,
        )

        logger.info(
            f"[ML] Autonomy prediction | node={node_id} "
            f"days={result['days_autonomy']} alert={result['alert']}"
        )
        return result

    async def get_leak_detection(
        self,
        node_id:  str,
        flow_lpm: float,
        level_pct: float,
    ) -> dict:
        """
        Ejecuta detección de fugas para un nodo.
        Por ahora corre con nodo local — cuando haya múltiples
        nodos se alimentará con datos de vecinos desde InfluxDB.
        """
        from app.services.influx_service import InfluxService

        influx   = InfluxService()
        neighbors = await influx.get_neighbor_nodes_data(node_id)

        neighbor_flows  = [n["flow_lpm"]  for n in neighbors]
        neighbor_levels = [n["level_pct"] for n in neighbors]

        result = detect_leak(
            node_id=node_id,
            flow_lpm=flow_lpm,
            level_pct=level_pct,
            neighbor_flows=neighbor_flows,
            neighbor_levels=neighbor_levels,
        )

        if result["leak_detected"]:
            logger.warning(
                f"[ML] FUGA DETECTADA | node={node_id} "
                f"score={result['anomaly_score']}"
            )

        return result


ml_service = MLService()