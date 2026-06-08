# ASIKO Boutique - Storefront Pages Tests
# Tests the homepage, lookbook, product detail, and DPP verification pages.

import os
import pytest
from unittest.mock import MagicMock, AsyncMock
from contextlib import asynccontextmanager
from starlette.testclient import TestClient

# Ensure Django settings are configured for Signer
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from app.routes.storefront import routes as storefront_routes


def _make_pool(products=None):
    """Create a mock pool with optional product data."""
    pool = MagicMock()

    @asynccontextmanager
    async def _acquire():
        conn = MagicMock()

        async def fetch_side_effect(sql, *args):
            return products or []

        async def fetchrow_side_effect(sql, *args):
            return None

        conn.fetch = AsyncMock(side_effect=fetch_side_effect)
        conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)
        yield conn

    pool.acquire = _acquire
    return pool


def _make_app(pool_fn=None):
    """Create a Starlette app with storefront routes."""
    app = Starlette(
        routes=storefront_routes,
        middleware=[Middleware(SessionMiddleware, secret_key="test-key", session_cookie="asiko_test")],
    )
    app.state.db_pool = (pool_fn or _make_pool)()
    return app


def _make_product(pid="test-1", name="Green Agbada", price=45000, stock=8, image="/static/uploads/test.jpg", model_3d=None):
    """Create a mock product row."""
    return {
        "id": pid,
        "name": name,
        "description": "A beautiful traditional agbada",
        "price": price,
        "stock_quantity": stock,
        "base_image": image,
        "model_3d_url": model_3d,
    }


class TestHomepage:
    """Test the storefront homepage."""

    def test_homepage_returns_200(self):
        """GET / returns 200."""
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert response.status_code == 200

    def test_homepage_shows_product_name(self):
        """Homepage displays product names."""
        pool = _make_pool(products=[_make_product()])
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert "Green Agbada" in response.text

    def test_homepage_shows_price_in_naira(self):
        """Homepage displays prices with Naira symbol."""
        pool = _make_pool(products=[_make_product(price=45000)])
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        # naira filter outputs ₦45,000 or &#8358;45,000 depending on template rendering
        assert "45,000" in response.text

    def test_homepage_product_links_to_pdp(self):
        """Product cards link to the product detail page."""
        pid = "link-test-123"
        pool = _make_pool(products=[_make_product(pid=pid)])
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert f"/product/{pid}" in response.text

    def test_homepage_shows_product_image(self):
        """Product cards show actual images when available."""
        pool = _make_pool(products=[_make_product(image="/static/uploads/green.jpg")])
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert "/static/uploads/green.jpg" in response.text

    def test_homepage_shows_3d_badge(self):
        """Product cards show 3D badge when model exists."""
        pool = _make_pool(products=[_make_product(model_3d="/models/test.glb")])
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert "3D" in response.text

    def test_homepage_empty_products(self):
        """Homepage renders gracefully with no products."""
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert response.status_code == 200

    def test_homepage_has_dark_mode_classes(self):
        """Homepage has dark mode Tailwind classes."""
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert "dark:" in response.text

    def test_homepage_has_cart_form(self):
        """Product cards have Add to Cart forms."""
        pool = _make_pool(products=[_make_product()])
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert "hx-post=\"/cart/add\"" in response.text


class TestLookbook:
    """Test the lookbook page."""

    def test_lookbook_returns_200(self):
        """GET /lookbook returns 200."""
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/lookbook")
        assert response.status_code == 200

    def test_lookbook_shows_product_name(self):
        """Lookbook displays product names."""
        pool = _make_pool(products=[_make_product()])
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/lookbook")
        assert "Green Agbada" in response.text

    def test_lookbook_shows_price(self):
        """Lookbook displays prices."""
        pool = _make_pool(products=[_make_product(price=45000)])
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/lookbook")
        assert "45,000" in response.text

    def test_lookbook_links_to_pdp(self):
        """Lookbook product cards link to PDP."""
        pid = "lookbook-link-456"
        pool = _make_pool(products=[_make_product(pid=pid)])
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/lookbook")
        assert f"/product/{pid}" in response.text

    def test_lookbook_empty_state(self):
        """Lookbook shows empty state when no products."""
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert response.status_code == 200

    def test_lookbook_has_hero(self):
        """Lookbook page has the hero section."""
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/lookbook")
        assert "The Lookbook" in response.text

    def test_lookbook_has_dark_mode(self):
        """Lookbook has dark mode classes."""
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/lookbook")
        assert "dark:" in response.text


