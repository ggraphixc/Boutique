# ASIKO Boutique — Admin CRUD Router Pipelines
# Product management endpoints for HTMX-driven admin interface.
# Returns raw HTML fragments for HTMX swaps (matches admin_inventory.py pattern).

import asyncpg
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route


async def get_admin_products_fragment(request: Request) -> HTMLResponse:
    """
    GET /admin/products — HTMX fragment: product table with inline edit/delete.
    Queries products with variant stock summary.
    """
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT p.id, p.name, p.slug, p.price, p.stock_quantity,
                   p.base_image, p.created_at,
                   COUNT(v.id) AS variant_count,
                   COALESCE(SUM(v.stock_qty), 0) AS total_variant_stock
            FROM products p
            LEFT JOIN product_variants v ON v.product_id = p.id
            GROUP BY p.id
            ORDER BY p.created_at DESC
            """
        )

    if not records:
        return HTMLResponse(
            "<div class='p-8 text-center border border-dashed border-neutral-300'>"
            "<p class='text-xs font-mono text-neutral-400 uppercase tracking-wider'>"
            "No products in ledger</p></div>"
        )

    rows_html = ""
    for r in records:
        price_val = float(r["price"]) if r["price"] else 0
        stock_val = r["total_variant_stock"] or 0
        stock_class = "text-[#10B981]" if stock_val > 0 else "text-[#EF4444]"
        created = r["created_at"].strftime("%Y-%m-%d") if r["created_at"] else "\u2014"
        row_id = f"product-row-{r['id']}"
        short_id = str(r["id"])[:8]
        delete_name = r["name"].replace("'", "&#39;")
        variant_count = r["variant_count"]
        product_name = r["name"]
        slug_val = r["slug"] or "\u2014"

        rows_html += (
            f"<tr class='border-b border-neutral-100 hover:bg-[#0D2A22]/[0.02] transition-colors' id='{row_id}'>"
            f"<td class='p-3 text-[11px] font-mono text-neutral-500 max-w-[80px] truncate'>{short_id}</td>"
            f"<td class='p-3'>"
            f"<span class='text-sm font-medium text-[#0D2A22]'>{product_name}</span>"
            f"<br><span class='text-[10px] font-mono text-neutral-400'>{slug_val}</span>"
            f"</td>"
            f"<td class='p-3 text-right font-mono text-sm text-[#0D2A22]'>&curren;{price_val:,.0f}</td>"
            f"<td class='p-3 text-center'>"
            f"<span class='text-xs font-mono {stock_class}'>{stock_val}</span>"
            f"<span class='text-[10px] text-neutral-400 ml-1'>({variant_count} vars)</span>"
            f"</td>"
            f"<td class='p-3 text-[10px] font-mono text-neutral-400'>{created}</td>"
            f"<td class='p-3 text-right'>"
            f"<button class='text-[10px] font-mono uppercase tracking-wider text-[#D4AF37] hover:text-[#0D2A22]' "
            f"hx-delete='/admin/products/{r['id']}' "
            f"hx-confirm='Delete {delete_name}? This cannot be undone.' "
            f"hx-target='#{row_id}' "
            f"hx-swap='outerHTML swap:1s'>Delete</button>"
            f"</td>"
            f"</tr>"
        )

    record_count = len(records)
    html = (
        "<div class='overflow-x-auto bg-white border border-[#0D2A22]/10 shadow-sm animate-fade-in'>"
        "<div class='px-4 py-3 border-b border-[#0D2A22]/5 flex justify-between items-center'>"
        "<h3 class='text-[10px] font-mono uppercase tracking-[0.2em] text-[#0D2A22] font-semibold'>"
        f"Product Ledger ({record_count} items)</h3>"
        "</div>"
        "<table class='w-full text-left border-collapse'>"
        "<thead><tr class='bg-[#0D2A22] text-[#FBF9F6] font-mono text-[10px] uppercase tracking-wider'>"
        "<th class='p-3'>ID</th>"
        "<th class='p-3'>Product</th>"
        "<th class='p-3 text-right'>Price</th>"
        "<th class='p-3 text-center'>Stock</th>"
        "<th class='p-3'>Created</th>"
        "<th class='p-3 text-right'>Actions</th>"
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table></div>"
    )
    return HTMLResponse(html)


async def handle_delete_product(request: Request) -> HTMLResponse:
    """
    DELETE /admin/products/{id} — Cascade-delete product and its variants.
    Returns empty 200 for HTMX to remove the row from DOM.
    """
    product_id = request.path_params.get("id")
    if not product_id:
        return JSONResponse(
            {"status": "error", "message": "MISSING_PRODUCT_ID"},
            status_code=400,
        )

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT id FROM products WHERE id = $1",
            product_id,
        )
        if not exists:
            return HTMLResponse(
                "<div class='text-xs font-mono text-[#EF4444] p-2'>Product not found.</div>",
                status_code=404,
            )

        try:
            await conn.execute("DELETE FROM products WHERE id = $1", product_id)
        except asyncpg.ForeignKeyViolationError:
            return HTMLResponse(
                "<div class='text-xs font-mono text-[#EF4444] p-2'>Cannot delete — this product has existing orders. Archive it instead.</div>",
                status_code=409,
            )

    return HTMLResponse("")


async def get_product_detail_fragment(request: Request) -> HTMLResponse:
    """
    GET /admin/products/{id}/detail — HTMX fragment: single product detail view.
    Returns inline product card with variants for quick-edit context.
    """
    product_id = request.path_params.get("id")
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        product = await conn.fetchrow(
            "SELECT * FROM products WHERE id = $1",
            product_id,
        )
        if not product:
            return HTMLResponse(
                "<div class='p-4 text-xs font-mono text-[#EF4444]'>Product not found.</div>",
                status_code=404,
            )

        variants = await conn.fetch(
            """
            SELECT id, size, color, stock_qty, mesh_node_identifier, custom_shader_color
            FROM product_variants
            WHERE product_id = $1
            ORDER BY size, color
            """,
            product_id,
        )

    price_val = float(product["price"]) if product["price"] else 0
    product_name = product["name"]
    slug_val = product["slug"] or "\u2014"

    variants_html = ""
    for v in variants:
        color_hex = v["custom_shader_color"] or "#ccc"
        variants_html += (
            f"<div class='flex items-center gap-2 text-[11px] font-mono py-1 border-b border-neutral-100'>"
            f"<span class='w-8 text-neutral-500'>{v['size']}</span>"
            f"<span class='flex items-center gap-1'>"
            f"<span class='inline-block w-3 h-3 rounded-full border border-neutral-200' "
            f"style='background-color: {color_hex}'></span> {v['color']}</span>"
            f"<span class='ml-auto text-[#0D2A22] font-semibold'>{v['stock_qty']}</span>"
            f"</div>"
        )

    if not variants_html:
        variants_html = "<p class='text-[10px] font-mono text-neutral-400 py-2'>No variants configured.</p>"

    html = (
        "<div class='bg-white border border-[#0D2A22]/10 p-5 shadow-sm animate-fade-in'>"
        f"<h4 class='text-sm font-medium text-[#0D2A22] mb-1'>{product_name}</h4>"
        f"<p class='text-[10px] font-mono text-neutral-400 mb-3'>{slug_val}</p>"
        f"<div class='grid grid-cols-2 gap-4 mb-4'>"
        f"<div><span class='block text-[9px] uppercase tracking-wider text-neutral-400 font-mono'>Price</span>"
        f"<span class='text-sm font-mono text-[#0D2A22]'>&curren;{price_val:,.0f}</span></div>"
        f"</div>"
        f"<div class='border-t border-[#0D2A22]/5 pt-3'>"
        f"<span class='block text-[9px] uppercase tracking-wider text-neutral-400 font-mono mb-2'>Variants</span>"
        f"{variants_html}"
        f"</div></div>"
    )
    return HTMLResponse(html)


async def get_general_settings_fragment(request: Request) -> HTMLResponse:
    """
    GET /admin/settings — HTMX fragment: general admin settings panel.
    Returns static settings layout for brand configuration.
    """
    html = (
        "<div class='bg-white border border-[#0D2A22]/10 p-6 shadow-sm animate-fade-in'>"
        "<h3 class='text-[10px] font-mono uppercase tracking-[0.2em] text-[#0D2A22] font-semibold mb-4'>"
        "General Configuration</h3>"
        "<div class='space-y-4'>"
        "<div class='flex items-center justify-between py-2 border-b border-neutral-100'>"
        "<div><span class='block text-sm text-[#0D2A22]'>Brand Name</span>"
        "<span class='block text-[10px] font-mono text-neutral-400'>Primary brand identity label</span></div>"
        "<span class='text-sm font-mono text-[#0D2A22]'>ASIKO</span>"
        "</div>"
        "<div class='flex items-center justify-between py-2 border-b border-neutral-100'>"
        "<div><span class='block text-sm text-[#0D2A22]'>Currency</span>"
        "<span class='block text-[10px] font-mono text-neutral-400'>Transaction denomination</span></div>"
        "<span class='text-sm font-mono text-[#0D2A22]'>NGN</span>"
        "</div>"
        "<div class='flex items-center justify-between py-2 border-b border-neutral-100'>"
        "<div><span class='block text-sm text-[#0D2A22]'>Session Expiry</span>"
        "<span class='block text-[10px] font-mono text-neutral-400'>Cart &amp; reservation timeout window</span></div>"
        "<span class='text-sm font-mono text-[#0D2A22]'>60 minutes</span>"
        "</div>"
        "<div class='flex items-center justify-between py-2 border-b border-neutral-100'>"
        "<div><span class='block text-sm text-[#0D2A22]'>Email Provider</span>"
        "<span class='block text-[10px] font-mono text-neutral-400'>Transactional dispatch service</span></div>"
        "<span class='text-sm font-mono text-[#10B981]'>Brevo (Active)</span>"
        "</div>"
        "<div class='flex items-center justify-between py-2'>"
        "<div><span class='block text-sm text-[#0D2A22]'>Payment Gateway</span>"
        "<span class='block text-[10px] font-mono text-neutral-400'>Settlement processor</span></div>"
        "<span class='text-sm font-mono text-[#D4AF37]'>OPay (Bank Transfer + Card)</span>"
        "</div>"
        "</div></div>"
    )
    return HTMLResponse(html)


async def create_product(request: Request):
    """
    POST /admin/products/create — Create a new product.
    Accepts multipart form: name, price, category, description, source_2d_file (optional).
    Returns redirect to reload the products section.
    """
    import os
    import secrets
    import re
    from starlette.responses import HTMLResponse, RedirectResponse

    form = await request.form()
    name = (form.get("name") or "").strip()
    price_raw = (form.get("price") or "0").strip()
    category = (form.get("category") or "").strip()
    stock_raw = (form.get("stock_quantity") or "0").strip()
    description = (form.get("description") or "").strip()
    uploaded_file = form.get("source_2d_file")

    if not name:
        return HTMLResponse(
            "<span class='text-xs text-red-500'>Please enter a product name.</span>",
            status_code=400,
        )

    try:
        price = float(price_raw)
    except (ValueError, TypeError):
        price = 0.0

    try:
        stock_quantity = int(float(stock_raw))
    except (ValueError, TypeError):
        stock_quantity = 0

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    # Handle optional image upload
    UPLOAD_DIR = "static/uploads"
    image_path = None
    if uploaded_file and hasattr(uploaded_file, "filename") and uploaded_file.filename:
        ext = os.path.splitext(uploaded_file.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            return HTMLResponse(
                "<span class='text-xs text-red-500'>Invalid image format. Use JPG, PNG, or WebP.</span>",
                status_code=400,
            )
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        secure_name = f"prod_{secrets.token_hex(8)}{ext}"
        file_path = os.path.join(UPLOAD_DIR, secure_name)
        contents = await uploaded_file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        image_path = f"/{file_path}"

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        # Fetch the default store (required NOT NULL column)
        store_id = await conn.fetchval("SELECT id FROM stores ORDER BY created_at LIMIT 1")
        if not store_id:
            return HTMLResponse(
                "<span class='text-xs text-red-500'>No store configured. Create a store first.</span>",
                status_code=400,
            )

        # Check for duplicate slug, append suffix if needed
        base_slug = slug
        suffix = 1
        while True:
            exists = await conn.fetchval(
                "SELECT id FROM products WHERE slug = $1", slug
            )
            if not exists:
                break
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        # Resolve category_id from category name
        category_id = None
        if category:
            category_id = await conn.fetchval(
                "SELECT id FROM categories WHERE name = $1", category
            )

        await conn.execute(
            """
            INSERT INTO products (store_id, name, slug, price, stock_quantity, base_image, description, category_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            store_id, name, slug, price, stock_quantity, image_path, description or None, category_id,
        )

    # Return a success message with HX-Redirect to reload the products section
    return HTMLResponse(
        "<div class='text-xs text-emerald-600 font-medium'>Product created successfully.</div>",
        headers={"HX-Redirect": "/admin/section/products?success=Product+created"},
    )


