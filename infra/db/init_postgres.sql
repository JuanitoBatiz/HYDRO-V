-- infra/db/init_postgres.sql
-- Script de inicialización de PostgreSQL para Hydro-V
-- Se ejecuta automáticamente la primera vez que el contenedor arranca
-- Las tablas reales las crea Alembic — este script configura extensiones
-- y crea el schema de auditoría.

-- ── Extensiones ───────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";     -- UUIDs si se necesitan
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- búsqueda trigram (full-text futuro)
CREATE EXTENSION IF NOT EXISTS "btree_gin";     -- índices GIN para JSONB (payload_snapshot)

-- ── Timezone del servidor ─────────────────────────────────────────
SET timezone = 'UTC';

-- ── Permisos del usuario hydrov ───────────────────────────────────
-- (el usuario ya existe porque lo crea POSTGRES_USER en docker-compose)
GRANT ALL PRIVILEGES ON DATABASE hydrov TO hydrov;
