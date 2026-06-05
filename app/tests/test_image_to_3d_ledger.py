# app/tests/test_image_to_3d_ledger.py
import pytest
from starlette.testclient import TestClient
from app.main import app

def test_product_creation_initializes_3d_pipeline():
    """Guarantees that provisioning a raw photo asset flags the tracking pipeline state as queued."""
    with TestClient(app) as client:
        # Simulate a non-technical store owner uploading an item image
        payload = {
            "name": "Luxury Ankara Gown",
            "source_2d_image_url": "/static/uploads/ankara_gown_front.jpg",
            "target_skeleton_fit": "female",
            "apparel_layer_depth": 2
        }
        
        # Post payload structure toward standard injection API endpoint lines
        response = client.post("/api/admin/products/provision", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["pipeline_status"] == "queued"
        assert data["model_3d_url"] is None  # Must remain empty until processing finishes execution

def test_pipeline_failure_logging_constraints():
    """Validates that asset generation failures cleanly populate debugging vectors without crashing."""
    with TestClient(app) as client:
        # Simulate a processing update signaling an image clarity failure
        failure_update = {
            "pipeline_status": "failed",
            "pipeline_error_log": "AI_MESH_GENERATOR_ERROR: Low image contrast. Edge extraction failed.",
            "automated_mesh_retry_count": 1
        }
        
        response = client.patch("/api/internal/pipeline/update/999", json=failure_update)
        
        assert response.status_code == 200
        assert response.json()["status"] == "state_locked_failed"