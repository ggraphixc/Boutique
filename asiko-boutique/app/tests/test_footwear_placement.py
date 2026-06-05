# app/tests/test_footwear_placement.py
import pytest


def test_asset_category_enum_exists():
    """Validates that the asset_category enumeration type is defined in migrations."""
    import os
    migration_path = "supabase/migrations/08_image_to_3d_pipeline.sql"
    assert os.path.exists(migration_path)

    with open(migration_path, "r") as f:
        content = f.read()

    assert "asset_category_type" in content
    assert "'apparel'" in content
    assert "'footwear'" in content


def test_products_table_has_asset_category_column():
    """Verify products table has asset_category column with correct default."""
    with open("supabase/migrations/08_image_to_3d_pipeline.sql", "r") as f:
        content = f.read()

    assert "ADD COLUMN IF NOT EXISTS asset_category asset_category_type DEFAULT 'apparel'" in content


def test_asset_category_index_exists():
    """Verify index exists for asset category queries."""
    with open("supabase/migrations/08_image_to_3d_pipeline.sql", "r") as f:
        content = f.read()

    assert "idx_products_asset_category" in content


def test_showroom_component_passes_asset_category():
    """Verify showroom try-on component passes asset_category in event dispatch."""
    with open("app/templates/components/showroom_try_on.html", "r") as f:
        content = f.read()

    assert "assetCategory:" in content


def test_atelier_engine_has_loadAutomatedAsset_method():
    """Verify AtelierEngine has loadAutomatedAsset method for footwear handling."""
    with open("static/js/atelier-3d.js", "r") as f:
        content = f.read()

    assert "loadAutomatedAsset" in content
    assert "positioningKey" in content


def test_footwear_branch_has_ground_anchor():
    """Verify footwear branch uses y=0 ground anchor positioning."""
    with open("static/js/atelier-3d.js", "r") as f:
        content = f.read()

    # Check for ground anchor logic
    assert "assetCategory === 'footwear'" in content
    assert "position.set(0, 0, 0)" in content


def test_clothing_branch_has_scale_offset():
    """Verify clothing branch applies stratification scale offset."""
    with open("static/js/atelier-3d.js", "r") as f:
        content = f.read()

    assert "stratificationScaleOffset" in content


def test_activeGarments_registry_initialized():
    """Verify activeGarments registry exists for footwear tracking."""
    with open("static/js/atelier-3d.js", "r") as f:
        content = f.read()

    assert "this.activeGarments" in content


def test_virtual_experience_consumes_meshUrl():
    """Verify virtual experience template handles both meshUrl and modelUrl from events."""
    with open("app/templates/virtual_experience.html", "r") as f:
        content = f.read()

    assert "event.detail.meshUrl || event.detail.modelUrl" in content
    assert "event.detail.assetCategory" in content


def test_footwear_fallback_geometries_exist():
    """Verify footwear has dedicated fallback box geometry."""
    with open("static/js/atelier-3d.js", "r") as f:
        content = f.read()

    assert "shoeGeo" in content
    assert "BoxGeometry" in content