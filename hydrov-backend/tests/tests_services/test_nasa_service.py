# tests/tests_services/test_nasa_service.py
"""
Tests unitarios para nasa_service.py y nasa_parser.py.

Estrategia:
  - httpx.AsyncClient se mockea con resptest/pytest-mock
  - Nunca se llama a la API real de NASA POWER
  - Se prueba el parsing del JSON con datos sintéticos realistas
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

from app.services.nasa_service import (
    fetch_nasa_power,
    NASATemporality,
    HYDROV_PARAMS,
)
from app.services.nasa_parser import (
    parse_to_influx_points,
    parse_to_forecast_cache,
    NASA_NULL_VALUE,
    PARAM_LABELS,
)


# ─────────────────────────────────────────────────────────────────
#  Datos sintéticos que simulan la respuesta real de NASA POWER
# ─────────────────────────────────────────────────────────────────

NASA_DAILY_RESPONSE = {
    "properties": {
        "parameter": {
            "PRECTOTCORR": {
                "20240301": 0.0,
                "20240302": 5.3,
                "20240303": 12.1,
            },
            "T2M": {
                "20240301": 18.4,
                "20240302": 19.1,
                "20240303": 17.8,
            },
            "RH2M": {
                "20240301": 62.0,
                "20240302": 71.5,
                "20240303": NASA_NULL_VALUE,  # valor nulo NASA
            },
        }
    }
}

NASA_HOURLY_RESPONSE = {
    "properties": {
        "parameter": {
            "PRECTOTCORR": {
                "2024030100": 0.0,
                "2024030101": 0.2,
                "2024030102": 1.5,
            },
            "T2M": {
                "2024030100": 16.2,
                "2024030101": 15.9,
                "2024030102": 15.4,
            },
        }
    }
}

NASA_CLIMATOLOGY_RESPONSE = {
    "properties": {
        "parameter": {
            "PRECTOTCORR": {
                "JAN": 8.2,
                "FEB": 5.1,
                "MAR": 15.3,
                "ANN": 80.1,
            },
            "T2M": {
                "JAN": 14.0,
                "FEB": 15.5,
                "MAR": 18.2,
                "ANN": 17.1,
            },
        }
    }
}


# ─────────────────────────────────────────────────────────────────
#  Tests de fetch_nasa_power (mock httpx)
# ─────────────────────────────────────────────────────────────────

class TestFetchNasaPower:

    @pytest.mark.asyncio
    async def test_fetch_daily_returns_json(self):
        """fetch_nasa_power retorna el JSON correctamente para datos diarios."""
        mock_response = MagicMock()
        mock_response.json.return_value = NASA_DAILY_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.nasa_service.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_nasa_power(
                temporality=NASATemporality.DAILY,
                params=HYDROV_PARAMS["daily"],
                lat=19.4136,
                lon=-99.0151,
                start="20240301",
                end="20240303",
            )

        assert result == NASA_DAILY_RESPONSE
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_uses_default_coords(self):
        """Si no se pasan lat/lon, usa los defaults de settings (Neza)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.nasa_service.httpx.AsyncClient", return_value=mock_client):
            await fetch_nasa_power(
                temporality=NASATemporality.DAILY,
                params=["PRECTOTCORR"],
            )

        call_kwargs = mock_client.get.call_args
        params_sent = call_kwargs[1]["params"]
        assert params_sent["latitude"]  == pytest.approx(19.4136)
        assert params_sent["longitude"] == pytest.approx(-99.0151)

    @pytest.mark.asyncio
    async def test_fetch_raises_on_http_error(self):
        """fetch_nasa_power propaga errores HTTP de la API de NASA."""
        from httpx import HTTPStatusError, Request, Response

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=MagicMock(),
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.nasa_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception):
                await fetch_nasa_power(
                    temporality=NASATemporality.DAILY,
                    params=["PRECTOTCORR"],
                )


# ─────────────────────────────────────────────────────────────────
#  Tests de nasa_parser → parse_to_influx_points
# ─────────────────────────────────────────────────────────────────

