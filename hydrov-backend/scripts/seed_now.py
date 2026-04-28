#!/usr/bin/env python3
# hydrov-backend/scripts/seed_now.py
"""
Seed de datos RECIENTES para Grafana — resuelve el "No data" en todos los paneles.

Problema diagnosticado:
  1. Último timestamp en InfluxDB era 2026-04-09 (seed de figuras)
  2. HYDRO-V-NEZA-001 (device real) no tenía datos en InfluxDB
  3. Grafana en modo "last 6h / last 1h" → No data

Solución:
  - Fase A: Inyectar 7 días de historial para HYDRO-V-NEZA-001
  - Fase B: Inyectar las últimas 6h para TODOS los devices (incluyendo NEZA-001)
  - Fase C: Escribir snapshot "ahora mismo" para los paneles Stat en tiempo real
  - Fase D: Loop continuo cada 30s (modo --live) para mantener paneles vivos

Uso:
    # Solo datos recientes (una vez):
    docker compose exec backend python scripts/seed_now.py

    # Con loop en vivo (no termina hasta Ctrl+C):
    docker compose exec backend python scripts/seed_now.py --live
"""
import asyncio
import math
import os
import random
import sys
import signal
import argparse
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
log = logging.getLogger("seed-now")

# ── Config ────────────────────────────────────────────────────────
INFLUX_URL    = os.getenv("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN",  "")
INFLUX_ORG    = os.getenv("INFLUX_ORG",    "hydrov")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET_TELEMETRY", "sensor_telemetry")

# ── Todos los devices que deben tener datos en Grafana ───────────
ALL_DEVICES = [
    {"code": "HYDRO-V-NEZA-001", "zone": "NZ-001", "h": 125.0},  # ← device real, prioritario
    {"code": "HYDRO-V-001",      "zone": "NZ-001", "h": 125.0},
    {"code": "HYDRO-V-002",      "zone": "NZ-001", "h": 110.0},
    {"code": "HYDRO-V-003",      "zone": "NZ-002", "h": 125.0},
    {"code": "HYDRO-V-004",      "zone": "NZ-002", "h":  95.0},
    {"code": "HYDRO-V-005",      "zone": "NZ-003", "h": 150.0},
]

LIVE_STOP = False


def handle_sigint(sig, frame):
    global LIVE_STOP
    log.info("Ctrl+C detectado — deteniendo loop en vivo...")
    LIVE_STOP = True


# ─────────────────────────────────────────────────────────────────
#  Simulador de estado por device
# ─────────────────────────────────────────────────────────────────

