"""
WebSocket Connection Manager for Boardroom AI.
Manages active WebSocket sessions for live streaming multi-agent debates to clients.
"""
from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept connection and associate it with user_id."""
        await websocket.accept()
        # Close duplicate connection if active
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].close()
            except Exception:
                pass
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        """Clean up disconnected user session."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        """Send JSON message to a specific user session."""
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

    async def broadcast(self, message: dict):
        """Send message to all active WebSocket clients."""
        for connection in self.active_connections.values():
            await connection.send_json(message)
