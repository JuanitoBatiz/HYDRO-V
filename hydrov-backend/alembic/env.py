# alembic/env.py
"""
Configuración de Alembic para Hydro-V.

Usa POSTGRES_DSN_SYNC (driver psycopg2 síncrono) porque Alembic
no es async. La DSN async (asyncpg) solo la usa FastAPI en runtime.

Para generar migraciones:
    cd hydrov-backend
    alembic revision --autogenerate -m "descripcion_de_cambio"

Para aplicar migraciones:
    alembic upgrade head

Para revertir una migración:
    alembic downgrade -1
"""
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Asegurarse de que el paquete 'app' esté en el path ──────────
# Esto permite importar app.* desde env.py sin instalarlo como paquete
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Importar config (lee el .env) ────────────────────────────────
from app.core.config import settings

# ── Importar Base + TODOS los modelos para que Alembic los detecte
from app.db.base import Base  # noqa: F401

# IMPORTANTE: si añades un modelo nuevo, impórtalo aquí también
from app.models.user import User                          # noqa: F401
from app.models.device import Device                      # noqa: F401
from app.models.telemetry import TelemetryEvent           # noqa: F401
from app.models.alert import EmergencyAlert               # noqa: F401
from app.models.prediction import AutonomyPrediction, LeakDetection  # noqa: F401

# ── Alembic Config ────────────────────────────────────────────────
config = context.config

# Leer configuración de logging del alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Sobreescribir la URL con la DSN síncrona real del .env
# (psycopg2, no asyncpg — Alembic no soporta async engines)
config.set_main_option("sqlalchemy.url", settings.POSTGRES_DSN_SYNC)

# El MetaData que Alembic comparará contra la DB
target_metadata = Base.metadata


# ─────────────────────────────────────────────────────────────────
#  Modo offline — genera SQL sin conectarse a la DB
# ─────────────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Genera el SQL de la migración sin conectarse a la DB.
    Útil para revisar los cambios antes de aplicarlos.
    Invocado con: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Renderizar tipos de servidor como JSONB correctamente
        render_as_batch=False,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ─────────────────────────────────────────────────────────────────
#  Modo online — aplica migraciones directamente en la DB
# ─────────────────────────────────────────────────────────────────

def run_migrations_online() -> None:
    """
    Aplica las migraciones directamente conectándose a PostgreSQL.
    Invocado con: alembic upgrade head
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # NullPool es correcto para scripts de migración
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,              # detecta cambios de tipo de columna
            compare_server_default=True,    # detecta cambios en server_default
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ── Punto de entrada ──────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
