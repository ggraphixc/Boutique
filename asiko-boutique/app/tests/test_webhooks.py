# app/tests/test_webhooks.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route


def test_meshy_webhook_method_not_allowed():
    """Verify GET method returns 405 for webhook endpoint."""
    from app.routes.webhooks import meshy_webhook_receiver
    
    mock_pool = MagicMock()
    routes = [
        Route("/api/v1/webhooks/meshy", endpoint=meshy_webhook_receiver, methods=["POST"]),
    ]
    test_app = Starlette(routes=routes)
    test_app.state.db_pool = mock_pool

    with TestClient(test_app) as client:
        response = client.get("/api/v1/webhooks/meshy")
        assert response.status_code == 405


def test_meshy_webhook_post_acknowledged():
    """Verify POST returns acknowledgment for deprecated endpoint."""
    from app.routes.webhooks import meshy_webhook_receiver
    
    mock_pool = MagicMock()
    routes = [
        Route("/api/v1/webhooks/meshy", endpoint=meshy_webhook_receiver, methods=["POST"]),
    ]
    test_app = Starlette(routes=routes)
    test_app.state.db_pool = mock_pool

    with TestClient(test_app) as client:
        mock_payload = {"id": "msy_task", "status": "succeeded"}
        response = client.post("/api/v1/webhooks/meshy", json=mock_payload)
        assert response.status_code == 200
        assert b"DEPRECATED_ENDPOINT_ACKNOWLEDGED" in response.content


def test_meshy_webhook_invalid_json_returns_ok():
    """Verify invalid JSON payload still returns 200 for deprecated endpoint."""
    from app.routes.webhooks import meshy_webhook_receiver
    
    mock_pool = MagicMock()
    routes = [
        Route("/api/v1/webhooks/meshy", endpoint=meshy_webhook_receiver, methods=["POST"]),
    ]
    test_app = Starlette(routes=routes)
    test_app.state.db_pool = mock_pool

    with TestClient(test_app) as client:
        response = client.post("/api/v1/webhooks/meshy", content=b"not valid json{{{")
        assert response.status_code == 200


def test_meshy_webhook_internal_error_returns_ok():
    """Verify internal errors return 200 for deprecated endpoint."""
    from app.routes.webhooks import meshy_webhook_receiver
    
    mock_pool = MagicMock()
    routes = [
        Route("/api/v1/webhooks/meshy", endpoint=meshy_webhook_receiver, methods=["POST"]),
    ]
    test_app = Starlette(routes=routes)
    test_app.state.db_pool = mock_pool

    with TestClient(test_app) as client:
        mock_payload = {"id": "msy_error_task", "status": "succeeded"}
        response = client.post("/api/v1/webhooks/meshy", json=mock_payload)
        assert response.status_code == 200