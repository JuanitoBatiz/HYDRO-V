#!/bin/bash
# scripts/deploy.sh
# ─────────────────────────────────────────────────────────────────
#  Script de despliegue de Hydro-V
#  Uso: ./scripts/deploy.sh [dev|staging|prod]
#
#  dev:     docker compose up --build (local)
#  staging: docker compose + migraciones (servidor de staging)
#  prod:    despliegue completo con backup previo y zero-downtime
# ─────────────────────────────────────────────────────────────────

set -euo pipefail   # Abortar ante cualquier error

# ── Colores para output ───────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()     { echo -e "${BLUE}[HYDRO-V]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Configuración ─────────────────────────────────────────────────
ENVIRONMENT="${1:-dev}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/hydrov-backend"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

log "Iniciando despliegue en modo: $ENVIRONMENT"
log "Directorio del proyecto: $PROJECT_ROOT"

# ── Verificar prerequisitos ───────────────────────────────────────
check_prerequisites() {
    log "Verificando prerequisitos..."
    command -v docker   >/dev/null 2>&1 || error "Docker no encontrado"
    command -v docker   compose version >/dev/null 2>&1 || error "Docker Compose no encontrado"
    [ -f "$BACKEND_DIR/.env" ] || error ".env no encontrado en $BACKEND_DIR — copia .env.example"
    success "Prerequisitos OK"
}

# ── Backup de PostgreSQL (solo prod/staging) ──────────────────────
backup_postgres() {
    log "Creando backup de PostgreSQL..."
    mkdir -p "$PROJECT_ROOT/backups"
    docker compose -f "$COMPOSE_FILE" exec -T postgres \
        pg_dump -U "${POSTGRES_USER:-hydrov}" "${POSTGRES_DB:-hydrov}" \
        > "$PROJECT_ROOT/backups/hydrov_$TIMESTAMP.sql"
    success "Backup guardado en backups/hydrov_$TIMESTAMP.sql"
}

# ── Aplicar migraciones de Alembic ───────────────────────────────
run_migrations() {
    log "Aplicando migraciones de Alembic..."
    docker compose -f "$COMPOSE_FILE" exec -T backend \
        alembic upgrade head
    success "Migraciones aplicadas"
}

# ── Build y pull de imágenes ──────────────────────────────────────
build_images() {
    log "Construyendo imágenes Docker..."
    docker compose -f "$COMPOSE_FILE" build \
        --no-cache \
        --parallel
    success "Imágenes construidas"
}

# ── Despliegue ────────────────────────────────────────────────────
deploy_dev() {
    log "=== MODO DESARROLLO ==="
    docker compose -f "$COMPOSE_FILE" up --build -d
    success "Stack levantado en modo desarrollo"
    echo ""
    log "Servicios disponibles:"
    echo "  Backend:  http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo "  Frontend: http://localhost:5173"
    echo "  InfluxDB: http://localhost:8086"
}

deploy_staging() {
    log "=== MODO STAGING ==="
    check_prerequisites
    log "Actualizando código desde git..."
    git -C "$PROJECT_ROOT" pull origin main

    build_images
    docker compose -f "$COMPOSE_FILE" up -d postgres influxdb redis
    sleep 10
    run_migrations
    docker compose -f "$COMPOSE_FILE" up -d backend frontend nginx
    success "Despliegue en staging completado"
}

deploy_prod() {
    log "=== MODO PRODUCCIÓN ==="
    warn "⚠️  Desplegando en PRODUCCIÓN. Tienes 5 segundos para cancelar (Ctrl+C)..."
    sleep 5

    check_prerequisites

    log "Actualizando código desde git..."
    git -C "$PROJECT_ROOT" pull origin main

    # Backup antes de cualquier cambio
    backup_postgres

    build_images

    # Zero-downtime: levantar nuevo backend antes de bajar el viejo
    log "Aplicando despliegue zero-downtime..."
    docker compose -f "$COMPOSE_FILE" up -d --no-deps postgres influxdb redis
    sleep 10
    run_migrations
    docker compose -f "$COMPOSE_FILE" up -d --no-deps backend
    sleep 15

    # Verificar que el backend está saludable antes de continuar
    log "Verificando health del backend..."
    for i in {1..10}; do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            success "Backend saludable ✓"
            break
        fi
        [ $i -eq 10 ] && error "Backend no responde después de 10 intentos — revisando logs..."
        sleep 5
    done

    docker compose -f "$COMPOSE_FILE" up -d --no-deps frontend nginx
    success "Despliegue en producción completado ✓"
}

# ── Health check post-deploy ──────────────────────────────────────
health_check() {
    log "Ejecutando health check del sistema..."
    sleep 5

    HEALTH=$(curl -sf http://localhost:8000/health 2>/dev/null || echo '{"status":"error"}')
    STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null || echo "error")

    if [ "$STATUS" = "ok" ]; then
        success "Sistema saludable: $HEALTH"
    else
        warn "Sistema en estado degradado: $HEALTH"
        log "Revisa los logs: docker compose logs backend"
    fi
}

# ── Punto de entrada ──────────────────────────────────────────────
case "$ENVIRONMENT" in
    dev)
        deploy_dev
        ;;
    staging)
        deploy_staging
        health_check
        ;;
    prod|production)
        deploy_prod
        health_check
        ;;
    down)
        log "Apagando todos los servicios..."
        docker compose -f "$COMPOSE_FILE" down
        success "Servicios detenidos"
        ;;
    logs)
        docker compose -f "$COMPOSE_FILE" logs -f --tail=100
        ;;
    *)
        echo "Uso: $0 [dev|staging|prod|down|logs]"
        exit 1
        ;;
esac
