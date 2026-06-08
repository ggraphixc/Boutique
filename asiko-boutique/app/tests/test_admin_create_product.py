# ASIKO Boutique - Admin Create Product Endpoint
# Tests the POST /admin/products/create endpoint for product creation.

import pytest
from unittest.mock import MagicMock, AsyncMock
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.testclient import TestClient

from app.routes.admin import routes as admin_crud_routes
from app.routes.admin_sections import routes as admin_sections_routes


def _make_pool_with_insert():
    """Mock pool that allows insert operations."""
    pool = MagicMock()

    @asynccontextmanager
    async def _acquire():
        conn = MagicMock()
        conn.fetchval = AsyncMock(return_value=None)  # No duplicate slug
        conn.execute = AsyncMock(return_value=None)
        conn.fetch = AsyncMock(return_value=[])  # Empty for product list
        yield conn

    pool.acquire = _acquire
    return pool


def _make_pool_with_store():
    """Mock pool that has a store (required for product creation)."""
    pool = MagicMock()
    store_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    call_count = {"n": 0}

    @asynccontextmanager
    async def _acquire():
        conn = MagicMock()
        # fetchval is called in order: 1) store_id, 2) slug check loop
        # First call returns store_id, subsequent calls return None (no slug conflict)
        async def fetchval_side_effect(sql, *args):
            call_count["n"] += 1
            if "FROM stores" in sql:
                return store_id
            return None  # No duplicate slug

        conn.fetchval = AsyncMock(side_effect=fetchval_side_effect)
        conn.execute = AsyncMock(return_value=None)
        conn.fetch = AsyncMock(return_value=[])  # Empty for product list
        yield conn

    pool.acquire = _acquire
    return pool


def _make_app_with_admin_routes(pool_fn=None):
    """Fresh Starlette app with admin CRUD + section routes + mocked pool."""
    test_app = Starlette(
        routes=admin_crud_routes + admin_sections_routes,
        middleware=[Middleware(SessionMiddleware, secret_key="test-key", session_cookie="asiko_test")],
    )
    test_app.state.db_pool = (pool_fn or _make_pool_with_store)()
    return test_app


class TestCreateProductEndpoint:
    """Test the POST /admin/products/create endpoint."""

    def test_create_product_returns_200(self):
        """POST /admin/products/create returns 200 with valid data."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/admin/products/create",
            data={
                "name": "Test Product",
                "price": "99.99",
                "category": "Outerwear",
                "description": "Test description",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

    def test_create_product_has_hx_redirect(self):
        """POST /admin/products/create returns HX-Redirect header."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/admin/products/create",
            data={
                "name": "Test Product",
                "price": "99.99",
            },
            follow_redirects=False,
        )
        assert "HX-Redirect" in response.headers
        assert response.headers["HX-Redirect"] == "/admin/section/products"

    def test_create_product_success_message(self):
        """POST /admin/products/create returns success message."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/admin/products/create",
            data={
                "name": "Test Product",
                "price": "99.99",
            },
            follow_redirects=False,
        )
        assert "Product created successfully" in response.text

    def test_create_product_missing_name_returns_400(self):
        """POST /admin/products/create with empty name returns 400."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/admin/products/create",
            data={
                "name": "",
                "price": "99.99",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Please enter a product name." in response.text

    def test_create_product_whitespace_name_returns_400(self):
        """POST /admin/products/create with whitespace-only name returns 400."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/admin/products/create",
            data={
                "name": "   ",
                "price": "99.99",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Please enter a product name." in response.text


class TestProductsSectionForm:
    """Test that the products section includes the create form."""

    def test_products_section_has_create_form(self):
        """Products section contains the HTMX form for creating products."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/section/products")
        assert response.status_code == 200
        assert 'hx-post="/admin/products/create"' in response.text

    def test_products_section_has_alpine_modal(self):
        """Products section contains the Alpine modal for new product."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/section/products", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert 'showNewProduct: false' in response.text
        assert 'x-show="showNewProduct"' in response.text

    def test_products_section_has_form_fields(self):
        """Products section form has all required fields."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/section/products")
        assert response.status_code == 200
        assert 'name="name"' in response.text
        assert 'name="price"' in response.text
        assert 'name="category"' in response.text
        assert 'name="description"' in response.text
        assert 'name="source_2d_file"' in response.text

    def test_products_section_has_submit_button(self):
        """Products section form has submit button."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/section/products")
        assert response.status_code == 200
        assert 'type="submit"' in response.text
        assert "Save Product" in response.text

    def test_products_section_has_new_product_button(self):
        """Products section has button to open modal."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/section/products")
        assert response.status_code == 200
        assert '@click="showNewProduct = true"' in response.text


