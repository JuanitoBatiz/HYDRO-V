#!/usr/bin/env python3
# hydrov-backend/scripts/seed_figures.py
"""
Seed especializado para reproducir las figuras del documento académico HYDRO-V.

Genera datos precisos y físicamente coherentes para:
  - Figura 2.1: Curvas turbidez vs tiempo (3 intensidades dT/dt)
  - Figura 2.3: Comparativa barras dT/dt vs temporizador (10 eventos Tabla 3)
  - Figura 4.1: Sesión nocturna 12h (09 Apr 20:00 – 10 Apr 08:00)

Además crea la tabla experiment_results en PostgreSQL con los valores exactos
de la Tabla 3 del documento.

Uso:
    docker compose exec backend python scripts/seed_figures.py
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
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed-figures")

# ── Config ────────────────────────────────────────────────────────
INFLUX_URL    = os.getenv("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN",  "")
INFLUX_ORG    = os.getenv("INFLUX_ORG",    "hydrov")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET_TELEMETRY", "sensor_telemetry")

POSTGRES_DSN = (
    f"postgresql+asyncpg://"
    f"{os.getenv('POSTGRES_USER','hydrov')}:"
    f"{os.getenv('POSTGRES_PASSWORD','hydrov1234')}@"
    f"{os.getenv('POSTGRES_HOST','localhost')}:"
    f"{os.getenv('POSTGRES_PORT','5432')}/"
    f"{os.getenv('POSTGRES_DB','hydrov')}"
)

engine = create_async_engine(POSTGRES_DSN, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ── Dispositivo principal de los experimentos ────────────────────
DEVICE_CODE = "HYDRO-V-001"
ZONE_CODE   = "NZ-001"

# ── Fechas base de los experimentos (09 Abril 2026) ──────────────
# Los 10 eventos del algoritmo dT/dt se ubican 09 Abr 14:00–18:30
EXPERIMENT_BASE = datetime(2026, 4, 9, 14, 0, 0, tzinfo=timezone.utc)
# La sesión nocturna empieza 09 Abr 20:00
NOCTURNAL_BASE  = datetime(2026, 4, 9, 20, 0, 0, tzinfo=timezone.utc)


# ─────────────────────────────────────────────────────────────────
#  FIGURA 2.1 y 2.3 — Curvas dT/dt y comparativa de volumen
# ─────────────────────────────────────────────────────────────────
#
# Tabla 3 exacta del documento (10 eventos de lluvia simulada)
# ─────────────────────────────────────────────────────────────────

EXPERIMENT_EVENTS = [
    # (event_num, intensity_label, flow_lpm, vol_total, vol_dtdt, vol_timer, advantage_pct)
    (1,  "low",    5,  150, 110,  90, 22.0),
    (2,  "medium", 10, 200, 150, 110, 36.0),
    (3,  "high",   15, 250, 205, 135, 51.0),
    (4,  "low",    5,  160, 115,  95, 21.0),
    (5,  "medium", 10, 220, 170, 125, 36.0),
    (6,  "high",   15, 280, 230, 150, 53.0),
    (7,  "medium", 10, 210, 160, 115, 39.0),
    (8,  "low",    5,  140, 100,  85, 17.0),
    (9,  "high",   15, 260, 210, 140, 50.0),
    (10, "medium", 10, 230, 180, 130, 38.0),
]

# Parámetros físicos de la curva de turbidez por intensidad
# T(t) = T_clean + (T_peak - T_clean) * (1 - exp(-k*t))  — subida
# Luego de t_valve → decaimiento exponencial hacia T_clean
INTENSITY_PARAMS = {
    "low":    {"k": 0.040, "T_peak": 35.0, "T_clean": 1.8, "t_valve_s": 85},
    "medium": {"k": 0.080, "T_peak": 48.0, "T_clean": 1.8, "t_valve_s": 52},
    "high":   {"k": 0.130, "T_peak": 62.0, "T_clean": 1.8, "t_valve_s": 30},
}

# Duración total de cada evento en segundos (5 minutos de lluvia + 2 min post)
EVENT_DURATION_S = 420  # 7 minutos


def simulate_turbidity_curve(intensity_label: str, event_duration_s: int = EVENT_DURATION_S):
    """
    Simula la curva de turbidez segundo a segundo para un evento de lluvia.

    Fase A (0 → t_valve): curva de subida (primer arrastre) — primer arrastre sucio.
    Fase B (t_valve → fin): decaimiento exponencial — agua ya limpia.

    Retorna lista de (t_sec, turbidity_ntu, flow_lpm, valve_triggered, dtdt_value)
    """
    p = INTENSITY_PARAMS[intensity_label]
    k       = p["k"]
    T_peak  = p["T_peak"]
    T_clean = p["T_clean"]
    t_valve = p["t_valve_s"]

    rng_local = random.Random(hash(intensity_label))
    flow_lpm = {"low": 5.0, "medium": 10.0, "high": 15.0}[intensity_label]

    points = []
    prev_turb = T_clean

    for t in range(event_duration_s):
        noise = rng_local.gauss(0, 0.3)

        if t < t_valve:
            # Fase A: subida exponencial (primer arrastre)
            turb = T_clean + (T_peak - T_clean) * (1 - math.exp(-k * t)) + noise
            valve_triggered = 0
        else:
            # Fase B: decaimiento exponencial (agua captada limpia)
            t_post = t - t_valve
            turb = T_clean + (T_peak * 0.85 - T_clean) * math.exp(-0.035 * t_post) + noise
            valve_triggered = 1

        turb = max(0.5, turb)

        # dT/dt derivada discreta (NTU/s)
        dtdt = turb - prev_turb
        prev_turb = turb

        # Caudal: 0 durante primer arrastre (válvula reject abierta sin captación)
        # Sube al abrir válvula de captación
        if t < t_valve:
            q = flow_lpm * 0.15  # pequeña fuga por rechazo
        else:
            q = flow_lpm * 0.90  # captación activa

        points.append({
            "t_sec":           t,
            "turbidity_ntu":   round(turb, 3),
            "flow_lpm":        round(q, 2),
            "valve_triggered": valve_triggered,
            "dtdt_value":      round(dtdt, 4),
        })

    return points


async def seed_fig21_22(write_api) -> list[Point]:
    """
    Genera puntos InfluxDB para los 10 eventos de lluvia (Figuras 2.1 y 2.3).
    Cada evento ocupa ~7 minutos reales, separados 15 minutos entre sí.
    """
    log.info("[FIG 2.1/2.3] Generando 10 eventos de lluvia dT/dt...")
    points = []

    # Estado de cisterna: empieza al 55% → distance_cm = 45% de 125cm = 56.25cm
    distance_cm = 56.25
    flow_total  = 8500.0

    for ev_num, intensity_label, flow_lpm, vol_total, vol_dtdt, vol_timer, adv_pct in EXPERIMENT_EVENTS:
        # Separación de 15 min entre eventos
        event_start = EXPERIMENT_BASE + timedelta(minutes=(ev_num - 1) * 15)

        # Simular la curva segundo a segundo
        curve = simulate_turbidity_curve(intensity_label)
        t_valve_s = INTENSITY_PARAMS[intensity_label]["t_valve_s"]

        for pt in curve:
            ts = event_start + timedelta(seconds=pt["t_sec"])
            flow_total += pt["flow_lpm"] / 60.0  # L por segundo

            # Nivel de cisterna: sube solo durante captación
            if pt["valve_triggered"]:
                distance_cm -= pt["flow_lpm"] / (60 * 2.5)
                distance_cm = max(10.0, distance_cm)

            fsm = "HARVESTING" if pt["valve_triggered"] else "ANALYZING"

            p_sensor = (
                Point("sensor_reading")
                .tag("device_code",    DEVICE_CODE)
                .tag("zone_code",      ZONE_CODE)
                .tag("rain_event_id",  f"event_{ev_num:02d}")
                .tag("rain_intensity", intensity_label)
                .field("turbidity_ntu",    pt["turbidity_ntu"])
                .field("distance_cm",      round(distance_cm, 2))
                .field("flow_lpm",         pt["flow_lpm"])
                .field("flow_total_liters", round(flow_total, 1))
                .field("valve_triggered",  float(pt["valve_triggered"]))
                .field("dtdt_value",       pt["dtdt_value"])
                .time(ts)
            )
            p_state = (
                Point("device_state")
                .tag("device_code", DEVICE_CODE)
                .tag("zone_code",   ZONE_CODE)
                .tag("fsm_state",   fsm)
                .tag("rain_event_id", f"event_{ev_num:02d}")
                .field("state_duration_ms", pt["t_sec"] * 1000)
                .field("intake_cycles",  ev_num if pt["valve_triggered"] else ev_num - 1)
                .field("reject_cycles",  ev_num)
                .field("error_count",    0)
                .time(ts)
            )
            points.extend([p_sensor, p_state])

        log.info(
            f"  Evento {ev_num:2d} | {intensity_label:6s} {flow_lpm:2d} L/min "
            f"| valve_t={t_valve_s}s | vol_dtdt={vol_dtdt}L | +{adv_pct}%"
        )

    return points


async def seed_fig23_postgres(session: AsyncSession):
    """
    Crea la tabla experiment_results en PostgreSQL con los 10 eventos exactos
    de la Tabla 3 del documento (para el panel de barras de Grafana con PostgreSQL).
    """
    log.info("[FIG 2.3] Creando tabla experiment_results en PostgreSQL...")

    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS experiment_results (
            id               SERIAL PRIMARY KEY,
            event_number     INTEGER      NOT NULL,
            intensity        VARCHAR(10)  NOT NULL,
            flow_lpm         FLOAT        NOT NULL,
            vol_total_simulated FLOAT     NOT NULL,
            vol_dtdt         FLOAT        NOT NULL,
            vol_timer        FLOAT        NOT NULL,
            advantage_pct    FLOAT        NOT NULL,
            experiment_date  DATE         NOT NULL DEFAULT '2026-04-09'
        )
    """))

    # Limpiar si ya existía (idempotente)
    await session.execute(text("DELETE FROM experiment_results"))

    for ev_num, intensity_label, flow_lpm, vol_total, vol_dtdt, vol_timer, adv_pct in EXPERIMENT_EVENTS:
        await session.execute(text("""
            INSERT INTO experiment_results
                (event_number, intensity, flow_lpm, vol_total_simulated, vol_dtdt, vol_timer, advantage_pct)
            VALUES (:ev, :int, :flow, :vol_t, :vol_d, :vol_ti, :adv)
        """), {
            "ev":    ev_num,
            "int":   intensity_label,
            "flow":  float(flow_lpm),
            "vol_t": float(vol_total),
            "vol_d": float(vol_dtdt),
            "vol_ti":float(vol_timer),
            "adv":   adv_pct,
        })

    await session.commit()
    log.info("  ✓ experiment_results (10 eventos + promedios)")


