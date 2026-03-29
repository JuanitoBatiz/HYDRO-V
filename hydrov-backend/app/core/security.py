# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.schemas.user import TokenPayloadSchema


# ── Bcrypt context ────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── OAuth2 scheme — apunta al futuro endpoint de login ────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ─────────────────────────────────────────────────────────────────
#  Password hashing
# ─────────────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Genera el hash bcrypt de una contraseña en texto plano.

    Uso al registrar un usuario:
        user.hashed_password = hash_password(password)
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica que una contraseña en texto plano coincide con su hash bcrypt.

    Uso en el endpoint de login:
        if not verify_password(form.password, user.hashed_password):
            raise HTTPException(401, "Credenciales inválidas")
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ─────────────────────────────────────────────────────────────────
#  JWT — Creación
# ─────────────────────────────────────────────────────────────────

def create_access_token(
    subject: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Genera un JWT firmado con HS256.

    Args:
        subject:       ID del usuario (claim 'sub').
        expires_delta: Tiempo de vida personalizado. Si no se pasa
                       usa ACCESS_TOKEN_EXPIRE_MINUTES del .env.

    Retorna el token como string listo para incluir en la respuesta.

    Uso en el endpoint de login:
        token = create_access_token(subject=user.id)
        return TokenSchema(access_token=token)
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload = {
        "sub": str(subject),   # JWT estándar: sub debe ser string
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


# ─────────────────────────────────────────────────────────────────
#  JWT — Decodificación
# ─────────────────────────────────────────────────────────────────

def decode_token(token: str) -> TokenPayloadSchema:
    """
    Decodifica y valida un JWT. Lanza HTTPException 401 si:
        - El token está expirado
        - La firma no es válida
        - El claim 'sub' está ausente o no es un entero válido

    Retorna un TokenPayloadSchema validado.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        raw = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        sub_str: Optional[str] = raw.get("sub")

        if sub_str is None:
            raise credentials_exception

        user_id = int(sub_str)

    except (JWTError, ValueError):
        raise credentials_exception

    return TokenPayloadSchema(sub=user_id, exp=raw.get("exp"))


# ─────────────────────────────────────────────────────────────────
#  FastAPI Dependency — usuario autenticado
# ─────────────────────────────────────────────────────────────────

async def get_current_user_id(
    token: str = Depends(oauth2_scheme),
) -> int:
    """
    Dependency de FastAPI que extrae el user_id del JWT del header
    'Authorization: Bearer <token>'.

    Uso en cualquier endpoint protegido:
        @router.get("/me")
        async def me(user_id: int = Depends(get_current_user_id)):
            ...

    Retorna el user_id (int). Si el token es inválido lanza 401.
    """
    payload = decode_token(token)
    return payload.sub
