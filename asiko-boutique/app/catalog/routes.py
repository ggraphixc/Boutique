# ASIKO Boutique - Catalog Interaction Engine
# Session-based state endpoints for PDP premium features
# Allocation | Atelier | Concierge | Capsule Matrix

import logging
import urllib.parse

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route

logger = logging.getLogger("asiko.catalog")


# ---------------------------------------------------------------------------
# FEATURE 4: TIERED ALLOCATION GATEKEEPER
# GET /catalog/allocation/{slug}
# Mock limited run of 3 units. Returns gold pulse if stock exists,
# archive notice if exhausted.
# ---------------------------------------------------------------------------

async def get_allocation_status(request: Request) -> Response:
    slug = request.path_params.get("slug", "unknown")

    # Mock: 3-unit limited run allocation
    available_allocation = 3

    # Check session to see if this user already reserved
    reserved_slugs = request.session.get("reserved_slugs", [])
    already_reserved = slug in reserved_slugs

    if already_reserved:
        html_fragment = f"""
        <div class="bg-[#0D2A22]/5 border border-[#D4AF37]/30 p-4 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <span class="relative flex h-2 w-2">
                    <span class="relative inline-flex rounded-full h-2 w-2 bg-[#10B981]"></span>
                </span>
                <div>
                    <p class="text-xs font-mono text-[#0D2A22] uppercase tracking-wider font-medium">Allocation Secured</p>
                    <p class="text-[11px] text-neutral-500 font-light mt-0.5">Your priority pass for this piece is confirmed.</p>
                </div>
            </div>
            <span class="text-[10px] font-mono uppercase bg-[#10B981] text-white px-2 py-1 tracking-widest">Locked</span>
        </div>
        """
    elif available_allocation > 0:
        html_fragment = f"""
        <div class="bg-[#0D2A22]/5 border border-[#0D2A22]/20 p-4 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <span class="relative flex h-2 w-2">
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#D4AF37] opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-2 w-2 bg-[#D4AF37]"></span>
                </span>
                <div>
                    <p class="text-xs font-mono text-[#0D2A22] uppercase tracking-wider font-medium">Allocation Cleared &amp; Verified</p>
                    <p class="text-[11px] text-neutral-500 font-light mt-0.5">Only {available_allocation} structural runs left globally for assignment.</p>
                </div>
            </div>
            <span class="text-[10px] font-mono uppercase bg-[#0D2A22] text-[#FBF9F6] px-2 py-1 tracking-widest">Priority Pass</span>
        </div>
        """
    else:
        html_fragment = """
        <div class="bg-neutral-100 border border-neutral-300 p-4 text-center">
            <p class="text-xs font-mono text-neutral-500 uppercase tracking-widest">Allocation Closed</p>
            <p class="text-[11px] text-neutral-400 font-light mt-1">This specific cut matrix has entered our archives.</p>
        </div>
        """

    return HTMLResponse(html_fragment)


# ---------------------------------------------------------------------------
# FEATURE 1: DIGITAL ATELIER - Measurement Vault (Session-Based)
# POST /catalog/waitlist
# Parses chest, waist, hips, display_unit. Stores to request.session.
# Returns confirmation fragment.
# ---------------------------------------------------------------------------

