# app/services/websocketservice.py
import asyncio
import json
# import aioredis
import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect
from app.core.config import settings
from app.core.logger import logger


class ConnectionManager:
    """
    Maneja conexiones WebSocket activas por node_id.
    El frontend React se suscribe a un node_id específico
    y recibe alertas en tiempo real.
    """

    def __init__(self):
        # node_id → lista de WebSockets conectados
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, node_id: str) -> None:
        await websocket.accept()
        if node_id not in self._connections:
            self._connections[node_id] = []
        self._connections[node_id].append(websocket)
        logger.info(f"[WS] Cliente conectado | node={node_id} total={len(self._connections[node_id])}")

    def disconnect(self, websocket: WebSocket, node_id: str) -> None:
        if node_id in self._connections:
            self._connections[node_id].discard(websocket) \
                if hasattr(self._connections[node_id], 'discard') \
                else self._connections[node_id].remove(websocket)
        logger.info(f"[WS] Cliente desconectado | node={node_id}")

    async def broadcast_to_node(self, node_id: str, message: dict) -> None:
        """Envía un mensaje a todos los clientes suscritos a un node_id."""
        if node_id not in self._connections:
            return
        dead_sockets = []
        for ws in self._connections[node_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_sockets.append(ws)
        # Limpiar conexiones muertas
        for ws in dead_sockets:
            self._connections[node_id].remove(ws)


# Singleton
manager = ConnectionManager()


async def redis_listener(node_id: str) -> None:
    """
    Escucha el canal Redis de alertas para un node_id
    y las reenvía por WebSocket al frontend.

    Se lanza como background task cuando un cliente
    WebSocket se conecta.
    """
    redis   = aioredis.from_url(settings.REDIS_URL)
    channel = settings.WS_ALERT_CHANNEL.format(node_id=node_id)
    pubsub  = redis.pubsub()

    await pubsub.subscribe(channel)
    logger.info(f"[WS] Redis listener activo en canal {channel}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await manager.broadcast_to_node(node_id, data)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await redis.aclose()


async def handle_websocket(websocket: WebSocket, node_id: str) -> None:
    """
    Handler principal del endpoint WebSocket.
    Uso en app/api/v1/endpoints/telemetry.py:

        @router.websocket("/ws/{node_id}")
        async def websocket_endpoint(websocket: WebSocket, node_id: str):
            await handle_websocket(websocket, node_id)
    """
    await manager.connect(websocket, node_id)

    # Lanzar listener de Redis en background
    listener_task = asyncio.create_task(redis_listener(node_id))

    try:
        while True:
            # Mantener conexión viva esperando mensajes del cliente
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, node_id)
        listener_task.cancel()