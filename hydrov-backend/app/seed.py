"""
Seed de catálogos Hydro-V — Arquitectura v2.0
Idempotente: verifica existencia antes de insertar.
Se ejecuta en el lifespan de FastAPI.
"""

async def run_seed(db):
    """
    Recibe una sesión de base de datos asyncpg.
    Guard: solo inserta si la tabla está vacía.
    """

    # --- ROLES ---
    roles_count = await db.fetchval("SELECT COUNT(*) FROM roles")
    if roles_count == 0:
        await db.executemany(
            "INSERT INTO roles (name, description) VALUES ($1, $2)",
            [
                ("admin",    "Acceso total. Gestiona usuarios, zonas y dispositivos."),
                ("operator", "Puede comandar válvulas y resolver alertas. No gestiona usuarios."),
                ("viewer",   "Solo lectura dentro de su zona asignada."),
            ]
        )

    # --- SENSOR TYPES ---
    st_count = await db.fetchval("SELECT COUNT(*) FROM sensor_types")
    if st_count == 0:
        await db.executemany(
            "INSERT INTO sensor_types (name, unit, description) VALUES ($1, $2, $3)",
            [
                ("turbidity", "NTU",   "Sensor Gravity analógico. Rango 0-3000 NTU. Pin ADC1 ESP32."),
                ("flow",      "L/min", "Caudalímetro YF-S201. 450 pulsos/litro. Interrupción HW."),
                ("level",     "cm",    "Ultrasónico JSN-SR04T impermeable. Rango 20-450 cm."),
            ]
        )

    # --- VALVE TYPES ---
    vt_count = await db.fetchval("SELECT COUNT(*) FROM valve_types")
    if vt_count == 0:
        await db.executemany(
            "INSERT INTO valve_types (name, default_state, description) VALUES ($1, $2, $3)",
            [
                ("rejection", "closed", "Válvula de Rechazo (VR). Activa en ANALYZING. NC 12V DC."),
                ("admission", "closed", "Válvula de Admisión (VA). Activa en HARVESTING. NC 12V DC."),
            ]
        )

    # --- ALERT TYPES ---
    at_count = await db.fetchval("SELECT COUNT(*) FROM alert_types")
    if at_count == 0:
        await db.executemany(
            "INSERT INTO alert_types (name, default_severity, description) VALUES ($1, $2, $3)",
            [
                ("turbidity_spike",    "high",     "Turbidez supera umbral crítico (>500 NTU). FSM → ANALYZING."),
                ("turbidity_stable_ok","low",      "Turbidez estabilizada bajo umbral. FSM → HARVESTING. Alerta de resolución positiva."),
                ("flow_anomaly",       "medium",   "Caudal inconsistente con estado FSM (flujo detectado con válvulas cerradas)."),
                ("level_critical_low", "high",     "Nivel de cisterna por debajo del 10%."),
                ("level_full",         "low",      "Cisterna ≥95%. FSM → FULL_TANK. Válvulas se cierran."),
                ("pressure_drop",      "high",     "Caída de presión detectada en grafo de red (GNN). Posible fuga inminente."),
                ("leak_detected",      "critical", "Fuga confirmada por correlación de anomalías entre nodos vecinos (GNN)."),
                ("sensor_failure",     "critical", "Lectura fuera de rango operativo. FSM → EMERGENCY."),
                ("emergency",          "critical", "Estado EMERGENCY en FSM. Cierre total de seguridad."),
                ("device_offline",     "high",     "Sin heartbeat por más de 5 minutos."),
            ]
        )
