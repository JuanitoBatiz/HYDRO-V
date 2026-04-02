-- HYDRO-V · init_postgres.sql · Arquitectura v2.0
-- Ejecutado una única vez en la primera materialización del volumen postgres_data

SET timezone = 'UTC';

-- Extensiones requeridas
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- uuid_generate_v4() para futuros IDs
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- Índices de similitud textual
CREATE EXTENSION IF NOT EXISTS "btree_gin";   -- Índices GIN para JSONB en alertas y audit_logs

-- Confirmar configuración
DO $$
BEGIN
  RAISE NOTICE 'Hydro-V PostgreSQL inicializado correctamente. Timezone: %', current_setting('timezone');
END $$;