class TestProductDetail:
    """Test the storefront product detail page."""

    def _make_pool_for_pdp(self, product_data=None):
        """Mock pool for PDP tests."""
        pool = MagicMock()
        pid = product_data.get("id", 1) if product_data else 1

        @asynccontextmanager
        async def _acquire():
            conn = MagicMock()

            async def fetchrow_side_effect(sql, *args):
                if "FROM products WHERE id" in sql:
                    return product_data or {
                        "id": pid,
                        "name": "Green Agbada",
                        "description": "Hand-stitched traditional agbada",
                        "price": 45000,
                        "base_image": "/static/uploads/green.jpg",
                        "model_3d_url": None,
                    }
                if "FROM asiko_capsule_assignments" in sql:
                    return None
                return None

            async def fetch_side_effect(sql, *args):
                return []

            conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)
            conn.fetch = AsyncMock(side_effect=fetch_side_effect)
            yield conn

        pool.acquire = _acquire
        return pool

    def test_pdp_returns_200(self):
        """GET /product/{id} returns 200."""
        pool = self._make_pool_for_pdp()
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/product/1")
        assert response.status_code == 200

    def test_pdp_shows_product_name(self):
        """PDP displays the product name."""
        pool = self._make_pool_for_pdp()
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/product/1")
        assert "Green Agbada" in response.text

    def test_pdp_shows_price(self):
        """PDP displays the price in Naira."""
        pool = self._make_pool_for_pdp()
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/product/1")
        assert "&#8358;" in response.text
        assert "45,000" in response.text

    def test_pdp_shows_description(self):
        """PDP displays the product description."""
        pool = self._make_pool_for_pdp()
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/product/1")
        assert "Hand-stitched traditional agbada" in response.text

    def test_pdp_has_breadcrumb(self):
        """PDP has a back-to-store breadcrumb."""
        pool = self._make_pool_for_pdp()
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/product/1")
        assert "Back to Store" in response.text
        assert 'href="/"' in response.text

    def test_pdp_has_measurement_section(self):
        """PDP has the measurement blueprints accordion."""
        pool = self._make_pool_for_pdp()
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/product/1")
        assert "Size &amp; Measurements" in response.text or "Size & Measurements" in response.text

    def test_pdp_has_whatsapp_link(self):
        """PDP has a WhatsApp concierge link."""
        pool = self._make_pool_for_pdp()
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/product/1")
        assert "catalog/concierge/redirect" in response.text

    def test_pdp_nonexistent_product(self):
        """PDP for nonexistent product returns 404."""
        pool = MagicMock()

        @asynccontextmanager
        async def _acquire():
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=None)
            conn.fetch = AsyncMock(return_value=[])
            yield conn

        pool.acquire = _acquire
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/product/99999")
        assert response.status_code == 404

    def test_pdp_has_dark_mode(self):
        """PDP has dark mode classes."""
        pool = self._make_pool_for_pdp()
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/product/1")
        assert "dark:" in response.text

    def test_pdp_with_3d_model_shows_badge(self):
        """PDP shows 3D badge when model exists."""
        pool = self._make_pool_for_pdp(product_data={
            "id": 1,
            "name": "3D Jacket",
            "description": "A jacket with 3D model",
            "price": 30000,
            "base_image": "/static/uploads/jacket.jpg",
            "model_3d_url": "/models/jacket.glb",
        })
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/product/1")
        assert "View in 3D" in response.text


class TestDPPVerification:
    """Test the DPP verification page."""

    def test_dpp_returns_200(self):
        """GET /dpp returns 200."""
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/dpp")
        assert response.status_code == 200

    def test_dpp_empty_serial(self):
        """DPP with no serial shows empty lookup state."""
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/dpp")
        assert response.status_code == 200

    def test_dpp_invalid_serial(self):
        """DPP with invalid serial format shows unverified state."""
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/dpp?serial=INVALID-SERIAL")
        assert response.status_code == 200


class TestProductGridFragment:
    """Test the HTMX product grid fragment."""

    def test_grid_fragment_returns_200(self):
        """GET /htmx/products returns 200."""
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/htmx/products")
        assert response.status_code == 200

    def test_grid_fragment_shows_products(self):
        """Grid fragment displays product names."""
        pool = _make_pool(products=[_make_product()])
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/htmx/products")
        assert "Green Agbada" in response.text

    def test_grid_fragment_links_to_pdp(self):
        """Grid fragment product cards link to PDP."""
        pid = "grid-link-789"
        pool = _make_pool(products=[_make_product(pid=pid)])
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/htmx/products")
        assert f"/product/{pid}" in response.text

    def test_grid_fragment_shows_image(self):
        """Grid fragment shows product images."""
        pool = _make_pool(products=[_make_product(image="/static/uploads/test.jpg")])
        app = _make_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/htmx/products")
        assert "/static/uploads/test.jpg" in response.text


