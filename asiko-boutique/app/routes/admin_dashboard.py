# ASIKO Boutique - Executive Dashboard
# Analytics, inline stock updater, waitlist notification trigger.

from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

from app.core import templates
from app.services.brevo import send_transactional_email


async def admin_dashboard_home(request: Request) -> HTMLResponse:
    """GET /admin/dashboard — Executive command center with metrics and inventory.

    Migrated to the v2 admin redesign. The legacy production-ledger,
    out-of-stock queues, and stock sentinel feed are preserved as a new
    "Operations" section at /admin/section/operations. The HTMX endpoints
    (update-stock, update-model-url, notify-waitlist) below are still
    served by this module and are wired to the operations section.
    """
    from app.routes.admin_sections import section_dashboard
    return await section_dashboard(request)


async def inline_update_stock(request: Request) -> HTMLResponse:
    """POST /admin/dashboard/update-stock — HTMX inline stock update."""
    form_data = await request.form()
    variant_id = form_data.get("variant_id")
    new_qty = int(form_data.get("stock_quantity", 0))

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE product_variants SET stock_qty = $1 WHERE id = $2;",
            new_qty, variant_id,
        )

    # Notify WebSocket subscribers about the stock change
    try:
        from app.realtime import notify, CH_STOCK_UPDATE
        await notify(pool, CH_STOCK_UPDATE, {
            "type": "stock_update",
            "variant_id": str(variant_id),
            "stock": new_qty,
        })
    except Exception:
        pass

    return HTMLResponse(
        f"<div class='text-xs font-mono text-[#10B981] animate-pulse' "
        f"hx-swap-oob='true' id='status-variant-{variant_id}'>"
        f"✓ Saved ({new_qty} units)</div>"
    )


async def inline_trigger_restock_alert(request: Request) -> HTMLResponse:
    """POST /admin/dashboard/notify-waitlist — Batch restock emails via Brevo."""
    form_data = await request.form()
    variant_id = form_data.get("variant_id")

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        async with conn.transaction():
            emails = await conn.fetch(
                "SELECT email FROM product_waitlists "
                "WHERE variant_id = $1 AND notified = false FOR UPDATE;",
                variant_id,
            )

            if emails:
                variant_info = await conn.fetchrow(
                    "SELECT p.name, v.size FROM product_variants v "
                    "JOIN products p ON v.product_id = p.id WHERE v.id = $1;",
                    variant_id,
                )

                for record in emails:
                    try:
                        await send_transactional_email(
                            to_email=record["email"],
                            subject=f"ÀSÌKÒ Restock Event: {variant_info['name']} Allocation Restored",
                            html_content=(
                                f"<h3>The Drop Has Arrived</h3>"
                                f"<p>Your requested item <b>{variant_info['name']}</b> "
                                f"(Size {variant_info['size']}) is back in stock.</p>"
                            ),
                        )
                    except Exception:
                        pass

                await conn.execute(
                    "UPDATE product_waitlists SET notified = true WHERE variant_id = $1;",
                    variant_id,
                )

    return HTMLResponse(
        f"<span class='text-xs font-mono uppercase text-[#10B981]'>"
        f"Sent to {len(emails)} Customers</span>"
    )


routes = [
    Route("/admin/dashboard", endpoint=admin_dashboard_home, methods=["GET"]),
    Route("/admin/dashboard/update-stock", endpoint=inline_update_stock, methods=["POST"]),
    Route("/admin/dashboard/notify-waitlist", endpoint=inline_trigger_restock_alert, methods=["POST"]),
]