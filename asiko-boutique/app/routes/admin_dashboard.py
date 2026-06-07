# ASIKO Boutique - Executive Dashboard
# Analytics, inline stock updater, waitlist notification trigger.

import os
import secrets
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.datastructures import UploadFile

from app.core import templates
from app.services.brevo import send_transactional_email

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def admin_dashboard_home(request: Request) -> HTMLResponse:
    """GET /admin/dashboard — Executive command center with metrics and inventory."""
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        total_revenue = await conn.fetchval(
            "SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'paid'"
        )
        pending_orders_count = await conn.fetchval(
            "SELECT COUNT(*) FROM orders WHERE status = 'pending'"
        )
        active_holds = await conn.fetchval(
            "SELECT COUNT(*) FROM product_reservations WHERE status = 'staged'"
        )
        waitlist_volume = await conn.fetchval(
            "SELECT COUNT(*) FROM product_waitlists WHERE notified = false"
        )

        inventory_rows = await conn.fetch(
            """
            SELECT p.id AS product_id, p.name, p.model_3d_url,
                   p.source_2d_image_url, p.pipeline_status,
                   v.id AS variant_id, v.size, v.color, v.stock_qty
            FROM product_variants v
            JOIN products p ON v.product_id = p.id
            ORDER BY p.id DESC, v.size ASC
            """
        )

        active_reservations = await conn.fetch(
            """
            SELECT r.id, p.name, r.quantity, r.status, r.created_at
            FROM product_reservations r
            JOIN product_variants v ON r.variant_id = v.id
            JOIN products p ON v.product_id = p.id
            ORDER BY r.created_at DESC LIMIT 8
            """
        )

        pending_waitlists = await conn.fetch(
            """
            SELECT w.variant_id, p.name AS product_name, v.size, v.color,
                    COUNT(w.email) AS demand_count
            FROM product_waitlists w
            JOIN product_variants v ON w.variant_id = v.id
            JOIN products p ON v.product_id = p.id
            WHERE w.notified = false
            GROUP BY w.variant_id, p.name, v.size, v.color
            ORDER BY demand_count DESC
            """
        )

    context = {
        "request": request,
        "metrics": {
            "revenue": total_revenue or 0.0,
            "pending_orders": pending_orders_count,
            "active_holds": active_holds,
            "waitlist_volume": waitlist_volume,
        },
        "inventory": [dict(r) for r in inventory_rows],
        "reservations": [dict(res) for res in active_reservations],
        "waitlists": [dict(w) for w in pending_waitlists],
    }
    return templates.TemplateResponse(request, "admin/dashboard.html", context)


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


async def inline_update_model_url(request: Request) -> HTMLResponse:
    """POST /admin/dashboard/update-model-url — HTMX inline update of model_3d_url."""
    import uuid as _uuid

    form_data = await request.form()
    product_id = form_data.get("product_id")
    # Accept either field name — legacy callers send `model_url`, the canonical
    # column is `model_3d_url`. Be lenient so test + dashboard + curl all work.
    model_url = (
        form_data.get("model_3d_url")
        or form_data.get("model_url")
        or ""
    ).strip()

    if not product_id:
        return HTMLResponse(
            "<span class='text-xs text-red-500'>Missing product_id</span>",
            status_code=400,
        )

    # Guard against malformed UUIDs — asyncpg raises UndefinedFunctionError or
    # InvalidTextRepresentation for non-UUID input. Return 400 instead of 500.
    try:
        _uuid.UUID(str(product_id))
    except (ValueError, AttributeError, TypeError):
        return HTMLResponse(
            f"<span class='text-xs text-red-500'>Invalid product_id: {product_id}</span>",
            status_code=400,
        )

    if not model_url:
        model_url = None

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE products SET model_3d_url = $1 WHERE id = $2;",
            model_url, product_id,
        )

    preview = ""
    if model_url:
        preview = f"<a href='{model_url}' target='_blank' class='underline hover:text-[#D4AF37]'>{model_url.rsplit('/', 1)[-1]}</a>"

    return HTMLResponse(
        f"<span class='text-[10px] font-mono text-[#10B981]' "
        f"hx-swap-oob='true' id='model-status-{product_id}'>"
        f"✓ {preview or 'No 3D model'}</span>"
    )


