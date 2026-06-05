# ASIKO Boutique - Omnichannel Stock Sentinel
# Admin inventory reservation engine with SELECT FOR UPDATE locking.

from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route


async def reserve_stock(request: Request) -> HTMLResponse:
    """
    POST /admin/reserve
    Admin-driven stock reservation override with row-level locking.
    """
    form_data = await request.form()
    variant_id = form_data.get("variant_id")
    quantity = int(form_data.get("quantity", 1))
    session_id = form_data.get("session_identifier", "ADMIN_OVERRIDE_HOLD")

    if not variant_id:
        return HTMLResponse(
            "<span class='text-xs font-mono text-red-500'>Error: Variant ID parameter required.</span>",
            status_code=400,
        )

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        async with conn.transaction():
            current_stock = await conn.fetchval(
                "SELECT stock_qty FROM product_variants WHERE id = $1 FOR UPDATE;",
                variant_id,
            )

            if current_stock is None:
                return HTMLResponse(
                    "<span class='text-xs font-mono text-red-500'>Error: Variant not found.</span>",
                    status_code=404,
                )

            if current_stock < quantity:
                return HTMLResponse(
                    f"<span class='text-xs font-mono text-amber-600'>"
                    f"Insufficient stock. Remaining: {current_stock}</span>",
                    status_code=400,
                )

            await conn.execute(
                """
                INSERT INTO product_reservations (variant_id, session_identifier, quantity, status, created_at)
                VALUES ($1, $2, $3, 'staged', NOW())
                """,
                variant_id, session_id, quantity,
            )

    return HTMLResponse(
        f"<div class='p-3 bg-[#0D2A22] text-[#FBF9F6] border border-[#D4AF37]/30 "
        f"text-xs font-mono animate-fade-in'>"
        f"✓ Admin Stock Hold Applied: Variant {variant_id} ({quantity} Units Locked)</div>"
    )


async def settle_reservations(request: Request) -> HTMLResponse:
    """
    POST /admin/settle
    Flush all stale checkout holds older than 60 minutes.
    """
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE product_reservations
            SET status = 'expired'
            WHERE status = 'staged' AND created_at < NOW() - INTERVAL '60 minutes'
            """
        )

    return HTMLResponse(
        "<div class='p-3 bg-neutral-900 text-neutral-200 text-xs font-mono animate-fade-in'>"
        "✓ Maintenance Sync Complete. Stale checkout holds evicted from ledger.</div>"
    )


async def list_reservations(request: Request) -> HTMLResponse:
    """
    GET /admin/reservations
    Live HTML summary ledger of all stock reservations.
    """
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT id, variant_id, session_identifier, quantity, status, created_at
            FROM product_reservations
            ORDER BY created_at DESC LIMIT 25
            """
        )

    if not records:
        return HTMLResponse(
            "<div class='p-4 text-xs font-mono text-neutral-400 border border-dashed border-neutral-300'>"
            "No active reservations found.</div>"
        )

    rows_html = ""
    for r in records:
        status_color = (
            "text-amber-500" if r["status"] == "staged"
            else ("text-green-500" if r["status"] == "paid" else "text-neutral-400")
        )
        rows_html += (
            f"<tr class='border-b border-neutral-200 text-[11px] font-mono'>"
            f"<td class='p-2 text-neutral-600'>{r['id']}</td>"
            f"<td class='p-2 font-bold text-neutral-800'>{r['variant_id']}</td>"
            f"<td class='p-2 truncate max-w-[120px]'>{r['session_identifier']}</td>"
            f"<td class='p-2 text-center'>{r['quantity']}</td>"
            f"<td class='p-2 font-semibold {status_color}'>{r['status']}</td>"
            f"<td class='p-2 text-neutral-400 text-right'>{r['created_at'].strftime('%H:%M:%S')}</td>"
            f"</tr>"
        )

    table_html = (
        "<div class='overflow-x-auto bg-[#FBF9F6] border border-neutral-200 shadow-sm p-4 animate-fade-in'>"
        "<h4 class='text-xs font-mono uppercase tracking-wider text-[#0D2A22] font-semibold mb-3'>"
        "Omnichannel Stock Sentinel Matrix</h4>"
        "<table class='w-full text-left border-collapse'>"
        "<thead><tr class='bg-[#0D2A22] text-[#FBF9F6] font-mono text-[10px] uppercase tracking-wider'>"
        "<th class='p-2'>ID</th>"
        "<th class='p-2'>Variant ID</th>"
        "<th class='p-2'>Session Key</th>"
        "<th class='p-2 text-center'>Qty</th>"
        "<th class='p-2'>Status</th>"
        "<th class='p-2 text-right'>Staged At</th>"
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table></div>"
    )
    return HTMLResponse(table_html)


routes = [
    Route("/admin/reserve", endpoint=reserve_stock, methods=["POST"]),
    Route("/admin/settle", endpoint=settle_reservations, methods=["POST"]),
    Route("/admin/reservations", endpoint=list_reservations, methods=["GET"]),
]
