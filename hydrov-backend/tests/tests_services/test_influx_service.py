# tests/tests_services/test_influx_service.py
"""
Tests unitarios para influx_service.py.

Estrategia:
  - InfluxManager se mockea completamente — sin InfluxDB real
  - Se prueba la lógica de queries y el manejo de errores/defaults
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta


# ─────────────────────────────────────────────────────────────────
#  Fixture: InfluxService con WriteApi y QueryApi mockeados
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def influx_service_mocked():
    """
    Retorna una instancia de InfluxService con el InfluxManager mockeado.
    Evita que el servicio intente conectarse a InfluxDB real.
    """
    from app.services.influx_service import InfluxService

    mock_write = AsyncMock()
    mock_query = AsyncMock()

    with patch("app.services.influx_service.InfluxManager") as mock_mgr:
        mock_mgr.get_write_api.return_value = mock_write
        mock_mgr.get_query_api.return_value = mock_query
        service = InfluxService()
        service._mock_write = mock_write
        service._mock_query = mock_query
        yield service, mock_write, mock_query


# ─────────────────────────────────────────────────────────────────
#  Tests de write_telemetry
# ─────────────────────────────────────────────────────────────────

class TestWriteTelemetry:

    @pytest.mark.asyncio
    async def test_write_telemetry_llama_write_api(self, influx_service_mocked):
        """write_telemetry debe llamar a write_api.write con el bucket correcto."""
        from influxdb_client import Point
        service, mock_write, _ = influx_service_mocked

        point = Point("sensor_telemetry").tag("node_id", "HYDRO-V-001").field("flow_lpm", 1.8)
        mock_write.write = AsyncMock()

        await service.write_telemetry(point)

        mock_write.write.assert_called_once()
        call_kwargs = mock_write.write.call_args[1]
        assert "sensor_telemetry" in call_kwargs.get("bucket", "")

    @pytest.mark.asyncio
    async def test_write_nasa_points_llama_write_api(self, influx_service_mocked):
        """write_nasa_points debe llamar a write_api.write con el bucket NASA."""
        from influxdb_client import Point
        service, mock_write, _ = influx_service_mocked

        points = [
            Point("nasa_weather").tag("lat", "19.41").field("precipitation_mm", 5.3),
        ]
        mock_write.write = AsyncMock()

        await service.write_nasa_points(points)

        mock_write.write.assert_called_once()
        call_kwargs = mock_write.write.call_args[1]
        assert "nasa" in call_kwargs.get("bucket", "").lower()


# ─────────────────────────────────────────────────────────────────
#  Tests de get_avg_daily_consumption
# ─────────────────────────────────────────────────────────────────

class TestGetAvgDailyConsumption:

    @pytest.mark.asyncio
    async def test_retorna_valor_cuando_hay_datos(self, influx_service_mocked):
        """Debe retornar el valor de InfluxDB cuando la query tiene resultados."""
        service, _, mock_query = influx_service_mocked

        mock_record = MagicMock()
        mock_record.get_value.return_value = 185.5

        mock_table = MagicMock()
        mock_table.records = [mock_record]

        mock_query.query = AsyncMock(return_value=[mock_table])

        result = await service.get_avg_daily_consumption("HYDRO-V-001", days=7)
        assert result == pytest.approx(185.5)

    @pytest.mark.asyncio
    async def test_retorna_default_cuando_no_hay_datos(self, influx_service_mocked):
        """Sin datos en InfluxDB debe retornar el default de 150 L/día."""
        service, _, mock_query = influx_service_mocked
        mock_query.query = AsyncMock(return_value=[])

        result = await service.get_avg_daily_consumption("HYDRO-V-999", days=7)
        assert result == 150.0

    @pytest.mark.asyncio
    async def test_retorna_default_cuando_influx_falla(self, influx_service_mocked):
        """Error de conexión a InfluxDB no debe propagar — retorna default."""
        service, _, mock_query = influx_service_mocked
        mock_query.query = AsyncMock(side_effect=Exception("Connection refused"))

        result = await service.get_avg_daily_consumption("HYDRO-V-001", days=7)
        assert result == 150.0


# ─────────────────────────────────────────────────────────────────
#  Tests de get_days_without_rain
# ─────────────────────────────────────────────────────────────────

class TestGetDaysWithoutRain:

    @pytest.mark.asyncio
    async def test_calcula_dias_correctamente(self, influx_service_mocked):
        """Debe calcular los días desde la última lectura de flujo significativo."""
        service, _, mock_query = influx_service_mocked

        # Simular que el último flujo fue hace 5 días
        last_flow_time = datetime.now(timezone.utc) - timedelta(days=5)

        mock_record = MagicMock()
        mock_record.get_time.return_value = last_flow_time

        mock_table = MagicMock()
        mock_table.records = [mock_record]

        mock_query.query = AsyncMock(return_value=[mock_table])

        result = await service.get_days_without_rain("HYDRO-V-001")
        assert result == 5

    @pytest.mark.asyncio
    async def test_retorna_0_cuando_no_hay_historial(self, influx_service_mocked):
        """Sin historial de flujo retorna 0 (conservador)."""
        service, _, mock_query = influx_service_mocked
        mock_query.query = AsyncMock(return_value=[])

        result = await service.get_days_without_rain("HYDRO-V-001")
        assert result == 0

    @pytest.mark.asyncio
    async def test_retorna_0_cuando_influx_falla(self, influx_service_mocked):
        """Error de InfluxDB retorna 0 sin propagar excepción."""
        service, _, mock_query = influx_service_mocked
        mock_query.query = AsyncMock(side_effect=ConnectionError("timeout"))

        result = await service.get_days_without_rain("HYDRO-V-001")
        assert result == 0


# ─────────────────────────────────────────────────────────────────
#  Tests de get_neighbor_nodes_data
# ─────────────────────────────────────────────────────────────────

class TestGetNeighborNodesData:

    @pytest.mark.asyncio
    async def test_retorna_lista_vacia_por_ahora(self, influx_service_mocked):
        """Por diseño, retorna lista vacía hasta que haya múltiples nodos."""
        service, _, _ = influx_service_mocked
        result = await service.get_neighbor_nodes_data("HYDRO-V-001")
        assert result == []
        assert isinstance(result, list)