class DeviceState:
    """Estado continuo de un device a través del tiempo."""

    def __init__(self, code: str, zone: str, cistern_h: float, seed: int):
        self.code       = code
        self.zone       = zone
        self.cistern_h  = cistern_h
        self.rng        = random.Random(seed)

        # Estado inicial realista (cisterna al 72%)
        self.distance_cm       = cistern_h * 0.28
        self.flow_total        = self.rng.uniform(12000, 22000)
        self.flow_lpm          = 0.0
        self.turbidity         = 1.9
        self.fsm               = "IDLE"
        self.state_dur_s       = 0
        self.intake_cycles     = self.rng.randint(8, 25)
        self.reject_cycles     = self.rng.randint(3, 12)
        self.error_count       = 0

        # Control de lluvia
        self.rain_active       = False
        self.rain_elapsed_s    = 0
        self.rain_duration_s   = 0
        self.rain_intensity    = 0.0
        self.reject_end_s      = 0

    def step(self, t: datetime, step_s: int = 30) -> dict:
        """Avanza step_s segundos y retorna los valores del instante."""
        hour = t.hour

        # Iniciar lluvia aleatoriamente
        if not self.rain_active and self.fsm == "IDLE":
            base_p = 0.0003 if not (14 <= hour <= 20) else 0.0015
            if self.rng.random() < base_p * step_s:
                self._start_rain(step_s)

        if self.rain_active:
            self.rain_elapsed_s += step_s
            self._rain_step(step_s)
        else:
            self._idle_step(hour, step_s)

        # Ruido
        self.turbidity = max(0.4, self.turbidity + self.rng.gauss(0, 0.08))
        # Límites físicos
        self.distance_cm = min(self.cistern_h * 0.96, max(self.cistern_h * 0.04, self.distance_cm))
        self.state_dur_s += step_s

        level_pct = round((1 - self.distance_cm / self.cistern_h) * 100, 1)

        return {
            "turbidity_ntu":      round(self.turbidity, 3),
            "distance_cm":        round(self.distance_cm, 2),
            "level_pct":          level_pct,
            "flow_lpm":           round(max(0.0, self.flow_lpm), 3),
            "flow_total_liters":  round(self.flow_total, 1),
            "fsm_state":          self.fsm,
            "state_duration_ms":  self.state_dur_s * 1000,
            "intake_cycles":      self.intake_cycles,
            "reject_cycles":      self.reject_cycles,
            "error_count":        self.error_count,
        }

    def _start_rain(self, step_s):
        self.rain_active    = True
        self.rain_elapsed_s = 0
        self.rain_intensity = self.rng.choice([5.0, 10.0, 15.0])
        self.rain_duration_s = int(self.rng.uniform(240, 720))
        self.reject_end_s   = int(self.rng.uniform(60, 150))
        self.fsm            = "ANALYZING"
        self.state_dur_s    = 0

    def _rain_step(self, step_s):
        e = self.rain_elapsed_s
        k = 0.06 * (self.rain_intensity / 5.0)
        T_peak = 12 + self.rain_intensity * 3.5

        if e < 25:  # ANALYZING
            self.fsm       = "ANALYZING"
            self.turbidity += k * (T_peak - self.turbidity) * step_s
            self.flow_lpm  = 0.0
        elif e < self.reject_end_s:  # Rechazo
            if self.fsm != "HARVESTING":
                self.fsm = "HARVESTING"
                self.reject_cycles += 1
                self.state_dur_s = 0
            self.turbidity *= 0.992 ** step_s
            self.flow_lpm   = self.rain_intensity * 0.8
            self.flow_total += self.flow_lpm * step_s / 60
        elif e < self.rain_duration_s:  # Captación
            self.turbidity  = max(1.1, self.turbidity * 0.995)
            self.flow_lpm   = self.rain_intensity * 0.92
            self.flow_total += self.flow_lpm * step_s / 60
            fill = self.flow_lpm / (60 * 2.8)
            self.distance_cm -= fill * step_s
            if self.fsm != "HARVESTING":
                self.intake_cycles += 1
                self.state_dur_s = 0
            self.fsm = "HARVESTING"
        else:
            self.rain_active = False
            self.flow_lpm    = 0.0
            lvl = 1 - (self.distance_cm / self.cistern_h)
            self.fsm = "FULL_TANK" if lvl > 0.94 else "IDLE"
            self.state_dur_s = 0

    def _idle_step(self, hour, step_s):
        self.fsm      = "IDLE"
        self.flow_lpm = 0.0
        rate = 0.00180
        if 7 <= hour <= 9 or 18 <= hour <= 21:
            rate *= 2.8
        elif 0 <= hour <= 5:
            rate *= 0.15
        self.distance_cm += rate * step_s
        self.turbidity    = max(1.3, 1.9 + self.rng.gauss(0, 0.18))


# ─────────────────────────────────────────────────────────────────
#  Generador de puntos InfluxDB
# ─────────────────────────────────────────────────────────────────

def make_points(sim: DeviceState, t: datetime, vals: dict) -> list[Point]:
    p_s = (
        Point("sensor_reading")
        .tag("device_code", sim.code)
        .tag("zone_code",   sim.zone)
        .field("turbidity_ntu",    vals["turbidity_ntu"])
        .field("distance_cm",      vals["distance_cm"])
        .field("flow_lpm",         vals["flow_lpm"])
        .field("flow_total_liters",vals["flow_total_liters"])
        .time(t)
    )
    p_d = (
        Point("device_state")
        .tag("device_code", sim.code)
        .tag("zone_code",   sim.zone)
        .tag("fsm_state",   vals["fsm_state"])
        .field("state_duration_ms", vals["state_duration_ms"])
        .field("intake_cycles",     vals["intake_cycles"])
        .field("reject_cycles",     vals["reject_cycles"])
        .field("error_count",       vals["error_count"])
        .time(t)
    )
    return [p_s, p_d]


async def write_batch(write_api, points, label=""):
    await write_api.write(bucket=INFLUX_BUCKET, record=points)
    if label:
        log.info(label)


# ─────────────────────────────────────────────────────────────────
#  FASE A — Historial 7 días para HYDRO-V-NEZA-001
# ─────────────────────────────────────────────────────────────────

async def seed_neza_history(write_api, now: datetime):
    log.info("[A] Inyectando 7 días de historial para HYDRO-V-NEZA-001...")
    dev    = ALL_DEVICES[0]
    sim    = DeviceState(dev["code"], dev["zone"], dev["h"], seed=777)
    start  = now - timedelta(days=7)
    step_s = 30
    BATCH  = 5000
    batch  = []
    points = 0

    t = start
    while t < now - timedelta(hours=6):   # las últimas 6h las cubre Fase B
        vals = sim.step(t, step_s)
        batch.extend(make_points(sim, t, vals))
        points += 2
        if len(batch) >= BATCH:
            await write_batch(write_api, batch)
            batch = []
        t += timedelta(seconds=step_s)

    if batch:
        await write_batch(write_api, batch)

    log.info(f"  ✓ HYDRO-V-NEZA-001: {points:,} puntos escritos (7 días)")
    return sim  # retorna el simulador con su estado para continuar en Fase B


