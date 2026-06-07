# ASIKO Boutique - Admin Section Endpoints
# Light-theme admin redesign: 8 sections served as HTMX fragments to #workspace-content.
#
# Sections:
#   /admin/section/dashboard     -> dashboard.html  (KPI + 3D pipeline health + activity)
#   /admin/section/products      -> products.html   (cards w/ 3D status badge)
#   /admin/section/categories    -> categories.html (CRUD list w/ colored tags)
#   /admin/section/all-products  -> all_products.html (inventory table w/ 3D status filter)
#   /admin/section/reviews       -> reviews.html    (per-product reviews)
#   /admin/section/ads           -> ads.html        (campaigns)
#   /admin/section/settings      -> settings.html   (store config)
#   /admin/section/about         -> about.html      (owner profile)
#
# All handlers are read-only GET except settings/about which accept POST.
# Empty DB is handled gracefully — sections render their empty states.

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.routing import Route

from app.core import templates

logger = logging.getLogger("asiko.admin.sections")


# ---------------------------------------------------------------------------
# Pipeline status display mapping
# DB enum (generation_status_type): idle, queued, generating_mesh, optimizing_gltf, completed, failed
# UI label:                       not_started, processing, generated, failed
# ---------------------------------------------------------------------------
PIPELINE_DISPLAY_MAP = {
    "idle":            "not_started",
    None:              "not_started",
    "queued":          "processing",
    "generating_mesh": "processing",
    "optimizing_gltf": "processing",
    "completed":       "generated",
    "failed":          "failed",
}

PIPELINE_BADGE_LABEL = {
    "not_started": "Not started",
    "processing":  "Processing",
    "generated":   "Generated",
    "failed":      "Failed",
}


def _map_pipeline_status(raw: Optional[str]) -> str:
    """Map a raw `generation_status_type` value to the UI display bucket."""
    return PIPELINE_DISPLAY_MAP.get(raw, "not_started")


