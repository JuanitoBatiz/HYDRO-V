#!/bin/bash
# infra/db/init_influxdb.sh
# ─────────────────────────────────────────────────────────────────
#  Inicializa los buckets secundarios de InfluxDB.
#  El bucket principal (sensor_telemetry) lo crea docker-compose
#  via DOCKER_INFLUXDB_INIT_BUCKET.
#  Este script crea el bucket de NASA POWER cache.
#
#  Se ejecuta automáticamente al arrancar el contenedor de InfluxDB.
# ─────────────────────────────────────────────────────────────────

set -e

INFLUX_URL="http://localhost:8086"
INFLUX_TOKEN="${INFLUX_TOKEN}"
INFLUX_ORG="${INFLUX_ORG:-hydrov}"

echo "[InfluxDB Init] Esperando que InfluxDB esté listo..."
until influx ping --host "$INFLUX_URL" 2>/dev/null; do
    sleep 2
done
echo "[InfluxDB Init] InfluxDB listo ✓"

# ── Crear bucket nasa_weather_cache (retención 90 días) ───────────
echo "[InfluxDB Init] Creando bucket nasa_weather_cache..."
influx bucket create \
    --name    "nasa_weather_cache" \
    --org     "$INFLUX_ORG" \
    --token   "$INFLUX_TOKEN" \
    --host    "$INFLUX_URL" \
    --retention "2160h" \
    2>/dev/null || echo "[InfluxDB Init] nasa_weather_cache ya existe — OK"

# ── Retención de sensor_telemetry: 30 días ────────────────────────
echo "[InfluxDB Init] Configurando retención de sensor_telemetry (30d)..."
BUCKET_ID=$(influx bucket list \
    --org   "$INFLUX_ORG" \
    --token "$INFLUX_TOKEN" \
    --host  "$INFLUX_URL" \
    --name  "sensor_telemetry" \
    --json  2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])" 2>/dev/null || echo "")

if [ -n "$BUCKET_ID" ]; then
    influx bucket update \
        --id        "$BUCKET_ID" \
        --retention "720h" \
        --token     "$INFLUX_TOKEN" \
        --host      "$INFLUX_URL" \
        2>/dev/null || echo "[InfluxDB Init] Retención ya configurada — OK"
fi

echo "[InfluxDB Init] Inicialización completa ✓"
