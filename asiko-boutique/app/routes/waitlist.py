# ASIKO Boutique - Out-of-Stock Waitlist Engine
# Idempotent demand capture with Brevo dispatch and HTMX inline swaps.

import re
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

from app.services.brevo import send_transactional_email


def _is_valid_email(email: str) -> bool:
    """Validate email structure before database staging."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email.strip()))


async def join_waitlist(request: Request) -> HTMLResponse:
    """
    POST /waitlist/join
    Idempotent demand capture with row-level deduplication.
    """
    form_data = await request.form()
    variant_id_raw = form_data.get("variant_id")
    email_raw = form_data.get("email")

    if not variant_id_raw or not email_raw:
        return HTMLResponse(
            "<span class='text-xs font-mono text-[#EF4444]'>"
            "Missing required routing coordinates.</span>",
            status_code=400,
        )

    email = email_raw.strip().lower()
    if not _is_valid_email(email):
        return HTMLResponse(
            "<span class='text-xs font-mono text-[#EF4444]'>"
            "Please provide a valid communication routing address.</span>",
            status_code=400,
        )

    try:
        variant_id = str(variant_id_raw)
    except ValueError:
        return HTMLResponse(
            "<span class='text-xs font-mono text-[#EF4444]'>"
            "Invalid variant allocation signature.</span>",
            status_code=400,
        )

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        # Verify variant exists
        variant = await conn.fetchrow(
            """
            SELECT v.id, v.size, v.color, p.name
            FROM product_variants v
            JOIN products p ON v.product_id = p.id
            WHERE v.id = $1
            """,
            variant_id,
        )

        if not variant:
            return HTMLResponse(
                "<span class='text-xs font-mono text-[#EF4444]'>"
                "Selected atelier asset does not exist.</span>",
                status_code=404,
            )

        # Idempotent insert: ON CONFLICT preserves uniqueness constraint
        await conn.execute(
            """
            INSERT INTO product_waitlists (email, variant_id)
            VALUES ($1, $2)
            ON CONFLICT (email, variant_id) DO NOTHING
            """,
            email, variant_id,
        )

    # Brevo confirmation with graceful fallback
    try:
        subject = f"ÀSÌKÒ Atelier Queue Registered: {variant['name']}"
        html_body = (
            "<h3>Atelier Request Logged</h3>"
            f"<p>We have added your address (<b>{email}</b>) to the restock priority list "
            f"for <b>{variant['name']}</b> (Size: {variant['size']}, Color: {variant['color']}).</p>"
            "<p>Our production team will notify you immediately via this channel "
            "as soon as our next capsule drop goes live.</p>"
        )
        await send_transactional_email(
            to_email=email, subject=subject, html_content=html_body,
        )
    except Exception:
        pass  # Gracefully absorb network dropouts

    return HTMLResponse(
        f"<div class='p-3 bg-[#0D2A22] text-[#FBF9F6] border border-[#D4AF37]/40 "
        f"text-xs font-mono tracking-wide animate-fade-in'>"
        f"✓ Priority Access Confirmed. You will receive an exclusive alert "
        f"when Size {variant['size']} is restocked.</div>"
    )


routes = [
    Route("/waitlist/join", endpoint=join_waitlist, methods=["POST"]),
]
