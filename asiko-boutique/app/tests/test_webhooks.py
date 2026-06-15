# app/tests/test_webhooks.py
# Tests for order-status and test-email webhook endpoints.
# These test the validation paths that don't require a DB connection.
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route

from app.routes.webhooks import order_status_webhook, send_test_email


def _make_test_app(endpoint, path):
    mock_pool = MagicMock()
    routes = [Route(path, endpoint, methods=["POST"])]
    test_app = Starlette(routes=routes)
    test_app.state.db_pool = mock_pool
    return test_app


def test_order_status_webhook_get_not_allowed():
    """GET should return 405 for order-status webhook."""
    app = _make_test_app(order_status_webhook, "/webhooks/order-status")
    with TestClient(app) as client:
        r = client.get("/webhooks/order-status")
        assert r.status_code == 405


def test_order_status_webhook_missing_fields():
    """POST with missing order_id or status should return 400."""
    app = _make_test_app(order_status_webhook, "/webhooks/order-status")
    with TestClient(app) as client:
        r = client.post("/webhooks/order-status", json={"order_id": "x"})
        assert r.status_code == 400
        r = client.post("/webhooks/order-status", json={"status": "paid"})
        assert r.status_code == 400


def test_order_status_webhook_invalid_status():
    """POST with invalid status value should return 400."""
    app = _make_test_app(order_status_webhook, "/webhooks/order-status")
    with TestClient(app) as client:
        r = client.post("/webhooks/order-status", json={"order_id": "x", "status": "bogus"})
        assert r.status_code == 400
        assert "Invalid status" in r.json()["error"]


def test_order_status_webhook_order_not_found():
    """POST with valid fields but missing order should return 404."""
    app = _make_test_app(order_status_webhook, "/webhooks/order-status")
    with TestClient(app) as client:
        with patch("app.routes.webhooks.fetch_order_by_id", new_callable=AsyncMock, return_value=None):
            r = client.post("/webhooks/order-status", json={"order_id": "no-such", "status": "paid"})
            assert r.status_code == 404


def test_send_test_email_get_not_allowed():
    """GET should return 405 for test-email endpoint."""
    app = _make_test_app(send_test_email, "/webhooks/test-email")
    with TestClient(app) as client:
        r = client.get("/webhooks/test-email")
        assert r.status_code == 405


def test_send_test_email_missing_email():
    """POST with missing email should return 400."""
    app = _make_test_app(send_test_email, "/webhooks/test-email")
    with TestClient(app) as client:
        r = client.post("/webhooks/test-email", json={})
        assert r.status_code == 400


def test_send_test_email_success():
    """POST with valid email should return 200 with sent status."""
    app = _make_test_app(send_test_email, "/webhooks/test-email")
    with TestClient(app) as client:
        with patch("app.routes.webhooks.send_brevo_email", new_callable=AsyncMock, return_value=True):
            r = client.post("/webhooks/test-email", json={"email": "test@example.com"})
            assert r.status_code == 200
            assert r.json()["sent"] is True
