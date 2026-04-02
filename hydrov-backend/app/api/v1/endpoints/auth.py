# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import json

from app.api.deps import get_db, get_current_user, get_current_token
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.user import (
    UserCreateSchema,
    UserLoginSchema,
    UserResponseSchema,
    TokenSchema,
)
from app.services.redis_service import redis_service

router = APIRouter()


# ─────────────────────────────────────────────────────────────────
#  POST /auth/register
# ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
)
async def register(
    payload: UserCreateSchema,
    db: AsyncSession = Depends(get_db),
) -> UserResponseSchema:
    """
    Registra un nuevo usuario en el sistema.
    - El email debe ser único.
    - La contraseña se almacena como hash bcrypt (nunca en texto plano).
    """
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El email '{payload.email}' ya está registrado",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        role_id=payload.role_id,
        zone_id=payload.zone_id,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ─────────────────────────────────────────────────────────────────
#  POST /auth/login
# ─────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenSchema,
    summary="Iniciar sesión — obtener JWT y guardar en Redis",
)
async def login(
    payload: UserLoginSchema,
    db: AsyncSession = Depends(get_db),
) -> TokenSchema:
    """
    Autentica con email + contraseña, retorna un JWT Bearer
    y guarda la sesión en Redis con un TTL de 24 horas.
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta inactiva — contacta al administrador",
        )

    # Generar JWT
    access_token = create_access_token(subject=user.id)
    expires_in = 86400  # 24 horas

    # Guardar en Redis para el middleware (V2.0)
    user_data = {
        "id": user.id,
        "email": user.email,
        "role_id": user.role_id,
        "zone_id": user.zone_id,
        "full_name": user.full_name,
    }
    await redis_service.redis_client.setex(
        f"session:{access_token}",
        expires_in,
        json.dumps(user_data)
    )

    # Actualizar last_login_at
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return TokenSchema(access_token=access_token, token_type="bearer", expires_in=expires_in)


# ─────────────────────────────────────────────────────────────────
#  POST /auth/logout
# ─────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    summary="Cerrar sesión",
)
async def logout(token: str = Depends(get_current_token)):
    """
    Invalida el token en Redis, forzando un logout efectivo.
    """
    await redis_service.redis_client.delete(f"session:{token}")
    return {"message": "Sesión cerrada exitosamente"}


# ─────────────────────────────────────────────────────────────────
#  GET /auth/me
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    summary="Perfil del usuario autenticado (desde Redis)",
)
async def get_me(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Retorna los datos del usuario cuyo JWT viene en el header y existe en Redis.
    """
    return current_user
