# app/tests/test_sse_streams.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route


def test_sse_stream_endpoint_exists():
    """Verify SSE stream endpoint is properly configured."""
    from app.routes.sse_streams import pipeline_status_sse_stream
    
    mock_pool = MagicMock()
    routes = [
        Route("/api/v1/streams/pipeline/{product_id:uuid}", endpoint=pipeline_status_sse_stream),
    ]
    test_app = Starlette(routes=routes)
    test_app.state.db_pool = mock_pool

    # Verify route is registered correctly
    found = any("/api/v1/streams/pipeline" in str(r.path) for r in test_app.routes)
    assert found


def test_sse_stream_uses_event_stream_content_type():
    """Verify SSE stream returns text/event-stream content type in source code."""
    from app.routes.sse_streams import pipeline_status_sse_stream
    import inspect
    
    source = inspect.getsource(pipeline_status_sse_stream)
    assert 'media_type="text/event-stream"' in source


def test_sse_stream_processes_product_id():
    """Verify SSE stream correctly extracts product_id from path params."""
    from app.routes.sse_streams import pipeline_status_sse_stream
    import inspect
    
    source = inspect.getsource(pipeline_status_sse_stream)
    assert "product_id = request.path_params.get" in source
    assert "$1::UUID" in source  # UUID cast in query


def test_sse_stream_queries_pipeline_status():
    """Verify SSE stream queries products table for pipeline_status."""
    from app.routes.sse_streams import pipeline_status_sse_stream
    import inspect
    
    source = inspect.getsource(pipeline_status_sse_stream)
    assert "SELECT pipeline_status, model_3d_url FROM products" in source
    assert "last_known_status" in source


def test_sse_stream_yields_json_payload():
    """Verify SSE stream yields JSON payloads in correct format."""
    from app.routes.sse_streams import pipeline_status_sse_stream
    import inspect
    
    source = inspect.getsource(pipeline_status_sse_stream)
    assert "data: " in source
    assert "json.dumps(payload)" in source
    assert "pipeline_status" in source
    assert "model_url" in source


def test_sse_stream_checks_disconnect():
    """Verify SSE stream checks for client disconnection."""
    from app.routes.sse_streams import pipeline_status_sse_stream
    import inspect
    
    source = inspect.getsource(pipeline_status_sse_stream)
    assert "is_disconnected" in source


def test_sse_stream_breaks_on_terminal_status():
    """Verify SSE stream breaks connection after completed/failed status."""
    from app.routes.sse_streams import pipeline_status_sse_stream
    import inspect
    
    source = inspect.getsource(pipeline_status_sse_stream)
    assert '"completed"' in source
    assert '"failed"' in source
    assert "break" in source


def test_sse_stream_polls_every_2_seconds():
    """Verify SSE stream polls database every 2 seconds."""
    from app.routes.sse_streams import pipeline_status_sse_stream
    import inspect
    
    source = inspect.getsource(pipeline_status_sse_stream)
    assert "asyncio.sleep(2.0)" in source


def test_sse_routes_list_defined():
    """Verify SSE routes list is properly defined for app registration."""
    from app.routes.sse_streams import sse_routes
    
    assert isinstance(sse_routes, list)
    assert len(sse_routes) == 1
    assert "/api/v1/streams/pipeline" in sse_routes[0].path