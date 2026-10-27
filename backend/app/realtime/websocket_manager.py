import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("mineguard.realtime")


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.debug(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.debug(f"WebSocket client disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast(self, message_type: str, data: Dict[str, Any]):
        """Broadcast a structured JSON event to all connected dashboard clients."""
        if not self.active_connections:
            return

        payload = {
            "type": message_type,
            "data": data
        }
        text_payload = json.dumps(payload, default=str)

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(text_payload)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(connection)

        for dead_conn in disconnected:
            self.disconnect(dead_conn)


ws_manager = WebSocketManager()
