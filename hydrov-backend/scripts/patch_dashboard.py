#!/usr/bin/env python3
"""
Parchea el dashboard hydrov_node_deep_dive.json corrigiendo:
  1. device_id → device_code en todos los filtros Flux
  2. fsm_state (tag) → campo numérico fsm_state_num para state-timeline
  3. intake_cycles/reject_cycles → measurement device_state (no sensor_reading)
  4. dtdt → dtdt_value (nombre real del field en InfluxDB)
  5. Válvula: INTAKE → HARVESTING (nombre real del estado FSM)

Uso:
    python scripts/patch_dashboard.py
"""
import json
import sys
from pathlib import Path

DASHBOARD_PATH = Path(__file__).parent.parent.parent / "infra" / "grafana" / "dashboards" / "hydrov_node_deep_dive.json"

def patch(dashboard: dict) -> dict:
    for panel in dashboard.get("panels", []):
        title = panel.get("title", "")
        for target in panel.get("targets", []):
            q = target.get("query", "")

            # ── Fix universal: device_id → device_code ─────────────
            q = q.replace('r.device_id == \\"${device_id}\\"',
                           'r.device_code == \\"${device_id}\\"')
            # variante sin escapes dobles (por si acaso)
            q = q.replace("r.device_id ==", "r.device_code ==")

            # ── Panel 1: Timeline FSM ──────────────────────────────
            # El state-timeline de Grafana necesita un field STRING (no tag).
            # Añadimos map() para promover fsm_state (tag) a field de string.
            if "Timeline" in title or "FSM" in title:
                # Reemplaza el filtro de fsm_state (que es un tag, no field)
                # por una versión que usa el field fsm_state_num
                q = (
                    'from(bucket: "sensor_telemetry")\n'
                    '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
                    '  |> filter(fn: (r) => r._measurement == "device_state")\n'
                    '  |> filter(fn: (r) => r.device_code == "${device_id}")\n'
                    '  |> filter(fn: (r) => r._field == "fsm_state_num")\n'
                    '  |> aggregateWindow(every: v.windowPeriod, fn: last, createEmpty: false)\n'
                    '  |> fill(usePrevious: true)\n'
                    '  |> yield(name: "fsm_state")'
                )

            # ── Panel 2: Estadísticas de Sesión ───────────────────
            elif "Estadísticas" in title or "Estadistica" in title:
                q = (
                    'from(bucket: "sensor_telemetry")\n'
                    '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
                    '  |> filter(fn: (r) => r._measurement == "sensor_reading")\n'
                    '  |> filter(fn: (r) => r.device_code == "${device_id}")\n'
                    '  |> filter(fn: (r) => r._field == "turbidity_ntu" or r._field == "flow_lpm" or r._field == "flow_total_liters")\n'
                    '  |> group(columns: ["_field"])\n'
                    '  |> reduce(\n'
                    '      fn: (r, accumulator) => ({\n'
                    '          min:   (r._value < accumulator.min) ? r._value : accumulator.min,\n'
                    '          max:   (r._value > accumulator.max) ? r._value : accumulator.max,\n'
                    '          sum:   accumulator.sum + r._value,\n'
                    '          count: accumulator.count + 1.0\n'
                    '      }),\n'
                    '      identity: {min: 9999.0, max: -9999.0, sum: 0.0, count: 0.0}\n'
                    '  )\n'
                    '  |> map(fn: (r) => ({r with mean: r.sum / r.count}))'
                )

            # ── Panel 3: Eficiencia de Captación ──────────────────
            elif "Eficiencia" in title:
                q = (
                    'intake = from(bucket: "sensor_telemetry")\n'
                    '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
                    '  |> filter(fn: (r) => r._measurement == "device_state")\n'
                    '  |> filter(fn: (r) => r.device_code == "${device_id}")\n'
                    '  |> filter(fn: (r) => r._field == "intake_cycles")\n'
                    '  |> last()\n\n'
                    'reject = from(bucket: "sensor_telemetry")\n'
                    '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
                    '  |> filter(fn: (r) => r._measurement == "device_state")\n'
                    '  |> filter(fn: (r) => r.device_code == "${device_id}")\n'
                    '  |> filter(fn: (r) => r._field == "reject_cycles")\n'
                    '  |> last()\n\n'
                    'join(\n'
                    '  tables: {intake: intake, reject: reject},\n'
                    '  on: ["device_code"]\n'
                    ')\n'
                    '  |> map(fn: (r) => ({\n'
                    '      _time: r._time_intake,\n'
                    '      _value: if (r._value_intake + r._value_reject) > 0.0\n'
                    '              then r._value_intake / (r._value_intake + r._value_reject) * 100.0\n'
                    '              else 0.0\n'
                    '  }))'
                )

            # ── Panel 4: Comparativa Turbidez vs Flujo ────────────
            elif "Turbidez" in title and "Flujo" in title:
                ref = target.get("refId", "A")
                if ref == "A":
                    q = (
                        'from(bucket: "sensor_telemetry")\n'
                        '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
                        '  |> filter(fn: (r) => r._measurement == "sensor_reading")\n'
                        '  |> filter(fn: (r) => r._field == "turbidity_ntu")\n'
                        '  |> filter(fn: (r) => r.device_code == "${device_id}")\n'
                        '  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)'
                    )
                else:
                    q = (
                        'from(bucket: "sensor_telemetry")\n'
                        '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
                        '  |> filter(fn: (r) => r._measurement == "sensor_reading")\n'
                        '  |> filter(fn: (r) => r._field == "flow_lpm")\n'
                        '  |> filter(fn: (r) => r.device_code == "${device_id}")\n'
                        '  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)'
                    )

            # ── Panel 5: Análisis dT/dt ────────────────────────────
            elif "dT/dt" in title or "Adaptativa" in title or "Decisión" in title:
                ref = target.get("refId", "A")
                if ref == "A":
                    q = (
                        'from(bucket: "sensor_telemetry")\n'
                        '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
                        '  |> filter(fn: (r) => r._measurement == "sensor_reading")\n'
                        '  |> filter(fn: (r) => r.device_code == "${device_id}")\n'
                        '  |> filter(fn: (r) => r._field == "dtdt_value")\n'
                        '  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)\n'
                        '  |> yield(name: "dT/dt")'
                    )
                else:
                    q = (
                        'from(bucket: "sensor_telemetry")\n'
                        '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
                        '  |> filter(fn: (r) => r._measurement == "device_state")\n'
                        '  |> filter(fn: (r) => r.device_code == "${device_id}")\n'
                        '  |> filter(fn: (r) => r._field == "fsm_state_num")\n'
                        '  |> map(fn: (r) => ({ r with _value: if r._value == 2.0 then 1.0 else 0.0 }))\n'
                        '  |> aggregateWindow(every: v.windowPeriod, fn: last, createEmpty: false)\n'
                        '  |> yield(name: "Valvula")'
                    )

            target["query"] = q

    return dashboard


if __name__ == "__main__":
    print(f"Parcheando: {DASHBOARD_PATH}")
    with open(DASHBOARD_PATH, "r", encoding="utf-8") as f:
        dash = json.load(f)

    dash = patch(dash)

    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        json.dump(dash, f, indent=2, ensure_ascii=False)

    print("✅ Dashboard parcheado correctamente.")
    print("   Reinicia Grafana para cargar los cambios:")
    print("   docker compose restart grafana")
