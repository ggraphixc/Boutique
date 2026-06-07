# ASIKO Boutique - Admin Section Endpoints
# Light-theme admin redesign: 12 sections served as HTMX fragments to #workspace-content.
#
# Sections:
#   /admin/section/dashboard     -> dashboard.html  (KPI + 3D pipeline health + activity)
#   /admin/section/sales         -> sales.html      (orders list w/ status filter + revenue)
#   /admin/section/view-site     -> view_site.html  (storefront preview iframe)
#   /admin/section/products      -> products.html   (cards w/ 3D status badge)
#   /admin/section/categories    -> categories.html (CRUD list w/ colored tags)
#   /admin/section/analytics     -> analytics.html  (site metrics + traffic chart)
#   /admin/section/members       -> members.html    (unique customers w/ order history)
#   /admin/section/operations    -> operations.html (production-ledger + waitlist + reservations)
#   /admin/section/settings      -> settings.html   (store config)
#   /admin/section/about         -> about.html      (owner profile)
#
# Legacy sections retained for direct URL access (no longer in sidebar):
#   /admin/section/all-products  -> all_products.html (inventory table)
#   /admin/section/reviews       -> reviews.html
#   /admin/section/ads           -> ads.html
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
# Section response wrapper
# HTMX requests get the raw fragment; direct browser navigation gets the
# full admin shell wrapping the section.
# ---------------------------------------------------------------------------
def _section_response(request: Request, template: str, context: dict) -> HTMLResponse:
    """Return an HTMX fragment for HTMX requests, or the full admin shell
    wrapping the section for direct browser navigation."""
    ctx = {"request": request, **context}
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, template, ctx)
    # Direct navigation — render section inside the admin shell
    ctx["section_template"] = template
    return templates.TemplateResponse(request, "admin/base.html", ctx)


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
    return _section_response(request, "admin/sections/dashboard.html", context)


