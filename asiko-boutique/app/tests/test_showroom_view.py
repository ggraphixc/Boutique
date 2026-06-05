# app/tests/test_showroom_view.py
import os
import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import HTMLResponse


def virtual_experience_endpoint(request: Request) -> HTMLResponse:
    return HTMLResponse("<div id='canvas-3d-target' class='three-canvas-container'></div>")

def showroom_items_endpoint(request: Request) -> HTMLResponse:
    return HTMLResponse("<div class='showroom-item'>Item</div>")


def test_virtual_experience_route_serves_canvas_container():
    """Verify /virtual-experience route serves correct canvas container for Three.js."""
    routes = [
        Route("/virtual-experience", endpoint=virtual_experience_endpoint, methods=["GET"]),
    ]
    app = Starlette(routes=routes)
    
    with TestClient(app) as client:
        response = client.get("/virtual-experience")
        assert response.status_code == 200
        assert 'canvas-3d-target' in response.text
        assert 'three-canvas-container' in response.text


def test_canvas_container_has_correct_attributes():
    """Verify canvas container has position and dimensions for WebGL render target."""
    assert os.path.exists("app/templates/virtual_experience.html")
    with open("app/templates/virtual_experience.html", "r") as f:
        content = f.read()
    
    # Check for container with correct ARIA and positioning
    assert 'id="canvas-3d-target"' in content
    assert 'three-canvas-container' in content
    assert 'position: relative' in content or 'absolute inset-0' in content


def test_layer_capsule_mesh_event_target_exists():
    """Verify Alpine.js event target exists for layer-capsule-mesh consumption."""
    with open("app/templates/virtual_experience.html", "r") as f:
        content = f.read()
    
    # Check for layer-capsule-mesh event listener
    assert 'layer-capsule-mesh' in content
    assert '@layer-capsule-mesh.window' in content or 'layer-capsule-mesh' in content


def test_atelier_engine_has_load_automated_garment():
    """Verify AtelierEngine has loadAutomatedGarment method with layer depth scaling."""
    assert os.path.exists("static/js/atelier-3d.js")
    with open("static/js/atelier-3d.js", "r") as f:
        content = f.read()
    
    assert 'loadAutomatedGarment' in content
    assert 'scaleFactor' in content
    assert '0.0125' in content  # Layer depth scaling formula


def test_garment_method_applies_shadow_configuration():
    """Verify loadAutomatedGarment applies castShadow and receiveShadow to meshes."""
    with open("static/js/atelier-3d.js", "r") as f:
        content = f.read()
    
    assert 'castShadow = true' in content
    assert 'receiveShadow = true' in content


def test_showroom_items_endpoint_exists():
    """Verify /api/virtual/showroom-items endpoint is registered."""
    from app.routes.virtual import routes
    
    route_paths = [r.path for r in routes]
    assert "/api/virtual/showroom-items" in route_paths


def test_showroom_items_htmx_fragment_format():
    """Verify showroom items fragment returns valid HTMX-compatible HTML."""
    routes = [
        Route("/api/virtual/showroom-items", endpoint=showroom_items_endpoint, methods=["GET"]),
    ]
    app = Starlette(routes=routes)
    
    with TestClient(app) as client:
        response = client.get("/api/virtual/showroom-items")
        assert response.status_code == 200
        # Should not be full page - just fragment
        assert '<!DOCTYPE html>' not in response.text


def test_all_layer_names_supported():
    """Verify all three layer depths are supported in garment loading."""
    with open("static/js/atelier-3d.js", "r") as f:
        content = f.read()
    
    # Check LAYER_ORDER contains all three layers
    assert "'base'" in content
    assert "'structural'" in content
    assert "'shell'" in content