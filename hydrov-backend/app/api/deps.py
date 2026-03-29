# app/api/deps.py
"""
Dependencias reutilizables de FastAPI.
Importar desde aquí en todos los endpoints para evitar duplicación.
"""
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
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
#  Usuario autenticado (combina JWT + DB lookup)
# ─────────────────────────────────────────────────────────────────

async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency que valida el JWT Y comprueba que el usuario existe
    y está activo en PostgreSQL.

    Retorna el ORM User completo. Lanza 401/403 si algo falla.

    Uso:
        async def endpoint(user: User = Depends(get_current_user)): ...
    """
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )
    return user


async def get_current_superuser(
    user: User = Depends(get_current_user),
) -> User:
    """
    Como get_current_user pero además exige is_superuser=True.
    Usar en endpoints de administración.
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return user
