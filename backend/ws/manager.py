"""
WebSocket connection manager.
Manages separate pools for admin clients and driver clients.
"""
import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.admin_connections: List[WebSocket] = []
        self.driver_connections: Dict[str, List[WebSocket]] = {}  # driver_id → [ws]

    # ── Admin ──────────────────────────────────────────────────────────────────

    async def connect_admin(self, ws: WebSocket):
        await ws.accept()
        self.admin_connections.append(ws)

    async def disconnect_admin(self, ws: WebSocket):
        if ws in self.admin_connections:
            self.admin_connections.remove(ws)

    async def broadcast_admin(self, event: str, data: dict):
        payload = json.dumps({"event": event, "data": data})
        dead = []
        for ws in self.admin_connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_admin(ws)

    # ── Driver ─────────────────────────────────────────────────────────────────

    async def connect_driver(self, driver_id: str, ws: WebSocket):
        await ws.accept()
        if driver_id not in self.driver_connections:
            self.driver_connections[driver_id] = []
        self.driver_connections[driver_id].append(ws)

    async def disconnect_driver(self, driver_id: str, ws: WebSocket):
        conns = self.driver_connections.get(driver_id, [])
        if ws in conns:
            conns.remove(ws)

    async def notify_driver(self, driver_id: str, event: str, data: dict):
        payload = json.dumps({"event": event, "data": data})
        conns = self.driver_connections.get(driver_id, [])
        dead = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_driver(driver_id, ws)

    async def broadcast_all_drivers(self, event: str, data: dict):
        for driver_id in list(self.driver_connections.keys()):
            await self.notify_driver(driver_id, event, data)


manager = ConnectionManager()
