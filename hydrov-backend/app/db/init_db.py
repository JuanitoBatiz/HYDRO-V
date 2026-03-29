# app/db/init_db.py
from sqlalchemy.ext.asyncio import AsyncEngine
from app.db.base import Base
from app.db.session import engine

# Importar todos los modelos aquí para que Base los registre
# Cada vez que agregues un modelo nuevo, impórtalo aquí también
from app.models.alert import EmergencyAlert      # noqa: F401
from app.models.device import Device             # noqa: F401
from app.models.telemetry import TelemetryEvent  # noqa: F401
from app.models.user import User                 # noqa: F401


async def init_db() -> None:
    """
    Crea todas las tablas en PostgreSQL si no existen.
    Se llama una sola vez en el lifespan de FastAPI.
    En producción usar Alembic en lugar de este método.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """
    Elimina todas las tablas. Solo para tests o reset de desarrollo.
    NUNCA llamar en producción.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)