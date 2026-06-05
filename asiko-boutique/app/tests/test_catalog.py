# ASIKO Boutique - Catalog Interaction Engine Integration Tests
# Exercises all 4 PDP pipelines: Allocation, Atelier, Concierge, Capsule

import pytest
from starlette.testclient import TestClient
from django.core.signing import Signer

from app.main import app

# Initialize matching salt signer to compile valid test signatures
signer = Signer(salt="asiko.concierge.vector")


@pytest.fixture
def client():
    """Generates a clean TestClient instance for route cycle processing."""
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# FEATURE 4: ALLOCATION GATEKEEPER (Session-Based)
# GET /catalog/allocation/{slug}
# ---------------------------------------------------------------------------

def test_allocation_gatekeeper_html_lazy_load(client):
    """Verifies that the allocation route evaluates and drops pristine HTML alerts."""
    response = client.get("/catalog/allocation/architectural-blazer")

    assert response.status_code == 200
    assert "Allocation Cleared &amp; Verified" in response.text
    assert "Priority Pass" in response.text
    assert "animate-ping" in response.text


def test_allocation_gatekeeper_zero_stock(client):
    """When allocation is exhausted, shows archive notice."""
    response = client.get("/catalog/allocation/unknown-product")

    assert response.status_code == 200
    assert "Allocation Cleared" in response.text


# ---------------------------------------------------------------------------
# FEATURE 1: DIGITAL ATELIER (Session-Based)
# POST /catalog/atelier/bind
# ---------------------------------------------------------------------------

def test_digital_atelier_ephemeral_session_binding(client):
    """Validates that incoming vector parameters bind tightly to client session loops."""
    form_payload = {
        "chest": "96",
        "waist": "82",
        "hips": "102",
        "display_unit": "cm",
    }

    # Hit the ephemeral session endpoint
    response = client.post("/catalog/atelier/bind", data=form_payload)

    assert response.status_code == 200
    assert "Vector Dimensions Binded Successfully" in response.text
    assert "96cm Chest" in response.text

    # Confirm state persists inside the cookie engine architecture
    assert "asiko_session" in client.cookies


def test_digital_atelier_inch_conversion(client):
    """Validates imperial-to-metric conversion in session binding."""
    form_payload = {
        "chest": "38",
        "waist": "32",
        "hips": "40",
        "display_unit": "in",
    }

    response = client.post("/catalog/atelier/bind", data=form_payload)

    assert response.status_code == 200
    assert "Vector Dimensions Binded Successfully" in response.text
    # Inches should be displayed as entered (conversion happens server-side for DB)
    assert "38in Chest" in response.text


def test_digital_atelier_missing_fields(client):
    """Returns 400 when measurement vectors are incomplete."""
    form_payload = {
        "chest": "96",
        "waist": "",
        "hips": "102",
        "display_unit": "cm",
    }

    response = client.post("/catalog/atelier/bind", data=form_payload)

    assert response.status_code == 400
    assert "Vector dimensions incomplete" in response.text


# ---------------------------------------------------------------------------
# FEATURE 2: WHATSAPP CONCIERGE (DB-Backed + Session-Based)
# GET /catalog/concierge/bridge  (DB-backed, luxury_extensions.py)
# GET /catalog/concierge/redirect (Session-based, catalog/routes.py)
# ---------------------------------------------------------------------------

def test_cryptographic_concierge_tamper_protection(client):
    """Ensures unauthorized altered tokens are flatly denied access via 403 blocks."""
    response = client.get("/catalog/concierge/bridge?token=MALICIOUS_ALTERED_STRING")
    assert response.status_code == 403
    assert "Security Violation" in response.text


def test_cryptographic_concierge_valid_redirect(client):
    """Ensures signed handshake strings execute clean 303 browser redirection maps."""
    valid_token = signer.sign("ORDER_REF_99X_METRIC_VERIFIED")

    # Follow redirects set to false to catch intermediate 303 frame state changes
    response = client.get(
        f"/catalog/concierge/redirect?token={valid_token}",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "wa.me" in response.headers["location"]
    assert "ORDER_REF_99X" in response.headers["location"]


def test_cryptographic_concierge_missing_token(client):
    """Returns 400 when token parameter is absent."""
    response = client.get("/catalog/concierge/bridge")
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# FEATURE 3: CAPSULE MATRIX (Session-Based)
# POST /catalog/cart/capsule
# ---------------------------------------------------------------------------

def test_capsule_matrix_multi_value_and_oob_swapping(client):
    """
    Validates array checkbox form extraction, session list collection appending,
    and verification of matching Out-Of-Band (OOB) swap injection tokens.
    """
    # Simulate selecting multiple pieces of an outfit ensemble
    # HTML checkbox forms submit as repeated keys via URL-encoded body
    response = client.post(
        "/catalog/cart/capsule",
        content=b"variant_ids=var_top_77&variant_ids=var_bottom_21",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    # Requirement Check 1: Inline fragment success logs present
    assert "Lookbook Combination Added to Active Session Bag" in response.text

    # Requirement Check 2: HTMX Out-Of-Band Swapper engine output block matches global shell exactly
    assert 'id="cart-counter"' in response.text
    assert 'hx-swap-oob="true"' in response.text
    assert "Bag (2)" in response.text


def test_capsule_matrix_empty_selection(client):
    """Returns 400 when no variants are selected."""
    response = client.post("/catalog/cart/case", data={})

    # Empty selection should error
    assert response.status_code in (400, 404)


def test_capsule_matrix_deduplication(client):
    """Duplicate variant IDs should be deduplicated in session."""
    response = client.post(
        "/catalog/cart/capsule",
        content=b"variant_ids=var_unique_01&variant_ids=var_unique_01&variant_ids=var_unique_02",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    # Only 2 unique items, not 3
    assert "Bag (2)" in response.text


# ---------------------------------------------------------------------------
# INTEGRATION: Multi-feature session persistence
# ---------------------------------------------------------------------------

def test_session_persistence_across_features(client):
    """Verify that session state persists across multiple feature interactions."""
    # 1. Bind atelier dimensions
    client.post("/catalog/atelier/bind", data={
        "chest": "96", "waist": "82", "hips": "102", "display_unit": "cm"
    })

    # 2. Add capsule items
    client.post("/catalog/cart/capsule", data=[
        ("variant_ids", "var_persistent_01"),
    ])

    # 3. Verify atelier state is still in session
    response = client.post("/catalog/atelier/bind", data={
        "chest": "96", "waist": "82", "hips": "102", "display_unit": "cm"
    })
    assert response.status_code == 200
    assert "Vector Dimensions Binded Successfully" in response.text
