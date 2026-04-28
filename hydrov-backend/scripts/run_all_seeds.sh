#!/bin/bash
# hydrov-backend/scripts/run_all_seeds.sh
# ─────────────────────────────────────────────────────────────────
# Ejecuta los 3 scripts de seed en orden correcto dentro del
# contenedor del backend.
#
# Uso:
#   docker compose exec backend bash scripts/run_all_seeds.sh
#   docker compose exec backend bash scripts/run_all_seeds.sh --skip-background
#
# Flags:
#   --skip-background  Omite el seed de 30 días de fondo (útil para re-runs)
#   --only-figures     Solo ejecuta el seed de figuras académicas
# ─────────────────────────────────────────────────────────────────

set -e

SKIP_BG=false
ONLY_FIGURES=false

for arg in "$@"; do
  case $arg in
    --skip-background) SKIP_BG=true ;;
    --only-figures)    ONLY_FIGURES=true ;;
  esac
done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          HYDRO-V — Seed Masivo de Datos                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Fase 1: PostgreSQL ────────────────────────────────────────────
if [ "$ONLY_FIGURES" = false ]; then
  echo "▶ [1/3] Iniciando seed de PostgreSQL..."
  python scripts/seed_postgres.py
  echo "✅ PostgreSQL completado"
  echo ""
fi

# ── Fase 2: InfluxDB Background (30 días) ────────────────────────
if [ "$SKIP_BG" = false ] && [ "$ONLY_FIGURES" = false ]; then
  echo "▶ [2/3] Iniciando seed de InfluxDB — telemetría 30 días..."
  echo "   (Esto puede tardar 2-4 minutos)"
  python scripts/seed_influx_background.py
  echo "✅ InfluxDB Background completado"
  echo ""
fi

# ── Fase 3: Figuras del documento ────────────────────────────────
echo "▶ [3/3] Iniciando seed de figuras académicas..."
python scripts/seed_figures.py
echo "✅ Figuras completadas"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✅ SEED MASIVO COMPLETADO                                   ║"
echo "║                                                              ║"
echo "║  Abre Grafana en http://localhost:3000                       ║"
echo "║  Usuario: admin | Contraseña: HydroV_Grafana_2024!          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
