import json
from pathlib import Path

DASH = Path('infra/grafana/dashboards/hydrov_mission_control.json')
d = json.loads(DASH.read_text(encoding='utf-8'))

for p in d['panels']:
    title = p.get('title', '')
    for t in p.get('targets', []):
        q = t.get('query', '')
        if not q:
            continue

        # ── Fix 1: device_id → device_code (universal) ─────────────────
        q = q.replace('r.device_id ==', 'r.device_code ==')

        # ── Fix 2: Estado del Sistema — fsm_state es TAG, usar fsm_state_num
        if 'Estado del Sistema' in title:
            q = (
                'from(bucket: "sensor_telemetry")\n'
                '  |> range(start: -2m)\n'
                '  |> filter(fn: (r) => r._measurement == "device_state")\n'
                '  |> filter(fn: (r) => r.device_code == "${device_id}")\n'
                '  |> filter(fn: (r) => r._field == "fsm_state_num")\n'
                '  |> last()'
            )

        # ── Fix 3: Ciclos de Válvulas — intake/reject están en device_state
        elif 'Ciclos' in title:
            ref = t.get('refId', 'A')
            field = 'intake_cycles' if ref == 'A' else 'reject_cycles'
            q = (
                f'from(bucket: "sensor_telemetry")\n'
                f'  |> range(start: -2m)\n'
                f'  |> filter(fn: (r) => r._measurement == "device_state")\n'
                f'  |> filter(fn: (r) => r.device_code == "${{device_id}}")\n'
                f'  |> filter(fn: (r) => r._field == "{field}")\n'
                f'  |> last()'
            )

        # ── Fix 4: Tiempo en Cada Estado FSM — state_duration_ms en device_state
        elif 'Tiempo en Cada Estado' in title or 'Estado FSM' in title:
            q = (
                'from(bucket: "sensor_telemetry")\n'
                '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
                '  |> filter(fn: (r) => r._measurement == "device_state")\n'
                '  |> filter(fn: (r) => r.device_code == "${device_id}")\n'
                '  |> filter(fn: (r) => r._field == "state_duration_ms")\n'
                '  |> group(columns: ["fsm_state"])\n'
                '  |> sum()'
            )

        # ── Fix 5: Nivel de Cisterna — ajuste del map con cistern_height correcto
        elif 'Nivel de Cisterna' in title:
            q = (
                'from(bucket: "sensor_telemetry")\n'
                '  |> range(start: -2m)\n'
                '  |> filter(fn: (r) => r._measurement == "sensor_reading")\n'
                '  |> filter(fn: (r) => r.device_code == "${device_id}")\n'
                '  |> filter(fn: (r) => r._field == "distance_cm")\n'
                '  |> last()\n'
                '  |> map(fn: (r) => ({r with _value: (1.0 - r._value / 125.0) * 100.0}))'
            )

        # ── Fix genérico para paneles de timeseries (range largo) ──────
        elif 'range(start: -1m)' in q:
            q = q.replace('range(start: -1m)', 'range(start: -5m)')
        elif 'range(start: -5m)' in q:
            pass  # ok

        t['query'] = q

DASH.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding='utf-8')
print("OK: hydrov_mission_control.json parcheado")
