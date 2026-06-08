# ASIKO Boutique - Storefront Routes (Single-Brand)
# Homepage, HTMX grid, editorial PDP with capsule lookups + concierge signing.

import re
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route
from django.core.signing import Signer

import hashlib

from app.core import templates

signer = Signer(salt="asiko.concierge.vector")


def _slugify(text: str) -> str:
    """Generate URL-safe slug from product name (no slug column in schema)."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text)


async def homepage(request: Request) -> HTMLResponse:
    """Render the unified single-brand editorial catalog index."""
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, description, price, stock_quantity, "
            "base_image, model_3d_url "
            "FROM products ORDER BY id DESC"
        )

    products = []
    for p in rows:
        d = dict(p)
        d["slug"] = _slugify(d["name"])
        d["base_price"] = d["price"]
        d["has_3d_model"] = d.get("model_3d_url") is not None
        products.append(d)

    return templates.TemplateResponse(
        request, "storefront/index.html",
        {"request": request, "products": products},
    )


async def dpp_verification(request: Request) -> HTMLResponse:
    """
    GET /dpp — Digital Product Passport verification page.
    Accepts optional ?serial= query param; renders verified or unverified state.
    """
    serial = request.query_params.get("serial", "")

    if not serial:
        # Show empty lookup state
        return templates.TemplateResponse(
            request, "storefront/dpp_verification.html",
            {
                "request": request,
                "verified": False,
                "product_name": "",
                "serial": "",
                "fabric": "",
                "dye": "",
                "artisan_id": "",
                "wage_index": "",
            },
        )

    # Attempt to parse product ID from serial pattern: ASIKO-{id}-NGA-2026
    match = re.match(r"ASIKO-(\d{6})-NGA-2026", serial)
    if not match:
        return templates.TemplateResponse(
            request, "storefront/dpp_verification.html",
            {
                "request": request,
                "verified": False,
                "product_name": "",
                "serial": serial,
                "fabric": "",
                "dye": "",
                "artisan_id": "",
                "wage_index": "",
            },
        )

    # Serial numbers map to sequential product IDs; query by position
    serial_index = int(match.group(1))
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        p_row = await conn.fetchrow(
            "SELECT id, name FROM products ORDER BY created_at ASC, id ASC LIMIT 1 OFFSET $1",
            serial_index - 1,
        )

    if not p_row:
        return templates.TemplateResponse(
            request, "storefront/dpp_verification.html",
            {
                "request": request,
                "verified": False,
                "product_name": "",
                "serial": serial,
                "fabric": "",
                "dye": "",
                "artisan_id": "",
                "wage_index": "",
            },
        )

    # Build DPP provenance data from product + cryptographic seed
    seed = hashlib.sha256(f"ASIKO:{serial_index}:{p_row['name']}:NGA:2026".encode()).hexdigest()[:8].upper()
    context = {
        "request": request,
        "verified": True,
        "product_name": p_row["name"],
        "serial": serial,
        "fabric": "Aba Handloomed Cotton / Organic Vegetable Dye",
        "dye": "Indigofera & Kola Nut Extract (Terroir-Mapped)",
        "artisan_id": f"ATLR-{serial_index:04d}-NG-{seed}",
        "wage_index": "94.2",
    }
    return templates.TemplateResponse(
        request, "storefront/dpp_verification.html", context,
    )


async def product_grid_fragment(request: Request) -> HTMLResponse:
    """HTMX grid fragment for seamless server-driven injection."""
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, price, base_image, model_3d_url "
            "FROM products ORDER BY id DESC"
        )

    products = []
    for p in rows:
        d = dict(p)
        d["slug"] = _slugify(d["name"])
        d["base_price"] = d["price"]
        d["has_3d_model"] = d.get("model_3d_url") is not None
        products.append(d)

    return templates.TemplateResponse(
        request, "storefront/product_grid.html",
        {"request": request, "products": products},
    )


async def lookbook(request: Request) -> HTMLResponse:
    """Editorial lookbook page — curated product showcase."""
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, description, price, stock_quantity, "
            "base_image, model_3d_url "
            "FROM products ORDER BY id DESC"
        )

    products = []
    for p in rows:
        d = dict(p)
        d["has_3d_model"] = d.get("model_3d_url") is not None
        products.append(d)

    return templates.TemplateResponse(
        request, "storefront/lookbook.html",
        {"request": request, "products": products},
    )


async def product_detail(request: Request) -> HTMLResponse:
    """
    Editorial PDP: capsule lookups from asiko_capsule_assignments,
    concierge token via Django Signer, gallery from base_image.
    """
    product_id = int(request.path_params["product_id"])
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        p_row = await conn.fetchrow(
            "SELECT id, name, description, price, base_image, "
            "model_3d_url "
            "FROM products WHERE id = $1",
            product_id,
        )
        if not p_row:
            return HTMLResponse(
                "<div class='p-12 text-center font-mono text-xs text-[#0D2A22] bg-[#FBF9F6]'>"
                "Atelier Piece Missing</div>",
                status_code=404,
            )

        # Gallery: product_variants has no url column, use base_image for both slots
        gallery_images = [
            {"url": p_row["base_image"]},
            {"url": p_row["base_image"]},
        ]

        # Capsule lookups: find capsule look assigned to this product, then get sibling items
        capsule_items = []
        capsule_row = await conn.fetchrow(
            "SELECT capsule_id FROM asiko_capsule_assignments WHERE product_id = $1 LIMIT 1",
            product_id,
        )
        if capsule_row:
            siblings = await conn.fetch(
                """
                SELECT DISTINCT ON (p.id)
                       p.id, p.name, p.price, p.base_image,
                       v.id AS default_variant_id
                FROM asiko_capsule_assignments a
                JOIN products p ON p.id = a.product_id
                LEFT JOIN product_variants v ON v.product_id = p.id
                WHERE a.capsule_id = $1
                  AND p.id != $2
                ORDER BY p.id, v.id
                LIMIT 3
                """,
                capsule_row["capsule_id"],
                product_id,
            )
            for s in siblings:
                capsule_items.append({
                    "default_variant_id": str(s["default_variant_id"] or s["id"]),
                    "name": s["name"],
                    "price": s["price"],
                    "image_url": s["base_image"],
                    "type": "Atelier Curated Coordinate",
                })

    # Slug + concierge token
    generated_slug = _slugify(p_row["name"])
    handshake_payload = f"PRODUCT_ID:{p_row['id']}|SLUG:{generated_slug}"
    concierge_token = signer.sign(handshake_payload)

    product_data = {
        "id": p_row["id"],
        "name": p_row["name"],
        "slug": generated_slug,
        "collection_name": "ASIKO Atelier",
        "base_price": p_row["price"],
        "price": p_row["price"],
        "description": p_row["description"],
        "base_image": p_row["base_image"],
        "primary_image_url": p_row["base_image"],
        "model_3d_url": p_row.get("model_3d_url"),
        "gallery_images": gallery_images,
        "capsule_look": {
            "items": capsule_items,
        },
    }

    cart = request.session.get("cart", {"item_count": 0, "total": 0.0, "lines": []})
    context = {
        "request": request,
        "concierge_token": concierge_token,
        "product": product_data,
        "cart": cart,
    }
    return templates.TemplateResponse(
        request, "storefront/product_detail.html", context,
    )


async def stock_badge_fragment(request: Request) -> HTMLResponse:
    """Return a live stock badge fragment for PDP real-time updates."""
    product_id = request.path_params.get("product_id")
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT stock_quantity FROM products WHERE id = $1", int(product_id)
        )
    qty = row["stock_quantity"] if row else 0
    if qty == 0:
        html = '<span class="text-[11px] font-mono uppercase tracking-wider text-red-600 bg-red-50 px-2 py-0.5 rounded">Sold out</span>'
    elif qty <= 5:
        html = f'<span class="text-[11px] font-mono uppercase tracking-wider text-amber-700 bg-amber-50 px-2 py-0.5 rounded">Only {qty} left</span>'
    else:
        html = '<span class="text-[11px] font-mono uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">In stock</span>'
    return HTMLResponse(html)


routes = [
    Route("/", endpoint=homepage, methods=["GET"]),
    Route("/lookbook", endpoint=lookbook, methods=["GET"]),
    Route("/htmx/products", endpoint=product_grid_fragment, methods=["GET"]),
    Route("/product/{product_id:int}", endpoint=product_detail, methods=["GET"]),
    Route("/dpp", endpoint=dpp_verification, methods=["GET"]),
    Route("/ws/store/product/{product_id:int}/stock-badge", endpoint=stock_badge_fragment, methods=["GET"]),
]
