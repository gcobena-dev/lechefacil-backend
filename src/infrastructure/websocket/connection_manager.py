from __future__ import annotations

import logging
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications."""

    def __init__(self) -> None:
        # Key: (tenant_id, user_id) -> list of WebSocket connections
        self.active_connections: dict[tuple[UUID, UUID], list[WebSocket]] = {}

    async def connect(self, tenant_id: UUID, user_id: UUID, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        key = (tenant_id, user_id)

        # Support multiple concurrent connections per user (tabs/devices/components)
        conns = self.active_connections.get(key)
        if conns is None:
            conns = []
            self.active_connections[key] = conns
        conns.append(websocket)
        logger.info(f"WebSocket connected: tenant={tenant_id} user={user_id} total={len(conns)}")

    def disconnect(
        self, tenant_id: UUID, user_id: UUID, websocket: WebSocket | None = None
    ) -> None:
        """Remove a WebSocket connection. If `websocket` is provided, remove only that one."""
        key = (tenant_id, user_id)
        if key in self.active_connections:
            conns_all = self.active_connections[key]
            if websocket is not None:
                conns = [
                    ws
                    for ws in conns_all
                    if ws is not websocket and ws.client_state.name != "DISCONNECTED"
                ]
            else:
                # Clean up closed websockets
                conns = [ws for ws in conns_all if ws.client_state.name != "DISCONNECTED"]
            if conns:
                self.active_connections[key] = conns
                logger.info(
                    f"WebSocket disconnected: tenant={tenant_id} "
                    f"user={user_id} remaining={len(conns)}"
                )
            else:
                del self.active_connections[key]
                logger.info(
                    f"WebSocket disconnected: tenant={tenant_id} user={user_id} remaining=0"
                )

    async def send_to_user(self, tenant_id: UUID, user_id: UUID, message: str) -> bool:
        """
        Send a message to a specific user.
        Returns True if sent successfully, False if user is not connected.
        """
        key = (tenant_id, user_id)
        conns = self.active_connections.get(key)

        if not conns:
            logger.debug(f"User not connected: tenant={tenant_id} user={user_id}")
            return False

        any_sent = False
        alive: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(message)
                any_sent = True
                alive.append(ws)
            except Exception as e:
                logger.warning(
                    f"Error sending to one connection tenant={tenant_id} user={user_id}: {e}"
                )
                # Skip this ws; it will be dropped
        # Update connections, dropping broken ones
        if alive:
            self.active_connections[key] = alive
        else:
            self.active_connections.pop(key, None)
        return any_sent

    def is_connected(self, tenant_id: UUID, user_id: UUID) -> bool:
        """Check if a user is currently connected."""
        return (tenant_id, user_id) in self.active_connections and bool(
            self.active_connections[(tenant_id, user_id)]
        )

    def get_connection_count(self) -> int:
        """Get the total number of active connections."""
        return sum(len(v) for v in self.active_connections.values())
