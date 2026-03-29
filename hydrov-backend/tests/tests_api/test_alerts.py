# tests/tests_api/test_alerts.py
"""
Tests de integración para los endpoints de alertas.

Endpoints cubiertos:
  GET   /api/v1/alerts/               — listar alertas con filtros
  GET   /api/v1/alerts/{id}           — detalle de alerta
  PATCH /api/v1/alerts/{id}/resolve   — marcar como resuelta
  GET   /api/v1/alerts/stats/summary  — métricas para dashboard
"""
import pytest
from unittest.mock import AsyncMock, patch


# ─────────────────────────────────────────────────────────────────
#  Tests GET /alerts/
# ─────────────────────────────────────────────────────────────────

class TestListAlerts:

    @pytest.mark.asyncio
    async def test_lista_todas_las_alertas(
        self, client, test_alert, auth_headers
    ):
        """Debe retornar la lista paginada de alertas."""
        response = await client.get("/api/v1/alerts/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_filtro_por_node_id(
        self, client, test_alert, test_device, auth_headers
    ):
        """Filtrar por node_id debe retornar solo alertas de ese nodo."""
        response = await client.get(
            f"/api/v1/alerts/?node_id={test_device.device_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["node_id"] == test_device.device_id

    @pytest.mark.asyncio
    async def test_filtro_resolved_false(
        self, client, test_alert, auth_headers
    ):
        """?resolved=false debe retornar solo alertas pendientes."""
        response = await client.get(
            "/api/v1/alerts/?resolved=false",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["resolved"] == False

    @pytest.mark.asyncio
    async def test_sin_autenticacion_retorna_401(self, client):
        """Sin JWT debe retornar 401."""
        response = await client.get("/api/v1/alerts/")
        assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────
#  Tests GET /alerts/{alert_id}
# ─────────────────────────────────────────────────────────────────

class TestGetAlert:

    @pytest.mark.asyncio
    async def test_retorna_detalle_de_alerta(
        self, client, test_alert, auth_headers
    ):
        """Debe retornar el detalle completo de la alerta."""
        response = await client.get(
            f"/api/v1/alerts/{test_alert.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"]         == test_alert.id
        assert data["node_id"]    == test_alert.node_id
        assert data["resolved"]   == False
        assert data["error_count"] == test_alert.error_count

    @pytest.mark.asyncio
    async def test_alerta_inexistente_retorna_404(
        self, client, auth_headers
    ):
        """ID de alerta que no existe debe retornar 404."""
        response = await client.get(
            "/api/v1/alerts/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────
#  Tests PATCH /alerts/{alert_id}/resolve
# ─────────────────────────────────────────────────────────────────

class TestResolveAlert:

    @pytest.mark.asyncio
    async def test_marca_alerta_como_resuelta(
        self, client, test_alert, auth_headers
    ):
        """PATCH /resolve debe marcar la alerta como resuelta."""
        response = await client.patch(
            f"/api/v1/alerts/{test_alert.id}/resolve",
            json={"resolved": True, "notes": "Sensor reemplazado"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resolved"]       == True
        assert data["resolved_notes"] == "Sensor reemplazado"
        assert data["resolved_at"]    is not None

    @pytest.mark.asyncio
    async def test_resolver_alerta_ya_resuelta_retorna_409(
        self, client, test_alert, auth_headers
    ):
        """Intentar resolver una alerta ya resuelta debe retornar 409."""
        # Primera resolución (OK)
        await client.patch(
            f"/api/v1/alerts/{test_alert.id}/resolve",
            json={"resolved": True},
            headers=auth_headers,
        )
        # Segunda resolución (debe fallar)
        response = await client.patch(
            f"/api/v1/alerts/{test_alert.id}/resolve",
            json={"resolved": True},
            headers=auth_headers,
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_resolver_alerta_inexistente_retorna_404(
        self, client, auth_headers
    ):
        """Resolver ID inexistente debe retornar 404."""
        response = await client.patch(
            "/api/v1/alerts/99999/resolve",
            json={"resolved": True},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_notas_demasiado_largas_retornan_422(
        self, client, test_alert, auth_headers
    ):
        """Notas > 500 chars deben retornar 422 (validación Pydantic)."""
        response = await client.patch(
            f"/api/v1/alerts/{test_alert.id}/resolve",
            json={"resolved": True, "notes": "x" * 501},
            headers=auth_headers,
        )
        assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────
#  Tests GET /alerts/stats/summary
# ─────────────────────────────────────────────────────────────────

class TestAlertStats:

    @pytest.mark.asyncio
    async def test_retorna_estructura_correcta(
        self, client, test_alert, auth_headers
    ):
        """El endpoint de stats debe retornar la estructura esperada."""
        response = await client.get(
            "/api/v1/alerts/stats/summary",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert isinstance(data["nodes"], list)

    @pytest.mark.asyncio
    async def test_stats_incluye_datos_del_nodo_de_prueba(
        self, client, test_alert, test_device, auth_headers
    ):
        """El resumen debe incluir el nodo de la alerta de prueba."""
        response = await client.get(
            "/api/v1/alerts/stats/summary",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        node_ids = [n["node_id"] for n in data["nodes"]]
        assert test_device.device_id in node_ids