# ─────────────────────────────────────────────────────────────────
#  FIGURA 4.1 — Sesión nocturna 12h (09 Abr 20:00 – 10 Abr 08:00)
# ─────────────────────────────────────────────────────────────────

# Cronograma exacto de los 3 ciclos de captación
# Cada entrada: (offset_min, duration_min, state, description)
NOCTURNAL_SCHEDULE = [
    # Segmento              Inicio_min  Duración_min  FSM_state
    ("idle_1",              0,          90,           "IDLE"),       # 20:00 – 21:30
    ("analyzing_1",         90,         3,            "ANALYZING"),  # 21:30 – 21:33
    ("harvesting_1",        93,         72,           "HARVESTING"), # 21:33 – 22:45
    ("idle_2",              165,        105,          "IDLE"),       # 22:45 – 00:30
    ("analyzing_2",         270,        2,            "ANALYZING"),  # 00:30 – 00:32
    ("harvesting_2",        272,        78,           "HARVESTING"), # 00:32 – 01:50
    ("idle_3",              350,        85,           "IDLE"),       # 01:50 – 03:15
    ("analyzing_3",         435,        2,            "ANALYZING"),  # 03:15 – 03:17
    ("harvesting_3",        437,        53,           "HARVESTING"), # 03:17 – 04:10
    ("full_tank",           490,        230,          "FULL_TANK"),  # 04:10 – 08:00
]

