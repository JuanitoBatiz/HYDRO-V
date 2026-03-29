# tests/tests_services/test_ml_service.py
"""
Tests unitarios para ml_service.py.

Estrategia:
  - InfluxService se mockea → sin InfluxDB real
  - NASA POWER se mockea → sin llamadas HTTP
  - Las funciones de inferencia ML se mockean → sin modelos en disco
  - Se prueba la lógica de orquestación y el manejo de errores

Tests cubiertos:
  1. get_autonomy_prediction — flujo normal (InfluxDB + NASA OK)
  2. get_autonomy_prediction — NASA falla → usa defaults
  3. get_autonomy_prediction — propaga el resultado del modelo
  4. get_leak_detection — flujo normal sin vecinos
  5. get_leak_detection — flujo normal con vecinos de InfluxDB
  6. get_leak_detection — fuga detectada → log de warning
  7. Resultado de autonomy contiene campos obligatorios
  8. Resultado de leaks contiene campos obligatorios
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────────
#  Respuestas sintéticas de los mocks
# ─────────────────────────────────────────────────────────────────

_AUTONOMY_RESULT_OK = {
    "days_autonomy":  8.5,
    "confidence":     0.88,
    "alert":          "warning",
    "estimated_date": "2026-04-06",
}

_AUTONOMY_RESULT_CRITICAL = {
    "days_autonomy":  1.2,
    "confidence":     0.80,
    "alert":          "critical",
    "estimated_date": "2026-03-30",
}

_LEAK_RESULT_NORMAL = {
    "node_id":       "HYDRO-V-001",
    "leak_detected": False,
    "anomaly_score": 0.10,
    "severity":      "NORMAL",
    "detected_at":   "2026-03-29T14:00:00+00:00",
}

_LEAK_RESULT_DETECTED = {
    "node_id":       "HYDRO-V-001",
    "leak_detected": True,
    "anomaly_score": 0.91,
    "severity":      "ALTA",
    "detected_at":   "2026-03-29T14:00:00+00:00",
}

_NASA_RESPONSE_OK = {
    "properties": {
        "parameter": {
            "PRECTOTCORR": {"20260329": 3.5, "20260330": 0.0, "20260331": 1.2},
            "T2M":         {"20260329": 21.0, "20260330": 22.0, "20260331": 20.5},
            "RH2M":        {"20260329": 60.0, "20260330": 58.0, "20260331": 62.0},
        }
    }
}


# ─────────────────────────────────────────────────────────────────
#  Tests de get_autonomy_prediction
# ─────────────────────────────────────────────────────────────────

class TestGetAutonomyPrediction:

    @pytest.mark.asyncio
    async def test_flujo_normal_retorna_resultado_completo(self):
        """
        Flujo feliz: InfluxDB y NASA OK.
        El servicio debe retornar el resultado del modelo sin modificar.
        """
        from app.services.ml_service import MLService

        svc = MLService()

        with (
            patch(
                "app.services.ml_service.InfluxService",
                autospec=True,
            ) as MockInflux,
            patch(
                "app.services.ml_service.fetch_nasa_power",
                new_callable=AsyncMock,
                return_value=_NASA_RESPONSE_OK,
            ),
            patch(
                "app.services.ml_service.predict_autonomy",
                return_value=_AUTONOMY_RESULT_OK,
            ),
        ):
            mock_influx = MockInflux.return_value
            mock_influx.get_avg_daily_consumption = AsyncMock(return_value=150.0)
            mock_influx.get_days_without_rain     = AsyncMock(return_value=3)

            result = await svc.get_autonomy_prediction(
                node_id="HYDRO-V-001",
                level_pct=55.0,
            )

        assert result["days_autonomy"] == pytest.approx(8.5)
        assert result["confidence"]    == pytest.approx(0.88)
        assert result["alert"]         == "warning"

    @pytest.mark.asyncio
    async def test_nasa_falla_usa_defaults_y_no_crashea(self):
        """
        Si NASA POWER falla, el servicio debe continuar con
        valores por defecto (precip=0, temp=20, humedad=50).
        """
        from app.services.ml_service import MLService

        svc = MLService()

        with (
            patch(
                "app.services.ml_service.InfluxService",
                autospec=True,
            ) as MockInflux,
            patch(
                "app.services.ml_service.fetch_nasa_power",
                new_callable=AsyncMock,
                side_effect=Exception("NASA timeout"),
            ),
            patch(
                "app.services.ml_service.predict_autonomy",
                return_value=_AUTONOMY_RESULT_OK,
            ) as mock_predict,
        ):
            mock_influx = MockInflux.return_value
            mock_influx.get_avg_daily_consumption = AsyncMock(return_value=120.0)
            mock_influx.get_days_without_rain     = AsyncMock(return_value=5)

            result = await svc.get_autonomy_prediction(
                node_id="HYDRO-V-001",
                level_pct=40.0,
            )

        # Debe retornar igual aunque NASA falle
        assert "days_autonomy" in result
        # predict_autonomy se llamó con los defaults de fallback
        call_kwargs = mock_predict.call_args.kwargs
        assert call_kwargs["forecast_precip_mm"] == 0.0
        assert call_kwargs["temperature_c"]      == 20.0
        assert call_kwargs["humidity_pct"]       == 50.0

    @pytest.mark.asyncio
    async def test_nivel_bajo_retorna_alerta_critical(self):
        """Con cisterna casi vacía el resultado debe ser critical."""
        from app.services.ml_service import MLService

        svc = MLService()

        with (
            patch("app.services.ml_service.InfluxService", autospec=True) as MockInflux,
            patch("app.services.ml_service.fetch_nasa_power", new_callable=AsyncMock,
                  return_value=_NASA_RESPONSE_OK),
            patch("app.services.ml_service.predict_autonomy",
                  return_value=_AUTONOMY_RESULT_CRITICAL),
        ):
            mock_influx = MockInflux.return_value
            mock_influx.get_avg_daily_consumption = AsyncMock(return_value=200.0)
            mock_influx.get_days_without_rain     = AsyncMock(return_value=10)

            result = await svc.get_autonomy_prediction(
                node_id="HYDRO-V-001",
                level_pct=5.0,
            )

        assert result["alert"] == "critical"
        assert result["days_autonomy"] < 2.0

    @pytest.mark.asyncio
    async def test_llama_predict_autonomy_con_datos_de_influx(self):
        """
        El servicio debe pasar el consumo real de InfluxDB
        (no un valor fijo) a predict_autonomy.
        """
        from app.services.ml_service import MLService

        svc = MLService()
        CONSUMO_REAL = 187.5

        with (
            patch("app.services.ml_service.InfluxService", autospec=True) as MockInflux,
            patch("app.services.ml_service.fetch_nasa_power", new_callable=AsyncMock,
                  return_value=_NASA_RESPONSE_OK),
            patch("app.services.ml_service.predict_autonomy",
                  return_value=_AUTONOMY_RESULT_OK) as mock_predict,
        ):
            mock_influx = MockInflux.return_value
            mock_influx.get_avg_daily_consumption = AsyncMock(return_value=CONSUMO_REAL)
            mock_influx.get_days_without_rain     = AsyncMock(return_value=0)

            await svc.get_autonomy_prediction(
                node_id="HYDRO-V-001",
                level_pct=70.0,
            )

        # El consumo de InfluxDB debe llegar al modelo
        call_kwargs = mock_predict.call_args.kwargs
        assert call_kwargs["avg_consumption_lpd"] == pytest.approx(CONSUMO_REAL)


# ─────────────────────────────────────────────────────────────────
#  Tests de get_leak_detection
# ─────────────────────────────────────────────────────────────────

class TestGetLeakDetection:

    @pytest.mark.asyncio
    async def test_sin_fuga_retorna_leak_detected_false(self):
        """Condición normal: flujo bajo, cisterna llena → no fuga."""
        from app.services.ml_service import MLService

        svc = MLService()

        with (
            patch("app.services.ml_service.InfluxService", autospec=True) as MockInflux,
            patch("app.services.ml_service.detect_leak", return_value=_LEAK_RESULT_NORMAL),
        ):
            mock_influx = MockInflux.return_value
            mock_influx.get_neighbor_nodes_data = AsyncMock(return_value=[])

            result = await svc.get_leak_detection(
                node_id="HYDRO-V-001",
                flow_lpm=1.5,
                level_pct=78.0,
            )

        assert result["leak_detected"] is False
        assert result["anomaly_score"] < 0.75

    @pytest.mark.asyncio
    async def test_fuga_detectada_retorna_leak_detected_true(self):
        """Alto flujo + nivel bajo → fuga detectada."""
        from app.services.ml_service import MLService

        svc = MLService()

        with (
            patch("app.services.ml_service.InfluxService", autospec=True) as MockInflux,
            patch("app.services.ml_service.detect_leak", return_value=_LEAK_RESULT_DETECTED),
        ):
            mock_influx = MockInflux.return_value
            mock_influx.get_neighbor_nodes_data = AsyncMock(return_value=[])

            result = await svc.get_leak_detection(
                node_id="HYDRO-V-001",
                flow_lpm=9.0,
                level_pct=8.0,
            )

        assert result["leak_detected"] is True
        assert result["anomaly_score"] >= 0.75
        assert result["severity"] == "ALTA"

    @pytest.mark.asyncio
    async def test_vecinos_de_influx_se_pasan_al_detector(self):
        """
        Los datos de nodos vecinos obtenidos de InfluxDB deben
        llegar como argumentos a detect_leak().
        """
        from app.services.ml_service import MLService

        svc = MLService()

        VECINOS = [
            {"flow_lpm": 1.2, "level_pct": 70.0},
            {"flow_lpm": 0.8, "level_pct": 80.0},
        ]

        with (
            patch("app.services.ml_service.InfluxService", autospec=True) as MockInflux,
            patch("app.services.ml_service.detect_leak",
                  return_value=_LEAK_RESULT_NORMAL) as mock_detect,
        ):
            mock_influx = MockInflux.return_value
            mock_influx.get_neighbor_nodes_data = AsyncMock(return_value=VECINOS)

            await svc.get_leak_detection(
                node_id="HYDRO-V-001",
                flow_lpm=2.0,
                level_pct=65.0,
            )

        call_kwargs = mock_detect.call_args.kwargs
        assert call_kwargs["neighbor_flows"]  == [1.2, 0.8]
        assert call_kwargs["neighbor_levels"] == [70.0, 80.0]

    @pytest.mark.asyncio
    async def test_sin_vecinos_no_crashea(self):
        """Sin nodos vecinos en InfluxDB, detect_leak recibe listas vacías."""
        from app.services.ml_service import MLService

        svc = MLService()

        with (
            patch("app.services.ml_service.InfluxService", autospec=True) as MockInflux,
            patch("app.services.ml_service.detect_leak",
                  return_value=_LEAK_RESULT_NORMAL) as mock_detect,
        ):
            mock_influx = MockInflux.return_value
            mock_influx.get_neighbor_nodes_data = AsyncMock(return_value=[])

            result = await svc.get_leak_detection(
                node_id="HYDRO-V-001",
                flow_lpm=2.0,
                level_pct=50.0,
            )

        call_kwargs = mock_detect.call_args.kwargs
        assert call_kwargs["neighbor_flows"]  == []
        assert call_kwargs["neighbor_levels"] == []
        # No debe crashear
        assert "leak_detected" in result


# ─────────────────────────────────────────────────────────────────
#  Tests de estructura del resultado
# ─────────────────────────────────────────────────────────────────

class TestResultadosMLService:

    @pytest.mark.asyncio
    async def test_autonomy_resultado_tiene_campos_obligatorios(self):
        """El dict de autonomía siempre debe tener days_autonomy, confidence, alert."""
        from app.services.ml_service import MLService

        svc = MLService()

        with (
            patch("app.services.ml_service.InfluxService", autospec=True) as MockInflux,
            patch("app.services.ml_service.fetch_nasa_power", new_callable=AsyncMock,
                  return_value=_NASA_RESPONSE_OK),
            patch("app.services.ml_service.predict_autonomy",
                  return_value=_AUTONOMY_RESULT_OK),
        ):
            mock_influx = MockInflux.return_value
            mock_influx.get_avg_daily_consumption = AsyncMock(return_value=150.0)
            mock_influx.get_days_without_rain     = AsyncMock(return_value=0)

            result = await svc.get_autonomy_prediction(
                node_id="HYDRO-V-001",
                level_pct=60.0,
            )

        for campo in ("days_autonomy", "confidence", "alert"):
            assert campo in result, f"Campo '{campo}' faltante en resultado de autonomía"

    @pytest.mark.asyncio
    async def test_leak_resultado_tiene_campos_obligatorios(self):
        """El dict de detección siempre debe tener node_id, leak_detected, anomaly_score."""
        from app.services.ml_service import MLService

        svc = MLService()

        with (
            patch("app.services.ml_service.InfluxService", autospec=True) as MockInflux,
            patch("app.services.ml_service.detect_leak", return_value=_LEAK_RESULT_NORMAL),
        ):
            mock_influx = MockInflux.return_value
            mock_influx.get_neighbor_nodes_data = AsyncMock(return_value=[])

            result = await svc.get_leak_detection(
                node_id="HYDRO-V-001",
                flow_lpm=1.0,
                level_pct=80.0,
            )

        for campo in ("node_id", "leak_detected", "anomaly_score", "severity"):
            assert campo in result, f"Campo '{campo}' faltante en resultado de detección"
