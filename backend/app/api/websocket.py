from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core.state_store import state_store

router = APIRouter()

_connections: list[WebSocket] = []


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    _connections.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)
            stats = await state_store.get_stats()
            await websocket.send_json(stats)
    except WebSocketDisconnect:
        _connections.remove(websocket)


async def broadcast_update(data: dict) -> None:
    disconnected = []
    for ws in _connections:
        try:
            await ws.send_json(data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in _connections:
            _connections.remove(ws)