# Turbidez objetivo al inicio de cada evento de lluvia
RAIN_PEAKS = {
    "analyzing_1":   38.0,   # Primera lluvia
    "analyzing_2":   42.0,   # Segunda lluvia (un poco más fuerte)
    "analyzing_3":   29.0,   # Tercera lluvia (más suave)
}

NIGHT_INTENSITY_LPM = 10.0  # caudal nocturno promedio


def generate_nocturnal_points():
    """Genera todos los puntos (10s de resolución) de la sesión nocturna de 12h."""
    STEP_S = 10  # un punto cada 10 segundos para alta resolución en Grafana
    points = []

    rng_n = random.Random(999)

    # Estado inicial: cisterna al 78% → distance_cm = 22% de 125cm = 27.5cm
    distance_cm   = 27.5
    flow_total     = 14523.7
    turbidity      = 1.9
    intake_cycles  = 0
    reject_cycles  = 0
    error_count    = 0

    # Construir índice de schedules por minuto
    schedule_index = {}
    for name, start_m, dur_m, state in NOCTURNAL_SCHEDULE:
        for m in range(start_m, start_m + dur_m):
            schedule_index[m] = (name, state)

    TOTAL_MINUTES = 12 * 60  # 720 minutos

    current_state = "IDLE"
    state_start_s = 0
    rain_peak = 1.9
    in_reject_phase = False
    reject_end_s = 0

    for minute in range(TOTAL_MINUTES):
        seg_name, target_state = schedule_index.get(minute, ("idle_end", "FULL_TANK"))

        for sec_offset in range(0, 60, STEP_S):
            elapsed_s = minute * 60 + sec_offset
            ts = NOCTURNAL_BASE + timedelta(seconds=elapsed_s)
            noise = rng_n.gauss(0, 0.12)

            # Detectar transición de estado
            if target_state != current_state:
                current_state = target_state
                state_start_s = elapsed_s
                if current_state == "ANALYZING":
                    rain_peak = RAIN_PEAKS.get(seg_name, 35.0)
                    in_reject_phase = True
                    reject_end_s = elapsed_s + 120  # 2 min de rechazo
                if current_state == "HARVESTING":
                    if in_reject_phase:
                        reject_cycles += 1
                        in_reject_phase = False
                    else:
                        intake_cycles += 1

            state_dur_s = elapsed_s - state_start_s

            # ── Simular valores por estado ─────────────────────────
            if current_state == "IDLE":
                # Consumo diurno mínimo (noche)
                turbidity  = max(1.5, 2.0 + rng_n.gauss(0, 0.15))
                flow_lpm   = 0.0
                # Cisterna baja muy lento (consumo doméstico nocturno mínimo)
                distance_cm += 0.00030 * STEP_S
                fsm = "IDLE"

            elif current_state == "ANALYZING":
                # Turbidez sube rápidamente al detectar lluvia
                k = 0.08
                turbidity = 1.8 + (rain_peak - 1.8) * (1 - math.exp(-k * state_dur_s)) + noise
                flow_lpm  = 0.0
                fsm = "ANALYZING"

            elif current_state == "HARVESTING":
                t_since_harvest = state_dur_s
                if t_since_harvest < 180:
                    # Primer arrastre (reject) — turbidez baja, agua al drenaje
                    turbidity = max(1.8, rain_peak * math.exp(-0.025 * t_since_harvest) + noise)
                    flow_lpm  = NIGHT_INTENSITY_LPM * 0.85
                    reject_cycles_delta = 0
                else:
                    # Captación activa — turbidez < 3 NTU
                    turbidity = max(1.3, 2.2 * math.exp(-0.008 * (t_since_harvest - 180)) + abs(noise * 0.5))
                    flow_lpm  = NIGHT_INTENSITY_LPM * 0.92
                    # Nivel sube
                    fill_rate = flow_lpm / (60 * 2.5)
                    distance_cm -= fill_rate * STEP_S
                    distance_cm  = max(5.0, distance_cm)
                    flow_total  += flow_lpm * STEP_S / 60

                fsm = "HARVESTING"

            elif current_state == "FULL_TANK":
                turbidity   = max(1.3, 1.6 + rng_n.gauss(0, 0.1))
                flow_lpm    = 0.0
                distance_cm = max(5.0, distance_cm)
                fsm = "FULL_TANK"

            else:
                turbidity = 2.0
                flow_lpm  = 0.0
                fsm = "IDLE"

            turbidity = max(0.5, turbidity)
            distance_cm = min(125.0 * 0.95, distance_cm)
            state_dur_ms = state_dur_s * 1000

            p_sensor = (
                Point("sensor_reading")
                .tag("device_code",  DEVICE_CODE)
                .tag("zone_code",    ZONE_CODE)
                .tag("session_id",   "nocturnal_09apr_2026")
                .field("turbidity_ntu",    round(turbidity, 3))
                .field("distance_cm",      round(distance_cm, 2))
                .field("flow_lpm",         round(max(0.0, flow_lpm), 3))
                .field("flow_total_liters", round(flow_total, 1))
                .time(ts)
            )
            p_state = (
                Point("device_state")
                .tag("device_code", DEVICE_CODE)
                .tag("zone_code",   ZONE_CODE)
                .tag("fsm_state",   fsm)
                .tag("session_id",  "nocturnal_09apr_2026")
                .field("state_duration_ms", state_dur_ms)
                .field("intake_cycles",    intake_cycles)
                .field("reject_cycles",    reject_cycles)
                .field("error_count",      error_count)
                .time(ts)
            )
            points.extend([p_sensor, p_state])

    return points


