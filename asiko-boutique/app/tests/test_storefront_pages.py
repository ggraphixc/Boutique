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


def _make_product(pid="test-1", name="Green Agbada", price=45000, stock=8, image="/static/uploads/test.jpg", category_name="Tailoring"):
    """Create a mock product row."""
    return {
        "id": pid,
        "name": name,
        "description": "A beautiful traditional agbada",
        "price": price,
        "stock_quantity": stock,
        "base_image": image,
        "category_name": category_name,
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
        response = client.get("/lookbook")
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

