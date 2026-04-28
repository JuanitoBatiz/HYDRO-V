#!/usr/bin/env python3
# hydrov-backend/scripts/seed_postgres.py
"""
Seed completo de PostgreSQL para HYDRO-V.
Inserta catálogos, zonas, devices, usuarios, sensores, válvulas,
topología de red, alertas históricas, leak_detections y emergency_alerts.

Uso (dentro del contenedor backend):
    python scripts/seed_postgres.py

Uso (desde host con .env cargado):
    cd hydrov-backend && python scripts/seed_postgres.py

El script es IDEMPOTENTE — detecta datos existentes y no duplica.
"""
import asyncio
import sys
import os
import random
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text, select
import bcrypt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed-postgres")

# ── Config de DB desde entorno ────────────────────────────────────
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

rng = random.Random(42)

NOW = datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────

def ago(days=0, hours=0, minutes=0) -> datetime:
    return NOW - timedelta(days=days, hours=hours, minutes=minutes)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


async def table_count(session: AsyncSession, table: str) -> int:
    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
    return result.scalar()


# ─────────────────────────────────────────────────────────────────
#  1. Catálogos
# ─────────────────────────────────────────────────────────────────

async def seed_catalogs(session: AsyncSession):
    log.info("[1/10] Sembrando catálogos...")

    # Roles
    if await table_count(session, "roles") == 0:
        await session.execute(text("""
            INSERT INTO roles (name, description) VALUES
            ('admin',    'Administrador del sistema — acceso total'),
            ('operator', 'Operador de campo — monitoreo y control de válvulas'),
            ('viewer',   'Visualizador — solo lectura de dashboards')
        """))
        log.info("  ✓ roles (3)")

    # Sensor types
    if await table_count(session, "sensor_types") == 0:
        await session.execute(text("""
            INSERT INTO sensor_types (name, unit, description) VALUES
            ('turbidity',  'NTU', 'Sensor de turbidez DFRobot SEN0189 — mide claridad del agua'),
            ('ultrasonic', 'cm',  'Sensor ultrasónico HC-SR04 — mide nivel de cisterna por distancia'),
            ('flow',       'L/min', 'Caudalímetro YF-S201 — mide flujo y volumen total captado')
        """))
        log.info("  ✓ sensor_types (3)")

    # Valve types
    if await table_count(session, "valve_types") == 0:
        await session.execute(text("""
            INSERT INTO valve_types (name, default_state, description) VALUES
            ('intake', 'closed', 'Válvula de captación — abre cuando la turbidez es aceptable'),
            ('reject', 'closed', 'Válvula de primer arrastre — abre para descartar agua sucia')
        """))
        log.info("  ✓ valve_types (2)")

    # Alert types
    if await table_count(session, "alert_types") == 0:
        await session.execute(text("""
            INSERT INTO alert_types (name, default_severity, description) VALUES
            ('high_turbidity',     'medium',   'Turbidez > umbral máximo (5 NTU). Agua no apta para captación.'),
            ('leak_detected',      'high',     'Modelo GNN detectó anomalía de flujo indicando posible fuga.'),
            ('tank_low',           'medium',   'Nivel de cisterna bajo (< 20%). Se requiere captación pronto.'),
            ('tank_empty',         'critical', 'Cisterna vacía (< 5%). Sin agua disponible.'),
            ('system_error',       'critical', 'Error crítico en la FSM del ESP32. Intervención requerida.'),
            ('first_flush_complete','low',     'Ciclo de primer arrastre completado. Sistema listo para captación.')
        """))
        log.info("  ✓ alert_types (6)")

    await session.commit()


# ─────────────────────────────────────────────────────────────────
#  2. Zonas
# ─────────────────────────────────────────────────────────────────

async def seed_zones(session: AsyncSession):
    log.info("[2/10] Sembrando zonas...")
    if await table_count(session, "zones") > 0:
        log.info("  ↩ zonas ya existen, saltando")
        return

    await session.execute(text("""
        INSERT INTO zones (zone_code, name, municipality, state, latitude, longitude, population, area_km2)
        VALUES
        ('NZ-001', 'Zona Norte Nezahualcóyotl',  'Nezahualcóyotl', 'Estado de México', 19.4462, -99.0195, 215000, 21.2),
        ('NZ-002', 'Zona Centro Nezahualcóyotl', 'Nezahualcóyotl', 'Estado de México', 19.4136, -99.0151, 280000, 25.8),
        ('NZ-003', 'Zona Sur Valle de Aragón',   'Nezahualcóyotl', 'Estado de México', 19.3890, -99.0040, 155000, 16.4)
    """))
    await session.commit()
    log.info("  ✓ zones (3)")


