#!/bin/bash
# infra/scripts/backup_db.sh
# ─────────────────────────────────────────────────────────────────
#  Backup automático de PostgreSQL e InfluxDB para Hydro-V.
#
#  Uso manual:
#    chmod +x infra/scripts/backup_db.sh
#    ./infra/scripts/backup_db.sh
#
#  Uso automático via cron (cada día a las 02:00):
#    0 2 * * * cd /ruta/a/HYDRO-V && ./infra/scripts/backup_db.sh
#
#  Retención: 7 días por defecto (configurable con RETENTION_DAYS)
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Cargar variables de entorno del .env ──────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$ROOT_DIR/hydrov-backend/.env"

if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -a && source "$ENV_FILE" && set +a
fi

# ── Configuración ─────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS="${RETENTION_DAYS:-7}"

PG_HOST="${POSTGRES_HOST:-localhost}"
PG_PORT="${POSTGRES_PORT:-5432}"
PG_USER="${POSTGRES_USER:-hydrov}"
PG_DB="${POSTGRES_DB:-hydrov}"

INFLUX_URL="${INFLUX_URL:-http://localhost:8086}"
INFLUX_TOKEN="${INFLUX_TOKEN:-}"
INFLUX_ORG="${INFLUX_ORG:-hydrov}"

# ── Colores ───────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

log_info()    { echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅  $1${NC}"; }
log_warn()    { echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️   $1${NC}"; }
log_error()   { echo -e "${RED}[$(date +'%H:%M:%S')] ❌  $1${NC}"; }
log_section() { echo -e "\n${BLUE}── $1 ──${NC}"; }

# ── Crear directorios ─────────────────────────────────────────────
mkdir -p "$BACKUP_DIR/postgres" "$BACKUP_DIR/influxdb" "$BACKUP_DIR/logs"
LOG_FILE="$BACKUP_DIR/logs/backup_${TIMESTAMP}.log"

{
echo "════════════════════════════════════════════════"
echo "  HYDRO-V Backup — $TIMESTAMP"
echo "  Retención: $RETENTION_DAYS días"
echo "════════════════════════════════════════════════"
} | tee "$LOG_FILE"


# ─────────────────────────────────────────────────────────────────
#  1. Backup PostgreSQL
# ─────────────────────────────────────────────────────────────────
log_section "PostgreSQL" | tee -a "$LOG_FILE"

PG_BACKUP_FILE="$BACKUP_DIR/postgres/hydrov_pg_${TIMESTAMP}.sql.gz"

if docker exec hydrov-postgres pg_dump \
    -U "$PG_USER" \
    -d "$PG_DB" \
    --format=plain \
    --no-owner \
    --no-acl 2>> "$LOG_FILE" | gzip > "$PG_BACKUP_FILE"; then

    PG_SIZE=$(du -sh "$PG_BACKUP_FILE" | cut -f1)
    log_info "PostgreSQL OK → $(basename "$PG_BACKUP_FILE") ($PG_SIZE)" | tee -a "$LOG_FILE"
    PG_OK=true
else
    log_error "Falló el backup de PostgreSQL" | tee -a "$LOG_FILE"
    PG_OK=false
fi


# ─────────────────────────────────────────────────────────────────
#  2. Backup InfluxDB
# ─────────────────────────────────────────────────────────────────
log_section "InfluxDB" | tee -a "$LOG_FILE"

INFLUX_TMP_DIR="$BACKUP_DIR/influxdb/hydrov_influx_${TIMESTAMP}"
INFLUX_BACKUP_FILE="$BACKUP_DIR/influxdb/hydrov_influx_${TIMESTAMP}.tar.gz"

mkdir -p "$INFLUX_TMP_DIR"

if docker exec hydrov-influxdb influx backup \
    --host "$INFLUX_URL" \
    --token "$INFLUX_TOKEN" \
    --org "$INFLUX_ORG" \
    "$INFLUX_TMP_DIR" 2>> "$LOG_FILE"; then

    tar -czf "$INFLUX_BACKUP_FILE" \
        -C "$BACKUP_DIR/influxdb" \
        "hydrov_influx_${TIMESTAMP}" 2>> "$LOG_FILE"
    rm -rf "$INFLUX_TMP_DIR"

    INFLUX_SIZE=$(du -sh "$INFLUX_BACKUP_FILE" | cut -f1)
    log_info "InfluxDB OK → $(basename "$INFLUX_BACKUP_FILE") ($INFLUX_SIZE)" | tee -a "$LOG_FILE"
    INFLUX_OK=true
else
    log_warn "Falló el backup de InfluxDB — continuando sin él" | tee -a "$LOG_FILE"
    rm -rf "$INFLUX_TMP_DIR"
    INFLUX_OK=false
fi


# ─────────────────────────────────────────────────────────────────
#  3. Limpiar backups antiguos (> RETENTION_DAYS)
# ─────────────────────────────────────────────────────────────────
log_section "Limpieza (retención $RETENTION_DAYS días)" | tee -a "$LOG_FILE"

PG_DELETED=$(find "$BACKUP_DIR/postgres" -name "*.sql.gz" -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
IN_DELETED=$(find "$BACKUP_DIR/influxdb" -name "*.tar.gz" -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
LG_DELETED=$(find "$BACKUP_DIR/logs"     -name "*.log"    -mtime +"$RETENTION_DAYS" -print -delete | wc -l)

log_info "Eliminados: $PG_DELETED PG, $IN_DELETED InfluxDB, $LG_DELETED logs" | tee -a "$LOG_FILE"


# ─────────────────────────────────────────────────────────────────
#  4. Resumen
# ─────────────────────────────────────────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "  Resumen — $TIMESTAMP" | tee -a "$LOG_FILE"
echo "────────────────────────────────────────────────" | tee -a "$LOG_FILE"

if [ "$PG_OK" = true ]; then
    log_info "PostgreSQL : ✅ $(basename "$PG_BACKUP_FILE")" | tee -a "$LOG_FILE"
else
    log_error "PostgreSQL : ❌ FALLÓ" | tee -a "$LOG_FILE"
fi

if [ "${INFLUX_OK:-false}" = true ]; then
    log_info "InfluxDB   : ✅ $(basename "$INFLUX_BACKUP_FILE")" | tee -a "$LOG_FILE"
else
    log_warn  "InfluxDB   : ⚠️  No disponible" | tee -a "$LOG_FILE"
fi

echo "  Log        : $LOG_FILE" | tee -a "$LOG_FILE"
echo "════════════════════════════════════════════════" | tee -a "$LOG_FILE"

# Salir con error si PostgreSQL falló (es crítico)
[ "$PG_OK" = true ] || exit 1
