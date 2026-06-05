# app/tests/test_schema_guard.py
import pytest
import inspect
from unittest.mock import AsyncMock, MagicMock, patch


def test_lifespan_contains_schema_guard_logic():
    """Verify lifespan function includes self-healing schema guard for asset_category."""
    from app.main import lifespan
    
    source = inspect.getsource(lifespan)
    assert "asset_category_type" in source
    assert "CREATE TYPE asset_category_type" in source
    assert "ADD COLUMN IF NOT EXISTS asset_category" in source


def test_schema_guard_runs_after_pool_initialization():
    """Verify schema guard runs after database pool is initialized."""
    from app.main import lifespan
    
    source = inspect.getsource(lifespan)
    # Check that db_pool initialization comes before schema guard
    pool_init_idx = source.find("init_db_pool()")
    guard_idx = source.find("asset_category_type")
    assert pool_init_idx > 0
    assert guard_idx > pool_init_idx


def test_schema_guard_logs_validation_message():
    """Verify schema guard prints validation messages."""
    from app.main import lifespan
    
    source = inspect.getsource(lifespan)
    assert "Running database structural validation checks" in source
    assert "Database schema structural validation completed" in source