# ─────────────────────────────────────────────────────────────────
#  3. Devices
# ─────────────────────────────────────────────────────────────────

async def seed_devices(session: AsyncSession):
    log.info("[3/10] Sembrando dispositivos...")
    if await table_count(session, "devices") > 0:
        log.info("  ↩ devices ya existen, saltando")
        return

    await session.execute(text("""
        INSERT INTO devices
            (zone_id, device_code, latitude, longitude, status, firmware_version,
             cistern_capacity_liters, cistern_height_cm, installed_at, last_seen_at)
        SELECT z.id, d.device_code, d.lat, d.lon, d.status, d.fw,
               d.cap, d.height,
               (NOW() - INTERVAL '90 days')::timestamptz,
               (NOW() - INTERVAL '2 minutes')::timestamptz
        FROM (VALUES
            ('NZ-001', 'HYDRO-V-001', 19.44620, -99.01950, 'active', '2.1.4', 3400.0, 125.0),
            ('NZ-001', 'HYDRO-V-002', 19.44801, -99.02103, 'active', '2.1.4', 2800.0, 110.0),
            ('NZ-002', 'HYDRO-V-003', 19.41360, -99.01510, 'active', '2.1.3', 3400.0, 125.0),
            ('NZ-002', 'HYDRO-V-004', 19.41005, -99.01801, 'active', '2.1.2', 2000.0,  95.0),
            ('NZ-003', 'HYDRO-V-005', 19.38900, -99.00400, 'active', '2.1.4', 4500.0, 150.0)
        ) AS d(zone_code, device_code, lat, lon, status, fw, cap, height)
        JOIN zones z ON z.zone_code = d.zone_code
    """))
    await session.commit()
    log.info("  ✓ devices (5)")


# ─────────────────────────────────────────────────────────────────
#  4. Users
# ─────────────────────────────────────────────────────────────────

async def seed_users(session: AsyncSession):
    log.info("[4/10] Sembrando usuarios...")
    if await table_count(session, "users") > 0:
        log.info("  ↩ users ya existen, saltando")
        return

    users = [
        ("admin@hydrov.mx",     "HydroV_Admin_2026!",  "Administrador HYDRO-V",      "admin",    True),
        ("jesus@hydrov.mx",     "HydroV_Dev_2026!",    "Jesús Bátiz — Desarrollador","admin",    True),
        ("op1@hydrov.mx",       "Operator123!",         "Operador Norte",              "operator", True),
        ("op2@hydrov.mx",       "Operator123!",         "Operadora Centro",            "operator", True),
        ("op3@hydrov.mx",       "Operator123!",         "Operador Sur",                "operator", True),
        ("viewer1@hydrov.mx",   "Viewer123!",           "Inspector Municipal 1",       "viewer",   True),
        ("viewer2@hydrov.mx",   "Viewer123!",           "Inspector Municipal 2",       "viewer",   True),
        ("viewer3@hydrov.mx",   "Viewer123!",           "Juez Evaluador",              "viewer",   True),
    ]

    for email, password, full_name, role_name, is_active in users:
        pw_hash = hash_password(password)
        await session.execute(text("""
            INSERT INTO users (role_id, email, password_hash, full_name, is_active, created_at)
            SELECT r.id, :email, :pw_hash, :full_name, :is_active, NOW()
            FROM roles r WHERE r.name = :role_name
        """), {
            "email": email, "pw_hash": pw_hash, "full_name": full_name,
            "is_active": is_active, "role_name": role_name
        })

    await session.commit()
    log.info(f"  ✓ users ({len(users)})")


# ─────────────────────────────────────────────────────────────────
#  5. Sensores y Válvulas
# ─────────────────────────────────────────────────────────────────

