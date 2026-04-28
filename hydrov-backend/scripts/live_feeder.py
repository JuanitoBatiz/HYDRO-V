#!/usr/bin/env python3
"""
Live feeder — escribe puntos cada 10s para TODOS los devices.
Perfecto para tomar capturas de Grafana con datos reales "ahora".

Detener: Ctrl+C  o  docker compose exec backend kill $(pgrep -f live_feeder)

Uso:
    # En segundo plano (recomendado para capturas):
    docker compose exec -d backend python scripts/live_feeder.py

    # En primer plano (ver logs):
    docker compose exec backend python scripts/live_feeder.py
"""
import asyncio, math, os, random, sys, signal, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("live-feeder")

INFLUX_URL    = os.getenv("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN",  "")
INFLUX_ORG    = os.getenv("INFLUX_ORG",    "hydrov")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET_TELEMETRY", "sensor_telemetry")
INTERVAL_S    = 10   # cada 10 segundos → paneles -1m siempre tienen datos

STOP = False

FSM_NUM = {"IDLE":0.0,"ANALYZING":1.0,"HARVESTING":2.0,"FULL_TANK":3.0,"EMERGENCY":4.0}

ALL_DEVICES = [
    {"code":"HYDRO-V-NEZA-001","zone":"NZ-001","h":125.0},
    {"code":"HYDRO-V-001",     "zone":"NZ-001","h":125.0},
    {"code":"HYDRO-V-002",     "zone":"NZ-001","h":110.0},
    {"code":"HYDRO-V-003",     "zone":"NZ-002","h":125.0},
    {"code":"HYDRO-V-004",     "zone":"NZ-002","h": 95.0},
    {"code":"HYDRO-V-005",     "zone":"NZ-003","h":150.0},
]

def handle_sigint(sig, frame):
    global STOP
    log.info("Deteniendo live feeder...")
    STOP = True

class QuickSim:
    """Simulador mínimo y rápido para el live loop."""
    def __init__(self, code, zone, h, seed):
        self.code, self.zone, self.h = code, zone, h
        rng = random.Random(seed)
        self.dist         = h * rng.uniform(0.05, 0.35)   # cisterna 65-95% llena
        self.flow_total   = rng.uniform(15000, 25000)
        self.turb         = rng.uniform(1.5, 2.8)
        self.prev_turb    = self.turb
        self.flow         = 0.0
        self.fsm          = "IDLE"
        self.state_dur    = 0
        self.intake_c     = rng.randint(12, 30)
        self.reject_c     = rng.randint(4, 15)
        self.rain         = False
        self.rain_t       = 0
        self.rain_dur     = 0
        self.rain_int     = 0.0
        self.reject_end   = 0
        self.rng          = rng

    def tick(self, step=INTERVAL_S):
        t = datetime.now(timezone.utc)
        h = t.hour

        # Posibilidad de lluvia
        if not self.rain and self.fsm == "IDLE":
            if self.rng.random() < 0.003 * step:
                self.rain      = True
                self.rain_t    = 0
                self.rain_int  = self.rng.choice([5.0, 10.0, 15.0])
                self.rain_dur  = int(self.rng.uniform(120, 600))
                self.reject_end= int(self.rng.uniform(40, 120))
                self.fsm       = "ANALYZING"
                self.state_dur = 0

        prev_t = self.prev_turb
        if self.rain:
            self.rain_t += step
            e, k = self.rain_t, 0.07*(self.rain_int/5.0)
            Tp = 10 + self.rain_int*3.2
            if e < 20:
                self.fsm = "ANALYZING"
                self.turb += k*(Tp-self.turb)*step; self.flow = 0.0
            elif e < self.reject_end:
                if self.fsm != "HARVESTING": self.fsm="HARVESTING"; self.reject_c+=1; self.state_dur=0
                self.turb *= 0.993**step; self.flow = self.rain_int*0.8
                self.flow_total += self.flow*step/60
            elif e < self.rain_dur:
                self.turb = max(1.1, self.turb*0.996); self.flow = self.rain_int*0.93
                self.flow_total += self.flow*step/60
                self.dist -= (self.flow/(60*2.8))*step
                if self.fsm!="HARVESTING": self.intake_c+=1; self.state_dur=0
                self.fsm = "HARVESTING"
            else:
                self.rain=False; self.flow=0.0
                self.fsm = "FULL_TANK" if (1-self.dist/self.h)>0.94 else "IDLE"; self.state_dur=0
        else:
            self.fsm="IDLE"; self.flow=0.0
            rate = 0.0018*(2.5 if 7<=h<=9 or 18<=h<=21 else 0.12 if 0<=h<=5 else 1.0)
            self.dist += rate*step
            self.turb = max(1.2, 1.9+self.rng.gauss(0,0.2))

        self.turb = max(0.4, self.turb+self.rng.gauss(0,0.07))
        self.dist = min(self.h*0.96, max(self.h*0.04, self.dist))
        self.state_dur += step
        dtdt = (self.turb - prev_t) / step
        self.prev_turb = self.turb
        lvl  = (1 - self.dist/self.h)*100.0

        return {
            "turbidity_ntu":     round(self.turb,3),
            "distance_cm":       round(self.dist,2),
            "level_pct":         round(lvl,1),
            "flow_lpm":          round(max(0.0,self.flow),3),
            "flow_total_liters": round(self.flow_total,1),
            "dtdt_value":        round(dtdt,5),
            "fsm_state":         self.fsm,
            "fsm_state_num":     FSM_NUM.get(self.fsm,0.0),
            "state_duration_ms": self.state_dur*1000,
            "intake_cycles":     self.intake_c,
            "reject_cycles":     self.reject_c,
            "error_count":       0,
        }

    def points(self, t, v):
        return [
            Point("sensor_reading")
            .tag("device_code",self.code).tag("zone_code",self.zone)
            .field("turbidity_ntu",    v["turbidity_ntu"])
            .field("distance_cm",      v["distance_cm"])
            .field("flow_lpm",         v["flow_lpm"])
            .field("flow_total_liters",v["flow_total_liters"])
            .field("dtdt_value",       v["dtdt_value"])
            .time(t),
            Point("device_state")
            .tag("device_code",self.code).tag("zone_code",self.zone)
            .tag("fsm_state",  v["fsm_state"])
            .field("fsm_state_num",    v["fsm_state_num"])
            .field("state_duration_ms",v["state_duration_ms"])
            .field("intake_cycles",    v["intake_cycles"])
            .field("reject_cycles",    v["reject_cycles"])
            .field("error_count",      v["error_count"])
            .time(t),
        ]

