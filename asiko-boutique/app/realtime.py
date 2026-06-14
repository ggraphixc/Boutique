# ASIKO Boutique - Real-Time WebSocket Connection Manager
# Centralized pub/sub hub: Postgres LISTEN/NOTIFY → WebSocket broadcast.
# No Redis required — asyncpg handles the lightweight pub/sub natively.

import json
import asyncio
import logging
from typing import Any, Dict, Set, Optional

import asyncpg
from starlette.websockets import WebSocket, WebSocketState

logger = logging.getLogger("asiko.realtime")

# ---------------------------------------------------------------------------
# Channel constants
# ---------------------------------------------------------------------------
CH_NEW_REVIEW = "new_review"
CH_NEW_ORDER = "new_order"
CH_STOCK_UPDATE = "stock_update"

ALL_CHANNELS = [
    CH_NEW_REVIEW,
    CH_NEW_ORDER,
    CH_STOCK_UPDATE,
]


class ConnectionManager:
    """
    Manages active WebSocket connections grouped by channel.
    Postgres LISTEN/NOTIFY feeds into this manager; WebSocket handlers
    read from it to push real-time updates to subscribed clients.
    """

    def __init__(self) -> None:
        # channel → set of open WebSocket connections
        self._channels: Dict[str, Set[WebSocket]] = {ch: set() for ch in ALL_CHANNELS}
        self._listeners: list[asyncio.Task] = []

    # -- WebSocket lifecycle ------------------------------------------------

    async def connect(self, ws: WebSocket, channels: list[str]) -> None:
        """Accept a WebSocket and subscribe it to the requested channels."""
        await ws.accept()
        for ch in channels:
            if ch in self._channels:
                self._channels[ch].add(ws)
        logger.info("WS connected to channels: %s", channels)

    async def disconnect(self, ws: WebSocket, channels: list[str]) -> None:
        """Remove a WebSocket from all its subscribed channels."""
        for ch in channels:
            self._channels.get(ch, set()).discard(ws)
        logger.info("WS disconnected from channels: %s", channels)

    # -- Broadcast ----------------------------------------------------------

    async def broadcast(self, channel: str, payload: dict) -> int:
        """
        Send a JSON payload to every WebSocket subscribed to `channel`.
        Returns the number of clients that received the message.
        Dead connections are pruned automatically.
        """
        if channel not in self._channels:
            return 0

        message = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        sent = 0

        for ws in list(self._channels[channel]):
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(message)
                    sent += 1
                else:
                    dead.append(ws)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self._channels[channel].discard(ws)

        return sent

    # -- Postgres LISTEN/NOTIFY listeners -----------------------------------

    def start_listeners(self, db_pool: asyncpg.Pool) -> None:
        """
        Spawn a background listener task for each Postgres NOTIFY channel.
        Each task acquires its own connection from the pool and listens
        indefinitely until the app shuts down.
        """
        for ch in ALL_CHANNELS:
            task = asyncio.create_task(self._listen_channel(db_pool, ch))
            self._listeners.append(task)
        logger.info("Started %d Postgres LISTEN tasks.", len(self._listeners))

    async def stop_listeners(self) -> None:
        """Cancel all listener tasks on shutdown."""
        for task in self._listeners:
            task.cancel()
        try:
            await asyncio.gather(*self._listeners, return_exceptions=True)
        except Exception:
            pass
        self._listeners.clear()
        logger.info("Postgres LISTEN tasks stopped.")

    async def _listen_channel(self, db_pool: asyncpg.Pool, channel: str) -> None:
        """
        Acquire a dedicated connection, issue LISTEN, and re-broadcast
        every NOTIFY payload to subscribed WebSocket clients.
        Reconnects automatically if the connection drops.
        """
        while True:
            conn: Optional[asyncpg.Connection] = None
            try:
                conn = await db_pool.acquire()
                await conn.add_listener(channel, self._on_notify)
                logger.info("LISTEN active on channel: %s", channel)

                # Keep the connection alive until cancelled or dropped
                while True:
                    await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("LISTEN connection lost on %s: %s — reconnecting in 3s", channel, exc)
                await asyncio.sleep(3)
            finally:
                if conn is not None:
                    try:
                        await db_pool.release(conn)
                    except Exception:
                        pass

    def _on_notify(self, conn: asyncpg.Connection, pid: int, channel: str, payload: str) -> None:
        """
        Callback invoked by asyncpg when a NOTIFY arrives.
        Schedules the broadcast on the event loop since we're in a
        synchronous callback context.
        """
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            data = {"raw": payload}

        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(self.broadcast(channel, data))
        else:
            asyncio.ensure_future(self.broadcast(channel, data))


# ---------------------------------------------------------------------------
# Singleton — imported by main.py, ws routes, and pipeline daemon
# ---------------------------------------------------------------------------
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Helper: acquire a connection and NOTIFY
# ---------------------------------------------------------------------------

async def notify(db_pool: asyncpg.Pool, channel: str, payload: dict) -> None:
    """
    Send a Postgres NOTIFY on `channel` with a JSON payload.
    Called by route handlers and the pipeline daemon after DB writes.
    """
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(f"SELECT pg_notify($1, $2)", channel, json.dumps(payload, default=str))
    except Exception as exc:
        logger.warning("NOTIFY failed on %s: %s", channel, exc)
