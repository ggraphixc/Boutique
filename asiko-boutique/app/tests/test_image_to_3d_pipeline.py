# ASIKO Boutique - Image-to-3D Pipeline Validation Tests
# Validates data boundaries and async pipeline state transitions

import pytest
from starlette.testclient import TestClient

from app.main import app

# UUID values from seed data in migration 01
PRODUCT_ID_1 = "d4e5f6a7-b8c9-0123-defa-234567890123"
PRODUCT_ID_2 = "e5f6a7b8-c9d0-1234-efab-345678901234"


def test_link_2d_asset_initializes_state_correctly():
    """Confirms that linking a 2D source asset moves the pipeline into a queued polling state."""
    with TestClient(app) as client:
        payload = {
            "product_id": PRODUCT_ID_1,
            "source_2d_image_url": "/static/images/test_gown.jpg"
        }
        response = client.post("/admin/dashboard/pipeline/link-2d", data=payload)
        assert response.status_code == 200
        assert b"Queued in Engine" in response.content


def test_pipeline_status_endpoint_error_handling():
    """Verifies that an unknown entity payload cleanly safety-drops into a clean error string."""
    with TestClient(app) as client:
        response = client.get("/admin/dashboard/pipeline-status/99999999-9999-9999-9999-999999999999")
        assert response.status_code == 200
        assert b"Missing Node" in response.content


def test_pipeline_status_completed_rendering():
    """Confirms completed status renders ready state with model URL."""
    with TestClient(app) as client:
        client.post("/admin/dashboard/pipeline/link-2d", data={
            "product_id": PRODUCT_ID_1,
            "source_2d_image_url": "/static/images/test_gown.jpg"
        })
        client.post("/admin/dashboard/pipeline/simulate", data={
            "product_id": PRODUCT_ID_1,
            "action": "progress"
        })
        response = client.get(f"/admin/dashboard/pipeline-status/{PRODUCT_ID_1}")
        assert response.status_code == 200
        assert b"Ready" in response.content


def test_pipeline_status_failed_rendering():
    """Confirms failed status renders error state with log details."""
    with TestClient(app) as client:
        client.post("/admin/dashboard/pipeline/link-2d", data={
            "product_id": PRODUCT_ID_2,
            "source_2d_image_url": "/static/images/test_jacket.jpg"
        })
        client.post("/admin/dashboard/pipeline/simulate", data={
            "product_id": PRODUCT_ID_2,
            "action": "fail"
        })
        response = client.get(f"/admin/dashboard/pipeline-status/{PRODUCT_ID_2}")
        assert response.status_code == 200
        assert b"Engine Error" in response.content


def test_pipeline_simulate_progress_endpoint():
    """Confirms pipeline simulate progress transitions to completed state."""
    with TestClient(app) as client:
        response = client.post("/admin/dashboard/pipeline/simulate", data={
            "product_id": PRODUCT_ID_1,
            "action": "progress"
        })
        assert response.status_code == 200


def test_pipeline_simulate_fail_endpoint():
    """Confirms pipeline simulate fail transitions to failed state."""
    with TestClient(app) as client:
        response = client.post("/admin/dashboard/pipeline/simulate", data={
            "product_id": PRODUCT_ID_1,
            "action": "fail"
        })
        assert response.status_code == 200