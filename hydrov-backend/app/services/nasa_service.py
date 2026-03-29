# app/services/nasa_service.py
import httpx
from enum import Enum
from typing import Optional
from app.core.config import settings


class NASATemporality(str, Enum):
    HOURLY      = "hourly"
    DAILY       = "daily"
    MONTHLY     = "monthly"
    CLIMATOLOGY = "climatology"


# ── Parámetros prioritarios por temporalidad ──────────────────────
HYDROV_PARAMS = {
    "hourly": [
        "PRECTOTCORR",       # Precipitación corregida
        "T2M",               # Temperatura a 2m
        "RH2M",              # Humedad relativa
        "WS2M",              # Velocidad del viento
        "ALLSKY_SFC_SW_DWN", # Irradiancia solar
    ],
    "daily": [
        "PRECTOTCORR",
        "T2M",
        "T2M_MAX",
        "T2M_MIN",
        "RH2M",
        "WS2M",
        "ALLSKY_SFC_SW_DWN",
    ],
    "monthly": [
        "PRECTOTCORR",
        "T2M",
        "T2M_MAX",
        "T2M_MIN",
        "RH2M",
        "WS2M",
    ],
    "climatology": [
        "PRECTOTCORR",
        "T2M",
        "RH2M",
        "WS2M",
    ],
}


async def fetch_nasa_power(
    temporality: NASATemporality,
    params:      list[str],
    lat:         float = None,
    lon:         float = None,
    start:       Optional[str] = None,
    end:         Optional[str] = None,
    community:   str = None,
    fmt:         str = "JSON",
    time_standard: str = None,
) -> dict:
    """
    Cliente base para todas las APIs temporales de NASA POWER.
    Retorna el JSON crudo de la respuesta.

    Parámetros:
        temporality:   hourly | daily | monthly | climatology
        params:        lista de parámetros NASA a solicitar
        lat/lon:       coordenadas del nodo (default: Nezahualcóyotl)
        start/end:     "20240101" para hourly/daily | "2024" para monthly
        community:     comunidad NASA POWER (default: SB)
        fmt:           formato de respuesta (default: JSON)
        time_standard: LST | UTC (default: LST)
    """
    # Usar valores de config si no se pasan explícitamente
    lat           = lat           or settings.NASA_DEFAULT_LAT
    lon           = lon           or settings.NASA_DEFAULT_LON
    community     = community     or settings.NASA_COMMUNITY
    time_standard = time_standard or settings.NASA_TIME_STANDARD

    url = f"{settings.NASA_POWER_BASE_URL}/api/temporal/{temporality}/point"

    query: dict = {
        "parameters":    ",".join(params),
        "community":     community,
        "longitude":     lon,
        "latitude":      lat,
        "format":        fmt,
        "time-standard": time_standard,
    }

    if start: query["start"] = start
    if end:   query["end"]   = end

    async with httpx.AsyncClient(timeout=settings.NASA_REQUEST_TIMEOUT) as client:
        resp = await client.get(url, params=query)
        resp.raise_for_status()
        return resp.json()