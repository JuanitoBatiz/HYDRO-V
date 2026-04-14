#!/usr/bin/env python3
"""
seed_redis_gnn.py — Inserta estados simulados de nodos vecinos en Redis para activar la GNN.

DOBLE-WRITE: Escribe en dos key patterns para satisfacer todos los consumers:
  - device:state:{code}   → usada por influx_service.get_neighbor_nodes_data()
  - sensor:latest:{code}  → usada por predictions.py endpoints /leaks y /autonomy

Ejecutar: python seed_redis_gnn.py
"""
import redis
import json
from datetime import datetime, timezone

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# ── Nodo HYDRO-V-002: Estado NORMAL (vecino saludable) ──────────────────────
estado_002 = {
    "device_id": "HYDRO-V-002",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "sensors": {
        "turbidity_ntu": "12.5",
        "distance_cm": "75.0",
        "flow_lpm": "0.80",
        "flow_total_liters": "45.20",
        "dtdt": "-0.50"
    },
    "system_state": {
        "state": "IDLE",
        "state_duration_ms": 120000,
        "intake_cycles": 8,
        "reject_cycles": 2,
        "error_count": 0
    },
    "tank_level_pct": 37.5   # (1 - 75/120) * 100
}

# ── Nodo HYDRO-V-003: Estado FUGA (flujo alto + nivel bajo) ─────────────────
# ANÁLISIS de features del LeakDetectorMLP (_physics_score fallback):
#   flow_lpm=9.5 > 6.0  AND  level_pct=11.7 < 30.0  → score += 0.50
#   flow_diff = |9.5 - 0.80| = 8.7 > 4.0             → score += 0.25
#   level_pct=11.7 > 10.0                              → +0.00 (no activa ese umbral)
#   level_diff = 11.7 - 37.5 = -25.8 < -15.0          → score += 0.15
#   score final = 0.90 → severity=ALTA, leak_detected=true
estado_003 = {
    "device_id": "HYDRO-V-003",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "sensors": {
        "turbidity_ntu": "8.0",
        "distance_cm": "172.0",    # → level_pct = (1 - 172/200)*100 = 14.0%  (cálculo del endpoint)
        "flow_lpm": "9.50",        # Flujo MUY alto → señal de fuga
        "flow_total_liters": "12.80",
        "dtdt": "0.20"
    },
    "system_state": {
        "state": "INTAKE",
        "state_duration_ms": 890000,
        "intake_cycles": 1,
        "reject_cycles": 0,
        "error_count": 0
    },
    "tank_level_pct": 11.7   # valor explícito para neighbor queries (influx_service)
}

ttl = 600  # 10 minutos — suficiente para la demo ante el jurado

# ── Escritura en device:state:{code} → usada por influx_service.get_neighbor_nodes_data()
r.setex("device:state:HYDRO-V-002", ttl, json.dumps(estado_002))
r.setex("device:state:HYDRO-V-003", ttl, json.dumps(estado_003))
print("✅ device:state:HYDRO-V-002 — escrito en Redis")
print("✅ device:state:HYDRO-V-003 — escrito en Redis")

# ── Escritura en sensor:latest:{code} → usada por predictions.py /leaks y /autonomy
r.setex("sensor:latest:HYDRO-V-002", ttl, json.dumps(estado_002))
r.setex("sensor:latest:HYDRO-V-003", ttl, json.dumps(estado_003))
print("✅ sensor:latest:HYDRO-V-002 — escrito en Redis")
print("✅ sensor:latest:HYDRO-V-003 — escrito en Redis")

print()
print(f"TTL: {ttl} segundos ({ttl // 60} minutos) — mismo para los 4 keys")
print()
print("Verificar con:")
print('  redis-cli keys "device:state:HYDRO-V-00*"')
print('  redis-cli keys "sensor:latest:HYDRO-V-00*"')
print()
print("Endpoint de prueba (necesita TOKEN):")
print('  curl -s "http://localhost:8000/api/v1/predictions/HYDRO-V-003/leaks" \\')
print('    -H "Authorization: Bearer $TOKEN" | python -m json.tool')