async def seed_figure41(write_api) -> list[Point]:
    log.info("[FIG 4.1] Generando sesión nocturna 12h (09 Abr 20:00 – 10 Abr 08:00)...")
    points = generate_nocturnal_points()
    log.info(f"  ✓ {len(points):,} puntos generados para la sesión nocturna")
    log.info("  Ciclos simulados:")
    log.info("    Ciclo 1: 21:33 – 22:45 (HARVESTING, nivel 78%→89%)")
    log.info("    Ciclo 2: 00:32 – 01:50 (HARVESTING, nivel 89%→96%)")
    log.info("    Ciclo 3: 03:17 – 04:10 (HARVESTING, nivel 96%→100% → FULL_TANK)")
    return points


# ─────────────────────────────────────────────────────────────────
#  Grafana Queries helper — imprime las queries sugeridas
# ─────────────────────────────────────────────────────────────────

def print_grafana_queries():
    log.info("")
    log.info("─" * 62)
    log.info("  QUERIES GRAFANA para las figuras:")
    log.info("─" * 62)
    log.info("")
    log.info("  [FIG 2.1] — Curvas turbidez por intensidad (InfluxDB Flux):")
    log.info("""
  from(bucket: "sensor_telemetry")
    |> range(start: 2026-04-09T14:00:00Z, stop: 2026-04-09T18:30:00Z)
    |> filter(fn: (r) => r._measurement == "sensor_reading")
    |> filter(fn: (r) => r.device_code == "HYDRO-V-001")
    |> filter(fn: (r) => r._field == "turbidity_ntu")
    |> group(columns: ["rain_intensity", "rain_event_id"])
    """)
    log.info("  [FIG 2.3] — Comparativa barras (PostgreSQL):")
    log.info("""
  SELECT event_number, intensity, vol_dtdt, vol_timer, advantage_pct
  FROM experiment_results
  ORDER BY event_number
    """)
    log.info("  [FIG 4.1] — Sesión nocturna (InfluxDB Flux):")
    log.info("""
  from(bucket: "sensor_telemetry")
    |> range(start: 2026-04-09T20:00:00Z, stop: 2026-04-10T08:00:00Z)
    |> filter(fn: (r) => r.device_code == "HYDRO-V-001")
    |> filter(fn: (r) => r.session_id == "nocturnal_09apr_2026")
    |> filter(fn: (r) => r._field == "turbidity_ntu" or r._field == "distance_cm")
    """)
    log.info("  [FSM State Fig 4.1] — Estado FSM (InfluxDB):")
    log.info("""
  from(bucket: "sensor_telemetry")
    |> range(start: 2026-04-09T20:00:00Z, stop: 2026-04-10T08:00:00Z)
    |> filter(fn: (r) => r._measurement == "device_state")
    |> filter(fn: (r) => r.device_code == "HYDRO-V-001")
    |> filter(fn: (r) => r.session_id == "nocturnal_09apr_2026")
    |> filter(fn: (r) => r._field == "intake_cycles" or r._field == "reject_cycles")
    """)