async def main():
    signal.signal(signal.SIGINT, handle_sigint)

    sims = {d["code"]: QuickSim(d["code"],d["zone"],d["h"],seed=i*37+5)
            for i,d in enumerate(ALL_DEVICES)}

    log.info("=" * 62)
    log.info(f"  HYDRO-V Live Feeder  — escribe cada {INTERVAL_S}s")
    log.info(f"  Devices: {len(sims)} | Bucket: {INFLUX_BUCKET}")
    log.info("  Detener: Ctrl+C")
    log.info("=" * 62)

    tick = 0
    async with InfluxDBClientAsync(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        w = client.write_api()

        # Primer tick inmediato + backfill de 5m para que los paneles -1m/-5m tengan datos
        log.info("  Backfill de 5 minutos para calentar los paneles...")
        backfill_pts = []
        now = datetime.now(timezone.utc).replace(microsecond=0)
        for delta in range(300, -1, -INTERVAL_S):  # 5min atrás → ahora
            t = now - timedelta(seconds=delta)
            for sim in sims.values():
                v = sim.tick(INTERVAL_S)
                backfill_pts.extend(sim.points(t, v))
        await w.write(bucket=INFLUX_BUCKET, record=backfill_pts)
        log.info(f"  ✓ Backfill: {len(backfill_pts)} puntos escritos")
        log.info("─" * 62)

        while not STOP:
            await asyncio.sleep(INTERVAL_S)
            if STOP:
                break
            tick += 1
            now   = datetime.now(timezone.utc).replace(microsecond=0)
            pts   = []
            lines = []
            for sim in sims.values():
                v = sim.tick(INTERVAL_S)
                pts.extend(sim.points(now, v))
                lines.append(
                    f"  {sim.code.replace('HYDRO-V-',''):<12} "
                    f"{v['fsm_state']:<12} "
                    f"turb={v['turbidity_ntu']:5.2f}NTU "
                    f"flow={v['flow_lpm']:5.1f}L/min "
                    f"lvl={v['level_pct']:5.1f}%"
                )
            await w.write(bucket=INFLUX_BUCKET, record=pts)
            log.info(f"[tick {tick:04d}] {now.strftime('%H:%M:%S')} — {len(pts)} puntos")
            for l in lines:
                log.info(l)

    log.info("✅ Live feeder detenido.")

if __name__ == "__main__":
    asyncio.run(main())
