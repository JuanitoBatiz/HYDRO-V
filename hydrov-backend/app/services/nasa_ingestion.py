# app/services/nasa_ingestion.py
from datetime import date, timedelta
from app.services.nasa_service import fetch_nasa_power, HYDROV_PARAMS, NASATemporality
from app.core.config import settings
from app.core.logger import logger


async def ingest_hourly(
    lat: float = None,
    lon: float = None,
    target_date: date = None,
) -> dict:
    """
    Trae datos horarios de un día específico.
    Llamado cada hora por el scheduler en main.py.
    """
    lat         = lat         or settings.NASA_DEFAULT_LAT
    lon         = lon         or settings.NASA_DEFAULT_LON
    target_date = target_date or date.today()

    d = target_date.strftime("%Y%m%d")

    logger.info(f"[NASA] Ingesting hourly data for {d} | lat={lat} lon={lon}")

    return await fetch_nasa_power(
        temporality=NASATemporality.HOURLY,
        params=HYDROV_PARAMS["hourly"],
        lat=lat,
        lon=lon,
        start=d,
        end=d,
    )


async def ingest_daily(
    lat:       float = None,
    lon:       float = None,
    days_back: int   = 7,
) -> dict:
    """
    Trae los últimos N días de datos diarios.
    Llamado una vez al día a las 06:00 LST por el scheduler.
    """
    lat = lat or settings.NASA_DEFAULT_LAT
    lon = lon or settings.NASA_DEFAULT_LON

    end   = date.today()
    start = end - timedelta(days=days_back)

    logger.info(f"[NASA] Ingesting daily data {start} → {end} | lat={lat} lon={lon}")

    return await fetch_nasa_power(
        temporality=NASATemporality.DAILY,
        params=HYDROV_PARAMS["daily"],
        lat=lat,
        lon=lon,
        start=start.strftime("%Y%m%d"),
        end=end.strftime("%Y%m%d"),
    )


async def ingest_monthly(
    lat:        float = None,
    lon:        float = None,
    start_year: int   = None,
    end_year:   int   = None,
) -> dict:
    """
    Trae datos mensuales para calibración estacional.
    Llamado el día 1 de cada mes por el scheduler.
    """
    lat        = lat        or settings.NASA_DEFAULT_LAT
    lon        = lon        or settings.NASA_DEFAULT_LON
    end_year   = end_year   or date.today().year
    start_year = start_year or (end_year - 5)  # últimos 5 años por defecto

    logger.info(f"[NASA] Ingesting monthly data {start_year} → {end_year} | lat={lat} lon={lon}")

    return await fetch_nasa_power(
        temporality=NASATemporality.MONTHLY,
        params=HYDROV_PARAMS["monthly"],
        lat=lat,
        lon=lon,
        start=str(start_year),
        end=str(end_year),
    )


async def ingest_climatology(
    lat: float = None,
    lon: float = None,
) -> dict:
    """
    Trae la climatología histórica completa.
    Se llama UNA SOLA VEZ al registrar un nuevo nodo.
    Provee la línea base permanente para ese nodo.
    """
    lat = lat or settings.NASA_DEFAULT_LAT
    lon = lon or settings.NASA_DEFAULT_LON

    logger.info(f"[NASA] Ingesting climatology baseline | lat={lat} lon={lon}")

    return await fetch_nasa_power(
        temporality=NASATemporality.CLIMATOLOGY,
        params=HYDROV_PARAMS["climatology"],
        lat=lat,
        lon=lon,
    )