async def link_2d_source_asset(request):
    """
    Accepts both multipart device file uploads and raw URL path values,
    persisting the resulting reference image string to trigger the 3D pipeline loop.
    """
    import os
    import secrets
    from starlette.datastructures import UploadFile

    form = await request.form()
    product_id = form.get("product_id")
    asset_category = form.get("asset_category", "apparel")
    image_url = form.get("source_2d_image_url")
    uploaded_file = form.get("source_2d_file")  # Starlette UploadFile instance

    UPLOAD_DIR = "static/uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    final_image_path = None

    # 1. Check if a device file upload was provided
    if uploaded_file and hasattr(uploaded_file, 'filename') and uploaded_file.filename:
        filename = uploaded_file.filename
        # Sanitize name extension to prevent directory traversal exploits
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
            return HTMLResponse(
                content="<span class='text-xs text-red-500'>Invalid image format.</span>"
            )

        # Create a unique unguessable file string to prevent caching collisions
        secure_filename = f"prod_{product_id}_{secrets.token_hex(4)}{ext}"
        file_path = os.path.join(UPLOAD_DIR, secure_filename)

        # Read file bytes streams and flush cleanly to server disk storage space
        contents = await uploaded_file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        final_image_path = f"/{file_path}"

    # 2. Fall back to standard text URL input if no file wrapper was uploaded
    elif image_url and image_url.strip():
        final_image_path = image_url.strip()

    if not final_image_path:
        return HTMLResponse(
            content="<span class='text-xs text-red-500'>Please upload a file or paste a valid URL path.</span>"
        )

    # 3. Synchronize database state parameters with our transactional execution handle
    db_pool = request.app.state.db_pool
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE products
            SET source_2d_image_url = $1,
                asset_category = $2,
                pipeline_status = 'queued',
                pipeline_error_log = NULL
            WHERE id = $3::UUID;
            """,
            final_image_path, asset_category, product_id
        )

    return HTMLResponse(
        content=f"""
        <div id="pipeline-status-{product_id}" hx-get="/admin/dashboard/pipeline-status/{product_id}" hx-trigger="every 3s" class="flex items-center space-x-2">
            <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
            <span class="text-xs font-mono uppercase tracking-wider text-amber-400">Processing Asset Ingestion</span>
        </div>
        """
    )


async def get_pipeline_status_fragment(request):
    """Returns the current processing status fragment for continuous HTMX updates."""
    product_id = request.path_params.get("id")
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT pipeline_status, model_3d_url, pipeline_error_log FROM products WHERE id = $1::UUID;",
            product_id
        )

    if not row:
        return HTMLResponse(content="<span class='text-xs text-red-500'>Missing Node</span>")

    status = row["pipeline_status"]

    if status == 'completed':
        return HTMLResponse(content=f"""
            <div id="pipeline-status-{product_id}" class="text-xs font-mono text-[#10B981] flex items-center space-x-1.5">
                <span>✅ Ready</span>
                <span class="text-[10px] text-white/40">({row['model_3d_url']})</span>
            </div>
        """)
    elif status == 'failed':
        return HTMLResponse(content=f"""
            <div id="pipeline-status-{product_id}" class="text-xs font-mono text-[#EF4444] group relative cursor-pointer">
                <span>❌ Engine Error</span>
                <div class="hidden group-hover:block absolute bg-black border border-white/10 p-2 rounded text-[10px] w-48 z-30 mt-1">
                    {row['pipeline_error_log']}
                </div>
            </div>
        """)
    else:
        return HTMLResponse(content=f"""
            <div id="pipeline-status-{product_id}" hx-get="/admin/dashboard/pipeline-status/{product_id}" hx-trigger="every 3s" class="flex items-center space-x-2">
                <span class="w-2 h-2 rounded-full bg-blue-400 animate-spin"></span>
                <span class="text-xs font-mono uppercase text-blue-300">{status.replace('_', ' ')}</span>
            </div>
        """)


async def simulate_pipeline_processing_worker(request):
    """Simulates background automated script operations for smooth pipeline state transitions."""
    form = await request.form()
    product_id = form.get("product_id")
    target_action = form.get("action")
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        if target_action == "fail":
            await conn.execute(
                """
                UPDATE products SET pipeline_status = 'failed',
                pipeline_error_log = 'AI_MESH_GENERATOR_ERROR: Resolution out of bounds.' WHERE id = $1::UUID;
                """, product_id
            )
        else:
            mock_model_url = f"/static/models/auto_generated_{product_id}.glb"
            await conn.execute(
                """
                UPDATE products SET pipeline_status = 'completed', model_3d_url = $1,
                pipeline_error_log = NULL WHERE id = $2::UUID;
                """, mock_model_url, product_id
            )

    return HTMLResponse(content="", headers={"HX-Refresh": "true"})


routes = [
    Route("/admin/dashboard", endpoint=admin_dashboard_home, methods=["GET"]),
    Route("/admin/dashboard/update-stock", endpoint=inline_update_stock, methods=["POST"]),
    Route("/admin/dashboard/notify-waitlist", endpoint=inline_trigger_restock_alert, methods=["POST"]),
    Route("/admin/dashboard/update-model-url", endpoint=inline_update_model_url, methods=["POST"]),
    Route("/admin/dashboard/pipeline/link-2d", endpoint=link_2d_source_asset, methods=["POST"]),
    Route("/admin/dashboard/pipeline-status/{id:uuid}", endpoint=get_pipeline_status_fragment, methods=["GET"]),
    Route("/admin/dashboard/pipeline/simulate", endpoint=simulate_pipeline_processing_worker, methods=["POST"]),
]