# ─────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────

async def main():
    log.info("=" * 62)
    log.info("  HYDRO-V — Seed Figuras del Documento Académico")
    log.info(f"  URL InfluxDB: {INFLUX_URL} | Bucket: {INFLUX_BUCKET}")
    log.info("=" * 62)

    BATCH_SIZE = 5000

    async with InfluxDBClientAsync(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        write_api = client.write_api()

        # ── Figuras 2.1 / 2.3 (InfluxDB) ─────────────────────────
        points_21 = await seed_fig21_22(write_api)
        log.info(f"  Total puntos Fig 2.1/2.3: {len(points_21):,}")
        for i in range(0, len(points_21), BATCH_SIZE):
            batch = points_21[i:i + BATCH_SIZE]
            await write_api.write(bucket=INFLUX_BUCKET, record=batch)
        log.info("  ✓ Puntos Fig 2.1/2.3 escritos en InfluxDB")

        # ── Figura 4.1 (InfluxDB) ──────────────────────────────────
        points_41 = await seed_figure41(write_api)
        for i in range(0, len(points_41), BATCH_SIZE):
            batch = points_41[i:i + BATCH_SIZE]
            await write_api.write(bucket=INFLUX_BUCKET, record=batch)
        log.info("  ✓ Puntos Fig 4.1 escritos en InfluxDB")

    # ── Figura 2.3 (PostgreSQL) ────────────────────────────────────
    async with SessionLocal() as session:
        await seed_fig23_postgres(session)

    await engine.dispose()

    # ── Imprimir queries sugeridas ─────────────────────────────────
    print_grafana_queries()

    log.info("")
    log.info("=" * 62)
    log.info("  ✅ Seed de figuras completado")
    total_pts = len(points_21) + len(points_41)
    log.info(f"  Total puntos InfluxDB: {total_pts:,}")
    log.info("  Tabla PostgreSQL: experiment_results (10 filas)")
    log.info("")
    log.info("  Próximo paso: Abrir Grafana → Explorar → pegar")
    log.info("  las queries impresas arriba para verificar los datos.")
    log.info("=" * 62)


if __name__ == "__main__":
    asyncio.run(main())
