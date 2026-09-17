"""In-process WebSocket fan-out for doctor queue updates (P3-B03).

Single-process only (no Redis/pub-sub) - acceptable for this app's current
deployment shape (one backend process). If the API is ever run with
multiple workers/replicas, a client connected to worker A would miss a
broadcast triggered by a mutation handled by worker B; the frontend's
polling fallback (`refetchInterval` in `frontend/src/app/opd/page.tsx`)
exists specifically to bound that staleness even then.
"""

import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class QueueConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, doctor_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[doctor_id].add(websocket)

    async def disconnect(self, doctor_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[doctor_id].discard(websocket)

    async def broadcast(self, doctor_id: str, message: dict) -> None:
        async with self._lock:
            connections = list(self._connections.get(doctor_id, ()))

        stale: list[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                stale.append(connection)

        if stale:
            async with self._lock:
                for connection in stale:
                    self._connections[doctor_id].discard(connection)


manager = QueueConnectionManager()
