from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core.state_store import state_store

logger = logging.getLogger(__name__)

router = APIRouter()

STATS_BROADCAST_INTERVAL = 2.0


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, dict | None] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[websocket] = None

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)

    async def handle_message(self, websocket: WebSocket, raw: str) -> None:
        try:
            message = json.loads(raw)
        except (ValueError, TypeError):
            return
        if not isinstance(message, dict):
            return
        action = message.get("action")
        if action == "subscribe":
            self._connections[websocket] = {
                "workflow_id": message.get("workflow_id")
            }
        elif action in ("subscribe_all", "unsubscribe"):
            self._connections[websocket] = None
        elif action == "ping":
            await websocket.send_json({"type": "pong"})

    def _subscribed(self, subscription: dict | None, workflow_id: str | None) -> bool:
        if subscription is None:
            return True
        return subscription.get("workflow_id") in (None, workflow_id)

    async def broadcast(self, data: dict) -> None:
        workflow_id = data.get("workflow_id")
        stale: list[WebSocket] = []
        for websocket, subscription in list(self._connections.items()):
            if not self._subscribed(subscription, workflow_id):
                continue
            try:
                await websocket.send_json(data)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)


websocket_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket_manager.connect(websocket)
    push_task = asyncio.create_task(broadcast_stats(websocket))
    try:
        while True:
            raw = await websocket.receive_text()
            await websocket_manager.handle_message(websocket, raw)
    except WebSocketDisconnect:
        pass
    finally:
        push_task.cancel()
        websocket_manager.disconnect(websocket)


async def broadcast_update(data: dict) -> None:
    await websocket_manager.broadcast(data)


async def broadcast_stats(websocket: WebSocket) -> None:
    while websocket in websocket_manager._connections:
        stats = await state_store.get_stats()
        stats_with_type = {"type": "stats", **stats}
        try:
            await websocket.send_json(stats_with_type)
        except Exception:
            websocket_manager.disconnect(websocket)
            return
        await asyncio.sleep(STATS_BROADCAST_INTERVAL)
