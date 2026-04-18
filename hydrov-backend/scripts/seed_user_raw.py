import asyncio
import asyncpg
import bcrypt
import sys

from app.core.config import settings

async def seed_admin():
    print(f"Generando hash limpio para admin123 y guardando en BD...")
    plain_password = b"admin123"
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password, salt).decode('utf-8')
    
    conn = await asyncpg.connect(settings.POSTGRES_DSN_SYNC.replace('postgresql://', 'postgresql://'))
    try:
        await conn.execute(
            """
            INSERT INTO users (email, hashed_password, name, is_active, is_superuser, created_at, updated_at) 
            VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
            ON CONFLICT (email) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
            """,
            "admin@hydrov.com", hashed, "Emmanuel Admin", True, True
        )
        print(f"✅ Usuario actualizado en BDD con hash: {hashed}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed_admin())
