# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.user import (
    UserCreateSchema,
    UserLoginSchema,
    UserResponseSchema,
    TokenSchema,
)

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
        name=payload.name,
        hashed_password=hash_password(payload.password),
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
    summary="Iniciar sesión — obtener JWT",
)
async def login(
    payload: UserLoginSchema,
    db: AsyncSession = Depends(get_db),
) -> TokenSchema:
    """
    Autentica con email + contraseña y retorna un JWT Bearer.
    Enviar en todas las rutas protegidas: `Authorization: Bearer <token>`
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
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

    return TokenSchema(access_token=create_access_token(subject=user.id))


# ─────────────────────────────────────────────────────────────────
#  GET /auth/me
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponseSchema,
    summary="Perfil del usuario autenticado",
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponseSchema:
    """
    Retorna los datos del usuario cuyo JWT viene en el header.
    Útil para que el frontend valide si la sesión sigue activa.
    """
    return current_user
