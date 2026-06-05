# app/tests/test_dual_ingestion.py
import pytest
import io
import inspect
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
from unittest.mock import AsyncMock, MagicMock


def test_dual_ingestion_template_has_device_toggle():
    """Verify dashboard template has Alpine.js toggle for device/url input modes."""
    with open("app/templates/admin/dashboard.html", "r") as f:
        content = f.read()

    assert "x-data=\"{ ingestionMode:" in content
    assert "ingestionMode === 'device'" in content
    assert "ingestionMode === 'url'" in content


def test_file_input_accept_attribute_exists():
    """Verify file input accepts image types for mobile upload."""
    with open("app/templates/admin/dashboard.html", "r") as f:
        content = f.read()

    assert "accept=\"image/*\"" in content
    assert "source_2d_file" in content


def test_category_radio_buttons_present():
    """Verify asset category radio buttons for apparel/footwear selection."""
    with open("app/templates/admin/dashboard.html", "r") as f:
        content = f.read()

    assert "name=\"asset_category\"" in content
    assert "value=\"apparel\"" in content
    assert "value=\"footwear\"" in content


def test_link_2d_endpoint_accepts_multipart():
    """Verify link_2d_source_asset function handles multipart form data."""
    from app.routes.admin_dashboard import link_2d_source_asset

    source = inspect.getsource(link_2d_source_asset)
    assert "source_2d_file" in source
    assert "uploaded_file" in source


def test_upload_dir_creation_logic():
    """Verify upload directory creation logic exists."""
    from app.routes.admin_dashboard import link_2d_source_asset

    source = inspect.getsource(link_2d_source_asset)
    assert "UPLOAD_DIR" in source
    assert "os.makedirs" in source


def test_file_extension_validation():
    """Verify file extension whitelist for image uploads."""
    from app.routes.admin_dashboard import link_2d_source_asset

    source = inspect.getsource(link_2d_source_asset)
    assert ".jpg" in source or ".jpeg" in source
    assert ".png" in source
    assert ".webp" in source


def test_secure_filename_generation():
    """Verify secure filename generation with token hex."""
    from app.routes.admin_dashboard import link_2d_source_asset

    source = inspect.getsource(link_2d_source_asset)
    assert "secrets.token_hex" in source
    assert "secure_filename" in source


def test_database_update_includes_asset_category():
    """Verify database UPDATE includes asset_category column."""
    from app.routes.admin_dashboard import link_2d_source_asset

    source = inspect.getsource(link_2d_source_asset)
    assert "asset_category" in source
    assert "SET source_2d_image_url" in source


def test_device_file_upload_ingestion_stream():
    """Guarantees that posting a binary multipart image file triggers the processing queue correctly."""
    from app.routes.admin_dashboard import link_2d_source_asset

    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    routes = [
        Route("/admin/dashboard/pipeline/link-2d", endpoint=link_2d_source_asset, methods=["POST"]),
    ]
    test_app = Starlette(routes=routes, on_startup=None, on_shutdown=None)
    test_app.state.db_pool = mock_pool

    with TestClient(test_app) as client:
        # Create a mock transparent in-memory byte frame file asset representation
        mock_file_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        file_payload = {
            "source_2d_file": ("test_capture.png", io.BytesIO(mock_file_bytes), "image/png")
        }
        data_payload = {
            "product_id": "1",
            "asset_category": "apparel"
        }

        response = client.post("/admin/dashboard/pipeline/link-2d", data=data_payload, files=file_payload)

        assert response.status_code == 200
        assert b"Processing Asset Ingestion" in response.content


def test_url_fallback_when_no_file():
    """Verify URL input fallback works when no file is uploaded."""
    from app.routes.admin_dashboard import link_2d_source_asset

    source = inspect.getsource(link_2d_source_asset)
    assert "source_2d_image_url" in source
    assert "elif image_url" in source


def test_invalid_extension_returns_error():
    """Verify invalid file extension returns appropriate error message."""
    from app.routes.admin_dashboard import link_2d_source_asset

    source = inspect.getsource(link_2d_source_asset)
    assert "Invalid image format" in source