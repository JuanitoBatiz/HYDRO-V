# tests/conftest.py
"""
Fixtures globales para la suite de tests de Hydro-V.

Estrategia de testing:
  - DB: SQLite en memoria para tests de API (rápido, sin Docker)
  - Servicios externos (MQTT, InfluxDB, NASA): siempre mockeados con pytest-mock
  - Tests de servicios: unitarios puros con mocks
  - Tests de API: AsyncClient contra la app FastAPI con DB de prueba

Requisitos adicionales (agregar a requirements-dev.txt):
    pytest>=8.0.0
    pytest-asyncio>=0.23.0
    pytest-mock>=3.12.0
    httpx>=0.27.0               # AsyncClient de FastAPI
    aiosqlite>=0.20.0           # SQLite async para tests
"""
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from datetime import datetime, timezone

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from app.main import app
from app.db.base import Base
from app.db.session import AsyncSessionLocal
from app.api.deps import get_db
from app.core.security import hash_password, create_access_token
from app.models.user import User
from app.models.device import Device
from app.models.telemetry import TelemetryEvent
from app.models.alert import EmergencyAlert


# ─────────────────────────────────────────────────────────────────
#  Config de pytest-asyncio
# ─────────────────────────────────────────────────────────────────

pytest_plugins = ["pytest_asyncio"]


# ─────────────────────────────────────────────────────────────────
#  Engine SQLite en memoria para tests
# ─────────────────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─────────────────────────────────────────────────────────────────
#  Fixture: base de datos de prueba (scope=session → una vez por run)
# ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def create_test_db():
    """Crea todas las tablas en SQLite :memory: antes del run completo."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ─────────────────────────────────────────────────────────────────
#  Fixture: sesión de DB por test (scope=function → se limpia sola)
# ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session(create_test_db) -> AsyncGenerator[AsyncSession, None]:
    """
    Provee una AsyncSession de prueba con rollback automático al final.
    Cada test ve la DB limpia gracias al rollback.
    """
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


# ─────────────────────────────────────────────────────────────────
#  Override de la dependencia get_db para los tests de API
# ─────────────────────────────────────────────────────────────────

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─────────────────────────────────────────────────────────────────
#  Fixture: AsyncClient con la app y la DB de prueba
# ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(create_test_db) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP async para tests de endpoints FastAPI.
    La DB está sobreescrita con SQLite :memory:.
    InfluxDB, MQTT y Redis deben mockearse en cada test.
    """
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────
#  Fixtures de datos de prueba
# ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Usuario de prueba con contraseña hasheada."""
    user = User(
        email="test@hydrov.mx",
        name="Test User",
        hashed_password=hash_password("password123"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_superuser(db_session: AsyncSession) -> User:
    """Superusuario de prueba."""
    user = User(
        email="admin@hydrov.mx",
        name="Admin User",
        hashed_password=hash_password("admin1234"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_device(db_session: AsyncSession) -> Device:
    """Nodo Hydro-V de prueba."""
    device = Device(
        device_id="HYDRO-V-001",
        name="Nodo Prueba Neza",
        lat=19.4136,
        lon=-99.0151,
        location="Nezahualcóyotl, CDMX",
        roof_area_m2=45.0,
        is_active=True,
    )
    db_session.add(device)
    await db_session.flush()
    await db_session.refresh(device)
    return device


@pytest_asyncio.fixture
async def test_telemetry_event(
    db_session: AsyncSession,
    test_device: Device,
) -> TelemetryEvent:
    """Evento de telemetría de prueba asociado al nodo de prueba."""
    event = TelemetryEvent(
        device_id=test_device.device_id,
        received_at=datetime.now(timezone.utc),
        turbidity_ntu=4.2,
        distance_cm=35.0,
        flow_lpm=1.8,
        flow_total_liters=120.5,
        state="HARVESTING",
        state_duration_ms=5000,
        intake_cycles=3,
        reject_cycles=1,
        error_count=0,
        esp32_uptime_ms=120000,
    )
    db_session.add(event)
    await db_session.flush()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def test_alert(
    db_session: AsyncSession,
    test_device: Device,
) -> EmergencyAlert:
    """Alerta de emergencia de prueba."""
    alert = EmergencyAlert(
        node_id=test_device.device_id,
        timestamp=datetime.now(timezone.utc),
        error_count=5,
        state_duration_ms=30000,
        payload_snapshot={"device_id": "HYDRO-V-001", "error": "sensor_failure"},
        resolved=False,
    )
    db_session.add(alert)
    await db_session.flush()
    await db_session.refresh(alert)
    return alert


# ─────────────────────────────────────────────────────────────────
#  Fixture: JWT tokens listos para usar en headers
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Headers de autorización para el usuario de prueba."""
    token = create_access_token(subject=test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(test_superuser: User) -> dict:
    """Headers de autorización para el admin de prueba."""
    token = create_access_token(subject=test_superuser.id)
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────
#  Payload de prueba del ESP32 (reutilizable en múltiples tests)
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def esp32_payload_valid() -> dict:
    """JSON válido tal como lo envía el ESP32 vía MQTT."""
    return {
        "device_id": "HYDRO-V-001",
        "timestamp": 120000,
        "sensors": {
            "turbidity_ntu": "4.20",
            "distance_cm":   "35.0",
            "flow_lpm":      "1.80",
            "flow_total_liters": "120.5",
        },
        "system_state": {
            "state":             "HARVESTING",
            "state_duration_ms": 5000,
            "intake_cycles":     3,
            "reject_cycles":     1,
            "error_count":       0,
        },
    }


@pytest.fixture
def esp32_payload_emergency() -> dict:
    """Payload de prueba con estado EMERGENCY."""
    return {
        "device_id": "HYDRO-V-001",
        "timestamp": 300000,
        "sensors": {
            "turbidity_ntu": "999.0",
            "distance_cm":   "0.0",
            "flow_lpm":      "0.0",
            "flow_total_liters": "120.5",
        },
        "system_state": {
            "state":             "EMERGENCY",
            "state_duration_ms": 30000,
            "intake_cycles":     5,
            "reject_cycles":     10,
            "error_count":       7,
        },
    }
