# infra/docker/backend.Dockerfile
# ─────────────────────────────────────────────────────────────────
#  Multi-stage build para el backend FastAPI de Hydro-V
#  Stage 1 (builder): instala dependencias Python
#  Stage 2 (runtime): imagen mínima sin herramientas de build
# ─────────────────────────────────────────────────────────────────

# ── Stage 1: Builder ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Instalar dependencias del sistema necesarias para compilar wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (layer cache eficiente)
COPY requirements.txt .

# Instalar dependencias en un directorio separado para copiarlo luego
# (⚠️ DOCKER USARÁ SU MEMORIA CACHÉ AQUÍ PARA AHORRARTE LA HORA Y MEDIA ⚠️)
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── LA CORRECCIÓN MÁGICA: Instalar requirements extra súper rápido ──
COPY requirements-extra.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements-extra.txt
# ─────────────────────────────────────────────────────────────────

# ── Stage 2: Runtime ─────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Solo dependencias de sistema runtime (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar paquetes Python instalados del builder
COPY --from=builder /install /usr/local

# Copiar el código fuente
COPY . .

# Usuario no-root para seguridad
RUN useradd --no-create-home --shell /bin/false hydrov \
    && chown -R hydrov:hydrov /app
USER hydrov

# Puerto de la aplicación
EXPOSE 8000

# Health check interno
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Arrancar con uvicorn en modo producción
# Para desarrollo, docker-compose sobreescribe esto con --reload
CMD ["uvicorn", "app.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "2", \
    "--log-level", "info"]