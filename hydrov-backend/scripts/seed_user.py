# hydrov-backend/scripts/seed_user.py
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Importar configuración y modelos
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User

async def seed_admin():
    print(f"Conectando a {settings.POSTGRES_DSN}...")
    engine = create_async_engine(settings.POSTGRES_DSN, echo=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Verificar si ya existe
        # (Para simplicidad, intentamos insertar y manejamos excepción o simplemente asumimos que está vacío por ahora)
        new_user = User(
            email="admin@hydrov.com",
            hashed_password=hash_password("admin123"),
            full_name="Emmanuel Admin",
            is_active=True,
            is_superuser=True
        )
        session.add(new_user)
        try:
            await session.commit()
            print("=========================================")
            print("✅ Usuario Administrador Creado Exitosamente")
            print("=========================================")
            print("Email: admin@hydrov.com")
            print("Pass : admin123")
            print("=========================================")
        except Exception as e:
            print(f"❌ Error al crear usuario (¿Ya existe?): {e}")
            await session.rollback()
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_admin())