async def seed_sensors_valves(session: AsyncSession):
    log.info("[5/10] Sembrando sensores y válvulas...")
    if await table_count(session, "sensors") > 0:
        log.info("  ↩ sensores ya existen, saltando")
        return

    # Sensores: 3 por device (solo los 3 tipos base, con ELSE defensivo)
    await session.execute(text("""
        INSERT INTO sensors (device_id, sensor_type_id, min_threshold, max_threshold, is_active)
        SELECT d.id, st.id,
            CASE st.name
                WHEN 'turbidity'  THEN 0.0
                WHEN 'ultrasonic' THEN 5.0
                WHEN 'flow'       THEN 0.0
                ELSE 0.0
            END,
            CASE st.name
                WHEN 'turbidity'  THEN 5.0
                WHEN 'ultrasonic' THEN 120.0
                WHEN 'flow'       THEN 25.0
                ELSE 100.0
            END,
            true
        FROM devices d
        CROSS JOIN sensor_types st
        WHERE st.name IN ('turbidity', 'ultrasonic', 'flow')
    """))

    # Válvulas: 2 por device
    await session.execute(text("""
        INSERT INTO valves (device_id, valve_type_id, current_state, last_commanded_at)
        SELECT d.id, vt.id, 'closed', NOW() - INTERVAL '1 hour'
        FROM devices d
        CROSS JOIN valve_types vt
    """))

    await session.commit()
    log.info("  ✓ sensors (15) + valves (10)")


# ─────────────────────────────────────────────────────────────────
#  6. Topología de Red (device_edges)
# ─────────────────────────────────────────────────────────────────

async def seed_device_edges(session: AsyncSession):
    log.info("[6/10] Sembrando topología de red (device_edges)...")
    if await table_count(session, "device_edges") > 0:
        log.info("  ↩ device_edges ya existen, saltando")
        return

    await session.execute(text("""
        INSERT INTO device_edges (source_device_id, target_device_id, is_bidirectional, pipe_diameter_mm)
        SELECT s.id, t.id, e.bidir, e.diameter
        FROM (VALUES
            ('HYDRO-V-001', 'HYDRO-V-002', true,  50.0),
            ('HYDRO-V-001', 'HYDRO-V-003', true,  75.0),
            ('HYDRO-V-003', 'HYDRO-V-004', false, 40.0),
            ('HYDRO-V-003', 'HYDRO-V-005', true,  50.0),
            ('HYDRO-V-002', 'HYDRO-V-004', true,  40.0)
        ) AS e(src, tgt, bidir, diameter)
        JOIN devices s ON s.device_code = e.src
        JOIN devices t ON t.device_code = e.tgt
    """))
    await session.commit()
    log.info("  ✓ device_edges (5 aristas, topología de estrella extendida)")


# ─────────────────────────────────────────────────────────────────
#  7. Alertas históricas (30 días)
# ─────────────────────────────────────────────────────────────────

async def seed_alerts(session: AsyncSession):
    log.info("[7/10] Sembrando alertas históricas...")
    if await table_count(session, "alerts") > 0:
        log.info("  ↩ alerts ya existen, saltando")
        return

    # Obtener IDs
    devices_r = await session.execute(text("SELECT id, device_code FROM devices ORDER BY id"))
    devices = devices_r.fetchall()
    at_r = await session.execute(text("SELECT id, name, default_severity FROM alert_types"))
    alert_types = {row.name: (row.id, row.default_severity) for row in at_r.fetchall()}
    sensors_r = await session.execute(text("SELECT id, device_id FROM sensors LIMIT 15"))
    sensors = sensors_r.fetchall()
    sensor_by_device = {}
    for s in sensors:
        sensor_by_device.setdefault(s.device_id, []).append(s.id)

    # Distribución usando los tipos reales de la DB
    alert_dist = [
        ("turbidity_spike",     25),
        ("flow_anomaly",        20),
        ("leak_detected",       20),
        ("level_critical_low",  15),
        ("device_offline",       8),
        ("sensor_failure",       5),
        ("emergency",            4),
        ("turbidity_stable_ok",  2),
        ("level_full",           1),
    ]

    entries = []
    TOTAL_ALERTS = 1200
    for atype, pct in alert_dist:
        count = int(TOTAL_ALERTS * pct / 100)
        at_id, default_sev = alert_types[atype]
        for _ in range(count):
            device = rng.choice(devices)
            days_back = rng.uniform(0, 30)
            detected_at = ago(days=days_back)
            is_resolved = rng.random() > 0.15
            resolved_at = (detected_at + timedelta(hours=rng.uniform(0.5, 48))) if is_resolved else None
            confidence = round(rng.uniform(0.70, 0.99), 3)

            sensor_id = None
            if atype in ("turbidity_spike", "flow_anomaly", "sensor_failure") and device.id in sensor_by_device:
                sensor_id = rng.choice(sensor_by_device[device.id])

            sev = default_sev

            entries.append({
                "device_id": device.id,
                "sensor_id": sensor_id,
                "alert_type_id": at_id,
                "severity": sev,
                "confidence_score": confidence,
                "description": f"Alerta automática: {atype.replace('_',' ')} en {device.device_code}",
                "payload_snapshot": "{}",
                "detected_at": detected_at,
                "resolved_at": resolved_at,
                "is_resolved": is_resolved,
            })

    rng.shuffle(entries)

    for chunk_start in range(0, len(entries), 100):
        chunk = entries[chunk_start:chunk_start + 100]
        await session.execute(text("""
            INSERT INTO alerts
                (device_id, sensor_id, alert_type_id, severity, confidence_score,
                 description, payload_snapshot, detected_at, resolved_at, is_resolved)
            VALUES
                (:device_id, :sensor_id, :alert_type_id, :severity, :confidence_score,
                 :description, CAST(:payload_snapshot AS jsonb), :detected_at, :resolved_at, :is_resolved)
        """), chunk)

    await session.commit()
    log.info(f"  ✓ alerts ({TOTAL_ALERTS})")


