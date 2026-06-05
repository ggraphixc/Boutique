# ASIKO Boutique - Integration Flow Tests
# Lifespant validation, E2E transactional flows, HTMX fragment assertions.

import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """TestClient with lifespan context — pool binds to app.state.db_pool."""
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# LIFESPAN & STOREFRONT
# ---------------------------------------------------------------------------

def test_lifespan_pool_binding(client):
    """Verify app.state.db_pool is set after lifespan startup."""
    assert hasattr(app.state, "db_pool")
    assert app.state.db_pool is not None


def test_storefront_editorial_load(client):
    """Homepage lands cleanly with brand markers."""
    response = client.get("/")
    assert response.status_code == 200
    assert "ASIKO" in response.text or "ÀSÌKÒ" in response.text


def test_storefront_htmx_grid_fragment(client):
    """HTMX product grid returns partial HTML."""
    response = client.get("/htmx/products")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# CART SESSION MUTATION
# ---------------------------------------------------------------------------

def test_cart_drawer_empty(client):
    """Empty cart drawer returns valid HTML fragment."""
    response = client.get("/cart/drawer")
    assert response.status_code == 200


def test_cart_add_missing_variant(client):
    """Cart add with missing variant_id returns 400."""
    response = client.post("/cart/add", data={"quantity": "1"})
    assert response.status_code == 400


def test_cart_add_invalid_variant(client):
    """Cart add with nonexistent variant returns 404."""
    response = client.post("/cart/add", data={
        "variant_id": "00000000-0000-0000-0000-000000000000",
        "quantity": "1",
    })
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# EXECUTIVE DASHBOARD
# ---------------------------------------------------------------------------

def test_dashboard_metrics_aggregation(client):
    """Dashboard renders metrics cards and inventory ledger."""
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    assert "Atelier Production Ledger" in response.text
    assert "Stock Sentinel Feed" in response.text


def test_dashboard_htmx_stock_update(client):
    """Inline stock updater returns OOB HTMX fragment."""
    test_variant_id = "00000000-0000-0000-0000-000000000001"
    response = client.post("/admin/dashboard/update-stock", data={
        "variant_id": test_variant_id,
        "stock_quantity": "45",
    })
    assert response.status_code == 200
    assert "hx-swap-oob='true'" in response.text
    assert f"id='status-variant-{test_variant_id}'" in response.text
    assert "Saved (45 units)" in response.text


# ---------------------------------------------------------------------------
# ADMIN INVENTORY SENTINEL
# ---------------------------------------------------------------------------

def test_admin_reservations_list(client):
    """Reservations ledger returns HTML table."""
    response = client.get("/admin/reservations")
    assert response.status_code == 200


def test_admin_reserve_missing_variant(client):
    """Reserve with missing variant_id returns 400."""
    response = client.post("/admin/reserve", data={"quantity": "1"})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# WAITLIST ENGINE
# ---------------------------------------------------------------------------

def test_waitlist_join_missing_fields(client):
    """Waitlist join with missing fields returns 400."""
    response = client.post("/waitlist/join", data={})
    assert response.status_code == 400


def test_waitlist_join_invalid_email(client):
    """Waitlist join with invalid email returns 400."""
    response = client.post("/waitlist/join", data={
        "variant_id": "1",
        "email": "not-an-email",
    })
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# CHECKOUT FLOW
# ---------------------------------------------------------------------------

def test_checkout_empty_cart_redirect(client):
    """Checkout with empty cart redirects to homepage."""
    response = client.get("/checkout", follow_redirects=False)
    assert response.status_code in (302, 303)


def test_checkout_shipping_summary(client):
    """Shipping summary HTMX endpoint returns cost fragment."""
    response = client.get("/checkout/shipping-summary?state=LA")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# DEBUG PDP
# ---------------------------------------------------------------------------

def test_debug_pdp_renders(client):
    """Debug PDP endpoint renders product detail template."""
    response = client.get("/test-pdp")
    assert response.status_code == 200
    assert "The Architectural Blazer" in response.text
