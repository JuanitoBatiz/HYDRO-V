#!/usr/bin/env python3
"""
Enriquece los datos existentes en InfluxDB con los fields faltantes:
  - fsm_state_num: versión numérica del fsm_state (para state-timeline de Grafana)
  - dtdt_value: derivada de turbidez calculada segundo a segundo

También re-escribe el historial de NEZA-001 con estos campos adicionales.

Estrategia: en lugar de hacer QUERY+TRANSFORM de los datos existentes
(lento y costoso), simplemente escribimos los 7 días completos de nuevo
para NEZA-001 y las últimas 6h para todos los devices, incluyendo
los campos nuevos en cada Point.

Uso:
    docker compose exec backend python scripts/seed_enrich.py
"""
import asyncio, math, os, random, sys, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("seed-enrich")

INFLUX_URL    = os.getenv("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN",  "")
INFLUX_ORG    = os.getenv("INFLUX_ORG",    "hydrov")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET_TELEMETRY", "sensor_telemetry")

ALL_DEVICES = [
    {"code": "HYDRO-V-NEZA-001", "zone": "NZ-001", "h": 125.0},
    {"code": "HYDRO-V-001",      "zone": "NZ-001", "h": 125.0},
    {"code": "HYDRO-V-002",      "zone": "NZ-001", "h": 110.0},
    {"code": "HYDRO-V-003",      "zone": "NZ-002", "h": 125.0},
    {"code": "HYDRO-V-004",      "zone": "NZ-002", "h":  95.0},
    {"code": "HYDRO-V-005",      "zone": "NZ-003", "h": 150.0},
]

# Mapa FSM → número (para state-timeline)
FSM_NUM = {"IDLE": 0.0, "ANALYZING": 1.0, "HARVESTING": 2.0, "FULL_TANK": 3.0, "EMERGENCY": 4.0}


class EnrichedSim:
    """Simulador que genera los 4 fields base + fsm_state_num + dtdt_value."""
    def __init__(self, code, zone, h, seed):
        self.code, self.zone, self.h = code, zone, h
        self.rng = random.Random(seed)
        self.dist        = h * 0.28
        self.flow_total  = self.rng.uniform(12000, 22000)
        self.flow_lpm    = 0.0
        self.turb        = 1.9
        self.prev_turb   = 1.9
        self.fsm         = "IDLE"
        self.state_dur   = 0
        self.intake_c    = self.rng.randint(8, 25)
        self.reject_c    = self.rng.randint(3, 12)
        self.err_count   = 0
        self.rain        = False
        self.rain_e      = 0
        self.rain_dur    = 0
        self.rain_int    = 0.0
        self.reject_end  = 0

    def step(self, t: datetime, s: int = 30):
        h = t.hour
        if not self.rain and self.fsm == "IDLE":
            p = (0.0015 if 14 <= h <= 20 else 0.0003) * s
            if self.rng.random() < p:
                self.rain, self.rain_e = True, 0
                self.rain_int = self.rng.choice([5.0, 10.0, 15.0])
                self.rain_dur = int(self.rng.uniform(240, 720))
                self.reject_end = int(self.rng.uniform(60, 150))
                self.fsm = "ANALYZING"; self.state_dur = 0

        prev_t = self.prev_turb
        if self.rain:
            self.rain_e += s
            e = self.rain_e
            k = 0.06 * (self.rain_int / 5.0)
            Tp = 12 + self.rain_int * 3.5
            if e < 25:
                self.fsm = "ANALYZING"
                self.turb += k * (Tp - self.turb) * s; self.flow_lpm = 0.0
            elif e < self.reject_end:
                if self.fsm != "HARVESTING": self.fsm = "HARVESTING"; self.reject_c += 1; self.state_dur = 0
                self.turb *= 0.992 ** s; self.flow_lpm = self.rain_int * 0.8
                self.flow_total += self.flow_lpm * s / 60
            elif e < self.rain_dur:
                self.turb = max(1.1, self.turb * 0.995); self.flow_lpm = self.rain_int * 0.92
                self.flow_total += self.flow_lpm * s / 60
                self.dist -= (self.flow_lpm / (60 * 2.8)) * s
                if self.fsm != "HARVESTING": self.intake_c += 1; self.state_dur = 0
                self.fsm = "HARVESTING"
            else:
                self.rain = False; self.flow_lpm = 0.0
                self.fsm = "FULL_TANK" if (1 - self.dist/self.h) > 0.94 else "IDLE"; self.state_dur = 0
        else:
            self.fsm = "IDLE"; self.flow_lpm = 0.0
            r = 0.00180 * (2.8 if 7<=h<=9 or 18<=h<=21 else 0.15 if 0<=h<=5 else 1.0)
            self.dist += r * s
            self.turb = max(1.3, 1.9 + self.rng.gauss(0, 0.18))

        self.turb = max(0.4, self.turb + self.rng.gauss(0, 0.08))
        self.dist = min(self.h * 0.96, max(self.h * 0.04, self.dist))
        self.state_dur += s

        # dtdt_value: derivada de turbidez (NTU/s, promediada sobre el step)
        dtdt = (self.turb - prev_t) / s
        self.prev_turb = self.turb

        return {
            "turbidity_ntu":    round(self.turb, 3),
            "distance_cm":      round(self.dist, 2),
            "flow_lpm":         round(max(0.0, self.flow_lpm), 3),
            "flow_total_liters":round(self.flow_total, 1),
            "dtdt_value":       round(dtdt, 5),
            "fsm_state":        self.fsm,
            "fsm_state_num":    FSM_NUM.get(self.fsm, 0.0),
            "state_duration_ms":self.state_dur * 1000,
            "intake_cycles":    self.intake_c,
            "reject_cycles":    self.reject_c,
            "error_count":      self.err_count,
        }

    def make_points(self, t, v):
        p_s = (Point("sensor_reading")
               .tag("device_code", self.code).tag("zone_code", self.zone)
               .field("turbidity_ntu",     v["turbidity_ntu"])
               .field("distance_cm",       v["distance_cm"])
               .field("flow_lpm",          v["flow_lpm"])
               .field("flow_total_liters", v["flow_total_liters"])
               .field("dtdt_value",        v["dtdt_value"])          # ← NEW
               .time(t))
        p_d = (Point("device_state")
               .tag("device_code", self.code).tag("zone_code", self.zone)
               .tag("fsm_state",   v["fsm_state"])
               .field("fsm_state_num",    v["fsm_state_num"])        # ← NEW (numérico)
               .field("state_duration_ms",v["state_duration_ms"])
               .field("intake_cycles",    v["intake_cycles"])
               .field("reject_cycles",    v["reject_cycles"])
               .field("error_count",      v["error_count"])
               .time(t))
        return [p_s, p_d]


