# app/tests/test_realtime.py
"""Tests for the WebSocket infrastructure: ConnectionManager, notify(), and fragment renderers."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.realtime import (
    ConnectionManager,
    manager,
    notify,
    CH_PIPELINE_UPDATE,
    CH_NEW_REVIEW,
    CH_NEW_ORDER,
    CH_STOCK_UPDATE,
    ALL_CHANNELS,
)


# ---------------------------------------------------------------------------
# ConnectionManager unit tests
# ---------------------------------------------------------------------------

class TestConnectionManagerInit:
    """ConnectionManager initializes with correct channel sets."""

    def test_singleton_has_all_channels(self):
        mgr = ConnectionManager()
        for ch in ALL_CHANNELS:
            assert ch in mgr._channels
            assert isinstance(mgr._channels[ch], set)
            assert len(mgr._channels[ch]) == 0

    def test_singleton_channels_match_constants(self):
        mgr = ConnectionManager()
        assert set(mgr._channels.keys()) == set(ALL_CHANNELS)


class TestConnectionManagerConnect:
    """connect() accepts WebSocket and adds to channels."""

    @pytest.mark.anyio
    async def test_connect_adds_to_requested_channels(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()

        await mgr.connect(ws, [CH_PIPELINE_UPDATE, CH_NEW_REVIEW])

        ws.accept.assert_called_once()
        assert ws in mgr._channels[CH_PIPELINE_UPDATE]
        assert ws in mgr._channels[CH_NEW_REVIEW]
        assert ws not in mgr._channels[CH_STOCK_UPDATE]

    @pytest.mark.anyio
    async def test_connect_ignores_unknown_channels(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()

        await mgr.connect(ws, ["nonexistent_channel"])

        ws.accept.assert_called_once()
        # Should not crash, just ignore unknown channel
        assert ws not in mgr._channels[CH_PIPELINE_UPDATE]


class TestConnectionManagerDisconnect:
    """disconnect() removes WebSocket from channels."""

    @pytest.mark.anyio
    async def test_disconnect_removes_from_channels(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()

        await mgr.connect(ws, [CH_PIPELINE_UPDATE, CH_NEW_REVIEW])
        assert ws in mgr._channels[CH_PIPELINE_UPDATE]

        await mgr.disconnect(ws, [CH_PIPELINE_UPDATE])
        assert ws not in mgr._channels[CH_PIPELINE_UPDATE]
        assert ws in mgr._channels[CH_NEW_REVIEW]

    @pytest.mark.anyio
    async def test_disconnect_unknown_channel_no_crash(self):
        mgr = ConnectionManager()
        ws = AsyncMock()

        # Should not raise
        await mgr.disconnect(ws, ["nonexistent_channel"])


class TestConnectionManagerBroadcast:
    """broadcast() sends JSON to all connected clients, prunes dead ones."""

    @pytest.mark.anyio
    async def test_broadcast_sends_to_connected_clients(self):
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.client_state = MagicMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.client_state = MagicMock()

        await mgr.connect(ws1, [CH_NEW_ORDER])
        await mgr.connect(ws2, [CH_NEW_ORDER])

        # Mock client_state to appear connected
        from starlette.websockets import WebSocketState
        ws1.client_state = WebSocketState.CONNECTED
        ws2.client_state = WebSocketState.CONNECTED

        sent = await mgr.broadcast(CH_NEW_ORDER, {"type": "test", "data": "hello"})

        assert sent == 2
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

        # Verify JSON payload
        call_args = ws1.send_text.call_args[0][0]
        payload = json.loads(call_args)
        assert payload["type"] == "test"
        assert payload["data"] == "hello"

    @pytest.mark.anyio
    async def test_broadcast_prunes_dead_connections(self):
        mgr = ConnectionManager()
        ws_dead = AsyncMock()
        ws_dead.accept = AsyncMock()

        await mgr.connect(ws_dead, [CH_NEW_ORDER])

        # Mark as not connected
        from starlette.websockets import WebSocketState
        ws_dead.client_state = WebSocketState.DISCONNECTED

        sent = await mgr.broadcast(CH_NEW_ORDER, {"type": "test"})

        assert sent == 0
        # Dead connection should be pruned
        assert ws_dead not in mgr._channels[CH_NEW_ORDER]

    @pytest.mark.anyio
    async def test_broadcast_prunes_on_send_error(self):
        mgr = ConnectionManager()
        ws_err = AsyncMock()
        ws_err.accept = AsyncMock()
        ws_err.send_text = AsyncMock(side_effect=Exception("connection lost"))

        await mgr.connect(ws_err, [CH_PIPELINE_UPDATE])

        from starlette.websockets import WebSocketState
        ws_err.client_state = WebSocketState.CONNECTED

        sent = await mgr.broadcast(CH_PIPELINE_UPDATE, {"type": "test"})

        assert sent == 0
        assert ws_err not in mgr._channels[CH_PIPELINE_UPDATE]

    @pytest.mark.anyio
    async def test_broadcast_unknown_channel_returns_zero(self):
        mgr = ConnectionManager()
        sent = await mgr.broadcast("nonexistent_channel", {"type": "test"})
        assert sent == 0

    @pytest.mark.anyio
    async def test_broadcast_default_str_serialization(self):
        """broadcast uses default=str for non-JSON-serializable values (e.g. UUID)."""
        mgr = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()

        await mgr.connect(ws, [CH_STOCK_UPDATE])

        from starlette.websockets import WebSocketState
        ws.client_state = WebSocketState.CONNECTED

        from uuid import uuid4
        sent = await mgr.broadcast(CH_STOCK_UPDATE, {"product_id": uuid4()})

        assert sent == 1
        call_args = ws.send_text.call_args[0][0]
        payload = json.loads(call_args)
        # UUID should be serialized as string via default=str
        assert isinstance(payload["product_id"], str)


# ---------------------------------------------------------------------------
# notify() helper tests
# ---------------------------------------------------------------------------

class TestNotifyHelper:
    """notify() sends a Postgres NOTIFY via the pool."""

    @pytest.mark.anyio
    async def test_notify_executes_pg_notify(self):
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        await notify(mock_pool, CH_PIPELINE_UPDATE, {"product_id": "abc"})

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert "pg_notify" in call_args[0]

    @pytest.mark.anyio
    async def test_notify_does_not_crash_on_error(self):
        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(side_effect=Exception("pool closed"))

        # Should not raise
        await notify(mock_pool, CH_STOCK_UPDATE, {"data": "test"})


# ---------------------------------------------------------------------------
# Pipeline daemon lazy connection tests
# ---------------------------------------------------------------------------

class TestPipelineDaemonLazyConnection:
    """AsikoPipelineDaemon lazy-connects to Gradio Space."""

    def test_daemon_init_does_not_connect(self):
        from app.workers.pipeline_daemon import AsikoPipelineDaemon
        mock_pool = MagicMock()
        daemon = AsikoPipelineDaemon(db_pool=mock_pool)

        assert daemon.ai_client is None
        assert daemon._connect_attempted is False

    @patch("gradio_client.Client", side_effect=Exception("DNS fail"))
    def test_ensure_client_returns_false_on_failure(self, mock_client_cls):
        from app.workers.pipeline_daemon import AsikoPipelineDaemon
        mock_pool = MagicMock()
        daemon = AsikoPipelineDaemon(db_pool=mock_pool)

        result = daemon._ensure_client()

        assert result is False
        assert daemon.ai_client is None
        assert daemon._connect_attempted is True

    @patch("gradio_client.Client")
    def test_ensure_client_returns_true_on_success(self, mock_client_cls):
        from app.workers.pipeline_daemon import AsikoPipelineDaemon
        mock_pool = MagicMock()
        daemon = AsikoPipelineDaemon(db_pool=mock_pool)

        result = daemon._ensure_client()

        assert result is True
        assert daemon.ai_client is not None

    def test_ensure_client_does_not_retry_after_first_failure(self):
        from app.workers.pipeline_daemon import AsikoPipelineDaemon
        with patch("gradio_client.Client", side_effect=Exception("DNS fail")):
            mock_pool = MagicMock()
            daemon = AsikoPipelineDaemon(db_pool=mock_pool)

            daemon._ensure_client()
            # Second call should not attempt connection
            result = daemon._ensure_client()
            assert result is False


# ---------------------------------------------------------------------------
# Fragment render function tests
# ---------------------------------------------------------------------------

class TestFragmentRenderers:
    """WS fragment renderers produce valid HTML fragments."""

    def test_render_pipeline_status_completed(self):
        from app.routes.ws_admin import _render_pipeline_status_fragment
        html = _render_pipeline_status_fragment({
            "product_id": "abc-123",
            "status": "completed",
            "model_url": "/static/optimized/mesh.glb",
        })
        assert "abc-123" in html
        assert "Ready" in html
        assert "pipeline-status-abc-123" in html

    def test_render_pipeline_status_processing(self):
        from app.routes.ws_admin import _render_pipeline_status_fragment
        html = _render_pipeline_status_fragment({
            "product_id": "abc-123",
            "status": "processing",
        })
        assert "abc-123" in html
        assert "animate-spin" in html

    def test_render_review_summary(self):
        from app.routes.ws_admin import _render_review_summary_fragment
        html = _render_review_summary_fragment({
            "rating_avg": 4.5,
            "total_reviews": 12,
            "five_star_count": 8,
            "needs_response": 2,
        })
        assert "4.5" in html
        assert "12" in html
        assert "8" in html
        assert "2" in html

    def test_render_stock_badge_in_stock(self):
        from app.routes.ws_store import _render_stock_badge_fragment
        html = _render_stock_badge_fragment({
            "product_id": "prod-1",
            "stock": 5,
        })
        assert "In Stock" in html
        assert "5 available" in html

    def test_render_stock_badge_out_of_stock(self):
        from app.routes.ws_store import _render_stock_badge_fragment
        html = _render_stock_badge_fragment({
            "product_id": "prod-1",
            "stock": 0,
        })
        assert "Out of Stock" in html

    def test_render_pdp_review(self):
        from app.routes.ws_store import _render_pdp_review_fragment
        html = _render_pdp_review_fragment({
            "product_id": "prod-1",
            "rating_avg": 4.0,
            "total_reviews": 3,
        })
        assert "prod-1" in html
        assert "4.0" in html
        assert "3 reviews" in html


# ---------------------------------------------------------------------------
# Route registration tests
# ---------------------------------------------------------------------------

class TestWSRouteRegistration:
    """WebSocket routes are registered correctly."""

    def test_ws_admin_routes_count(self):
        from app.routes.ws_admin import ws_admin_routes
        assert len(ws_admin_routes) == 3

    def test_ws_store_routes_count(self):
        from app.routes.ws_store import ws_store_routes
        assert len(ws_store_routes) == 1

    def test_ws_admin_route_paths(self):
        from app.routes.ws_admin import ws_admin_routes
        paths = [r.path for r in ws_admin_routes]
        assert "/ws/admin/dashboard" in paths
        assert "/ws/admin/reviews" in paths
        # pipeline has {product_id} param
        assert any("pipeline" in p for p in paths)

    def test_ws_store_route_path(self):
        from app.routes.ws_store import ws_store_routes
        assert ws_store_routes[0].path == "/ws/store/product/{product_id}"
