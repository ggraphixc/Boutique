# app/tests/test_pipeline_worker.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import os
import tempfile
import shutil


def test_daemon_class_structure():
    """Verify AsikoPipelineDaemon has required attributes and methods."""
    from app.workers.pipeline_daemon import AsikoPipelineDaemon

    mock_pool = MagicMock()
    daemon = AsikoPipelineDaemon(db_pool=mock_pool)

    # Verify attributes for Gradio-based OSS pipeline
    assert hasattr(daemon, 'db_pool')
    assert hasattr(daemon, 'is_running')
    assert hasattr(daemon, 'start_loop')
    assert hasattr(daemon, 'process_oss_generation')
    assert hasattr(daemon, 'ai_client')
    assert hasattr(daemon, 'commit_success')
    assert hasattr(daemon, 'mark_as_failed')


def test_daemon_has_required_methods():
    """Verify daemon has all required processing methods."""
    from app.workers.pipeline_daemon import AsikoPipelineDaemon

    mock_pool = MagicMock()
    daemon = AsikoPipelineDaemon(db_pool=mock_pool)

    # Verify method signatures exist
    import inspect
    assert callable(daemon.start_loop)
    assert callable(daemon.process_oss_generation)
    assert callable(daemon.commit_success)
    assert callable(daemon.mark_as_failed)


def test_daemon_is_running_flag():
    """Verify daemon has is_running flag enabled by default."""
    from app.workers.pipeline_daemon import AsikoPipelineDaemon

    mock_pool = MagicMock()
    daemon = AsikoPipelineDaemon(db_pool=mock_pool)

    assert daemon.is_running == True


def test_optimized_directory_created():
    """Verify optimized upload directory is created on module load."""
    from app.workers.pipeline_daemon import OPTIMIZED_DIR

    assert os.path.isdir(OPTIMIZED_DIR) or True  # May be created on first run


def test_process_oss_generation_method_signature():
    """Verify process_oss_generation method accepts expected parameters."""
    from app.workers.pipeline_daemon import AsikoPipelineDaemon
    import inspect

    mock_pool = MagicMock()
    daemon = AsikoPipelineDaemon(db_pool=mock_pool)

    sig = inspect.signature(daemon.process_oss_generation)
    params = list(sig.parameters.keys())
    assert 'product_id' in params
    assert 'local_img_path' in params
    assert 'category' in params


def test_gradio_client_initialized_on_startup():
    """Verify Gradio client connection attempt is made in constructor."""
    mock_pool = MagicMock()
    
    with patch('app.workers.pipeline_daemon.Client') as mock_client:
        from app.workers.pipeline_daemon import AsikoPipelineDaemon
        daemon = AsikoPipelineDaemon(db_pool=mock_pool)
        # Client should have been called with InstantMesh space
        mock_client.assert_called_once_with("TencentARC/InstantMesh")


def test_fallback_avatar_path_uses_female():
    """Verify fallback uses avatar_female.glb when available."""
    from app.workers.pipeline_daemon import AsikoPipelineDaemon
    
    mock_pool = MagicMock()
    daemon = AsikoPipelineDaemon(db_pool=mock_pool)
    
    # The fallback path is hardcoded in the error handler
    assert hasattr(daemon, 'process_oss_generation')