async def edit_product(request: Request):
    """
    POST /admin/products/{id}/edit — Update an existing product.
    Accepts multipart form: name, price, stock_quantity, category, description, source_2d_file (optional).
    Returns redirect to reload the products section.
    """
    import os
    import secrets
    import re

    product_id = request.path_params.get("id")
    if not product_id:
        return HTMLResponse(
            "<span class='text-xs text-red-500'>Product not found.</span>",
            status_code=400,
        )

    form = await request.form()
    name = (form.get("name") or "").strip()
    price_raw = (form.get("price") or "0").strip()
    category = (form.get("category") or "").strip()
    stock_raw = (form.get("stock_quantity") or "0").strip()
    description = (form.get("description") or "").strip()
    uploaded_file = form.get("source_2d_file")

    if not name:
        return HTMLResponse(
            "<span class='text-xs text-red-500'>Please enter a product name.</span>",
            status_code=400,
        )

    try:
        price = float(price_raw)
    except (ValueError, TypeError):
        price = 0.0

    try:
        stock_quantity = int(float(stock_raw))
    except (ValueError, TypeError):
        stock_quantity = 0

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    # Handle optional new image upload
    UPLOAD_DIR = "static/uploads"
    image_path = None
    if uploaded_file and hasattr(uploaded_file, "filename") and uploaded_file.filename:
        ext = os.path.splitext(uploaded_file.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            return HTMLResponse(
                "<span class='text-xs text-red-500'>Invalid image format. Use JPG, PNG, or WebP.</span>",
                status_code=400,
            )
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        secure_name = f"prod_{secrets.token_hex(8)}{ext}"
        file_path = os.path.join(UPLOAD_DIR, secure_name)
        contents = await uploaded_file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        image_path = f"/{file_path}"

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        # Verify product exists
        exists = await conn.fetchval("SELECT id FROM products WHERE id = $1", product_id)
        if not exists:
            return HTMLResponse(
                "<span class='text-xs text-red-500'>Product not found.</span>",
                status_code=404,
            )

        # Check for duplicate slug (excluding current product)
        base_slug = slug
        suffix = 1
        while True:
            dup = await conn.fetchval(
                "SELECT id FROM products WHERE slug = $1 AND id != $2",
                slug, product_id,
            )
            if not dup:
                break
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        # Resolve category_id from category name
        category_id = None
        if category:
            category_id = await conn.fetchval(
                "SELECT id FROM categories WHERE name = $1", category
            )

        # Build update query
        if image_path:
            await conn.execute(
                """
                UPDATE products
                SET name = $1, slug = $2, price = $3, stock_quantity = $4,
                    base_image = $5, description = $6, category_id = $7
                WHERE id = $8
                """,
                name, slug, price, stock_quantity, image_path, description or None, category_id, product_id,
            )
        else:
            await conn.execute(
                """
                UPDATE products
                SET name = $1, slug = $2, price = $3, stock_quantity = $4,
                    description = $5, category_id = $6
                WHERE id = $7
                """,
                name, slug, price, stock_quantity, description or None, category_id, product_id,
            )

    return HTMLResponse(
        "<div class='text-xs text-emerald-600 font-medium'>Product updated successfully.</div>",
        headers={"HX-Redirect": "/admin/section/products?success=Product+updated"},
    )


routes = [
    Route("/admin/products", endpoint=get_admin_products_fragment, methods=["GET"]),
    Route("/admin/products/create", endpoint=create_product, methods=["POST"]),
    Route("/admin/products/{id}/edit", endpoint=edit_product, methods=["POST"]),
    Route("/admin/products/{id}/detail", endpoint=get_product_detail_fragment, methods=["GET"]),
    Route("/admin/products/{id}", endpoint=handle_delete_product, methods=["DELETE"]),
    Route("/admin/settings", endpoint=get_general_settings_fragment, methods=["GET"]),
]
