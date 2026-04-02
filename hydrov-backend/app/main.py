# app/main.py
import asyncio
from contextlib import asynccontextmanager

import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import logger
from app.db.influx_client import InfluxManager
from app.db.init_db import init_db
from app.services.mqtt_service import mqtt_to_influx_loop
from app.services.nasa_ingestion import ingest_hourly, ingest_daily, ingest_monthly


# ─────────────────────────────────────────────────────────────────
#  Estado global compartido (accesible desde endpoints via app.state)
# ─────────────────────────────────────────────────────────────────
_pg_pool:     asyncpg.Pool | None    = None
_mqtt_task:   asyncio.Task | None    = None
_scheduler:   AsyncIOScheduler | None = None


# ─────────────────────────────────────────────────────────────────
#  Lifespan — startup & shutdown
# ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Todo lo que está antes del 'yield' se ejecuta al arrancar.
    Todo lo que está después del 'yield' se ejecuta al apagar.
    """
    global _pg_pool, _mqtt_task, _scheduler

    # ── 1. PostgreSQL connection pool ─────────────────────────────
    logger.info("[Startup] Conectando PostgreSQL...")
    _pg_pool = await asyncpg.create_pool(
        dsn=settings.POSTGRES_DSN_SYNC.replace("postgresql://", "postgresql://"),
        min_size=5,
        max_size=20,
        command_timeout=60,
    )
    app.state.pg_pool = _pg_pool
    logger.info("[Startup] PostgreSQL pool listo ✓")

    # ── 2. Tablas Alembic y Seed Catalyst v2.0 ─────────────────────
    from app.seed import run_seed
    try:
        async with _pg_pool.acquire() as db:
            await run_seed(db)
        logger.info("[Startup] Seed de catálogos v2.0 inyectado ✓")
    except Exception as e:
        logger.error(f"[Startup] Error ejecutando seed: {e}")

    # ── 3. InfluxDB async client ──────────────────────────────────
    logger.info("[Startup] Conectando InfluxDB...")
    await InfluxManager.connect()
    logger.info("[Startup] InfluxDB listo ✓")

    # ── 4. MQTT background task ───────────────────────────────────
    logger.info("[Startup] Lanzando MQTT listener...")
    _mqtt_task = asyncio.create_task(
        mqtt_to_influx_loop(_pg_pool),
        name="mqtt_to_influx_loop",
    )
    logger.info("[Startup] MQTT listener activo ✓")

    # ── 5. APScheduler — ingesta periódica de NASA POWER ─────────
    logger.info("[Startup] Configurando APScheduler...")
    _scheduler = AsyncIOScheduler(timezone="America/Mexico_City")

    # Cada N horas: datos horarios del día actual
    _scheduler.add_job(
        ingest_hourly,
        trigger="interval",
        hours=settings.NASA_SCHEDULER_HOURLY_INTERVAL,
        id="nasa_hourly",
        name="NASA POWER — datos horarios",
        replace_existing=True,
    )

    # Cada día a las 06:00 LST: últimos 7 días de datos diarios
    _scheduler.add_job(
        ingest_daily,
        trigger="cron",
        hour=settings.NASA_SCHEDULER_DAILY_CRON_HOUR,
        minute=0,
        id="nasa_daily",
        name="NASA POWER — datos diarios",
        replace_existing=True,
    )

    # El día 1 de cada mes: datos mensuales para calibración estacional
    _scheduler.add_job(
        ingest_monthly,
        trigger="cron",
        day=1,
        hour=7,
        minute=0,
        id="nasa_monthly",
        name="NASA POWER — datos mensuales",
        replace_existing=True,
    )

    _scheduler.start()
    app.state.scheduler = _scheduler
    logger.info("[Startup] APScheduler activo ✓")

    logger.info(
        f"[Startup] {settings.APP_NAME} v{settings.APP_VERSION} "
        f"listo en modo '{settings.ENVIRONMENT}' 🚀"
    )

    # ── Entrega el control a FastAPI ──────────────────────────────
    yield

    # ══ SHUTDOWN ══════════════════════════════════════════════════

    logger.info("[Shutdown] Apagando servicios...")

    # 1. Detener scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Shutdown] APScheduler detenido ✓")

    # 2. Cancelar MQTT task
    if _mqtt_task and not _mqtt_task.done():
        _mqtt_task.cancel()
        try:
            await _mqtt_task
        except asyncio.CancelledError:
            pass
        logger.info("[Shutdown] MQTT listener detenido ✓")

    # 3. Cerrar InfluxDB
    await InfluxManager.close()
    logger.info("[Shutdown] InfluxDB cerrado ✓")

    # 4. Cerrar PostgreSQL pool
    if _pg_pool:
        await _pg_pool.close()
        logger.info("[Shutdown] PostgreSQL pool cerrado ✓")

    logger.info("[Shutdown] Hydro-V apagado limpiamente ✓")


# ─────────────────────────────────────────────────────────────────
#  Aplicación FastAPI
# ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Backend del sistema IoT de captación y gestión hídrica HYDRO-V. "
        "Recibe telemetría de nodos ESP32 vía MQTT, la persiste en InfluxDB "
        "y expone endpoints REST + WebSocket al dashboard."
    ),
    docs_url="/docs"     if settings.DEBUG else None,
    redoc_url="/redoc"   if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────
#  CORS
# ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────
#  Routers
# ─────────────────────────────────────────────────────────────────
# from app.api.v1.router import api_v1_router  # noqa: E402 — después del app
# app.include_router(api_v1_router, prefix="/api/v1")


# ─────────────────────────────────────────────────────────────────
#  Health check — siempre público, incluso en producción
# ─────────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"], summary="Health check del sistema")
async def health_check():
    """
    Verifica que el backend está vivo y los servicios críticos están up.
    Usado por Docker healthcheck y load balancers.
    """
    influx_ok = InfluxManager._client is not None
    pg_ok     = _pg_pool is not None and not _pg_pool._closed

    return {
        "status":      "ok" if (influx_ok and pg_ok) else "degraded",
        "version":     settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "services": {
            "postgres": "up" if pg_ok     else "down",
            "influxdb": "up" if influx_ok else "down",
            "mqtt":     "up" if (_mqtt_task and not _mqtt_task.done()) else "down",
            "scheduler": "up" if (_scheduler and _scheduler.running)   else "down",
        },
    }
