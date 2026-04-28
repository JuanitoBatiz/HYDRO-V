# app/api/deps.py
"""
Dependencias reutilizables de FastAPI.
Importar desde aquí en todos los endpoints para evitar duplicación.
"""
from typing import AsyncGenerator, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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


# ─────────────────────────────────────────────────────────────────
#  Acceso server-to-server (Grafana / servicios internos)
# ─────────────────────────────────────────────────────────────────

# Esquemas de seguridad para verify_grafana_or_user:
# auto_error=False → la función decide el 401, no FastAPI automáticamente.
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_optional_bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


async def verify_grafana_or_user(
    x_api_key: str | None = Depends(_api_key_header),
    token:     str | None = Depends(_optional_bearer),
) -> dict:
    """
    Dependencia dual para endpoints consumidos por Grafana y usuarios humanos.

    Flujo de resolución (en orden):
      1. Si el header X-API-Key está presente y coincide con GRAFANA_API_KEY
         → acceso concedido como identidad interna 'grafana-service'.
      2. Si hay un Bearer token válido en Redis
         → acceso concedido como el usuario autenticado.
      3. En cualquier otro caso → 401 Unauthorized.

    Uso:
        async def endpoint(_ = Depends(verify_grafana_or_user)): ...
    """
    # ── Rama 1: API Key de servicio ──────────────────────────────
    if x_api_key is not None:
        if x_api_key == settings.GRAFANA_API_KEY:
            return {"sub": "grafana-service", "role_id": 0, "internal": True}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key inválida",
        )

    # ── Rama 2: JWT Bearer ───────────────────────────────────────
    if token:
        session_data = await redis_service.redis_client.get(f"session:{token}")
        if session_data:
            return json.loads(session_data)

    # ── Rama 3: Sin credenciales ─────────────────────────────────
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Se requiere autenticación (Bearer token o X-API-Key)",
        headers={"WWW-Authenticate": "Bearer"},
    )