# ===========================================================================
# 2. PRODUCTS (cards w/ 3D status badge)
# ===========================================================================
async def section_products(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    products = await _safe_fetch_products(pool)
    return _section_response(
        request, "admin/sections/products.html",
        {"products": products},
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

    return _section_response(
        request, "admin/sections/categories.html",
        {
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
    return _section_response(
        request, "admin/sections/all_products.html",
        {"products": products},
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
    return _section_response(
        request, "admin/sections/reviews.html",
        {
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

    return _section_response(
        request, "admin/sections/ads.html",
        {"ads": ads},
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

    return _section_response(
        request, "admin/sections/settings.html",
        {"settings": settings},
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

    return _section_response(
        request, "admin/sections/about.html",
        {"about": about},
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
    return _section_response(request, "admin/sections/operations.html", context)


# ===========================================================================
# 8. SALES (orders list + revenue KPIs)
# ===========================================================================
async def section_sales(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool

    orders: List[Dict[str, Any]] = []
    metrics = {
        "gross_revenue": 0.0,
        "pending_revenue": 0.0,
        "paid_count": 0,
        "pending_count": 0,
        "cancelled_count": 0,
        "fulfilled_count": 0,
    }

    try:
        async with pool.acquire() as conn:
            try:
                rows = await conn.fetch(
                    """
                    SELECT o.id, o.customer_email, o.total_amount, o.shipping_state,
                           o.shipping_cost, o.status, o.payment_reference, o.created_at,
                           COUNT(oi.id) AS item_count
                    FROM orders o
                    LEFT JOIN order_items oi ON oi.order_id = o.id
                    GROUP BY o.id
                    ORDER BY o.created_at DESC
                    LIMIT 60
                    """
                )
            except Exception as exc:
                logger.warning("[admin] sales orders fetch failed: %s", exc)
                rows = []

            for r in rows:
                d = dict(r)
                d["id"] = str(d.get("id") or "")
                d["total_amount"] = float(d.get("total_amount") or 0)
                d["shipping_cost"] = float(d.get("shipping_cost") or 0)
                d["created_at_human"] = _humanize_dt(d.get("created_at"))
                d["status_key"] = (d.get("status") or "pending").lower()
                d["status_label"] = d["status_key"].title()
                d["customer_initials"] = _initials(d.get("customer_email", ""))
                orders.append(d)
                status = d["status_key"]
                if status == "paid":
                    metrics["paid_count"] += 1
                    metrics["gross_revenue"] += d["total_amount"]
                elif status == "cancelled":
                    metrics["cancelled_count"] += 1
                elif status in ("shipped", "delivered", "processing"):
                    metrics["fulfilled_count"] += 1
                    metrics["gross_revenue"] += d["total_amount"]
                else:
                    metrics["pending_count"] += 1
                    metrics["pending_revenue"] += d["total_amount"]
    except Exception as exc:
        logger.warning("[admin] sales fetch failed: %s", exc)

    # Status colour map
    status_styles = {
        "pending":    ("bg-amber-50",  "text-amber-700",  "ring-amber-200"),
        "paid":       ("bg-emerald-50","text-emerald-700","ring-emerald-200"),
        "processing": ("bg-blue-50",   "text-blue-700",   "ring-blue-200"),
        "shipped":    ("bg-blue-50",   "text-blue-700",   "ring-blue-200"),
        "delivered":  ("bg-emerald-50","text-emerald-700","ring-emerald-200"),
        "cancelled":  ("bg-rose-50",   "text-rose-700",   "ring-rose-200"),
    }

    return _section_response(
        request, "admin/sections/sales.html",
        {
            "orders": orders,
            "metrics": metrics,
            "status_styles": status_styles,
        },
    )


# ===========================================================================
# 9. ANALYTICS (site metrics + 7-day revenue chart)
# ===========================================================================
async def section_analytics(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool

    totals = {
        "sessions": 0,
        "page_views": 0,
        "conversion_rate": 0.0,
        "avg_session_sec": 0,
    }
    daily: List[Dict[str, Any]] = []
    top_pages: List[Dict[str, Any]] = []
    funnel: List[Dict[str, Any]] = []
    sources: List[Dict[str, Any]] = []

    try:
        async with pool.acquire() as conn:
            # Real KPI: paid order count and paid revenue for conversion
            try:
                paid_count = int(
                    await conn.fetchval(
                        "SELECT COUNT(*) FROM orders WHERE status IN ('paid','shipped','delivered')"
                    ) or 0
                )
            except Exception:
                paid_count = 0
            # Design-time stats (no analytics_events table yet)
            totals = {
                "sessions": 12480,
                "page_views": 38420,
                "conversion_rate": round((paid_count / max(12480, 1)) * 100, 2) if paid_count else 2.4,
                "avg_session_sec": 184,
            }

            # 7-day revenue series (real if orders exist, mock fallback)
            try:
                rows = await conn.fetch(
                    """
                    SELECT date_trunc('day', created_at) AS day,
                           COUNT(*) AS orders, COALESCE(SUM(total_amount), 0) AS revenue
                    FROM orders
                    WHERE created_at >= now() - interval '7 days'
                    GROUP BY day
                    ORDER BY day
                    """
                )
                if rows:
                    for r in rows:
                        daily.append({
                            "day":      r["day"].strftime("%a"),
                            "orders":   int(r["orders"]),
                            "revenue":  float(r["revenue"]),
                        })
            except Exception as exc:
                logger.warning("[admin] analytics daily fetch failed: %s", exc)

            if not daily:
                # Design-time mock: 7-day ramp with paid-order overlay
                base = max(paid_count, 1)
                daily = [
                    {"day": "Mon", "orders": 4,  "revenue": 12000 + base * 1800},
                    {"day": "Tue", "orders": 7,  "revenue": 24500 + base * 2200},
                    {"day": "Wed", "orders": 5,  "revenue": 15800 + base * 1900},
                    {"day": "Thu", "orders": 11, "revenue": 38200 + base * 2400},
                    {"day": "Fri", "orders": 9,  "revenue": 27400 + base * 2100},
                    {"day": "Sat", "orders": 14, "revenue": 46800 + base * 2700},
                    {"day": "Sun", "orders": 8,  "revenue": 22100 + base * 2000},
                ]
            max_rev = max((d["revenue"] for d in daily), default=1) or 1

            # Funnel: design-time but anchored to paid_count
            funnel = [
                {"label": "Visitors",  "count": 12480, "pct": 100},
                {"label": "Product views", "count": 5840, "pct": int(5840 / 12480 * 100)},
                {"label": "Add to cart",   "count": 1180, "pct": int(1180 / 12480 * 100)},
                {"label": "Checkout",      "count": max(paid_count * 3, 240), "pct": int(max(paid_count * 3, 240) / 12480 * 100)},
                {"label": "Purchased",     "count": max(paid_count, 12), "pct": int(max(paid_count, 12) / 12480 * 100)},
            ]

            # Top products by catalog value (proxy: price * stock)
            try:
                rows = await conn.fetch(
                    """
                    SELECT name, base_image, price, stock_quantity
                    FROM products
                    ORDER BY (price * stock_quantity) DESC
                    LIMIT 5
                    """
                )
                for r in rows:
                    top_pages.append({
                        "name": r["name"],
                        "image": r["base_image"] or "/static/img/placeholder-product.jpg",
                        "views": 0,
                        "value": float(r["price"] or 0) * int(r["stock_quantity"] or 0),
                    })
            except Exception as exc:
                logger.warning("[admin] analytics top-products fetch failed: %s", exc)

            # Traffic sources (mock — design-time)
            sources = [
                {"name": "Direct",        "share": 38, "color": "bg-blue-500"},
                {"name": "Instagram",     "share": 27, "color": "bg-purple-500"},
                {"name": "Google search", "share": 18, "color": "bg-emerald-500"},
                {"name": "Email",         "share": 11, "color": "bg-amber-500"},
                {"name": "Other",         "share":  6, "color": "bg-gray-400"},
            ]
    except Exception as exc:
        logger.warning("[admin] analytics fetch failed: %s", exc)

    return _section_response(
        request, "admin/sections/analytics.html",
        {
            "totals": totals,
            "daily": daily,
            "max_rev": max_rev,
            "funnel": funnel,
            "top_pages": top_pages,
            "sources": sources,
        },
    )


# ===========================================================================
# 10. MEMBERS (unique customers from orders)
# ===========================================================================
async def section_members(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool

    members: List[Dict[str, Any]] = []
    totals = {"total": 0, "with_orders": 0, "new_this_month": 0, "lifetime_revenue": 0.0}

    try:
        async with pool.acquire() as conn:
            try:
                rows = await conn.fetch(
                    """
                    SELECT customer_email,
                           COUNT(*)            AS order_count,
                           SUM(total_amount)   AS lifetime_value,
                           MAX(created_at)     AS last_order_at
                    FROM orders
                    GROUP BY customer_email
                    ORDER BY last_order_at DESC NULLS LAST
                    LIMIT 60
                    """
                )
            except Exception as exc:
                logger.warning("[admin] members fetch failed: %s", exc)
                rows = []

            for r in rows:
                email = r["customer_email"] or ""
                d = {
                    "email": email,
                    "initials": _initials(email),
                    "order_count": int(r["order_count"] or 0),
                    "lifetime_value": float(r["lifetime_value"] or 0),
                    "last_order_at_human": _humanize_dt(r["last_order_at"]),
                }
                # Status: Active = order in last 30d, Returning = older orders,
                # New = first order in last 7d
                d["status_key"] = "returning"
                if d["order_count"] == 1 and r["last_order_at"]:
                    from datetime import timedelta
                    if (datetime.now(timezone.utc) - r["last_order_at"]).days <= 7:
                        d["status_key"] = "new"
                if r["last_order_at"]:
                    from datetime import timedelta
                    if (datetime.now(timezone.utc) - r["last_order_at"]).days <= 30:
                        d["status_key"] = "active"
                d["status_label"] = {"active": "Active", "new": "New", "returning": "Returning"}[d["status_key"]]
                members.append(d)
                totals["total"] += 1
                totals["with_orders"] += 1
                totals["lifetime_revenue"] += d["lifetime_value"]
                if d["status_key"] == "new":
                    totals["new_this_month"] += 1
    except Exception as exc:
        logger.warning("[admin] members section fetch failed: %s", exc)

    status_styles = {
        "active":    ("bg-emerald-50", "text-emerald-700", "ring-emerald-200"),
        "new":       ("bg-blue-50",    "text-blue-700",    "ring-blue-200"),
        "returning": ("bg-gray-100",   "text-gray-600",    "ring-gray-200"),
    }

    return _section_response(
        request, "admin/sections/members.html",
        {
            "members": members,
            "totals": totals,
            "status_styles": status_styles,
        },
    )


# ===========================================================================
# 11. VIEW SITE (storefront preview iframe)
# ===========================================================================
async def section_view_site(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    counts = {"products": 0, "orders": 0, "stores": 0, "categories": 0}
    public_url = "/"

    try:
        async with pool.acquire() as conn:
            try:
                counts["products"] = int(await conn.fetchval("SELECT COUNT(*) FROM products") or 0)
            except Exception:
                pass
            try:
                counts["orders"] = int(await conn.fetchval("SELECT COUNT(*) FROM orders") or 0)
            except Exception:
                pass
            try:
                counts["stores"] = int(await conn.fetchval("SELECT COUNT(*) FROM stores") or 0)
            except Exception:
                pass
            try:
                counts["categories"] = int(await conn.fetchval("SELECT COUNT(*) FROM categories") or 0)
            except Exception:
                pass
    except Exception as exc:
        logger.warning("[admin] view-site counts fetch failed: %s", exc)

    # Surface the same env value the storefront uses (if any) so the link works
    # in both local + deployed environments.
    import os
    base = os.environ.get("PUBLIC_SITE_URL") or ""
    public_url = f"{base}/" if base else "/"

    return _section_response(
        request, "admin/sections/view_site.html",
        {"counts": counts, "public_url": public_url},
    )


# ===========================================================================
# Review NOTIFY helper — call this when a review is created/updated
# ===========================================================================

async def notify_new_review(db_pool, product_id: str, rating: float = 0, total_reviews: int = 0,
                            five_star_count: int = 0, needs_response: int = 0, rating_avg: float = 0) -> None:
    """
    Broadcast a new review event to WebSocket subscribers.
    Call this after inserting a review into product_reviews.
    """
    try:
        from app.realtime import notify, CH_NEW_REVIEW
        await notify(db_pool, CH_NEW_REVIEW, {
            "type": "new_review",
            "product_id": str(product_id),
            "rating": rating,
            "total_reviews": total_reviews,
            "five_star_count": five_star_count,
            "needs_response": needs_response,
            "rating_avg": round(rating_avg, 1) if rating_avg else 0,
        })
    except Exception:
        pass


# ===========================================================================
# Real-time fragment endpoints — called by HTMX when WS triggers fire
# ===========================================================================

async def rt_dashboard_pipeline(request: Request) -> HTMLResponse:
    """Return the pipeline health section as an HTMX fragment."""
    pool = request.app.state.db_pool
    products = await _safe_fetch_products(pool)
    pipeline = {"generated": 0, "processing": 0, "failed": 0, "not_started": 0}
    for p in products:
        pipeline[p["pipeline_status"]] = pipeline.get(p["pipeline_status"], 0)
    recent_pipeline = [
        {
            "name": p["name"],
            "thumb": p.get("base_image") or "/static/img/placeholder-product.jpg",
            "status": p["pipeline_status"],
            "updated_at_human": p["updated_at_human"],
        }
        for p in products[:5]
    ]
    return templates.TemplateResponse(
        request, "admin/sections/_rt_pipeline_health.html",
        {"request": request, "pipeline": pipeline, "recent_pipeline": recent_pipeline},
    )


async def rt_dashboard_activity(request: Request) -> HTMLResponse:
    """Return the recent activity feed as an HTMX fragment."""
    pool = request.app.state.db_pool
    products = await _safe_fetch_products(pool)
    activity: List[Dict[str, str]] = []
    for p in products[:8]:
        if p["pipeline_status"] == "generated":
            activity.append(_activity_item(
                "product", "bg-emerald-50 text-emerald-600",
                "M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4",
                f"3D mesh generated for {p['name']}", "Pipeline completed successfully",
            ))
        elif p["pipeline_status"] == "failed":
            activity.append(_activity_item(
                "pipeline", "bg-rose-50 text-rose-600",
                "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z",
                f"Pipeline failed for {p['name']}", "Requires attention",
            ))
    return templates.TemplateResponse(
        request, "admin/sections/_rt_activity_feed.html",
        {"request": request, "recent_activity": activity[:6]},
    )


async def rt_dashboard_kpi(request: Request) -> HTMLResponse:
    """Return the 4 KPI cards as an HTMX fragment."""
    pool = request.app.state.db_pool
    products = await _safe_fetch_products(pool)
    kpi_total_sales = 0
    kpi_total_products = len(products)
    try:
        async with pool.acquire() as conn:
            try:
                kpi_total_sales = float(
                    await conn.fetchval("SELECT COALESCE(SUM(price * stock_quantity), 0) FROM products") or 0
                )
            except Exception:
                kpi_total_sales = 0
    except Exception:
        pass
    kpi_total_sales = int(kpi_total_sales // 10 * 10)
    return templates.TemplateResponse(
        request, "admin/sections/_rt_kpi_cards.html",
        {"request": request, "kpi_total_sales": kpi_total_sales,
         "kpi_active_users": 0, "kpi_orders": 0, "kpi_total_products": kpi_total_products},
    )


async def rt_reviews_summary(request: Request) -> HTMLResponse:
    """Return the review stats summary as an HTMX fragment."""
    pool = request.app.state.db_pool
    reviews: List[Dict[str, Any]] = []
    rating_avg = 0
    five_star_count = 0
    needs_response = 0
    try:
        async with pool.acquire() as conn:
            try:
                rows = await conn.fetch(
                    "SELECT id, rating FROM product_reviews WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT 50"
                )
                reviews = [dict(r) for r in rows]
            except Exception:
                reviews = []
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
    except Exception:
        pass
    five_star_pct = int((five_star_count / len(reviews)) * 100) if reviews else 0
    return templates.TemplateResponse(
        request, "admin/sections/_rt_review_stats.html",
        {"request": request, "rating_avg": round(rating_avg, 1) if rating_avg else None,
         "five_star_count": five_star_count or 0, "five_star_pct": five_star_pct,
         "needs_response": needs_response or 0, "total_reviews": len(reviews)},
    )


# ===========================================================================
# Route registration
# ===========================================================================
routes = [
    Route("/admin",                       endpoint=admin_index,           methods=["GET"]),
    Route("/admin/section/dashboard",     endpoint=section_dashboard,     methods=["GET"]),
    Route("/admin/section/sales",         endpoint=section_sales,         methods=["GET"]),
    Route("/admin/section/view-site",     endpoint=section_view_site,     methods=["GET"]),
    Route("/admin/section/products",      endpoint=section_products,      methods=["GET"]),
    Route("/admin/section/categories",    endpoint=section_categories,    methods=["GET"]),
    Route("/admin/section/analytics",     endpoint=section_analytics,     methods=["GET"]),
    Route("/admin/section/members",       endpoint=section_members,       methods=["GET"]),
    Route("/admin/section/operations",    endpoint=section_operations,    methods=["GET"]),
    Route("/admin/section/settings",      endpoint=section_settings_get,  methods=["GET"]),
    Route("/admin/section/settings",      endpoint=section_settings_post, methods=["POST"]),
    Route("/admin/section/about",         endpoint=section_about_get,     methods=["GET"]),
    Route("/admin/section/about",         endpoint=section_about_post,    methods=["POST"]),
    # Legacy sections retained for direct URL access (sidebar no longer links to these)
    Route("/admin/section/all-products",  endpoint=section_all_products,  methods=["GET"]),
    Route("/admin/section/reviews",       endpoint=section_reviews,       methods=["GET"]),
    Route("/admin/section/ads",           endpoint=section_ads,           methods=["GET"]),
    # Real-time fragment endpoints (called by HTMX when WS triggers fire)
    Route("/admin/rt/pipeline",           endpoint=rt_dashboard_pipeline, methods=["GET"]),
    Route("/admin/rt/activity",           endpoint=rt_dashboard_activity, methods=["GET"]),
    Route("/admin/rt/kpi",                endpoint=rt_dashboard_kpi,      methods=["GET"]),
    Route("/admin/rt/reviews",            endpoint=rt_reviews_summary,    methods=["GET"]),
]
