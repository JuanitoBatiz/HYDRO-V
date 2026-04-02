import os

base_dir = r"c:\Users\jesus\OneDrive\Desktop\HYDRO-V\hydrov-backend\app\models"
os.makedirs(base_dir, exist_ok=True)

# Eliminar modelos viejos (prediction, telemetry si existen)
for old in ["prediction.py", "telemetry.py"]:
    ob = os.path.join(base_dir, old)
    if os.path.exists(ob):
        os.remove(ob)

def w(name, content):
    with open(os.path.join(base_dir, name), "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

w("zone.py", """
from sqlalchemy import Integer, String, Float, DateTime, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime

class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    municipality: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, CheckConstraint("latitude >= -90 AND latitude <= 90"), nullable=False)
    longitude: Mapped[float] = mapped_column(Float, CheckConstraint("longitude >= -180 AND longitude <= 180"), nullable=False)
    population: Mapped[int | None] = mapped_column(Integer, CheckConstraint("population > 0"), nullable=True)
    area_km2: Mapped[float | None] = mapped_column(Float, CheckConstraint("area_km2 > 0"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
""")

w("device.py", """
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, CheckConstraint, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime
from sqlalchemy.sql import func

class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False, index=True)
    device_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, CheckConstraint("latitude >= -90 AND latitude <= 90"), nullable=False)
    longitude: Mapped[float] = mapped_column(Float, CheckConstraint("longitude >= -180 AND longitude <= 180"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), CheckConstraint("status IN ('active', 'inactive', 'maintenance')"), nullable=False, index=True)
    firmware_version: Mapped[str] = mapped_column(String(20), nullable=False)
    cistern_capacity_liters: Mapped[float] = mapped_column(Float, CheckConstraint("cistern_capacity_liters > 0"), default=1100.0, nullable=False)
    cistern_height_cm: Mapped[float] = mapped_column(Float, CheckConstraint("cistern_height_cm > 0"), default=120.0, nullable=False)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

class DeviceEdge(Base):
    __tablename__ = "device_edges"
    __table_args__ = (
        CheckConstraint("source_device_id <> target_device_id", name="chk_no_self_edge"),
        UniqueConstraint("source_device_id", "target_device_id", name="idx_device_edges_unique")
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    target_device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    is_bidirectional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pipe_diameter_mm: Mapped[float | None] = mapped_column(Float, CheckConstraint("pipe_diameter_mm > 0"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
""")

w("sensor_type.py", """
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class SensorType(Base):
    __tablename__ = "sensor_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
""")

w("sensor.py", """
from sqlalchemy import Integer, Boolean, Float, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime

class Sensor(Base):
    __tablename__ = "sensors"
    __table_args__ = (
        CheckConstraint("min_threshold <= max_threshold", name="chk_sensor_thresholds"),
        UniqueConstraint("device_id", "sensor_type_id", name="idx_sensors_device_type")
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    sensor_type_id: Mapped[int] = mapped_column(ForeignKey("sensor_types.id"), nullable=False)
    min_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    max_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
""")

w("valve_type.py", """
from sqlalchemy import Integer, String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class ValveType(Base):
    __tablename__ = "valve_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    default_state: Mapped[str] = mapped_column(String(10), CheckConstraint("default_state IN ('open', 'closed')"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
""")

w("valve.py", """
from sqlalchemy import Integer, String, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime

class Valve(Base):
    __tablename__ = "valves"
    __table_args__ = (
        UniqueConstraint("device_id", "valve_type_id", name="idx_valves_device_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    valve_type_id: Mapped[int] = mapped_column(ForeignKey("valve_types.id"), nullable=False)
    current_state: Mapped[str] = mapped_column(String(10), CheckConstraint("current_state IN ('open', 'closed')"), default="closed", nullable=False)
    last_commanded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
""")

w("alert_type.py", """
from sqlalchemy import Integer, String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AlertType(Base):
    __tablename__ = "alert_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    default_severity: Mapped[str] = mapped_column(String(20), CheckConstraint("default_severity IN ('low', 'medium', 'high', 'critical')"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
""")

w("alert.py", """
from sqlalchemy import Integer, String, Float, Text, Boolean, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime
from sqlalchemy.sql import func

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    sensor_id: Mapped[int | None] = mapped_column(ForeignKey("sensors.id"), nullable=True)
    alert_type_id: Mapped[int] = mapped_column(ForeignKey("alert_types.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')"), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_snapshot: Mapped[dict] = mapped_column(JSONB, server_default='{}', nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

Index("idx_alerts_active", Alert.device_id, postgresql_where=(Alert.is_resolved == False))
Index("idx_alerts_payload", Alert.payload_snapshot, postgresql_using="gin")
""")

w("role.py", """
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
""")

w("user.py", """
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

Index("idx_users_active", User.is_active, postgresql_where=(User.is_active == True))
""")

w("audit_log.py", """
from sqlalchemy import BigInteger, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime
from sqlalchemy.sql import func

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    valve_id: Mapped[int | None] = mapped_column(ForeignKey("valves.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSONB, server_default='{}', nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

Index("idx_audit_payload", AuditLog.payload_json, postgresql_using="gin")
""")

w("__init__.py", """
from .zone import Zone
from .role import Role
from .sensor_type import SensorType
from .valve_type import ValveType
from .alert_type import AlertType
from .device import Device, DeviceEdge
from .user import User
from .sensor import Sensor
from .valve import Valve
from .alert import Alert
from .audit_log import AuditLog
""")

with open(r"c:\\Users\\jesus\\OneDrive\\Desktop\\HYDRO-V\\hydrov-backend\\app\\seed.py", "w", encoding="utf-8") as f:
    f.write('''"""
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
''')
