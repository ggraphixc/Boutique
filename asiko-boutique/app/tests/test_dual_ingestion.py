# app/tests/test_dual_ingestion.py
import pytest


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

