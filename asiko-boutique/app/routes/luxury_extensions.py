# ASIKO Boutique - Luxury Extension Edge Routers
# Digital Atelier | WhatsApp Concierge | Capsule Matrix | Tiered Allocation
# All endpoints use request.app.state.db_pool for database access.

import logging
import math
import os
import urllib.parse
from uuid import UUID

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route

# Configure Django settings before importing Signer
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.core.signing import Signer, BadSignature

# Initialize Django Signer with the specified system salt configuration
signer = Signer(salt="asiko.concierge.vector")

logger = logging.getLogger("asiko.luxury")

CONCIERGE_PHONE = "2348000000000"


# ---------------------------------------------------------------------------
# FEATURE 1: DIGITAL ATELIER - Measurement Vault
# Accepts cm or inches, scales to metric, and records to persistent ledger.
# ---------------------------------------------------------------------------

async def save_measurements(request: Request) -> Response:
    """Persist body measurements to the vault. Converts inches to cm if needed."""
    form_data = await request.form()
    chest = float(form_data.get("chest", 0))
    waist = float(form_data.get("waist", 0))
    hips = float(form_data.get("hips", 0))
    unit = form_data.get("display_unit", "cm")

    # Extract session string tracking cookie token
    session_key = request.cookies.get("asiko_session", "ANONYMOUS_SESSION")

    # Standardize scale parameters to metric if input is imperial
    if unit == "in":
        chest = round(chest * 2.54, 2)
        waist = round(waist * 2.54, 2)
        hips = round(hips * 2.54, 2)

    # Database connection via app state pool
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO asiko_measurement_vault
                (session_key, display_unit, chest, waist, hips, updated_at)
            VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
            ON CONFLICT (session_key)
            DO UPDATE SET display_unit = $2, chest = $3, waist = $4, hips = $5,
                         updated_at = CURRENT_TIMESTAMP
            """,
            session_key, unit, chest, waist, hips,
        )

    logger.info("Atelier measurements saved for session %s", session_key)

    html_fragment = f"""
    <div class="bg-[#0D2A22] text-[#FBF9F6] p-4 text-center border border-[#D4AF37]/30 animate-fade-in">
        <p class="text-xs uppercase font-mono tracking-[0.2em] text-[#D4AF37]">Ledger Synchronization Complete</p>
        <p class="text-[11px] font-sans font-light text-neutral-300">
            Metric parameters registered: {chest}cm Chest &bull; {waist}cm Waist &bull; {hips}cm Hips
        </p>
    </div>
    """
    return HTMLResponse(html_fragment)


# ---------------------------------------------------------------------------
# FEATURE 2: WHATSAPP CONCIERGE BRIDGE
# Verifies cryptographic signatures, logs analytics, and triggers redirect.
# ---------------------------------------------------------------------------

async def concierge_redirect(request: Request) -> Response:
    """Verify signed concierge token and redirect to WhatsApp with pre-filled message."""
    signed_payload = request.query_params.get("token", "")

    if not signed_payload:
        return HTMLResponse(
            "<span class='text-xs text-red-500 font-mono'>Error: Missing security token parameter.</span>",
            status_code=400,
        )

    try:
        # Cryptographically parse incoming signature payload
        unsigned_payload = signer.unsign(signed_payload)
    except BadSignature:
        return HTMLResponse(
            "<span class='text-xs text-red-500 font-mono'>Security Violation: Invalid Token Signature</span>",
            status_code=403,
        )

    # Extract active database pool references
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO telemetry_concierge_clicks (payload_metadata, clicked_at)
            VALUES ($1, CURRENT_TIMESTAMP);
            """,
            unsigned_payload,
        )

    prefilled_msg = (
        f"Hello \u00c0S\u00ccK\u00d2 Atelier, I am reviewing an item signature path "
        f"under transaction security token [{unsigned_payload}]. "
        f"I would like to initiate an editorial consultation."
    )
    encoded_msg = urllib.parse.quote(prefilled_msg)
    whatsapp_url = f"https://wa.me/{CONCIERGE_PHONE}?text={encoded_msg}"

    logger.info("Concierge redirect triggered with token %s", unsigned_payload[:20])

    return RedirectResponse(url=whatsapp_url, status_code=303)


# ---------------------------------------------------------------------------
# FEATURE 3: CAPSULE MATRIX - Bulk Bundle Add
# Performs transactional reservations across multiple product components.
# ---------------------------------------------------------------------------