async def seed_device(write_api, dev, days_back, step_s, seed):
    now   = datetime.now(timezone.utc).replace(microsecond=0)
    start = now - timedelta(days=days_back)
    sim   = EnrichedSim(dev["code"], dev["zone"], dev["h"], seed)
    batch, total = [], 0
    t = start
    while t <= now:
        v = sim.step(t, step_s)
        batch.extend(sim.make_points(t, v))
        total += 2
        if len(batch) >= 5000:
            await write_api.write(bucket=INFLUX_BUCKET, record=batch)
            batch = []
        t += timedelta(seconds=step_s)
    if batch:
        await write_api.write(bucket=INFLUX_BUCKET, record=batch)
    return total


async def main():
    log.info("=" * 62)
    log.info("  HYDRO-V — Seed Enriquecido (fsm_state_num + dtdt_value)")
    log.info("=" * 62)

    async with InfluxDBClientAsync(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        w = client.write_api()

        # NEZA-001: 7 días completos (30s resolución)
        log.info("[1/6] HYDRO-V-NEZA-001 — 7 días (step=30s)...")
        n = await seed_device(w, ALL_DEVICES[0], days_back=7, step_s=30, seed=1001)
        log.info(f"  ✓ {n:,} puntos")

        # Resto de devices: últimas 6h (30s resolución)
        for i, dev in enumerate(ALL_DEVICES[1:], start=2):
            log.info(f"[{i}/6] {dev['code']} — 6h...")
            n = await seed_device(w, dev, days_back=0.25, step_s=30, seed=1000 + i * 17)
            log.info(f"  ✓ {n:,} puntos")

    log.info("")
    log.info("=" * 62)
    log.info("  ✅ Enriquecimiento completado")
    log.info("  Fields añadidos: fsm_state_num, dtdt_value")
    log.info("  Próximo paso: recargar dashboards en Grafana")
    log.info("=" * 62)

if __name__ == "__main__":
    asyncio.run(main())