# ─────────────────────────────────────────────────────────────────
#  FASE B — Últimas 6h para TODOS los devices
# ─────────────────────────────────────────────────────────────────

async def seed_recent_6h(write_api, now: datetime, neza_sim: DeviceState):
    log.info("[B] Inyectando últimas 6h para 6 devices...")
    step_s = 30
    start  = now - timedelta(hours=6)
    BATCH  = 5000

    # Simuladores: NEZA-001 continúa desde donde quedó en Fase A
    sims = {d["code"]: (DeviceState(d["code"], d["zone"], d["h"], seed=i*31+5)
                        if d["code"] != "HYDRO-V-NEZA-001" else neza_sim)
            for i, d in enumerate(ALL_DEVICES)}

    batch  = []
    total  = 0

    t = start
    while t <= now:
        for dev_code, sim in sims.items():
            vals = sim.step(t, step_s)
            batch.extend(make_points(sim, t, vals))
            total += 2

        if len(batch) >= BATCH:
            await write_batch(write_api, batch)
            batch = []
        t += timedelta(seconds=step_s)

    if batch:
        await write_batch(write_api, batch)

    log.info(f"  ✓ 6 devices × 6h: {total:,} puntos escritos")
    return sims  # retorna simuladores para Fase C/D


# ─────────────────────────────────────────────────────────────────
#  FASE C — Snapshot "ahora" (para paneles Stat en tiempo real)
# ─────────────────────────────────────────────────────────────────

async def seed_snapshot_now(write_api, sims: dict):
    log.info("[C] Escribiendo snapshot del instante actual...")
    now    = datetime.now(timezone.utc)
    points = []
    for dev_code, sim in sims.items():
        vals = sim.step(now, step_s=30)
        points.extend(make_points(sim, now, vals))
        log.info(
            f"  {dev_code:20s} | FSM={vals['fsm_state']:10s} "
            f"| turb={vals['turbidity_ntu']:5.2f} NTU "
            f"| flow={vals['flow_lpm']:5.2f} L/min "
            f"| dist={vals['distance_cm']:6.1f} cm "
            f"| lvl={vals['level_pct']:5.1f}%"
        )
    await write_batch(write_api, points, f"  ✓ {len(points)} puntos 'ahora' escritos")


# ─────────────────────────────────────────────────────────────────
#  FASE D — Loop en vivo (--live)
# ─────────────────────────────────────────────────────────────────

async def live_loop(write_api, sims: dict):
    log.info("[D] Iniciando simulación en vivo (Ctrl+C para detener)...")
    log.info("    Escribe 1 punto cada 30s por device. Grafana verá datos en tiempo real.")
    log.info("─" * 62)
    tick = 0
    while not LIVE_STOP:
        await asyncio.sleep(30)
        if LIVE_STOP:
            break
        tick += 1
        now    = datetime.now(timezone.utc)
        points = []
        status = []
        for dev_code, sim in sims.items():
            vals = sim.step(now, step_s=30)
            points.extend(make_points(sim, now, vals))
            status.append(f"{dev_code.replace('HYDRO-V-',''):<12} {vals['fsm_state']:<11} {vals['turbidity_ntu']:5.2f}NTU {vals['level_pct']:5.1f}%")

        await write_batch(write_api, points)
        log.info(f"  [tick {tick:04d}] {now.strftime('%H:%M:%S')}")
        for s in status:
            log.info(f"    {s}")

    log.info("  Loop en vivo detenido.")


# ─────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────

async def main(live: bool):
    signal.signal(signal.SIGINT, handle_sigint)

    log.info("=" * 62)
    log.info("  HYDRO-V — Seed Datos Recientes (resuelve 'No data')")
    log.info(f"  URL: {INFLUX_URL} | Bucket: {INFLUX_BUCKET}")
    log.info(f"  Devices: {[d['code'] for d in ALL_DEVICES]}")
    log.info("=" * 62)

    now = datetime.now(timezone.utc).replace(microsecond=0)

    async with InfluxDBClientAsync(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        write_api = client.write_api()

        neza_sim = await seed_neza_history(write_api, now)
        sims     = await seed_recent_6h(write_api, now, neza_sim)
        await seed_snapshot_now(write_api, sims)

        if live:
            await live_loop(write_api, sims)

    log.info("")
    log.info("=" * 62)
    log.info("  ✅ Seed completado — Grafana debería mostrar datos ahora")
    log.info("")
    log.info("  Si los paneles siguen vacíos: verifica el time range")
    log.info("  en Grafana (debe ser 'Last 6 hours' o mayor).")
    log.info("")
    if not live:
        log.info("  Para datos en tiempo real (paneles 'ahora'):")
        log.info("  docker compose exec backend python scripts/seed_now.py --live")
    log.info("=" * 62)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                        help="Mantiene un loop que escribe 1 punto/30s indefinidamente")
    args = parser.parse_args()
    asyncio.run(main(args.live))
