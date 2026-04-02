# tests/tests_services/test_websocket_service.py
"""
Tests unitarios para websocketservice.py.

Estrategia:
  - WebSocket de FastAPI se mockea con MagicMock → sin servidor TCP real
  - Redis pub/sub se mockea → sin Redis real
  - Se prueba la lógica del ConnectionManager y el handler de mensajes

Tests cubiertos:
  1. connect() añade el WebSocket al registro del nodo
  2. disconnect() elimina el WebSocket del registro
  3. broadcast_to_node() envía a todos los WS de un nodo
  4. broadcast_to_node() nodo sin conexiones → no falla
  5. handle_websocket() recibe mensaje de Redis y lo reenvía al WS
  6. handle_websocket() WS desconectado → limpia sin crash
  7. handle_websocket() Redis falla → clientea sigue conectado
  8. send_personal_message() un solo destinatario
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ─────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────

def make_websocket(node_id: str = "HYDRO-V-001") -> MagicMock:
    """Simula una conexión WebSocket de FastAPI."""
    ws              = MagicMock()
    ws.accept       = AsyncMock()
    ws.send_json    = AsyncMock()
    ws.send_text    = AsyncMock()
    ws.receive_text = AsyncMock(return_value="ping")
    ws.close        = AsyncMock()
    return ws


def make_redis_pubsub(messages: list[dict]) -> MagicMock:
    """
    Simula un canal Redis pub/sub que emite un mensaje por iteración.
    Una vez agotados los mensajes, lanza StopAsyncIteration.
    """
    pubsub = MagicMock()

    async def _aiter():
        for msg in messages:
            yield msg
        # Simula que el canal se cierra (sin bucle infinito en el test)

    pubsub.__aiter__ = _aiter
    pubsub.subscribe  = AsyncMock()
    pubsub.close      = AsyncMock()
    pubsub.aclose     = AsyncMock()
    return pubsub


_SAMPLE_ALERT = {
    "type":      "emergency",
    "node_id":   "HYDRO-V-001",
    "message":   "Nivel crítico detectado",
    "timestamp": "2026-03-29T14:00:00+00:00",
}


# ─────────────────────────────────────────────────────────────────
#  Tests del ConnectionManager
# ─────────────────────────────────────────────────────────────────

class TestConnectionManager:

    @pytest.mark.asyncio
    async def test_connect_registra_websocket(self):
        """connect() debe aceptar el WS y añadirlo al registro."""
        from app.services.websocketservice import ConnectionManager

        manager = ConnectionManager()
        ws      = make_websocket()

        await manager.connect(ws, "HYDRO-V-001")

        ws.accept.assert_called_once()
        assert ws in manager.active_connections.get("HYDRO-V-001", [])

    @pytest.mark.asyncio
    async def test_disconnect_elimina_websocket(self):
        """disconnect() debe quitar el WS del registro del nodo."""
        from app.services.websocketservice import ConnectionManager

        manager = ConnectionManager()
        ws      = make_websocket()

        await manager.connect(ws, "HYDRO-V-001")
        manager.disconnect(ws, "HYDRO-V-001")

        assert ws not in manager.active_connections.get("HYDRO-V-001", [])

    @pytest.mark.asyncio
    async def test_multiples_clientes_mismo_nodo(self):
        """Varios WebSockets pueden conectarse al mismo nodo."""
        from app.services.websocketservice import ConnectionManager

        manager = ConnectionManager()
        ws1, ws2, ws3 = make_websocket(), make_websocket(), make_websocket()

        await manager.connect(ws1, "HYDRO-V-001")
        await manager.connect(ws2, "HYDRO-V-001")
        await manager.connect(ws3, "HYDRO-V-001")

        conexiones = manager.active_connections.get("HYDRO-V-001", [])
        assert len(conexiones) == 3

    @pytest.mark.asyncio
    async def test_disconnect_nodo_inexistente_no_crashea(self):
        """disconnect() en un nodo sin conexiones no debe lanzar excepción."""
        from app.services.websocketservice import ConnectionManager

        manager = ConnectionManager()
        ws      = make_websocket()

        # No debería lanzar KeyError ni similares
        manager.disconnect(ws, "NODO-INEXISTENTE")

    @pytest.mark.asyncio
    async def test_broadcast_to_node_envia_a_todos(self):
        """broadcast_to_node() debe llamar send_json en cada WS del nodo."""
        from app.services.websocketservice import ConnectionManager

        manager = ConnectionManager()
        ws1, ws2 = make_websocket(), make_websocket()

        await manager.connect(ws1, "HYDRO-V-001")
        await manager.connect(ws2, "HYDRO-V-001")

        data = {"type": "alert", "message": "Fuga detectada"}
        await manager.broadcast_to_node("HYDRO-V-001", data)

        ws1.send_json.assert_called_once_with(data)
        ws2.send_json.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_broadcast_nodo_sin_conexiones_no_crashea(self):
        """broadcast_to_node() en nodo sin conexiones debe retornar silenciosamente."""
        from app.services.websocketservice import ConnectionManager

        manager = ConnectionManager()

        # No debe fallar si no hay nadie escuchando
        await manager.broadcast_to_node("HYDRO-V-999", {"type": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_distinto_nodo_no_recibe(self):
        """Un WS conectado a 'nodo-A' no debe recibir mensajes de 'nodo-B'."""
        from app.services.websocketservice import ConnectionManager

        manager = ConnectionManager()
        ws_a    = make_websocket()
        ws_b    = make_websocket()

        await manager.connect(ws_a, "HYDRO-V-001")
        await manager.connect(ws_b, "HYDRO-V-002")

        await manager.broadcast_to_node("HYDRO-V-001", {"msg": "solo para nodo 1"})

        ws_a.send_json.assert_called_once()
        ws_b.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_personal_message_envia_texto(self):
        """send_personal_message() debe llamar send_text en el WS indicado."""
        from app.services.websocketservice import ConnectionManager

        manager = ConnectionManager()
        ws      = make_websocket()

        await manager.send_personal_message("hola mundo", ws)

        ws.send_text.assert_called_once_with("hola mundo")


# ─────────────────────────────────────────────────────────────────
#  Tests de handle_websocket (integración WS + Redis pub/sub)
# ─────────────────────────────────────────────────────────────────

class TestHandleWebSocket:

    @pytest.mark.asyncio
    async def test_alerta_redis_se_reenvía_al_websocket(self):
        """
        Cuando Redis publica un mensaje en el canal del nodo,
        handle_websocket debe reenviarlo al cliente vía send_json.
        """
        from app.services.websocketservice import handle_websocket

        ws = make_websocket()

        # Redis entrega UN mensaje y luego el iterador se cierra
        redis_msg = {
            "type":    "message",
            "data":    json.dumps(_SAMPLE_ALERT).encode(),
            "channel": b"hydrov:HYDRO-V-001:alerts",
        }
        mock_pubsub = make_redis_pubsub([redis_msg])
        mock_redis  = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub

        with patch(
            "app.services.websocketservice.redis.from_url",
            return_value=mock_redis,
        ):
            await handle_websocket(ws, "HYDRO-V-001")

        ws.send_json.assert_called()
        sent_data = ws.send_json.call_args[0][0]
        assert sent_data["node_id"]  == "HYDRO-V-001"
        assert sent_data["type"]     == "emergency"

    @pytest.mark.asyncio
    async def test_websocket_acepta_conexion_al_inicio(self):
        """handle_websocket debe llamar accept() antes de entrar al loop."""
        from app.services.websocketservice import handle_websocket

        ws = make_websocket()

        mock_pubsub = make_redis_pubsub([])   # sin mensajes → loop termina rápido
        mock_redis  = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub

        with patch(
            "app.services.websocketservice.redis.from_url",
            return_value=mock_redis,
        ):
            await handle_websocket(ws, "HYDRO-V-001")

        ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_desconectado_no_propaga_excepcion(self):
        """
        Si el WS se desconecta abruptamente (WebSocketDisconnect),
        handle_websocket debe limpiar la conexión sin propagar la excepción.
        """
        from app.services.websocketservice import handle_websocket
        from fastapi import WebSocketDisconnect

        ws          = make_websocket()
        ws.send_json = AsyncMock(side_effect=WebSocketDisconnect(code=1001))

        redis_msg = {
            "type":    "message",
            "data":    json.dumps(_SAMPLE_ALERT).encode(),
            "channel": b"hydrov:HYDRO-V-001:alerts",
        }
        mock_pubsub = make_redis_pubsub([redis_msg])
        mock_redis  = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub

        with patch(
            "app.services.websocketservice.redis.from_url",
            return_value=mock_redis,
        ):
            # No debe lanzar WebSocketDisconnect hacia afuera
            try:
                await handle_websocket(ws, "HYDRO-V-001")
            except WebSocketDisconnect:
                pytest.fail("handle_websocket propagó WebSocketDisconnect")

    @pytest.mark.asyncio
    async def test_redis_falla_no_crashea_websocket(self):
        """
        Si la conexión a Redis falla al iniciar, el handler debe
        cerrar el WS limpiamente sin lanzar excepción.
        """
        from app.services.websocketservice import handle_websocket

        ws = make_websocket()

        with patch(
            "app.services.websocketservice.redis.from_url",
            side_effect=ConnectionError("Redis no disponible"),
        ):
            try:
                await handle_websocket(ws, "HYDRO-V-001")
            except ConnectionError:
                pytest.fail("handle_websocket propagó ConnectionError de Redis")

    @pytest.mark.asyncio
    async def test_mensaje_sin_data_se_ignora(self):
        """
        Mensajes de Redis de tipo 'subscribe' (sin payload de datos)
        deben ignorarse sin intentar hacer send_json.
        """
        from app.services.websocketservice import handle_websocket

        ws = make_websocket()

        # Mensaje de confirmación de suscripción (sin datos de alerta)
        subscribe_msg = {
            "type":    "subscribe",
            "data":    1,          # Redis envía el número de suscripciones activas
            "channel": b"hydrov:HYDRO-V-001:alerts",
        }
        mock_pubsub = make_redis_pubsub([subscribe_msg])
        mock_redis  = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub

        with patch(
            "app.services.websocketservice.redis.from_url",
            return_value=mock_redis,
        ):
            await handle_websocket(ws, "HYDRO-V-001")

        # Solo se llama accept(), no send_json
        ws.accept.assert_called_once()
        ws.send_json.assert_not_called()