def _humanize_dt(dt) -> str:
    if dt is None:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt
    if delta.days > 30:
        return dt.strftime("%b %-d, %Y")
    if delta.days >= 1:
        return f"{delta.days}d ago"
    hours = int(delta.total_seconds() // 3600)
    if hours >= 1:
        return f"{hours}h ago"
    minutes = max(int(delta.total_seconds() // 60), 0)
    if minutes >= 1:
        return f"{minutes}m ago"
    return "just now"


def _initials(name: str) -> str:
    if not name:
        return "—"
    parts = [p for p in name.strip().split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return parts[0][:2].upper()


async def _safe_fetch_products(pool) -> List[Dict[str, Any]]:
    """Fetch products + joined category + mapped pipeline_status, tolerant of NULLs."""
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT p.id, p.name, p.slug, p.price, p.stock_quantity,
                       p.base_image, p.model_3d_url, p.pipeline_status,
                       p.asset_category, p.created_at, p.updated_at,
                       c.id AS category_id, c.name AS category_name, c.color AS category_color
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.updated_at DESC NULLS LAST, p.created_at DESC
                LIMIT 60
                """
            )
    except Exception as exc:
        logger.warning("[admin] products fetch failed: %s", exc)
        return []

    products: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        raw_status = d.get("pipeline_status")
        d["pipeline_status"] = _map_pipeline_status(raw_status)
        d["pipeline_status_raw"] = raw_status
        d["pipeline_label"] = PIPELINE_BADGE_LABEL.get(d["pipeline_status"], "Not started")
        d["updated_at_human"] = _humanize_dt(d.get("updated_at"))
        d["price"] = float(d.get("price") or 0)
        products.append(d)
    return products


# ===========================================================================
# 1. DASHBOARD
# ===========================================================================
# Activity feed item kinds: 'sale', 'user', 'product', 'review', 'pipeline'
_ACTIVITY_ICONS = {
    "sale":     {"icon_bg": "bg-emerald-50", "icon_color": "text-emerald-600"},
    "user":     {"icon_bg": "bg-blue-50",    "icon_color": "text-blue-600"},
    "product":  {"icon_bg": "bg-amber-50",   "icon_color": "text-amber-600"},
    "review":   {"icon_bg": "bg-purple-50",  "icon_color": "text-purple-600"},
    "pipeline": {"icon_bg": "bg-orange-50",  "icon_color": "text-orange-600"},
    "default":  {"icon_bg": "bg-gray-100",   "icon_color": "text-gray-600"},
}


def _activity_item(kind: str, title: str, subtitle: str, time_ago: str) -> Dict[str, str]:
    icons = _ACTIVITY_ICONS.get(kind, _ACTIVITY_ICONS["default"])
    return {
        "kind": kind,
        "title": title,
        "subtitle": subtitle,
        "time_ago": time_ago,
        **icons,
    }


async def section_dashboard(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    products = await _safe_fetch_products(pool)

    # --- Pipeline status counts ---
    pipeline = {"generated": 0, "processing": 0, "failed": 0, "not_started": 0}
    for p in products:
        pipeline[p["pipeline_status"]] = pipeline.get(p["pipeline_status"], 0) + 1

    total_products = len(products)
    products_with_3d = pipeline["generated"]
    health_pct = int((products_with_3d / total_products) * 100) if total_products else 0

    # --- KPI cards ---
    # Products is the only real metric (no orders/payments/users tables yet).
    # The others are placeholder zeros until the order + session tables exist.
    # Total Sales = sum of (price * stock_quantity) for completed pieces is a
    # useful "catalog value" proxy; we still show $0 on empty stores.
    kpi_total_sales = 0
    kpi_active_users = 0
    kpi_orders = 0
    try:
        async with pool.acquire() as conn:
            try:
                kpi_total_sales = float(
                    await conn.fetchval(
                        "SELECT COALESCE(SUM(price * stock_quantity), 0) FROM products"
                    ) or 0
                )
            except Exception:
                kpi_total_sales = 0
    except Exception:
        pass
    # Round down to nearest 10 for a cleaner dashboard look
    kpi_total_sales = int(kpi_total_sales // 10 * 10)
    kpi_total_products = total_products

    # --- Recent pipeline activity (real, from products table) ---
    recent_pipeline = [
        {
            "name": p["name"],
            "thumb": p.get("base_image") or "/static/img/placeholder-product.jpg",
            "status": p["pipeline_status"],
            "updated_at_human": p["updated_at_human"],
        }
        for p in products[:5]
    ]

    # --- Recent activity (unified feed) ---
    # Real: pipeline transitions + new products from products table.
    # Mock: sales + user signups + reviews (no orders/users/reviews table reads here).
    activity: List[Dict[str, str]] = []

    for p in products[:8]:
        if p["pipeline_status"] == "generated":
            activity.append(_activity_item(
                "pipeline",
                f"3D model generated for {p['name']}",
                f"GLB ready in pipeline",
                p["updated_at_human"],
            ))
        elif p["pipeline_status"] == "processing":
            activity.append(_activity_item(
                "pipeline",
                f"Generating 3D for {p['name']}",
                "Mesh conversion in progress",
                p["updated_at_human"],
            ))
        elif p["pipeline_status"] == "failed":
            activity.append(_activity_item(
                "pipeline",
                f"3D generation failed for {p['name']}",
                "Retry available",
                p["updated_at_human"],
            ))
        else:
            activity.append(_activity_item(
                "product",
                f"New product added — {p['name']}",
                f"${int(p['price'])} · queued for 3D",
                p["updated_at_human"],
            ))

    # Design-time mock activity so the feed feels alive even on empty stores.
    # These are clearly demo entries (TODO: replace when orders/users exist).
    activity.extend([
        _activity_item("sale",     "New order from Adaeze O.", "Trench · M · $480",     "12m ago"),
        _activity_item("user",     "New customer registered",  "Lagos, Nigeria",        "27m ago"),
        _activity_item("review",   "5★ review on Knit Sweater","\"Fits perfectly\"",    "1h ago"),
        _activity_item("sale",     "New order from Marcus T.", "Knit · L · $320",       "2h ago"),
        _activity_item("user",     "New customer registered",  "London, UK",            "3h ago"),
    ])
    # Sort by freshness (mock items first because they have lower time_ago values
    # like "12m ago" vs products' "Xd ago" / "Xh ago")
    activity = activity[:6]

    # --- Quick Stats (left as design placeholders until analytics are wired) ---
    quick_stats = {
        "conversion_rate": 3.2,
        "bounce_rate": 45,
        "page_views": "8.7k",
        "page_views_pct": 72,  # 8.7k / ~12k ceiling
    }

    # --- Top sellers (mock — no orders table; show generated + highest priced) ---
    generated_products = [p for p in products if p["pipeline_status"] == "generated"]
    top_sellers = [
        {
            "name": p["name"],
            "image": p.get("base_image") or "/static/img/placeholder-product.jpg",
            "units_sold": 0,
            "price": p["price"],
        }
        for p in (generated_products or products)[:4]
    ]

    # --- Recent orders (still kept in context for any future template use) ---
    recent_orders = [
        {"customer_name": "Adaeze O.", "customer_initials": "AO", "item_summary": "Trench · M", "amount": 480, "status_label": "Paid"},
        {"customer_name": "Marcus T.",  "customer_initials": "MT", "item_summary": "Knit · L",   "amount": 320, "status_label": "Fulfilled"},
        {"customer_name": "Yuki H.",    "customer_initials": "YH", "item_summary": "Scarf",      "amount": 180, "status_label": "Shipped"},
        {"customer_name": "Olu K.",     "customer_initials": "OK", "item_summary": "Suit · 40R", "amount": 1250, "status_label": "Paid"},
    ]

    context = {
        "request": request,
        # KPIs
        "kpi_total_sales": kpi_total_sales,
        "kpi_active_users": kpi_active_users,
        "kpi_orders": kpi_orders,
        "kpi_total_products": kpi_total_products,
        # Pipeline
        "products_with_3d": products_with_3d,
        "pipeline_health_pct": health_pct,
        "pipeline": pipeline,
        "recent_pipeline": recent_pipeline,
        # Activity feed
        "recent_activity": activity,
        # Quick stats
        "quick_stats": quick_stats,
        # Top sellers + legacy
        "top_sellers": top_sellers,
        "recent_orders": recent_orders,
    }
    return templates.TemplateResponse(request, "admin/sections/dashboard.html", context)


# ===========================================================================
# 2. PRODUCTS (cards w/ 3D status badge)
# ===========================================================================
async def section_products(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    products = await _safe_fetch_products(pool)
    return templates.TemplateResponse(
        request, "admin/sections/products.html",
        {"request": request, "products": products},
    )


# ===========================================================================
# 3. CATEGORIES
# ===========================================================================
async def section_categories(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    categories: List[Dict[str, Any]] = []
    uncategorized_count = 0
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.id, c.name, c.slug, c.color, c.is_active, c.display_order,
                       COUNT(p.id) AS product_count
                FROM categories c
                LEFT JOIN products p ON p.category_id = c.id
                GROUP BY c.id
                ORDER BY c.display_order ASC, c.name ASC
                """
            )
            for r in rows:
                d = dict(r)
                d["product_count"] = int(d.get("product_count") or 0)
                categories.append(d)
            try:
                uncategorized_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM products WHERE category_id IS NULL"
                )
            except Exception:
                uncategorized_count = 0
    except Exception as exc:
        logger.warning("[admin] categories fetch failed: %s", exc)

    return templates.TemplateResponse(
        request, "admin/sections/categories.html",
        {
            "request": request,
            "categories": categories,
            "uncategorized_count": uncategorized_count or 0,
        },
    )


# ===========================================================================
# 4. ALL PRODUCTS (table view)
# ===========================================================================
async def section_all_products(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    products = await _safe_fetch_products(pool)
    return templates.TemplateResponse(
        request, "admin/sections/all_products.html",
        {"request": request, "products": products},
    )


# ===========================================================================
# 5. REVIEWS
# ===========================================================================
async def section_reviews(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    reviews: List[Dict[str, Any]] = []
    rating_avg = 0
    five_star_count = 0
    needs_response = 0

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT r.id, r.rating, r.title, r.body, r.verified, r.replied,
                       r.created_at, r.customer_name, r.customer_email,
                       p.id AS product_id, p.name AS product_name, p.base_image AS product_image
                FROM product_reviews r
                JOIN products p ON p.id = r.product_id
                WHERE r.deleted_at IS NULL
                ORDER BY r.created_at DESC
                LIMIT 50
                """
            )
            for r in rows:
                d = dict(r)
                d["created_at_human"] = _humanize_dt(d.get("created_at"))
                reviews.append(d)
            try:
                rating_avg = await conn.fetchval(
                    "SELECT COALESCE(AVG(rating)::FLOAT, 0) FROM product_reviews WHERE deleted_at IS NULL"
                )
            except Exception:
                rating_avg = 0
            try:
                five_star_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM product_reviews WHERE deleted_at IS NULL AND rating = 5"
                )
            except Exception:
                five_star_count = 0
            try:
                needs_response = await conn.fetchval(
                    "SELECT COUNT(*) FROM product_reviews WHERE deleted_at IS NULL AND replied = false"
                )
            except Exception:
                needs_response = 0
    except Exception as exc:
        logger.warning("[admin] reviews fetch failed (table may not exist yet): %s", exc)

    five_star_pct = int((five_star_count / len(reviews)) * 100) if reviews else 0
    return templates.TemplateResponse(
        request, "admin/sections/reviews.html",
        {
            "request": request,
            "reviews": reviews,
            "rating_avg": round(rating_avg, 1) if rating_avg else None,
            "five_star_count": five_star_count or 0,
            "five_star_pct": five_star_pct,
            "needs_response": needs_response or 0,
        },
    )


# ===========================================================================
# 6. ADS
# ===========================================================================
async def section_ads(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    ads: List[Dict[str, Any]] = []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, placement, image, color_from, color_to, status,
                       starts_at, ends_at, impressions, clicks
                FROM ads
                ORDER BY starts_at DESC NULLS LAST, created_at DESC
                LIMIT 30
                """
            )
            for r in rows:
                d = dict(r)
                d["starts_at_human"] = _humanize_dt(d.get("starts_at"))
                d["ends_at_human"]   = _humanize_dt(d.get("ends_at"))
                impressions = int(d.get("impressions") or 0)
                clicks = int(d.get("clicks") or 0)
                d["ctr"] = f"{(clicks / impressions * 100):.1f}%" if impressions else "—"
                ads.append(d)
    except Exception as exc:
        logger.warning("[admin] ads fetch failed (table may not exist yet): %s", exc)

    return templates.TemplateResponse(
        request, "admin/sections/ads.html",
        {"request": request, "ads": ads},
    )


# ===========================================================================
# 7. SETTINGS
# ===========================================================================
async def section_settings_get(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    settings: Dict[str, Any] = {}
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM store_settings WHERE id = 1")
            if row:
                settings = dict(row)
    except Exception as exc:
        logger.warning("[admin] settings fetch failed (table may not exist yet): %s", exc)

    return templates.TemplateResponse(
        request, "admin/sections/settings.html",
        {"request": request, "settings": settings},
    )


async def section_settings_post(request: Request) -> HTMLResponse:
    """Save store_settings; re-render the section on success."""
    pool = request.app.state.db_pool
    form = await request.form()

    payload = {
        "currency":                (form.get("currency") or "USD").strip()[:8],
        "timezone":                (form.get("timezone") or "UTC").strip()[:64],
        "locale":                  (form.get("locale") or "en").strip()[:8],
        "shipping_domestic":       float(form.get("shipping_domestic") or 0),
        "shipping_international":  float(form.get("shipping_international") or 0),
        "free_shipping_threshold": float(form.get("free_shipping_threshold") or 0),
        "mesh_provider":           (form.get("mesh_provider") or "instantmesh").strip()[:40],
        "auto_mesh":               form.get("auto_mesh") in ("on", "true", "1"),
    }

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO store_settings (
                    id, currency, timezone, locale,
                    shipping_domestic, shipping_international, free_shipping_threshold,
                    mesh_provider, auto_mesh, updated_at
                ) VALUES (
                    1, $1, $2, $3, $4, $5, $6, $7, $8, now()
                )
                ON CONFLICT (id) DO UPDATE SET
                    currency = EXCLUDED.currency,
                    timezone = EXCLUDED.timezone,
                    locale = EXCLUDED.locale,
                    shipping_domestic = EXCLUDED.shipping_domestic,
                    shipping_international = EXCLUDED.shipping_international,
                    free_shipping_threshold = EXCLUDED.free_shipping_threshold,
                    mesh_provider = EXCLUDED.mesh_provider,
                    auto_mesh = EXCLUDED.auto_mesh,
                    updated_at = now()
                """,
                payload["currency"], payload["timezone"], payload["locale"],
                payload["shipping_domestic"], payload["shipping_international"],
                payload["free_shipping_threshold"], payload["mesh_provider"],
                payload["auto_mesh"],
            )
    except Exception as exc:
        logger.error("[admin] settings save failed: %s", exc)

    # Re-render the section
    return await section_settings_get(request)


# ===========================================================================
# 8. ABOUT ME
# ===========================================================================
async def section_about_get(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    about: Dict[str, Any] = {}
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM about_me WHERE id = 1")
            if row:
                about = dict(row)
    except Exception as exc:
        logger.warning("[admin] about_me fetch failed (table may not exist yet): %s", exc)

    return templates.TemplateResponse(
        request, "admin/sections/about.html",
        {"request": request, "about": about},
    )


async def section_about_post(request: Request) -> HTMLResponse:
    """Save about_me singleton; re-render the section on success."""
    pool = request.app.state.db_pool
    form = await request.form()

    def _opt(name: str, default: str = "") -> str:
        v = form.get(name)
        return (v.strip() if isinstance(v, str) else default)

    payload = {
        "name":         _opt("name"),
        "role":         _opt("role"),
        "email":        _opt("email"),
        "location":     _opt("location"),
        "instagram":    _opt("instagram"),
        "founded_year": form.get("founded_year") or None,
        "tagline":      _opt("tagline"),
        "story":        _opt("story"),
    }

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO about_me (
                    id, name, role, email, location, instagram, founded_year, tagline, story, updated_at
                ) VALUES (
                    1, $1, $2, $3, $4, $5, $6, $7, $8, now()
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    role = EXCLUDED.role,
                    email = EXCLUDED.email,
                    location = EXCLUDED.location,
                    instagram = EXCLUDED.instagram,
                    founded_year = EXCLUDED.founded_year,
                    tagline = EXCLUDED.tagline,
                    story = EXCLUDED.story,
                    updated_at = now()
                """,
                payload["name"], payload["role"], payload["email"],
                payload["location"], payload["instagram"], payload["founded_year"],
                payload["tagline"], payload["story"],
            )
    except Exception as exc:
        logger.error("[admin] about_me save failed: %s", exc)

    return await section_about_get(request)


# ===========================================================================
# 9. ADMIN INDEX (renders base.html shell)
# ===========================================================================
async def admin_index(request: Request) -> HTMLResponse:
    """GET /admin — Render the light-theme admin shell. The workspace child
    element loads the dashboard via HTMX on page load."""
    return templates.TemplateResponse(
        request, "admin/base.html",
        {"request": request},
    )


# ===========================================================================
# 10. OPERATIONS (production ledger + waitlist + reservation feeds)
# Migrated from app/routes/admin_dashboard.py admin_dashboard_home.
# The HTMX endpoints (/admin/dashboard/update-stock, /admin/dashboard/update-model-url,
# /admin/dashboard/notify-waitlist) are still served by the legacy module.
# ===========================================================================
async def section_operations(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool

    # KPI metrics (operational signals, distinct from the v2 dashboard's commercial KPIs)
    total_revenue = 0.0
    pending_orders_count = 0
    active_holds = 0
    waitlist_volume = 0
    inventory: List[Dict[str, Any]] = []
    active_reservations: List[Dict[str, Any]] = []
    pending_waitlists: List[Dict[str, Any]] = []

    try:
        async with pool.acquire() as conn:
            try:
                total_revenue = float(
                    await conn.fetchval(
                        "SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'paid'"
                    ) or 0
                )
            except Exception:
                total_revenue = 0.0
            try:
                pending_orders_count = int(
                    await conn.fetchval(
                        "SELECT COUNT(*) FROM orders WHERE status = 'pending'"
                    ) or 0
                )
            except Exception:
                pending_orders_count = 0
            try:
                active_holds = int(
                    await conn.fetchval(
                        "SELECT COUNT(*) FROM product_reservations WHERE status = 'staged'"
                    ) or 0
                )
            except Exception:
                active_holds = 0
            try:
                waitlist_volume = int(
                    await conn.fetchval(
                        "SELECT COUNT(*) FROM product_waitlists WHERE notified = false"
                    ) or 0
                )
            except Exception:
                waitlist_volume = 0

            try:
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
                inventory = [dict(r) for r in inventory_rows]
            except Exception as exc:
                logger.warning("[admin] inventory fetch failed: %s", exc)

            try:
                rows = await conn.fetch(
                    """
                    SELECT r.id, p.name, r.quantity, r.status, r.created_at
                    FROM product_reservations r
                    JOIN product_variants v ON r.variant_id = v.id
                    JOIN products p ON v.product_id = p.id
                    ORDER BY r.created_at DESC LIMIT 8
                    """
                )
                for r in rows:
                    d = dict(r)
                    d["created_at_human"] = _humanize_dt(d.get("created_at"))
                    active_reservations.append(d)
            except Exception as exc:
                logger.warning("[admin] reservations fetch failed: %s", exc)

            try:
                rows = await conn.fetch(
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
                pending_waitlists = [dict(r) for r in rows]
            except Exception as exc:
                logger.warning("[admin] waitlist fetch failed: %s", exc)

    except Exception as exc:
        logger.warning("[admin] operations fetch failed: %s", exc)

    context = {
        "request": request,
        "metrics": {
            "revenue": total_revenue,
            "pending_orders": pending_orders_count,
            "active_holds": active_holds,
            "waitlist_volume": waitlist_volume,
        },
        "inventory": inventory,
        "reservations": active_reservations,
        "waitlists": pending_waitlists,
    }
    return templates.TemplateResponse(request, "admin/sections/operations.html", context)


# ===========================================================================
# Route registration
# ===========================================================================
routes = [
    Route("/admin",                       endpoint=admin_index,           methods=["GET"]),
    Route("/admin/section/dashboard",     endpoint=section_dashboard,     methods=["GET"]),
    Route("/admin/section/products",      endpoint=section_products,      methods=["GET"]),
    Route("/admin/section/categories",    endpoint=section_categories,    methods=["GET"]),
    Route("/admin/section/all-products",  endpoint=section_all_products,  methods=["GET"]),
    Route("/admin/section/reviews",       endpoint=section_reviews,       methods=["GET"]),
    Route("/admin/section/ads",           endpoint=section_ads,           methods=["GET"]),
    Route("/admin/section/settings",      endpoint=section_settings_get,  methods=["GET"]),
    Route("/admin/section/settings",      endpoint=section_settings_post, methods=["POST"]),
    Route("/admin/section/about",         endpoint=section_about_get,     methods=["GET"]),
    Route("/admin/section/about",         endpoint=section_about_post,    methods=["POST"]),
    Route("/admin/section/operations",    endpoint=section_operations,    methods=["GET"]),
]