# ─────────────────────────────────────────────────────────────────
#  8. Leak Detections
# ─────────────────────────────────────────────────────────────────

async def seed_leak_detections(session: AsyncSession):
    log.info("[8/10] Sembrando detecciones de fuga...")
    if await table_count(session, "leak_detections") > 0:
        log.info("  ↩ leak_detections ya existen, saltando")
        return

    devices_r = await session.execute(text("SELECT id, device_code FROM devices ORDER BY id"))
    devices = devices_r.fetchall()

    entries = []
    TOTAL = 3000

    for _ in range(TOTAL):
        device = rng.choice(devices)
        days_back = rng.uniform(0, 30)
        detected_at = ago(days=days_back)

        # Score con distribución bimodal: mayoría normal (0.05-0.40), picos de fuga (0.75-0.98)
        if rng.random() < 0.20:  # 20% son fugas reales
            score = round(rng.uniform(0.75, 0.98), 4)
        else:
            score = round(rng.triangular(0.05, 0.45, 0.18), 4)

        severity = (
            "critical" if score >= 0.90 else
            "high"     if score >= 0.75 else
            "medium"   if score >= 0.50 else
            "low"
        )
        is_resolved = rng.random() > 0.25 if score > 0.75 else True
        neighbor_count = rng.randint(1, 4)

        entries.append({
            "device_id": device.id,
            "node_id": device.device_code,
            "detected_at": detected_at,
            "anomaly_score": score,
            "severity": severity,
            "model_version": "v1.2.0",
            "neighbor_count": neighbor_count,
            "payload_snapshot": "{}",
            "resolved": is_resolved,
            "resolved_at": (detected_at + timedelta(hours=rng.uniform(1, 24))) if is_resolved else None,
        })

    for chunk_start in range(0, len(entries), 200):
        chunk = entries[chunk_start:chunk_start + 200]
        await session.execute(text("""
            INSERT INTO leak_detections
                (device_id, node_id, detected_at, anomaly_score, severity,
                 model_version, neighbor_count, payload_snapshot, resolved, resolved_at)
            VALUES
                (:device_id, :node_id, :detected_at, :anomaly_score, :severity,
                 :model_version, :neighbor_count, CAST(:payload_snapshot AS jsonb), :resolved, :resolved_at)
        """), chunk)

    await session.commit()
    log.info(f"  ✓ leak_detections ({TOTAL})")


# ─────────────────────────────────────────────────────────────────
#  9. Emergency Alerts
# ─────────────────────────────────────────────────────────────────

