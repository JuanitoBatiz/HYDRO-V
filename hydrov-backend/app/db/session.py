# app/db/session.py
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────
engine: AsyncEngine = create_async_engine(
    settings.POSTGRES_DSN,
    echo=settings.DEBUG,       # loguea SQL solo en DEBUG
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,        # verifica conexiones antes de usarlas
)

# ── Session factory ───────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,    # evita lazy loading issues en async
)

# ── Dependency para FastAPI ───────────────────────────────────────
async def get_db() -> AsyncSession:
    """
    Dependency de FastAPI. Uso en endpoints:

        from app.db.session import get_db
        from sqlalchemy.ext.asyncio import AsyncSession
        from fastapi import Depends

        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise