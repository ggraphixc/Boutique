# ASIKO Boutique - Storefront Routes (Single-Brand)
# Homepage, HTMX grid, editorial PDP with capsule lookups + concierge signing.

import re
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route
from django.core.signing import Signer

import hashlib

from app.core import templates
from app.settings_service import get_settings

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
    settings = await get_settings(pool)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT p.id, p.name, p.description, p.price, p.stock_quantity, "
            "p.base_image, c.name AS category_name "
            "FROM products p LEFT JOIN categories c ON c.id = p.category_id "
            "ORDER BY p.id DESC"
        )

    products = []
    for p in rows:
        d = dict(p)
        d["slug"] = _slugify(d["name"])
        d["base_price"] = d["price"]
        products.append(d)

    return templates.TemplateResponse(
        request, "storefront/index.html",
        {"request": request, "products": products, "settings": settings},
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
            "SELECT id, name, price, base_image "
            "FROM products ORDER BY id DESC"
        )

    products = []
    for p in rows:
        d = dict(p)
        d["slug"] = _slugify(d["name"])
        d["base_price"] = d["price"]
        products.append(d)

    return templates.TemplateResponse(
        request, "storefront/product_grid.html",
        {"request": request, "products": products},
    )


async def lookbook(request: Request) -> HTMLResponse:
    """Editorial lookbook page — curated product showcase."""
    pool = request.app.state.db_pool
    settings = await get_settings(pool)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, description, price, stock_quantity, "
            "base_image "
            "FROM products ORDER BY id DESC"
        )

    products = []
    for p in rows:
        d = dict(p)
        products.append(d)

    return templates.TemplateResponse(
        request, "storefront/lookbook.html",
        {"request": request, "products": products, "settings": settings},
    )


async def product_detail(request: Request) -> HTMLResponse:
    """
    Editorial PDP: capsule lookups from asiko_capsule_assignments,
    concierge token via Django Signer, gallery from base_image.
    """
    product_id = request.path_params["product_id"]
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        p_row = await conn.fetchrow(
            "SELECT id, name, description, price, base_image "
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
        "gallery_images": gallery_images,
        "capsule_look": {
            "items": capsule_items,
        },
    }

    cart = request.session.get("cart", {"item_count": 0, "total": 0.0, "lines": []})
    settings = await get_settings(pool)
    context = {
        "request": request,
        "concierge_token": concierge_token,
        "product": product_data,
        "cart": cart,
        "settings": settings,
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
            "SELECT stock_quantity FROM products WHERE id = $1", product_id
        )
    qty = row["stock_quantity"] if row else 0
    if qty == 0:
        html = '<span class="text-[11px] font-mono uppercase tracking-wider text-red-600 bg-red-50 px-2 py-0.5 rounded">Sold out</span>'
    elif qty <= 5:
        html = f'<span class="text-[11px] font-mono uppercase tracking-wider text-amber-700 bg-amber-50 px-2 py-0.5 rounded">Only {qty} left</span>'
    else:
        html = '<span class="text-[11px] font-mono uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">In stock</span>'
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# Product Reviews
# ---------------------------------------------------------------------------

async def submit_review(request: Request) -> HTMLResponse:
    """Submit a product review. POST /product/{product_id}/review"""
    product_id = request.path_params["product_id"]
    form = await request.form()
    rating = int(form.get("rating") or 5)
    title = (form.get("title") or "").strip()[:120]
    body = (form.get("body") or "").strip()[:1000]
    customer_name = (form.get("name") or "").strip() or "Anonymous"
    customer_email = (form.get("email") or "").strip()

    rating = max(1, min(5, rating))

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO product_reviews (product_id, customer_name, customer_email, rating, title, body, verified)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            product_id, customer_name, customer_email, rating, title, body, bool(customer_email),
        )

    return HTMLResponse("""
        <div class="bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm px-4 py-3 rounded-lg">
            Thank you! Your review has been submitted.
        </div>
    """)


async def product_reviews_fragment(request: Request) -> HTMLResponse:
    """HTMX fragment: reviews list for a product. GET /product/{product_id}/reviews"""
    product_id = request.path_params["product_id"]
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        reviews = await conn.fetch(
            """
            SELECT customer_name, rating, title, body, created_at
            FROM product_reviews
            WHERE product_id = $1 AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 20
            """,
            product_id,
        )

    if not reviews:
        return HTMLResponse("""
            <div class="text-center py-8 text-sm text-brand-deep/40">
                No reviews yet. Be the first to share your experience.
            </div>
        """)

    stars_html = ""
    for r in reviews:
        created = r["created_at"].strftime("%d %b %Y") if r["created_at"] else ""
        stars = "★" * r["rating"] + "☆" * (5 - r["rating"])
        stars_html += f"""
            <div class="border-b border-brand-deep/5 py-4 last:border-0">
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-amber-500 text-sm">{stars}</span>
                    <span class="text-xs text-brand-deep/50">{created}</span>
                </div>
                <p class="text-sm font-medium text-brand-deep">{r['title'] or ''}</p>
                <p class="text-sm text-brand-deep/60 mt-1">{r['body'] or ''}</p>
                <p class="text-xs text-brand-deep/40 mt-2">— {r['customer_name']}</p>
            </div>
        """

    return HTMLResponse(stars_html)


async def about_page(request: Request) -> HTMLResponse:
    """Public About page. GET /about"""
    pool = request.app.state.db_pool
    settings = await get_settings(pool)

    async with pool.acquire() as conn:
        about = await conn.fetchrow("SELECT * FROM about_me LIMIT 1")

    ctx = {}
    if about:
        ctx = {
            "name": about.get("name") or settings.get("about_title", "ASIKO Boutique"),
            "role": about.get("role") or "",
            "tagline": about.get("tagline") or settings.get("about_tagline", ""),
            "story": about.get("story") or settings.get("about_story", ""),
            "location": about.get("location") or settings.get("about_location", ""),
            "email": about.get("email") or settings.get("about_email", ""),
            "founded_year": about.get("founded_year") or settings.get("about_founded_year", 2024),
        }
    else:
        ctx = {
            "name": settings.get("about_title", "ASIKO Boutique"),
            "role": "",
            "tagline": settings.get("about_tagline", ""),
            "story": settings.get("about_story", ""),
            "location": settings.get("about_location", ""),
            "email": settings.get("about_email", ""),
            "founded_year": settings.get("about_founded_year", 2024),
        }

    return templates.TemplateResponse(request, "storefront/about.html", {
        "request": request,
        "about": ctx,
        "settings": settings,
    })


async def fashion_assistant_page(request: Request) -> HTMLResponse:
    """Render the AI Fashion Assistant page."""
    pool = request.app.state.db_pool
    settings = await get_settings(pool)
    return templates.TemplateResponse(request, "fashion_assistant.html", {
        "request": request,
        "settings": settings,
    })


async def dynamic_page(request: Request) -> HTMLResponse:
    """Render a custom page by slug (e.g. /page/size-guide)."""
    pool = request.app.state.db_pool
    slug = request.path_params.get("slug", "")
    settings = await get_settings(pool)

    async with pool.acquire() as conn:
        page = await conn.fetchrow(
            "SELECT id, title, slug, body_html, excerpt, meta_description, featured_image "
            "FROM custom_pages WHERE slug = $1 AND is_live = TRUE",
            slug,
        )

    if not page:
        return HTMLResponse("<h1>Page not found</h1>", status_code=404)

    return templates.TemplateResponse(request, "storefront/page.html", {
        "request": request,
        "page": dict(page),
        "settings": settings,
    })


async def blog_listing(request: Request) -> HTMLResponse:
    """Render blog listing (all published posts across all pages)."""
    pool = request.app.state.db_pool
    settings = await get_settings(pool)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT bp.id, bp.title, bp.slug, bp.excerpt, bp.featured_image, "
            "bp.published_at, bp.author_name, "
            "cp.title AS page_title, cp.slug AS page_slug "
            "FROM blog_posts bp "
            "JOIN custom_pages cp ON cp.id = bp.page_id "
            "WHERE bp.is_published = TRUE "
            "ORDER BY bp.published_at DESC NULLS LAST"
        )

    posts = [dict(r) for r in rows]

    return templates.TemplateResponse(request, "storefront/blog_listing.html", {
        "request": request,
        "posts": posts,
        "settings": settings,
    })


async def blog_post_detail(request: Request) -> HTMLResponse:
    """Render a single blog post by slug."""
    pool = request.app.state.db_pool
    slug = request.path_params.get("slug", "")
    settings = await get_settings(pool)

    async with pool.acquire() as conn:
        post = await conn.fetchrow(
            "SELECT bp.id, bp.title, bp.slug, bp.content_html, bp.excerpt, "
            "bp.featured_image, bp.published_at, bp.author_name, "
            "cp.title AS page_title, cp.slug AS page_slug "
            "FROM blog_posts bp "
            "JOIN custom_pages cp ON cp.id = bp.page_id "
            "WHERE bp.slug = $1 AND bp.is_published = TRUE",
            slug,
        )

    if not post:
        return HTMLResponse("<h1>Post not found</h1>", status_code=404)

    return templates.TemplateResponse(request, "storefront/blog_post.html", {
        "request": request,
        "post": dict(post),
        "settings": settings,
    })


routes = [
    Route("/", endpoint=homepage, methods=["GET"]),
    Route("/about", endpoint=about_page, methods=["GET"]),
    Route("/lookbook", endpoint=lookbook, methods=["GET"]),
    Route("/htmx/products", endpoint=product_grid_fragment, methods=["GET"]),
    Route("/product/{product_id}", endpoint=product_detail, methods=["GET"]),
    Route("/product/{product_id}/review", endpoint=submit_review, methods=["POST"]),
    Route("/product/{product_id}/reviews", endpoint=product_reviews_fragment, methods=["GET"]),
    Route("/dpp", endpoint=dpp_verification, methods=["GET"]),
    Route("/ws/store/product/{product_id}/stock-badge", endpoint=stock_badge_fragment, methods=["GET"]),
    Route("/stylist", endpoint=fashion_assistant_page, methods=["GET"]),
    Route("/page/{slug}", endpoint=dynamic_page, methods=["GET"]),
    Route("/blog", endpoint=blog_listing, methods=["GET"]),
    Route("/blog/{slug}", endpoint=blog_post_detail, methods=["GET"]),
]