# ============================================================
# Virtual Atelier Tests
# ============================================================

from app.routes.virtual import routes as virtual_routes


def _make_virtual_app(pool_fn=None):
    """Create a Starlette app with virtual atelier routes."""
    app = Starlette(
        routes=virtual_routes,
        middleware=[Middleware(SessionMiddleware, secret_key="test-key", session_cookie="asiko_test")],
    )
    app.state.db_pool = (pool_fn or _make_pool)()
    return app


def _make_showroom_product(pid="showroom-1", name="Silk Blazer", price=120000,
                           model_3d="/static/uploads/models/blazer.glb",
                           variant=None):
    """Create a mock showroom product record with optional variant data."""
    base = {
        "id": pid,
        "name": name,
        "model_3d_url": model_3d,
        "price": price,
    }
    if variant:
        base.update({
            "variant_id": variant.get("variant_id", "v-1"),
            "size": variant.get("size", "M"),
            "color": variant.get("color", "Black"),
            "mesh_node_identifier": variant.get("mesh", "blazer_form"),
            "custom_shader_color": variant.get("color_hex", "#0D2A22"),
        })
    else:
        base.update({
            "variant_id": None,
            "size": None,
            "color": None,
            "mesh_node_identifier": None,
            "custom_shader_color": None,
        })
    return base


class TestVirtualExperience:
    """Test the /virtual-experience page."""

    def test_virtual_experience_returns_200(self):
        """GET /virtual-experience returns 200."""
        app = _make_virtual_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/virtual-experience")
        assert response.status_code == 200

    def test_virtual_experience_has_canvas(self):
        """Page includes the Three.js canvas element."""
        app = _make_virtual_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/virtual-experience")
        assert "atelier-33d-canvas" in response.text

    def test_virtual_experience_has_gender_switch(self):
        """Page includes male/female gender toggle."""
        app = _make_virtual_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/virtual-experience")
        assert "switchGender" in response.text


class TestShowroomItems:
    """Test the /api/virtual/showroom-items HTMX fragment."""

    def test_showroom_returns_200(self):
        """GET /api/virtual/showroom-items returns 200."""
        app = _make_virtual_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/virtual/showroom-items")
        assert response.status_code == 200

    def test_showroom_empty_state(self):
        """Empty database shows 'No 3D assets' message."""
        app = _make_virtual_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/virtual/showroom-items")
        assert "No 3D assets" in response.text

    def test_showroom_displays_product_name(self):
        """Showroom displays product names when 3D models exist."""
        product = _make_showroom_product(
            name="Emerind Agbada",
            variant={"size": "L", "color": "Emerald", "mesh": "agbada_form", "color_hex": "#2d6a4f"},
        )
        pool = _make_pool(products=[product])
        app = _make_virtual_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/virtual/showroom-items")
        assert "Emerind Agbada" in response.text

    def test_showroom_displays_model_url_in_dispatch(self):
        """Showroom cards dispatch load-showroom-model with modelUrl."""
        model_url = "/static/uploads/models/test_dress.glb"
        product = _make_showroom_product(model_3d=model_url)
        pool = _make_pool(products=[product])
        app = _make_virtual_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/virtual/showroom-items")
        assert model_url in response.text
        assert "load-showroom-model" in response.text

    def test_showroom_product_without_variant(self):
        """Products without variants still appear (LEFT JOIN fix)."""
        product = _make_showroom_product(
            pid="no-variant-prod",
            name="Solo Gown",
            variant=None,
        )
        pool = _make_pool(products=[product])
        app = _make_virtual_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/virtual/showroom-items")
        assert "Solo Gown" in response.text
        assert "load-showroom-model" in response.text

    def test_showroom_shows_variant_details(self):
        """Showroom displays variant color and size info."""
        product = _make_showroom_product(
            variant={"size": "S", "color": "Ivory", "mesh": "dress_form", "color_hex": "#FFFFF0"},
        )
        pool = _make_pool(products=[product])
        app = _make_virtual_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/virtual/showroom-items")
        assert "Ivory" in response.text
        assert "Size S" in response.text

    def test_showroom_aria_labels(self):
        """Showroom cards have accessible aria-label."""
        product = _make_showroom_product(name="Structured Top")
        pool = _make_pool(products=[product])
        app = _make_virtual_app(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/virtual/showroom-items")
        assert 'aria-label="View Structured Top"' in response.text
