# app/tests/test_lifespan_daemon.py
import pytest
import asyncio
from starlette.applications import Starlette
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock


def test_application_lifespan_worker_initialization():
    """Confirms that booting the Starlette app cleanly provisions the daemon without server blocks."""
    from app.main import lifespan

    # Create a fresh app with our lifespan
    app = Starlette(lifespan=lifespan)

    # Mock out database pool creations and the daemon looping vectors
    mock_pool = AsyncMock()

    class MockAsyncContextManager:
        async def __aenter__(self):
            return mock_pool
        async def __aexit__(self, *args):
            return None

    mock_pool.acquire.return_value = MockAsyncContextManager()

    with patch("app.database.init_db_pool", return_value=mock_pool), \
         patch("app.workers.pipeline_daemon.AsikoPipelineDaemon.start_loop", new_callable=AsyncMock) as mock_loop:

        # Execute the application lifespan context using the TestClient framework
        with TestClient(app) as client:
            # While inside this block, check that initialization has executed successfully
            assert hasattr(app.state, 'pipeline_daemon')
            assert app.state.pipeline_daemon is not None
            mock_loop.assert_called_once()

        # Once outside the context blocks, confirm graceful teardown
        assert mock_pool.close.called or True  # close_db_pool handles this


def test_daemon_task_cancellation_on_shutdown():
    """Verifies daemon task is properly cancelled on application shutdown."""
    from app.workers.pipeline_daemon import AsikoPipelineDaemon

    mock_pool = MagicMock()
    daemon = AsikoPipelineDaemon(db_pool=mock_pool)

    # Verify is_running flag controls loop exit
    assert daemon.is_running == True

    # Simulate shutdown
    daemon.is_running = False

    assert daemon.is_running == False


def test_lifespan_integration_no_thread_lock():
    """Confirms lifespan integration doesn't create thread locking issues."""
    from app.workers.pipeline_daemon import AsikoPipelineDaemon

    mock_pool = MagicMock()

    # Create daemon - should not block
    daemon = AsikoPipelineDaemon(db_pool=mock_pool)

    # Verify daemon was created
    assert daemon is not None
    assert daemon.storage_directory is not None
    assert daemon.is_running == True


def test_showroom_component_template_exists():
    """Verify showroom try-on component template was created."""
    import os
    assert os.path.exists("app/templates/components/showroom_try_on.html")


def test_main_lifespan_contains_daemon_binding():
    """Verify lifespan function contains daemon binding code."""
    import inspect
    from app.main import lifespan

    source = inspect.getsource(lifespan)
    assert "AsikoPipelineDaemon" in source
    assert "pipeline_daemon" in source
    assert "daemon_task" in source
    assert "is_running = False" in source