async def seed_emergency_alerts(session: AsyncSession):
    log.info("[9/10] Sembrando emergency_alerts...")
    if await table_count(session, "emergency_alerts") > 0:
        log.info("  ↩ emergency_alerts ya existen, saltando")
        return

    devices_r = await session.execute(text("SELECT id, device_code FROM devices ORDER BY id"))
    devices = devices_r.fetchall()

    fsm_states = ["SYSTEM_ERROR", "EMERGENCY"]
    entries = []

    for _ in range(300):
        device = rng.choice(devices)
        days_back = rng.uniform(0, 30)
        ts = ago(days=days_back)
        fsm_state = rng.choice(fsm_states)
        error_count = rng.randint(1, 8)
        state_duration_ms = rng.randint(5000, 120000)
        is_resolved = rng.random() > 0.20

        entries.append({
            "device_id": device.id,
            "node_id": device.device_code,
            "timestamp": ts,
            "error_count": error_count,
            "state_duration_ms": state_duration_ms,
            "fsm_state": fsm_state,
            "payload_snapshot": "{}",
            "resolved": is_resolved,
            "resolved_at": (ts + timedelta(hours=rng.uniform(0.5, 12))) if is_resolved else None,
        })

    for chunk_start in range(0, len(entries), 100):
        chunk = entries[chunk_start:chunk_start + 100]
        await session.execute(text("""
            INSERT INTO emergency_alerts
                (device_id, node_id, timestamp, error_count, state_duration_ms,
                 fsm_state, payload_snapshot, resolved, resolved_at)
            VALUES
                (:device_id, :node_id, :timestamp, :error_count, :state_duration_ms,
                 :fsm_state, CAST(:payload_snapshot AS jsonb), :resolved, :resolved_at)
        """), chunk)

    await session.commit()
    log.info("  ✓ emergency_alerts (300)")


# ─────────────────────────────────────────────────────────────────
#  10. Audit Logs
# ─────────────────────────────────────────────────────────────────

async def seed_audit_logs(session: AsyncSession):
    log.info("[10/10] Sembrando audit_logs...")
    if await table_count(session, "audit_logs") > 0:
        log.info("  ↩ audit_logs ya existen, saltando")
        return

    devices_r = await session.execute(text("SELECT id FROM devices"))
    device_ids = [r.id for r in devices_r.fetchall()]
    users_r = await session.execute(text("SELECT id FROM users"))
    user_ids = [r.id for r in users_r.fetchall()]
    valves_r = await session.execute(text("SELECT id FROM valves"))
    valve_ids = [r.id for r in valves_r.fetchall()]

    actions = [
        ("valve_open",       0.25),
        ("valve_close",      0.25),
        ("alert_resolved",   0.20),
        ("device_updated",   0.15),
        ("user_login",       0.15),
    ]

    entries = []
    TOTAL = 2000
    for _ in range(TOTAL):
        action = rng.choices([a[0] for a in actions], [a[1] for a in actions])[0]
        days_back = rng.uniform(0, 30)
        entries.append({
            "user_id":    rng.choice(user_ids),
            "device_id":  rng.choice(device_ids),
            "valve_id":   rng.choice(valve_ids) if "valve" in action else None,
            "action":     action,
            "payload_json": "{}",
            "ip_address": f"192.168.1.{rng.randint(10, 250)}",
            "created_at": ago(days=days_back),
        })

    for chunk_start in range(0, len(entries), 200):
        chunk = entries[chunk_start:chunk_start + 200]
        await session.execute(text("""
            INSERT INTO audit_logs (user_id, device_id, valve_id, action, payload_json, ip_address, created_at)
            VALUES (:user_id, :device_id, :valve_id, :action, CAST(:payload_json AS jsonb), CAST(:ip_address AS inet), :created_at)
        """), chunk)

    await session.commit()
    log.info(f"  ✓ audit_logs ({TOTAL})")


# ─────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────

async def main():
    log.info("=" * 62)
    log.info("  HYDRO-V — Seed PostgreSQL")
    log.info(f"  DSN: {POSTGRES_DSN.split('@')[1]}")
    log.info("=" * 62)

    async with SessionLocal() as session:
        await seed_catalogs(session)
        await seed_zones(session)
        await seed_devices(session)
        await seed_users(session)
        await seed_sensors_valves(session)
        await seed_device_edges(session)
        await seed_alerts(session)
        await seed_leak_detections(session)
        await seed_emergency_alerts(session)
        await seed_audit_logs(session)

    await engine.dispose()
    log.info("")
    log.info("=" * 62)
    log.info("  ✅ Seed PostgreSQL completado")
    log.info("  Grafana debería mostrar datos en los paneles SQL ahora.")
    log.info("=" * 62)


if __name__ == "__main__":
    asyncio.run(main())
