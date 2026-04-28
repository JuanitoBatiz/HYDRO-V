#!/usr/bin/env python3
# hydrov-backend/scripts/seed_influx_background.py
"""
Seed de telemetría de fondo para InfluxDB — 30 días de operación continua.
Genera ~432,000 puntos distribuidos en 5 nodos con patrones realistas
de operación diurna/nocturna y eventos de lluvia aleatorios.

Uso (dentro del contenedor backend):
    python scripts/seed_influx_background.py

Uso (desde host):
    INFLUX_URL=http://localhost:8086 INFLUX_TOKEN=... python scripts/seed_influx_background.py

El script escribe en lotes de 5,000 puntos para no saturar la memoria.
"""
import asyncio
import sys
import os
import math
import random
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed-influx-bg")

# ── Config ────────────────────────────────────────────────────────
INFLUX_URL    = os.getenv("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN",  "")
INFLUX_ORG    = os.getenv("INFLUX_ORG",    "hydrov")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET_TELEMETRY", "sensor_telemetry")

NOW = datetime.now(timezone.utc).replace(second=0, microsecond=0)
START_TIME = NOW - timedelta(days=30)

rng = random.Random(42)

# ── Dispositivos ──────────────────────────────────────────────────
DEVICES = [
    {"code": "HYDRO-V-001", "zone": "NZ-001", "cistern_h_cm": 125.0},
    {"code": "HYDRO-V-002", "zone": "NZ-001", "cistern_h_cm": 110.0},
    {"code": "HYDRO-V-003", "zone": "NZ-002", "cistern_h_cm": 125.0},
    {"code": "HYDRO-V-004", "zone": "NZ-002", "cistern_h_cm":  95.0},
    {"code": "HYDRO-V-005", "zone": "NZ-003", "cistern_h_cm": 150.0},
]

INTERVAL_S = 30  # un punto cada 30 segundos


# ─────────────────────────────────────────────────────────────────
#  Simulador de estado por dispositivo
# ─────────────────────────────────────────────────────────────────