class TestEditProductEndpoint:
    """Test the POST /admin/products/{id}/edit endpoint."""

    def _make_pool_for_edit(self):
        """Mock pool with a product that exists."""
        pool = MagicMock()
        product_id = "test-product-id-123"

        @asynccontextmanager
        async def _acquire():
            conn = MagicMock()
            call_count = {"n": 0}

            async def fetchval_side_effect(sql, *args):
                call_count["n"] += 1
                # First call: check product exists
                if "SELECT id FROM products WHERE id" in sql and "slug" not in sql:
                    return product_id
                # Slug check calls
                if "SELECT id FROM products WHERE slug" in sql:
                    return None  # No slug conflict
                # Category lookup
                if "SELECT id FROM categories WHERE name" in sql:
                    return "cat-123"
                return None

            conn.fetchval = AsyncMock(side_effect=fetchval_side_effect)
            conn.execute = AsyncMock(return_value=None)
            conn.fetch = AsyncMock(return_value=[])
            yield conn

        pool.acquire = _acquire
        return pool, product_id

    def test_edit_product_returns_200(self):
        """POST /admin/products/{id}/edit returns 200 with valid data."""
        pool, pid = self._make_pool_for_edit()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            f"/admin/products/{pid}/edit",
            data={
                "name": "Updated Product",
                "price": "25000",
                "stock_quantity": "10",
                "category": "Dresses",
                "description": "Updated description",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

    def test_edit_product_has_hx_redirect(self):
        """POST /admin/products/{id}/edit returns HX-Redirect header."""
        pool, pid = self._make_pool_for_edit()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            f"/admin/products/{pid}/edit",
            data={
                "name": "Updated Product",
                "price": "25000",
            },
            follow_redirects=False,
        )
        assert "HX-Redirect" in response.headers
        assert response.headers["HX-Redirect"] == "/admin/section/products"

    def test_edit_product_success_message(self):
        """POST /admin/products/{id}/edit returns success message."""
        pool, pid = self._make_pool_for_edit()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            f"/admin/products/{pid}/edit",
            data={
                "name": "Updated Product",
                "price": "25000",
            },
            follow_redirects=False,
        )
        assert "Product updated successfully" in response.text

    def test_edit_product_missing_name_returns_400(self):
        """POST /admin/products/{id}/edit with empty name returns 400."""
        pool, pid = self._make_pool_for_edit()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            f"/admin/products/{pid}/edit",
            data={
                "name": "",
                "price": "25000",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Please enter a product name." in response.text


class TestDeleteProductEndpoint:
    """Test the DELETE /admin/products/{id} endpoint."""

    def _make_pool_for_delete(self):
        """Mock pool with a product that exists."""
        pool = MagicMock()
        product_id = "test-product-id-456"

        @asynccontextmanager
        async def _acquire():
            conn = MagicMock()
            conn.fetchval = AsyncMock(return_value=product_id)  # Product exists
            conn.execute = AsyncMock(return_value=None)
            yield conn

        pool.acquire = _acquire
        return pool, product_id

    def test_delete_product_returns_200(self):
        """DELETE /admin/products/{id} returns 200."""
        pool, pid = self._make_pool_for_delete()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.delete(f"/admin/products/{pid}")
        assert response.status_code == 200

    def test_delete_product_returns_empty_body(self):
        """DELETE /admin/products/{id} returns empty body for HTMX."""
        pool, pid = self._make_pool_for_delete()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.delete(f"/admin/products/{pid}")
        assert response.text == ""


class TestProductsSectionUI:
    """Test the products section UI elements."""

    def test_products_section_has_edit_delete_buttons(self):
        """Products section has Edit and Delete buttons when products exist."""
        from unittest.mock import AsyncMock
        from contextlib import asynccontextmanager

        pool = MagicMock()
        product_id = "test-product-id-789"

        @asynccontextmanager
        async def _acquire():
            conn = MagicMock()
            # _safe_fetch_products calls conn.fetch() with the product query
            conn.fetch = AsyncMock(return_value=[
                {
                    "id": product_id,
                    "name": "Test Jacket",
                    "slug": "test-jacket",
                    "price": 25000.0,
                    "stock_quantity": 5,
                    "base_image": "/static/uploads/test.jpg",
                    "model_3d_url": None,
                    "pipeline_status": "idle",
                    "asset_category": None,
                    "created_at": None,
                    "category_id": "cat-1",
                    "category_name": "Outerwear",
                    "category_color": None,
                }
            ])
            yield conn

        pool.acquire = _acquire

        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/section/products", headers={"HX-Request": "true"})
        assert response.status_code == 200
        # Edit button exists on the product card
        assert "Edit" in response.text
        # Delete button exists with hx-delete
        assert "hx-delete" in response.text
        assert "Delete" in response.text

    def test_products_section_has_edit_modal(self):
        """Products section has the edit product modal."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/section/products", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "showEditProduct" in response.text
        assert "Edit Product" in response.text
        assert "Save Changes" in response.text

    def test_products_section_has_new_product_modal(self):
        """Products section has the new product modal."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/section/products", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "showNewProduct" in response.text
        assert "Add New Product" in response.text
        assert "Save Product" in response.text

    def test_products_section_has_open_edit_function(self):
        """Products section has the openEdit Alpine function."""
        app = _make_app_with_admin_routes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/section/products", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "openEdit(p)" in response.text or "openEdit(" in response.text

    def test_products_section_cards_link_to_detail(self):
        """Product cards have hx-get links to the detail page."""
        from unittest.mock import AsyncMock
        from contextlib import asynccontextmanager

        pool = MagicMock()
        pid = "detail-link-test-id"

        @asynccontextmanager
        async def _acquire():
            conn = MagicMock()
            conn.fetch = AsyncMock(return_value=[
                {
                    "id": pid,
                    "name": "Link Test Jacket",
                    "slug": "link-test-jacket",
                    "price": 30000.0,
                    "stock_quantity": 10,
                    "base_image": "/static/uploads/test.jpg",
                    "model_3d_url": None,
                    "pipeline_status": "idle",
                    "asset_category": None,
                    "created_at": None,
                    "category_id": "cat-1",
                    "category_name": "Tailoring",
                    "category_color": None,
                }
            ])
            yield conn

        pool.acquire = _acquire
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/section/products", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert f'/admin/section/product/{pid}' in response.text


class TestProductDetailPage:
    """Test the product detail page."""

    def _make_pool_for_detail(self):
        """Mock pool with a product and variants."""
        pool = MagicMock()
        product_id = "detail-test-product-123"

        @asynccontextmanager
        async def _acquire():
            conn = MagicMock()
            from asyncpg import Record

            # Product record
            product_data = {
                "id": product_id,
                "name": "Green Agbada",
                "slug": "green-agbada",
                "price": 45000.0,
                "stock_quantity": 8,
                "base_image": "/static/uploads/green.jpg",
                "model_3d_url": None,
                "pipeline_status": "idle",
                "description": "Hand-stitched traditional agbada",
                "category_id": "cat-1",
                "category_name": "Outerwear",
                "category_color": None,
                "created_at": None,
                "updated_at": None,
                "pipeline_error_log": None,
            }

            async def fetchrow_side_effect(sql, *args):
                if "FROM products p" in sql and "WHERE p.id" in sql:
                    return product_data
                return None

            async def fetch_side_effect(sql, *args):
                if "FROM product_variants" in sql:
                    return [
                        {"id": "v1", "size": "L", "color": "Green", "stock_qty": 5, "mesh_node_identifier": None, "custom_shader_color": "#2d5a27"},
                        {"id": "v2", "size": "XL", "color": "Green", "stock_qty": 3, "mesh_node_identifier": None, "custom_shader_color": "#2d5a27"},
                    ]
                return []

            conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)
            conn.fetch = AsyncMock(side_effect=fetch_side_effect)
            yield conn

        pool.acquire = _acquire
        return pool, product_id

    def test_detail_returns_200(self):
        """GET /admin/section/product/{id} returns 200."""
        pool, pid = self._make_pool_for_detail()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(f"/admin/section/product/{pid}", headers={"HX-Request": "true"})
        assert response.status_code == 200

    def test_detail_shows_product_name(self):
        """Detail page shows the product name."""
        pool, pid = self._make_pool_for_detail()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(f"/admin/section/product/{pid}", headers={"HX-Request": "true"})
        assert "Green Agbada" in response.text

    def test_detail_shows_price(self):
        """Detail page shows the product price in Naira."""
        pool, pid = self._make_pool_for_detail()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(f"/admin/section/product/{pid}", headers={"HX-Request": "true"})
        assert "&#8358;" in response.text
        assert "45,000" in response.text

    def test_detail_shows_description(self):
        """Detail page shows the product description."""
        pool, pid = self._make_pool_for_detail()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(f"/admin/section/product/{pid}", headers={"HX-Request": "true"})
        assert "Hand-stitched traditional agbada" in response.text

    def test_detail_shows_variants(self):
        """Detail page shows product variants."""
        pool, pid = self._make_pool_for_detail()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(f"/admin/section/product/{pid}", headers={"HX-Request": "true"})
        assert "Green" in response.text
        assert "L" in response.text
        assert "XL" in response.text

    def test_detail_has_back_button(self):
        """Detail page has a back-to-products link."""
        pool, pid = self._make_pool_for_detail()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(f"/admin/section/product/{pid}", headers={"HX-Request": "true"})
        assert "Back to Products" in response.text
        assert "/admin/section/products" in response.text

    def test_detail_has_delete_button(self):
        """Detail page has a delete button."""
        pool, pid = self._make_pool_for_detail()
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(f"/admin/section/product/{pid}", headers={"HX-Request": "true"})
        assert "hx-delete" in response.text
        assert "Delete Product" in response.text

    def test_detail_nonexistent_product_redirects(self):
        """Detail page for nonexistent product redirects to products list."""
        pool = MagicMock()

        @asynccontextmanager
        async def _acquire():
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=None)
            conn.fetch = AsyncMock(return_value=[])
            yield conn

        pool.acquire = _acquire
        app = _make_app_with_admin_routes(pool_fn=lambda: pool)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/section/product/nonexistent-id", headers={"HX-Request": "true"})
        assert response.status_code == 200