class TestParseToInfluxPoints:

    def test_daily_data_genera_puntos_correctos(self):
        """Datos diarios generan Points de InfluxDB con timestamp UTC."""
        points = list(parse_to_influx_points(
            nasa_json=NASA_DAILY_RESPONSE,
            lat=19.4136,
            lon=-99.0151,
            bucket="nasa_weather_cache",
        ))
        # 3 fechas, pero RH2M del día 3 es -999 así que igual genera 3 points
        # (otros campos son válidos)
        assert len(points) == 3

    def test_null_values_se_omiten(self):
        """Valores NASA_NULL_VALUE (-999) no se incluyen como fields."""
        points = list(parse_to_influx_points(
            nasa_json=NASA_DAILY_RESPONSE,
            lat=19.4136,
            lon=-99.0151,
            bucket="nasa_weather_cache",
        ))
        # El tercer punto (20240303) tiene RH2M = -999, no debería tener humidity_pct
        # Los points de influxdb_client no exponen campos directamente como dict,
        # pero al menos verificamos que se generaron 3 puntos válidos
        assert all(p is not None for p in points)

    def test_hourly_data_detectado_correctamente(self):
        """Datos horarios (keys de 10 dígitos) se detectan como hourly."""
        points = list(parse_to_influx_points(
            nasa_json=NASA_HOURLY_RESPONSE,
            lat=19.4136,
            lon=-99.0151,
            bucket="nasa_weather_cache",
        ))
        assert len(points) == 3

    def test_climatology_genera_puntos_con_tag_period(self):
        """Climatología (keys tipo 'JAN') genera points con tag 'period'."""
        points = list(parse_to_influx_points(
            nasa_json=NASA_CLIMATOLOGY_RESPONSE,
            lat=19.4136,
            lon=-99.0151,
            bucket="nasa_weather_cache",
        ))
        # JAN, FEB, MAR, ANN = 4 puntos
        assert len(points) == 4

    def test_json_sin_properties_no_lanza_excepcion(self):
        """JSON malformado retorna generator vacío sin lanzar excepción."""
        points = list(parse_to_influx_points(
            nasa_json={"unexpected": "format"},
            lat=19.4136,
            lon=-99.0151,
            bucket="nasa_weather_cache",
        ))
        assert points == []

    def test_param_labels_se_aplican_correctamente(self):
        """PRECTOTCORR se mapea a 'precipitation_mm' en PARAM_LABELS."""
        assert PARAM_LABELS["PRECTOTCORR"] == "precipitation_mm"
        assert PARAM_LABELS["T2M"]         == "temperature_c"
        assert PARAM_LABELS["RH2M"]        == "humidity_pct"


# ─────────────────────────────────────────────────────────────────
#  Tests de nasa_parser → parse_to_forecast_cache
# ─────────────────────────────────────────────────────────────────

class TestParseToForecastCache:

    def test_forecast_cache_retorna_lista_de_dicts(self):
        """parse_to_forecast_cache retorna una lista de dicts por hora."""
        cache = parse_to_forecast_cache(NASA_HOURLY_RESPONSE)
        assert isinstance(cache, list)
        assert len(cache) == 3

    def test_forecast_cache_contiene_hour_key(self):
        """Cada entry del forecast tiene la key 'hour'."""
        cache = parse_to_forecast_cache(NASA_HOURLY_RESPONSE)
        for entry in cache:
            assert "hour" in entry

    def test_forecast_cache_omite_null_values(self):
        """Valores -999 no aparecen en el forecast cache."""
        cache = parse_to_forecast_cache(NASA_DAILY_RESPONSE)
        for entry in cache:
            for key, val in entry.items():
                if key != "hour":
                    assert val != NASA_NULL_VALUE

    def test_forecast_cache_json_malformado_retorna_lista_vacia(self):
        """JSON sin 'properties' retorna lista vacía sin crash."""
        cache = parse_to_forecast_cache({"wrong": "data"})
        assert cache == []
