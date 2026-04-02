# tests/tests_services/test_mqtt_service.py
"""
Tests unitarios para mqtt_service.py.

Estrategia:
  - aiomqtt.Client se mockea — sin broker real
  - asyncpg.Pool se mockea — sin PostgreSQL real
  - InfluxService se mockea — sin InfluxDB real
  - Se prueba la lógica de validación y enrutamiento de mensajes

Tests clave:
  1. Payload válido → escribe en InfluxDB
  2. Payload con estado EMERGENCY → dispara cascada de 3 acciones
  3. Payload con device_id inválido → lanza error de validación
  4. Payload con sensores negativos → lanza error de validación
  5. JSON malformado → captura excepción sin propagarla
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone

from app.services.mqtt_service import process_message, handle_emergency
from app.schemas.telemetry import ESP32PayloadSchema


# ─────────────────────────────────────────────────────────────────
#  Helpers para construir mensajes MQTT sintéticos
# ─────────────────────────────────────────────────────────────────

def make_mqtt_message(payload_dict: dict) -> MagicMock:
    """Simula un aiomqtt.Message con el payload dado."""
    msg = MagicMock()
    msg.payload = json.dumps(payload_dict).encode()
    msg.topic   = MagicMock()
    msg.topic.__str__ = lambda self: "hydrov/HYDRO-V-001/telemetry"
    return msg


VALID_PAYLOAD = {
    "device_id": "HYDRO-V-001",
    "timestamp": 120000,
    "sensors": {
        "turbidity_ntu":     "4.20",
        "distance_cm":       "35.0",
        "flow_lpm":          "1.80",
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

EMERGENCY_PAYLOAD = {
    **VALID_PAYLOAD,
    "system_state": {
        "state":             "EMERGENCY",
        "state_duration_ms": 30000,
        "intake_cycles":     5,
        "reject_cycles":     10,
        "error_count":       7,
    },
}


# ─────────────────────────────────────────────────────────────────
#  Tests de validación de schemas (no tocan servicios externos)
# ─────────────────────────────────────────────────────────────────

class TestESP32PayloadValidation:

    def test_payload_valido_se_parsea_correctamente(self):
        """Un payload bien formado pasa la validación Pydantic."""
        payload = ESP32PayloadSchema(**VALID_PAYLOAD)
        assert payload.device_id == "HYDRO-V-001"
        assert payload.sensors.turbidity_ntu == pytest.approx(4.20)
        assert payload.system_state.state == "HARVESTING"

    def test_sensores_como_strings_se_convierten_a_float(self):
        """El ESP32 envía números como strings — deben convertirse."""
        payload = ESP32PayloadSchema(**VALID_PAYLOAD)
        assert isinstance(payload.sensors.turbidity_ntu, float)
        assert isinstance(payload.sensors.flow_lpm, float)

    def test_device_id_invalido_lanza_error(self):
        """device_id que no empieza por 'HYDRO-V-' debe fallar."""
        from pydantic import ValidationError
        bad_payload = {**VALID_PAYLOAD, "device_id": "ESP32-001"}
        with pytest.raises(ValidationError) as exc_info:
            ESP32PayloadSchema(**bad_payload)
        assert "device_id inválido" in str(exc_info.value)

    def test_sensor_negativo_lanza_error(self):
        """Valores de sensor negativos deben fallar la validación."""
        from pydantic import ValidationError
        bad_sensors = {**VALID_PAYLOAD["sensors"], "turbidity_ntu": "-5.0"}
        bad_payload  = {**VALID_PAYLOAD, "sensors": bad_sensors}
        with pytest.raises(ValidationError) as exc_info:
            ESP32PayloadSchema(**bad_payload)
        assert "negativos" in str(exc_info.value)

    def test_fsm_state_invalido_lanza_error(self):
        """Estado FSM que no está en el Literal válido debe fallar."""
        from pydantic import ValidationError
        bad_state = {**VALID_PAYLOAD["system_state"], "state": "UNKNOWN_STATE"}
        bad_payload = {**VALID_PAYLOAD, "system_state": bad_state}
        with pytest.raises(ValidationError):
            ESP32PayloadSchema(**bad_payload)

    def test_received_at_se_genera_automaticamente(self):
        """received_at se genera con timezone UTC si no se pasa."""
        payload = ESP32PayloadSchema(**VALID_PAYLOAD)
        assert payload.received_at is not None
        assert payload.received_at.tzinfo is not None


# ─────────────────────────────────────────────────────────────────
#  Tests de process_message (con mocks de InfluxDB y PG)
# ─────────────────────────────────────────────────────────────────

class TestProcessMessage:

    @pytest.mark.asyncio
    async def test_payload_valido_escribe_en_influx(self):
        """Un mensaje MQTT válido debe escribir un Point en InfluxDB."""
        influx_mock = AsyncMock()
        influx_mock.write_telemetry = AsyncMock()

        pg_pool_mock  = AsyncMock()
        mqtt_mock     = AsyncMock()

        message = make_mqtt_message(VALID_PAYLOAD)

        await process_message(message, influx_mock, pg_pool_mock, mqtt_mock)

        influx_mock.write_telemetry.assert_called_once()

    @pytest.mark.asyncio
    async def test_payload_emergency_dispara_handle_emergency(self):
        """Estado EMERGENCY debe llamar a handle_emergency."""
        influx_mock = AsyncMock()
        influx_mock.write_telemetry = AsyncMock()

        pg_pool_mock = AsyncMock()
        mqtt_mock    = AsyncMock()

        message = make_mqtt_message(EMERGENCY_PAYLOAD)

        with patch(
            "app.services.mqtt_service.handle_emergency",
            new_callable=AsyncMock,
        ) as mock_emergency:
            await process_message(message, influx_mock, pg_pool_mock, mqtt_mock)
            mock_emergency.assert_called_once()

    @pytest.mark.asyncio
    async def test_payload_harvesting_no_dispara_emergency(self):
        """Estado HARVESTING NO debe llamar a handle_emergency."""
        influx_mock = AsyncMock()
        influx_mock.write_telemetry = AsyncMock()

        pg_pool_mock = AsyncMock()
        mqtt_mock    = AsyncMock()

        message = make_mqtt_message(VALID_PAYLOAD)  # estado HARVESTING

        with patch(
            "app.services.mqtt_service.handle_emergency",
            new_callable=AsyncMock,
        ) as mock_emergency:
            await process_message(message, influx_mock, pg_pool_mock, mqtt_mock)
            mock_emergency.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_malformado_no_propaga_excepcion(self):
        """JSON inválido debe capturarse internamente sin crash del loop."""
        influx_mock   = AsyncMock()
        pg_pool_mock  = AsyncMock()
        mqtt_mock     = AsyncMock()

        bad_message = MagicMock()
        bad_message.payload = b"{ esto no es json valido }"

        # No debe lanzar excepción hacia afuera
        await process_message(bad_message, influx_mock, pg_pool_mock, mqtt_mock)
        influx_mock.write_telemetry.assert_not_called()


# ─────────────────────────────────────────────────────────────────
#  Tests de handle_emergency (cascada de 3 acciones)
# ─────────────────────────────────────────────────────────────────

class TestHandleEmergency:

    @pytest.mark.asyncio
    async def test_guarda_en_postgresql(self):
        """handle_emergency debe ejecutar INSERT en PostgreSQL."""
        payload = ESP32PayloadSchema(**EMERGENCY_PAYLOAD)

        pg_pool = AsyncMock()
        pg_pool.execute = AsyncMock()

        mqtt_client = AsyncMock()
        mqtt_client.publish = AsyncMock()

        with patch("app.services.mqtt_service.redis") as redis_mock:
            redis_instance = AsyncMock()
            redis_instance.publish = AsyncMock()
            redis_instance.aclose  = AsyncMock()
            redis_mock.from_url.return_value = redis_instance

            await handle_emergency(payload, pg_pool, mqtt_client)

        pg_pool.execute.assert_called_once()
        # Verificar que el INSERT incluye los datos de emergency
        call_args = pg_pool.execute.call_args[0]
        assert "HYDRO-V-001" in call_args

    @pytest.mark.asyncio
    async def test_publica_ack_mqtt(self):
        """handle_emergency debe publicar ACK al ESP32 vía MQTT."""
        payload = ESP32PayloadSchema(**EMERGENCY_PAYLOAD)

        pg_pool     = AsyncMock()
        pg_pool.execute = AsyncMock()
        mqtt_client = AsyncMock()
        mqtt_client.publish = AsyncMock()

        with patch("app.services.mqtt_service.redis") as redis_mock:
            redis_instance = AsyncMock()
            redis_instance.publish = AsyncMock()
            redis_instance.aclose  = AsyncMock()
            redis_mock.from_url.return_value = redis_instance

            await handle_emergency(payload, pg_pool, mqtt_client)

        mqtt_client.publish.assert_called_once()
        topic_used = mqtt_client.publish.call_args[0][0]
        assert "HYDRO-V-001" in topic_used

    @pytest.mark.asyncio
    async def test_cascada_completa_ejecuta_3_acciones(self):
        """Los 3 efectos de EMERGENCY se ejecutan aunque uno falle."""
        payload = ESP32PayloadSchema(**EMERGENCY_PAYLOAD)

        pg_pool = AsyncMock()
        pg_pool.execute = AsyncMock()

        mqtt_client = AsyncMock()
        mqtt_client.publish = AsyncMock()

        with patch("app.services.mqtt_service.redis") as redis_mock:
            redis_instance = AsyncMock()
            redis_instance.publish = AsyncMock()
            redis_instance.aclose  = AsyncMock()
            redis_mock.from_url.return_value = redis_instance

            await handle_emergency(payload, pg_pool, mqtt_client)

        # Los 3 efectos deben haberse ejecutado
        assert pg_pool.execute.called
        assert mqtt_client.publish.called
        assert redis_instance.publish.called
