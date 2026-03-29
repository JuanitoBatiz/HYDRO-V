#!/bin/bash
# infra/scripts/setup_local.sh
# ─────────────────────────────────────────────────────────────────
#  Script de configuración del entorno local de Hydro-V.
#  Ejecutar UNA SOLA VEZ al clonar el repositorio por primera vez.
#
#  Qué hace:
#    1. Verifica prerequisitos (Docker, Python, Node)
#    2. Crea el .env desde .env.example
#    3. Instala dependencias Python (backend + dev)
#    4. Genera los modelos ML dummy (para que el backend arranque)
#    5. Levanta el stack Docker (PG, InfluxDB, Redis)
#    6. Aplica migraciones de Alembic
#    7. Verifica que todo está vivo con /health
#
#  Uso:
#    chmod +x infra/scripts/setup_local.sh
#    ./infra/scripts/setup_local.sh
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Colores ───────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()     { echo -e "${BLUE}[setup]${NC} $1"; }
ok()      { echo -e "${GREEN}  ✓${NC} $1"; }
warn()    { echo -e "${YELLOW}  ⚠${NC} $1"; }
error()   { echo -e "${RED}  ✗ ERROR:${NC} $1"; exit 1; }
section() { echo -e "\n${CYAN}══ $1 ══${NC}"; }

# ── Rutas ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/hydrov-backend"
ML_DIR="$ROOT_DIR/hydrov-ml"

echo ""
echo -e "${CYAN}"
echo "  ██╗  ██╗██╗   ██╗██████╗ ██████╗  ██████╗       ██╗   ██╗"
echo "  ██║  ██║╚██╗ ██╔╝██╔══██╗██╔══██╗██╔═══██╗      ██║   ██║"
echo "  ███████║ ╚████╔╝ ██║  ██║██████╔╝██║   ██║█████╗██║   ██║"
echo "  ██╔══██║  ╚██╔╝  ██║  ██║██╔══██╗██║   ██║╚════╝╚██╗ ██╔╝"
echo "  ██║  ██║   ██║   ██████╔╝██║  ██║╚██████╔╝       ╚████╔╝ "
echo "  ╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝         ╚═══╝  "
echo -e "${NC}"
echo "  Sistema IoT de Captación Hídrica — Setup Local"
echo "  Directorio: $ROOT_DIR"
echo ""

# ─────────────────────────────────────────────────────────────────
section "1. Verificando prerequisitos"
# ─────────────────────────────────────────────────────────────────

check_cmd() {
    command -v "$1" >/dev/null 2>&1 && ok "$1 encontrado" || error "$1 no encontrado. Instálalo primero."
}

check_cmd docker
check_cmd python3
check_cmd pip3
check_cmd node
check_cmd npm

# Verificar versión de Python
PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
    ok "Python $PYTHON_VER ✓"
else
    error "Python 3.11+ requerido. Versión actual: $PYTHON_VER"
fi

# Verificar Docker corriendo
docker info >/dev/null 2>&1 || error "Docker no está corriendo. Inícialo primero."
ok "Docker corriendo"


# ─────────────────────────────────────────────────────────────────
section "2. Configurando .env"
# ─────────────────────────────────────────────────────────────────

if [ -f "$BACKEND_DIR/.env" ]; then
    warn ".env ya existe — no se sobreescribirá"
    warn "Edita $BACKEND_DIR/.env manualmente con tus credenciales"
else
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    ok ".env creado desde .env.example"
    warn "⚠️  IMPORTANTE: edita $BACKEND_DIR/.env y rellena:"
    warn "    POSTGRES_PASSWORD, INFLUX_TOKEN, MQTT_HOST/USER/PASSWORD, SECRET_KEY"
    echo ""
    read -rp "  ¿Ya editaste el .env? [s/N]: " confirm
    [[ "${confirm,,}" == "s" ]] || { warn "Edita el .env y vuelve a correr este script."; exit 0; }
fi


# ─────────────────────────────────────────────────────────────────
section "3. Instalando dependencias Python"
# ─────────────────────────────────────────────────────────────────

log "Instalando requirements del backend..."
pip3 install -q -r "$BACKEND_DIR/requirements-dev.txt"
ok "Dependencias del backend instaladas"

log "Instalando dependencias del módulo ML..."
cd "$BACKEND_DIR"
pip3 install -q numpy scikit-learn torch
ok "Dependencias ML instaladas"
cd "$ROOT_DIR"


# ─────────────────────────────────────────────────────────────────
section "4. Generando modelos ML dummy"
# ─────────────────────────────────────────────────────────────────

if [ -f "$ML_DIR/models/linear_autonomy.pkl" ] && \
   [ -f "$ML_DIR/models/gnn_leak_detector_best.pth" ]; then
    ok "Modelos ML ya existen — omitiendo generación"
else
    log "Generando modelos ML (esto tarda ~30 segundos)..."
    python3 "$BACKEND_DIR/scripts/generate_synthetic_data.py" --model all
    ok "Modelos ML generados"
fi


# ─────────────────────────────────────────────────────────────────
section "5. Levantando stack Docker (sin backend ni frontend)"
# ─────────────────────────────────────────────────────────────────

log "Levantando PostgreSQL, InfluxDB y Redis..."
docker compose -f "$ROOT_DIR/docker-compose.yml" \
    up -d postgres influxdb redis

log "Esperando que los servicios estén healthy..."
MAX_WAIT=60
ELAPSED=0
while true; do
    PG_UP=$(docker compose -f "$ROOT_DIR/docker-compose.yml" \
        ps postgres --format json 2>/dev/null | python3 -c \
        "import sys,json; d=json.load(sys.stdin); print(d[0].get('Health',''))" \
        2>/dev/null || echo "unknown")

    if [ "$PG_UP" = "healthy" ] || docker exec hydrov-postgres pg_isready -U hydrov >/dev/null 2>&1; then
        ok "PostgreSQL healthy"
        break
    fi

    ELAPSED=$((ELAPSED + 5))
    [ $ELAPSED -ge $MAX_WAIT ] && error "PostgreSQL no levantó en ${MAX_WAIT}s"
    sleep 5
    log "  Esperando... (${ELAPSED}s)"
done


# ─────────────────────────────────────────────────────────────────
section "6. Aplicando migraciones Alembic"
# ─────────────────────────────────────────────────────────────────

log "Ejecutando: alembic upgrade head"
cd "$BACKEND_DIR"
alembic upgrade head
ok "Migraciones aplicadas"
cd "$ROOT_DIR"


# ─────────────────────────────────────────────────────────────────
section "7. Verificación final"
# ─────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅  Entorno local configurado correctamente ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
log "Para arrancar el backend:"
echo "    cd hydrov-backend && uvicorn app.main:app --reload"
echo ""
log "Servicios disponibles:"
echo "    PostgreSQL : localhost:5432"
echo "    InfluxDB   : http://localhost:8086"
echo "    Redis      : localhost:6379"
echo "    API Docs   : http://localhost:8000/docs  (cuando arranque el backend)"
echo ""
log "Para apagar todo:"
echo "    docker compose down"