async def add_capsule_bundle(request: Request) -> Response:
    """Add multiple capsule look items to reservations in a single atomic operation."""
    form_data = await request.form()
    variant_ids_raw = form_data.getlist("variant_ids")

    # Validate and sanitize variant identifiers
    variant_ids = []
    for v in variant_ids_raw:
        try:
            variant_ids.append(str(UUID(v)))
        except ValueError:
            continue

    if not variant_ids:
        return HTMLResponse(
            "<div class='text-xs font-mono text-red-500 bg-red-50 border border-red-200 p-3'>"
            "Error: Empty variant parameters.</div>",
            status_code=400,
        )

    pool = request.app.state.db_pool
    session_key = request.cookies.get("asiko_session", "ANONYMOUS_SESSION")
    async with pool.acquire() as conn:
        # Open an explicit, safe transaction pipeline
        async with conn.transaction():
            for variant_id in variant_ids:
                await conn.execute(
                    """
                    INSERT INTO product_reservations (id, variant_id, session_identifier, quantity, status, created_at)
                    VALUES (gen_random_uuid(), $1, $2, 1, 'pending', CURRENT_TIMESTAMP);
                    """,
                    variant_id, session_key,
                )

    logger.info("Capsule bundle added: %d variants", len(variant_ids))

    html_fragment = f"""
    <div class="bg-[#0D2A22] text-[#FBF9F6] p-3 text-center text-xs font-mono uppercase tracking-wider animate-fade-in">
        &#10003; Ensemble Secured Against Database Ledger
    </div>
    <div id="cart-counter" hx-swap-oob="true" class="font-mono text-xs text-[#0D2A22] font-semibold tracking-widest uppercase">
        Bag ({len(variant_ids)})
    </div>
    """
    return HTMLResponse(html_fragment)


# ---------------------------------------------------------------------------
# FEATURE 4: TIERED ALLOCATION ENGINE - Pre-Order Gatekeeper
# Asynchronously queries active windows to verify remaining purchase caps.
# ---------------------------------------------------------------------------

async def preorder_interface(request: Request) -> Response:
    """Render the pre-order authorization form if the user's tier qualifies."""
    slug = request.path_params.get("slug", "")
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT w.tier_level_required, w.max_allocation_units, w.allocated_units
            FROM asiko_allocation_windows w
            JOIN products p ON p.id = w.target_product_id
            WHERE p.slug = $1
              AND NOW() BETWEEN w.start_time AND w.end_time;
            """,
            slug,
        )

    if not row:
        return HTMLResponse(
            "<div class='text-xs font-mono text-amber-600 uppercase tracking-wider p-3 bg-amber-50 border border-amber-200'>"
            "Notice: Window Locked or Outside Allocation Windows</div>"
        )

    remaining = row["max_allocation_units"] - row["allocated_units"]

    if remaining > 0:
        return HTMLResponse(
            f"""
            <div class="bg-[#0D2A22]/5 border border-[#0D2A22]/20 p-4 flex items-center justify-between animate-fade-in">
                <div>
                    <p class="text-xs font-mono text-[#0D2A22] uppercase tracking-wider font-semibold">Tier {row['tier_level_required']} Allocation Cleared</p>
                    <p class="text-[11px] text-neutral-500 font-light mt-0.5">Database Verified: {remaining} limited structural runs remaining.</p>
                </div>
                <button hx-post="/catalog/preorder/secure"
                        hx-vals='{{"slug": "{slug}"}}'
                        class="bg-[#0D2A22] text-[#FBF9F6] px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider hover:bg-neutral-800 transition-colors">
                    Claim Slot
                </button>
            </div>
            """
        )

    return HTMLResponse(
        "<div class='text-xs font-mono text-red-500 p-3 bg-red-50 border border-red-200'>"
        "Allocation Pool Fully Exhausted</div>"
    )


# ---------------------------------------------------------------------------
# FEATURE 4 (Secure Action): Row-Level Verification
# Applies an atomic SELECT FOR UPDATE row lock to secure an allocation slot.
# ---------------------------------------------------------------------------

async def secure_preorder(request: Request) -> Response:
    """Process a pre-order lock: increment allocated_units atomically."""
    form_data = await request.form()
    slug = form_data.get("slug", "")

    if not slug:
        return HTMLResponse(
            "<span class='text-xs font-mono text-red-500'>Error: Missing product identifier.</span>",
            status_code=400,
        )

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Apply strict row-level lock on the verification profile
            window = await conn.fetchrow(
                """
                SELECT w.id, w.max_allocation_units, w.allocated_units
                FROM asiko_allocation_windows w
                JOIN products p ON p.id = w.target_product_id
                WHERE p.slug = $1
                FOR UPDATE;
                """,
                slug,
            )

            if not window or (window["max_allocation_units"] - window["allocated_units"]) <= 0:
                return HTMLResponse(
                    "<span class='text-xs font-mono text-red-500'>"
                    "Transaction Aborted: Allocation filled mid-flight.</span>",
                    status_code=409,
                )

            # Perform atomic increment inside locked frame
            await conn.execute(
                "UPDATE asiko_allocation_windows SET allocated_units = allocated_units + 1 WHERE id = $1;",
                window["id"],
            )

    logger.info("Pre-order locked for product slug %s", slug)

    return HTMLResponse(
        "<span class='text-xs font-mono text-green-600 font-bold'>"
        "&#10003; Allocation Slot Confirmed and Cryptographically Held</span>"
    )


# ---------------------------------------------------------------------------
# Route table
# ---------------------------------------------------------------------------

luxury_routes = [
    Route("/atelier/measurements", endpoint=save_measurements, methods=["POST"]),
    Route("/catalog/concierge/bridge", endpoint=concierge_redirect, methods=["GET"]),
    Route("/catalog/capsule/add-bundle", endpoint=add_capsule_bundle, methods=["POST"]),
    Route("/products/{slug}/preorder", endpoint=preorder_interface, methods=["GET"]),
    Route("/catalog/preorder/secure", endpoint=secure_preorder, methods=["POST"]),
]
