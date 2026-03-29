# app/services/nasa_parser.py
from datetime import datetime, timezone
from typing import Generator
from influxdb_client import Point
from app.core.logger import logger

# Valor nulo de NASA POWER — siempre -999
NASA_NULL_VALUE = -999.0

# Mapeo de parámetros NASA a nombres legibles para InfluxDB
PARAM_LABELS = {
    "PRECTOTCORR":       "precipitation_mm",
    "T2M":               "temperature_c",
    "T2M_MAX":           "temperature_max_c",
    "T2M_MIN":           "temperature_min_c",
    "RH2M":              "humidity_pct",
    "WS2M":              "wind_speed_ms",
    "ALLSKY_SFC_SW_DWN": "solar_irradiance_wm2",
}


def _is_hourly(sample_key: str) -> bool:
    """Detecta si los datos son horarios (key de 10 dígitos) o diarios (8 dígitos)."""
    return len(sample_key) == 10


def _parse_timestamp(key: str, hourly: bool) -> datetime:
    """Convierte la key de NASA POWER a datetime UTC."""
    fmt = "%Y%m%d%H" if hourly else "%Y%m%d"
    dt  = datetime.strptime(key, fmt)
    return dt.replace(tzinfo=timezone.utc)


def parse_to_influx_points(
    nasa_json:   dict,
    lat:         float,
    lon:         float,
    bucket:      str,
    measurement: str = "nasa_weather",
) -> Generator[Point, None, None]:
    """
    Convierte el JSON crudo de NASA POWER en Points de InfluxDB.

    Uso en nasa_ingestion después de cada fetch:
        points = list(parse_to_influx_points(data, lat, lon, bucket="nasa_weather_cache"))
        await write_api.write(bucket=bucket, record=points)

    Maneja automáticamente:
        - Datos horarios (keys de 10 dígitos: YYYYMMDDHH)
        - Datos diarios  (keys de 8  dígitos: YYYYMMDD)
        - Climatología   (keys mensuales: "JAN", "FEB" ... "ANN")
        - Valores nulos NASA (-999) → None
    """
    try:
        params_data: dict = nasa_json["properties"]["parameter"]
    except KeyError:
        logger.error("[NASA Parser] JSON inesperado — falta 'properties.parameter'")
        return

    if not params_data:
        logger.warning("[NASA Parser] JSON sin parámetros")
        return

    # Detectar temporalidad por la forma de las keys
    first_param_values = next(iter(params_data.values()))
    sample_key         = next(iter(first_param_values))
    hourly             = _is_hourly(sample_key)
    is_climatology     = not sample_key.isdigit()  # "JAN", "FEB", etc.

    # Recolectar todos los timestamps únicos
    timestamps: set[str] = set()
    for param_values in params_data.values():
        timestamps.update(param_values.keys())

    for ts_str in sorted(timestamps):

        # ── Climatología: keys son strings de mes ("JAN", "ANN") ──
        if is_climatology:
            point = (
                Point(measurement)
                .tag("lat",    str(lat))
                .tag("lon",    str(lon))
                .tag("period", ts_str)        # "JAN", "FEB", ..., "ANN"
                .tag("type",   "climatology")
            )
        else:
            ts    = _parse_timestamp(ts_str, hourly)
            ptype = "hourly" if hourly else "daily"
            point = (
                Point(measurement)
                .tag("lat",  str(lat))
                .tag("lon",  str(lon))
                .tag("type", ptype)
                .time(ts)
            )

        # ── Agregar cada parámetro como field ─────────────────────
        has_valid_field = False

        for param, values in params_data.items():
            raw = values.get(ts_str, NASA_NULL_VALUE)

            # Ignorar valores nulos de NASA
            if raw == NASA_NULL_VALUE or raw is None:
                continue

            # Usar nombre legible si está en el mapeo, si no usar el original
            field_name = PARAM_LABELS.get(param, param.lower())
            point      = point.field(field_name, float(raw))
            has_valid_field = True

        # Solo yieldeamos el point si tiene al menos un campo válido
        if has_valid_field:
            yield point
        else:
            logger.debug(f"[NASA Parser] Timestamp {ts_str} sin campos válidos — omitido")


def parse_to_forecast_cache(nasa_json: dict) -> list[dict]:
    """
    Convierte datos horarios de NASA POWER en una lista de dicts
    para guardar en Redis como forecast de las próximas 24h.

    Retorna:
        [
            {"hour": "2024030800", "precipitation_mm": 2.5, "temperature_c": 18.4, ...},
            ...
        ]
    """
    try:
        params_data = nasa_json["properties"]["parameter"]
    except KeyError:
        logger.error("[NASA Parser] JSON inesperado para forecast cache")
        return []

    if not params_data:
        return []

    forecast: list[dict] = []
    first_values = next(iter(params_data.values()))

    for ts_str in sorted(first_values.keys()):
        entry: dict = {"hour": ts_str}

        for param, values in params_data.items():
            raw = values.get(ts_str, NASA_NULL_VALUE)
            if raw == NASA_NULL_VALUE:
                continue
            field_name      = PARAM_LABELS.get(param, param.lower())
            entry[field_name] = float(raw)

        forecast.append(entry)

    return forecast