class DeviceSimulator:
    """Mantiene el estado continuo de un dispositivo a través del tiempo."""

    def __init__(self, code: str, zone: str, cistern_h_cm: float, seed: int):
        self.code = code
        self.zone = zone
        self.cistern_h_cm = cistern_h_cm
        self.rng = random.Random(seed)

        # Estado inicial: cisterna al 65% → distance_cm = 35% de la altura
        self.distance_cm = cistern_h_cm * 0.35
        self.flow_total_liters = self.rng.uniform(5000, 15000)
        self.flow_lpm = 0.0
        self.turbidity_ntu = 1.8
        self.fsm_state = "IDLE"
        self.state_duration_ms = 0
        self.intake_cycles = 0
        self.reject_cycles = 0
        self.error_count = 0

        # Control de lluvia
        self.rain_active = False
        self.rain_elapsed_s = 0
        self.rain_intensity_lpm = 0.0
        self.rain_duration_s = 0
        self.analyzing_s = 0
        self.harvesting_s = 0
        self.reject_s = 0

    def step(self, t: datetime) -> dict:
        """Avanza un paso de INTERVAL_S segundos y retorna los valores actuales."""
        hour = t.hour
        dt = INTERVAL_S

        # ── Decidir si empieza lluvia ──────────────────────────────
        # Probabilidad de inicio de lluvia: mayor en horas vespertinas (14-20h)
        if not self.rain_active and self.fsm_state == "IDLE":
            rain_prob = 0.0002  # base por tick (30s)
            if 14 <= hour <= 20:
                rain_prob = 0.0012  # pico vespertino (temporada lluvias CDMX)
            if self.rng.random() < rain_prob:
                self._start_rain()

        # ── Máquina de estados ─────────────────────────────────────
        if self.rain_active:
            self.rain_elapsed_s += dt
            self._update_rain_state(dt)
        else:
            self._update_idle_state(hour, dt)

        # ── Ruido en turbidez ──────────────────────────────────────
        noise = self.rng.gauss(0, 0.1)
        self.turbidity_ntu = max(0.5, self.turbidity_ntu + noise)

        # ── Nivel no baja de 5% (cisterna nunca vacía) ─────────────
        max_dist = self.cistern_h_cm * 0.95
        self.distance_cm = min(max_dist, max(self.cistern_h_cm * 0.05, self.distance_cm))

        self.state_duration_ms += dt * 1000

        return {
            "turbidity_ntu":     round(self.turbidity_ntu, 3),
            "distance_cm":       round(self.distance_cm, 2),
            "flow_lpm":          round(max(0.0, self.flow_lpm), 3),
            "flow_total_liters": round(self.flow_total_liters, 1),
            "fsm_state":         self.fsm_state,
            "state_duration_ms": self.state_duration_ms,
            "intake_cycles":     self.intake_cycles,
            "reject_cycles":     self.reject_cycles,
            "error_count":       self.error_count,
        }

    def _start_rain(self):
        """Inicia un evento de lluvia."""
        self.rain_active = True
        self.rain_elapsed_s = 0
        self.rain_intensity_lpm = self.rng.choice([5.0, 10.0, 15.0])
        self.rain_duration_s = int(self.rng.uniform(300, 900))  # 5-15 min
        self.reject_s = int(self.rng.uniform(45, 120))          # primer arrastre
        self.analyzing_s = 20
        self.harvesting_s = self.rain_duration_s - self.reject_s - self.analyzing_s
        self.fsm_state = "ANALYZING"
        self.state_duration_ms = 0

    def _update_rain_state(self, dt: int):
        elapsed = self.rain_elapsed_s

        if elapsed < self.analyzing_s:
            # ANALYZING: turbidez sube rápidamente
            self.fsm_state = "ANALYZING"
            k = 0.04 * (self.rain_intensity_lpm / 5.0)
            target = 15 + self.rain_intensity_lpm * 3.2
            self.turbidity_ntu += k * (target - self.turbidity_ntu) * dt
            self.flow_lpm = 0.0

        elif elapsed < self.analyzing_s + self.reject_s:
            # HARVESTING (reject/primer arrastre): válvula de rechazo abierta
            if self.fsm_state != "HARVESTING":
                self.fsm_state = "HARVESTING"
                self.reject_cycles += 1
                self.state_duration_ms = 0
            self.turbidity_ntu *= 0.985 ** dt  # baja gradualmente
            self.flow_lpm = self.rain_intensity_lpm * 0.8
            self.flow_total_liters += self.flow_lpm * dt / 60
            # nivel no cambia en rechazo (agua va al drenaje)

        elif elapsed < self.rain_duration_s:
            # HARVESTING (captación): turbidez < 5 NTU, captando
            self.turbidity_ntu = max(1.2, self.turbidity_ntu * 0.99)
            self.flow_lpm = self.rain_intensity_lpm * 0.9
            self.flow_total_liters += self.flow_lpm * dt / 60
            # Nivel sube (distancia baja)
            fill_rate_cm_per_s = self.flow_lpm / (60 * 2.5)  # aprox. 2.5 L por cm
            self.distance_cm -= fill_rate_cm_per_s * dt
            if self.fsm_state != "HARVESTING":
                self.intake_cycles += 1
                self.state_duration_ms = 0
            self.fsm_state = "HARVESTING"
        else:
            # Fin de lluvia
            self.rain_active = False
            self.flow_lpm = 0.0
            level_pct = 1 - (self.distance_cm / self.cistern_h_cm)
            self.fsm_state = "FULL_TANK" if level_pct > 0.95 else "IDLE"
            self.state_duration_ms = 0

    def _update_idle_state(self, hour: int, dt: int):
        """Simula consumo gradual en estado IDLE."""
        self.fsm_state = "IDLE"
        self.flow_lpm = 0.0

        # Consumo: ~150L/día = 0.00174 cm/s (para cisterna de 125cm)
        # Mayor consumo en horas pico (7-9am y 6-8pm)
        base_rate = 0.00174  # cm/s
        if 7 <= hour <= 9 or 18 <= hour <= 20:
            base_rate *= 2.5
        elif 0 <= hour <= 5:
            base_rate *= 0.2  # poca demanda nocturna

        self.distance_cm += base_rate * dt
        self.turbidity_ntu = max(1.2, 2.0 + self.rng.gauss(0, 0.2))


