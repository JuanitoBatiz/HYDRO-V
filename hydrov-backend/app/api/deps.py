# app/api/deps.py
"""
Dependencias reutilizables de FastAPI.
Importar desde aquí en todos los endpoints para evitar duplicación.
"""
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id, oauth2_scheme
from app.db.session import AsyncSessionLocal
from app.db.influx_client import InfluxManager
from app.models.user import User


# ─────────────────────────────────────────────────────────────────
#  PostgreSQL — session SQLAlchemy
# ─────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency que provee una AsyncSession de SQLAlchemy.
    Hace commit automático al salir limpio, rollback si hay excepción.

    Uso:
        async def endpoint(db: AsyncSession = Depends(get_db)): ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─────────────────────────────────────────────────────────────────
#  PostgreSQL — raw pool asyncpg (para mqtt_service y queries raw)
# ─────────────────────────────────────────────────────────────────

async def get_pg_pool(request: Request):
    """
    Retorna el asyncpg pool inyectado en app.state por el lifespan.
    Usado en endpoints que necesitan queries raw sin ORM (ej: bulk inserts).

    Uso:
        async def endpoint(pool = Depends(get_pg_pool)): ...
    """
    return request.app.state.pg_pool


# ─────────────────────────────────────────────────────────────────
#  InfluxDB
# ─────────────────────────────────────────────────────────────────

def get_influx_write():
    """
    Retorna el WriteApiAsync de InfluxDB (ya inicializado en lifespan).

    Uso:
        async def endpoint(write_api = Depends(get_influx_write)): ...
    """
    return InfluxManager.get_write_api()


def get_influx_query():
    """
    Retorna el QueryApiAsync de InfluxDB.

    Uso:
        async def endpoint(query_api = Depends(get_influx_query)): ...
    """
    return InfluxManager.get_query_api()


# ─────────────────────────────────────────────────────────────────
#  Usuario autenticado (combina JWT + Redis session lookup)
# ─────────────────────────────────────────────────────────────────
from app.services.redis_service import redis_service
import json

async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """
    Dependency que valida el Bearer token directamente contra Redis (V2.0).
    Retorna un diccionario con los datos del usuario. Lanza 401 si no existe.
    """
    session_data = await redis_service.redis_client.get(f"session:{token}")
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada o inválida",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return json.loads(session_data)


async def get_current_token(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dependency para obtener el string del token.
    """
    return token


async def get_current_superuser(
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Como get_current_user pero además exige role_id == 1 (admin).
    Usar en endpoints de administración.
    """
    if user.get("role_id") != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return user