async def bind_atelier_dimensions(request: Request) -> Response:
    form_data = await request.form()
    chest = form_data.get("chest")
    waist = form_data.get("waist")
    hips = form_data.get("hips")
    display_unit = form_data.get("display_unit", "cm")

    # Validate all measurements are present
    if not all([chest, waist, hips]):
        return HTMLResponse(
            '<div class="bg-rose-50 border border-rose-200 p-4 text-center text-xs font-mono text-rose-700 uppercase tracking-wider">'
            "Vector dimensions incomplete. Please provide chest, waist, and hip measurements.</div>",
            status_code=400,
        )

    # Bind to session (encrypted cookie state)
    request.session["atelier_dimensions"] = {
        "chest": chest,
        "waist": waist,
        "hips": hips,
        "unit": display_unit,
    }

    logger.info("Atelier dimensions bound: %s/%s/%s %s", chest, waist, hips, display_unit)

    html_fragment = f"""
    <div class="bg-[#0D2A22] text-[#FBF9F6] p-4 text-center border border-[#D4AF37]/30 space-y-2">
        <p class="text-xs uppercase font-mono tracking-[0.2em] text-[#D4AF37]">Vector Dimensions Binded Successfully</p>
        <p class="text-[11px] font-sans font-light text-neutral-300">
            Profile Dimensions Bound: {chest}{display_unit} Chest &bull; {waist}{display_unit} Waist &bull; {hips}{display_unit} Hips
        </p>
    </div>
    """
    return HTMLResponse(html_fragment)


# ---------------------------------------------------------------------------
# FEATURE 2: WHATSAPP CONCIERGE BRIDGE
# GET /catalog/concierge/redirect
# Reads token from query, assembles WhatsApp message, 303 redirect.
# ---------------------------------------------------------------------------

async def concierge_redirect(request: Request) -> Response:
    token = request.query_params.get("token", "GUEST_TRACK")
    atelier_phone_number = "2348000000000"

    prefilled_text = (
        f"Hello \u00c0S\u00ccK\u00d2 Atelier, I am reviewing an item signature path "
        f"under transaction security token {token}. "
        f"I would like to initiate an editorial consultation."
    )
    encoded_message = urllib.parse.quote(prefilled_text)

    whatsapp_url = f"https://wa.me/{atelier_phone_number}?text={encoded_message}"

    logger.info("Concierge redirect triggered with token %s", token[:20])

    return RedirectResponse(url=whatsapp_url, status_code=303)


# ---------------------------------------------------------------------------
# FEATURE 3: CAPSULE MATRIX - Bulk Bundle Add (Session-Based)
# POST /catalog/cart/capsule
# Processes multi-checkbox variant_ids, appends to session cart list,
# returns inline confirmation + OOB cart counter refresh.
# ---------------------------------------------------------------------------

async def acquire_capsule_matrix(request: Request) -> Response:
    form_data = await request.form()
    variant_ids = form_data.getlist("variant_ids")

    if not variant_ids:
        return HTMLResponse(
            '<div class="text-xs font-mono text-rose-700 bg-rose-50 border border-rose-200 p-3">'
            "Selection error: Please preserve at least one foundational element to execute ensemble generation.</div>",
            status_code=400,
        )

    # Deduplicate while preserving order
    current_cart = request.session.get("cart_items", [])
    for variant in variant_ids:
        if variant not in current_cart:
            current_cart.append(variant)
    request.session["cart_items"] = current_cart

    new_total_count = len(current_cart)
    logger.info("Capsule matrix: %d variants added to session cart (total: %d)", len(variant_ids), new_total_count)

    # Return inline confirmation + OOB cart counter swap
    html_fragment = f"""
    <div class="bg-[#0D2A22]/5 border border-[#0D2A22] p-4 text-center text-xs font-mono text-[#0D2A22] uppercase tracking-wider">
        &#10003; Lookbook Combination Added to Active Session Bag
    </div>
    <div id="cart-counter" hx-swap-oob="true" class="font-mono text-xs text-[#0D2A22] font-semibold tracking-widest uppercase">
        Bag ({new_total_count})
    </div>
    """
    return HTMLResponse(html_fragment)


# ---------------------------------------------------------------------------
# Route table
# Paths are relative — mounted under /catalog in main.py
# ---------------------------------------------------------------------------

routes = [
    Route("/allocation/{slug}", endpoint=get_allocation_status, methods=["GET"]),
    Route("/atelier/bind", endpoint=bind_atelier_dimensions, methods=["POST"]),
    Route("/concierge/redirect", endpoint=concierge_redirect, methods=["GET"]),
    Route("/cart/capsule", endpoint=acquire_capsule_matrix, methods=["POST"]),
]