# ─────────────────────────────────────────────────────────────────
#  Escritor de puntos en lote
# ─────────────────────────────────────────────────────────────────

async def write_batch(write_api, points: list, batch_num: int, total_batches: int):
    await write_api.write(bucket=INFLUX_BUCKET, record=points)
    log.info(f"  Lote {batch_num:3d}/{total_batches} — {len(points):,} puntos escritos")


async def main():
    log.info("=" * 62)
    log.info("  HYDRO-V — Seed InfluxDB Background (30 días)")
    log.info(f"  URL: {INFLUX_URL} | Bucket: {INFLUX_BUCKET}")
    log.info(f"  Rango: {START_TIME.strftime('%Y-%m-%d')} → {NOW.strftime('%Y-%m-%d')}")
    log.info("=" * 62)

    # Inicializar simuladores (uno por device, con semilla distinta)
    simulators = {
        d["code"]: DeviceSimulator(d["code"], d["zone"], d["cistern_h_cm"], seed=i * 13)
        for i, d in enumerate(DEVICES)
    }

    # Calcular total de puntos
    total_seconds = int((NOW - START_TIME).total_seconds())
    steps = total_seconds // INTERVAL_S
    total_points = steps * len(DEVICES) * 2  # sensor_reading + device_state
    log.info(f"  Puntos a generar: ~{total_points:,} ({steps:,} ticks × {len(DEVICES)} devices × 2 measurements)")

    BATCH_SIZE = 5000
    all_points = []
    batch_count = 0
    point_count = 0
    estimated_batches = math.ceil(total_points / BATCH_SIZE)

    async with InfluxDBClientAsync(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        write_api = client.write_api()

        current_t = START_TIME
        while current_t < NOW:
            for dev_code, sim in simulators.items():
                vals = sim.step(current_t)
                zone = next(d["zone"] for d in DEVICES if d["code"] == dev_code)

                p_sensor = (
                    Point("sensor_reading")
                    .tag("device_code", dev_code)
                    .tag("zone_code", zone)
                    .field("turbidity_ntu",     vals["turbidity_ntu"])
                    .field("distance_cm",        vals["distance_cm"])
                    .field("flow_lpm",           vals["flow_lpm"])
                    .field("flow_total_liters",  vals["flow_total_liters"])
                    .time(current_t)
                )
                p_state = (
                    Point("device_state")
                    .tag("device_code", dev_code)
                    .tag("zone_code", zone)
                    .tag("fsm_state", vals["fsm_state"])
                    .field("state_duration_ms",  vals["state_duration_ms"])
                    .field("intake_cycles",      vals["intake_cycles"])
                    .field("reject_cycles",      vals["reject_cycles"])
                    .field("error_count",        vals["error_count"])
                    .time(current_t)
                )
                all_points.extend([p_sensor, p_state])
                point_count += 2

            # Flush cuando el lote está lleno
            if len(all_points) >= BATCH_SIZE:
                batch_count += 1
                await write_batch(write_api, all_points, batch_count, estimated_batches)
                all_points = []

            current_t += timedelta(seconds=INTERVAL_S)

        # Flush del último lote
        if all_points:
            batch_count += 1
            await write_batch(write_api, all_points, batch_count, estimated_batches)

    log.info("")
    log.info("=" * 62)
    log.info(f"  ✅ Seed InfluxDB Background completado")
    log.info(f"  Total puntos escritos: {point_count:,}")
    log.info("=" * 62)


if __name__ == "__main__":
    asyncio.run(main())
