from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    def connect(self, user_id: str, websocket: WebSocket):
        self._connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(user_id, None)

    async def push(self, user_id: str, payload: dict):
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                pass

    def is_connected(self, user_id: str) -> bool:
        return bool(self._connections.get(user_id))


manager = ConnectionManager()
