# ASIKO Boutique - Admin Section Endpoints
# Light-theme admin redesign: 12 sections served as HTMX fragments to #workspace-content.
#
# Sections:
#   /admin/section/dashboard     -> dashboard.html  (KPI + activity)
#   /admin/section/sales         -> sales.html      (orders list w/ status filter + revenue)
#   /admin/section/view-site     -> view_site.html  (storefront preview iframe)
#   /admin/section/products      -> products.html   (cards)
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
    from app.settings_service import DEFAULTS
    if "settings" not in ctx:
        ctx["settings"] = dict(DEFAULTS)
    ctx["section_template"] = template
    return templates.TemplateResponse(request, "admin/base.html", ctx)


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
    """Fetch products + joined category, tolerant of NULLs."""
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT p.id, p.name, p.slug, p.price, p.stock_quantity,
                       p.base_image, p.asset_category, p.created_at,
                       c.id AS category_id, c.name AS category_name, c.color AS category_color
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.created_at DESC NULLS LAST
                LIMIT 60
                """
            )
    except Exception as exc:
        logger.warning("[admin] products fetch failed: %s", exc)
        return []

    products: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        d["updated_at_human"] = _humanize_dt(d.get("created_at"))
        d["price"] = float(d.get("price") or 0)
        products.append(d)
    return products


# ===========================================================================
# 1. DASHBOARD
# ===========================================================================
# Activity feed item kinds: 'sale', 'user', 'product', 'review'
_ACTIVITY_ICONS = {
    "sale":     {"icon_bg": "bg-emerald-50", "icon_color": "text-emerald-600"},
    "user":     {"icon_bg": "bg-blue-50",    "icon_color": "text-blue-600"},
    "customer": {"icon_bg": "bg-blue-50",    "icon_color": "text-blue-600"},
    "product":  {"icon_bg": "bg-amber-50",   "icon_color": "text-amber-600"},
    "review":   {"icon_bg": "bg-purple-50",  "icon_color": "text-purple-600"},
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

    total_products = len(products)

    # --- Real KPI cards + recent orders + reviews in ONE connection ---
    kpi_total_sales = 0
    kpi_active_users = 0
    kpi_orders = 0
    kpi_total_products = total_products
    recent_orders_raw = []
    recent_reviews = []
    try:
        async with pool.acquire() as conn:
            # KPI stats in single query
            try:
                stats = await conn.fetchrow("""
                    SELECT
                        (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status IN ('paid','shipped','delivered')) AS total_sales,
                        (SELECT COUNT(DISTINCT customer_email) FROM orders WHERE customer_email IS NOT NULL) AS active_users,
                        (SELECT COUNT(*) FROM orders) AS order_count
                """)
                kpi_total_sales = float(stats["total_sales"] or 0)
                kpi_active_users = int(stats["active_users"] or 0)
                kpi_orders = int(stats["order_count"] or 0)
            except Exception:
                pass

            try:
                recent_orders_raw = await conn.fetch(
                    """SELECT customer_email, total_amount, status, created_at
                       FROM orders ORDER BY created_at DESC LIMIT 5"""
                )
            except Exception:
                pass

            try:
                recent_reviews = await conn.fetch(
                    """SELECT r.rating, r.title, p.name, r.created_at
                       FROM product_reviews r JOIN products p ON r.product_id = p.id
                       WHERE r.deleted_at IS NULL ORDER BY r.created_at DESC LIMIT 3"""
                )
            except Exception:
                pass
    except Exception:
        pass

    kpi_total_sales = int(kpi_total_sales // 10 * 10)

    # --- Real activity feed from DB ---
    activity: List[Dict[str, str]] = []

    # Real recent orders
    for o in recent_orders_raw:
        email = o["customer_email"] or "Guest"
        name = email.split("@")[0].replace(".", " ").title()
        activity.append(_activity_item(
            "sale",
            f"New order from {name}",
            f"₦{o['total_amount']:,.0f} · {o['status']}",
            _humanize_dt(o["created_at"]),
        ))

    # Real recent reviews
    for rev in recent_reviews:
        activity.append(_activity_item(
            "review",
            f"{rev['rating']}★ review on {rev['name']}",
            f'"{rev["title"][:40]}"' if rev["title"] else "",
            _humanize_dt(rev["created_at"]),
        ))

    activity = activity[:8]

    # --- Page views, top sellers, recent orders (reuse same connection) ---
    page_views_count = 0
    top_sellers = []
    recent_orders = []
    try:
        async with pool.acquire() as conn:
            # Page views count
            try:
                page_views_count = int(
                    await conn.fetchval("SELECT COUNT(*) FROM page_views") or 0
                )
            except Exception:
                pass

            # Top sellers with real units sold
            try:
                top_sellers_raw = await conn.fetch(
                    """SELECT p.name, p.base_image, p.price,
                              COALESCE(SUM(oi.quantity), 0) as units_sold
                       FROM products p
                       LEFT JOIN order_items oi ON oi.product_id = p.id
                       LEFT JOIN orders o ON o.id = oi.order_id AND o.status IN ('paid','shipped','delivered')
                       GROUP BY p.id, p.name, p.base_image, p.price
                       ORDER BY units_sold DESC, p.price DESC
                       LIMIT 4"""
                )
                top_sellers = [
                    {
                        "name": s["name"],
                        "image": s.get("base_image") or "/static/img/placeholder-product.jpg",
                        "units_sold": int(s["units_sold"]),
                        "price": s["price"],
                    }
                    for s in top_sellers_raw
                ]
            except Exception:
                top_sellers = [
                    {
                        "name": p["name"],
                        "image": p.get("base_image") or "/static/img/placeholder-product.jpg",
                        "units_sold": 0,
                        "price": p["price"],
                    }
                    for p in products[:4]
                ]

            # Recent orders
            try:
                recent_orders_raw = await conn.fetch(
                    """SELECT o.id, o.customer_email, o.total_amount, o.status, o.created_at,
                              STRING_AGG(p.name, ' · ') as item_summary
                       FROM orders o
                       LEFT JOIN order_items oi ON o.id = oi.order_id
                       LEFT JOIN products p ON oi.product_id = p.id
                       GROUP BY o.id
                       ORDER BY o.created_at DESC LIMIT 4"""
                )
                recent_orders = [
                    {
                        "customer_name": (o["customer_email"] or "Guest").split("@")[0].replace(".", " ").title(),
                        "customer_initials": "".join(w[0] for w in (o["customer_email"] or "G").split("@")[0].split(".")[:2]).upper()[:2],
                        "item_summary": (o["item_summary"] or "Order")[:30],
                        "amount": float(o["total_amount"]),
                        "status_label": o["status"].title(),
                    }
                    for o in recent_orders_raw
                ]
            except Exception:
                recent_orders = []
    except Exception:
        pass

    quick_stats = {
        "conversion_rate": round((kpi_orders / max(page_views_count, 1)) * 100, 1) if page_views_count else 0,
        "bounce_rate": 0,
        "page_views": f"{page_views_count:,}",
        "page_views_pct": min(page_views_count // 100, 100) if page_views_count else 0,
        "sales_change_pct": 0,
        "users_change_pct": 0,
    }

    # Week-over-week comparison
    try:
        async with pool.acquire() as conn:
            try:
                week_cmp = await conn.fetchrow("""
                    SELECT
                        COALESCE(SUM(CASE WHEN created_at >= date_trunc('week', NOW()) THEN total_amount ELSE 0 END), 0) AS this_week,
                        COALESCE(SUM(CASE WHEN created_at >= date_trunc('week', NOW()) - interval '7 days'
                                           AND created_at <  date_trunc('week', NOW()) THEN total_amount ELSE 0 END), 0) AS last_week
                    FROM orders WHERE status IN ('paid','shipped','delivered')
                """)
                this_week = float(week_cmp["this_week"] or 0)
                last_week = float(week_cmp["last_week"] or 0)
                if last_week > 0:
                    quick_stats["sales_change_pct"] = round(((this_week - last_week) / last_week) * 100)
            except Exception:
                pass
            try:
                user_cmp = await conn.fetchrow("""
                    SELECT
                        COUNT(DISTINCT CASE WHEN created_at >= date_trunc('week', NOW()) THEN session_id END) AS this_week,
                        COUNT(DISTINCT CASE WHEN created_at >= date_trunc('week', NOW()) - interval '7 days'
                                            AND created_at <  date_trunc('week', NOW()) THEN session_id END) AS last_week
                    FROM page_views
                """)
                this_week_u = int(user_cmp["this_week"] or 0)
                last_week_u = int(user_cmp["last_week"] or 0)
                if last_week_u > 0:
                    quick_stats["users_change_pct"] = round(((this_week_u - last_week_u) / last_week_u) * 100)
            except Exception:
                pass
    except Exception:
        pass

    context = {
        "request": request,
        "kpi_total_sales": kpi_total_sales,
        "kpi_active_users": kpi_active_users,
        "kpi_orders": kpi_orders,
        "kpi_total_products": kpi_total_products,
        "recent_activity": activity,
        "quick_stats": quick_stats,
        "top_sellers": top_sellers,
        "recent_orders": recent_orders,
    }
    return _section_response(request, "admin/sections/dashboard.html", context)


# ===========================================================================
# 2. PRODUCTS
# ===========================================================================
async def section_products(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    products = await _safe_fetch_products(pool)
    return _section_response(
        request, "admin/sections/products.html",
        {"products": products},
    )


async def section_product_detail(request: Request) -> HTMLResponse:
    """Full detail view for a single product."""
    product_id = request.path_params.get("id")
    pool = request.app.state.db_pool

    async with pool.acquire() as conn:
        product = await conn.fetchrow(
            """
            SELECT p.*, c.name AS category_name, c.color AS category_color
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id = $1
            """,
            product_id,
        )
        if not product:
            return _section_response(
                request, "admin/sections/products.html",
                {"products": await _safe_fetch_products(pool)},
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

    product_dict = dict(product)
    product_dict["price"] = float(product_dict.get("price") or 0)
    product_dict["stock_quantity"] = int(product_dict.get("stock_quantity") or 0)

    variants_list = [dict(v) for v in variants]

    return _section_response(
        request, "admin/sections/product_detail.html",
        {"product": product_dict, "variants": variants_list},
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


async def _render_settings_section(request: Request) -> str:
    """Re-render the settings section HTML for HTMX response."""
    pool = request.app.state.db_pool
    try:
        from app.settings_service import get_settings
        settings = await get_settings(pool)
    except Exception:
        settings = {}

    # Use the app's Jinja2 environment directly for reliable rendering
    from jinja2 import Environment, FileSystemLoader
    _env = Environment(loader=FileSystemLoader("app/templates"), autoescape=True)
    tmpl = _env.get_template("admin/sections/settings.html")
    return tmpl.render(settings=settings, request=request)


async def section_settings_post(request: Request) -> HTMLResponse:
    """Save store_settings; supports per-section saves via 'section' field."""
    pool = request.app.state.db_pool
    form = await request.form()
    section = form.get("section", "")

    def _val(key, default="", max_len=None):
        v = (form.get(key) or default).strip()
        if max_len:
            v = v[:max_len]
        return v

    def _bool(key, default=False):
        return form.get(key) in ("on", "true", "1")

    def _float(key, default=0.0):
        try:
            return float(form.get(key) or default)
        except (ValueError, TypeError):
            return default

    def _int(key, default=0):
        try:
            return int(form.get(key) or default)
        except (ValueError, TypeError):
            return default

    # Per-section payload maps
    SECTION_PAYLOADS = {
        "store_profile": {
            "store_name": _val("store_name", "ASIKO Boutique", 100),
            "contact_email": _val("contact_email", "", 200),
            "store_description": _val("store_description", "", 2000),
            "phone": _val("phone", "", 50),
            "store_address": _val("store_address", "", 300),
        },
        "ai_provider": {
            "ai_provider": _val("ai_provider", "openrouter", 20),
            "ai_api_key": _val("ai_api_key", "", 500),
            "ai_model": _val("ai_model", "google/gemini-2.0-flash-001", 120),
            "ai_system_prompt": form.get("ai_system_prompt") or "",
            "ai_max_tokens": _int("ai_max_tokens", 1024),
            "ai_temperature": _float("ai_temperature"),
        },
        "ai_stylist_page": {
            "ai_stylist_enabled": _bool("ai_stylist_enabled"),
            "ai_stylist_welcome": form.get("ai_stylist_welcome") or "",
            "ai_stylist_suggestions": form.get("ai_stylist_suggestions") or "",
        },
        "hero": {
            "hero_title": form.get("hero_title") or "Authentic",
            "hero_title_accent": form.get("hero_title_accent") or "Nigerian Fashion",
            "hero_subtitle": form.get("hero_subtitle") or "",
            "hero_badge_text": form.get("hero_badge_text") or "",
            "hero_cta_text": form.get("hero_cta_text") or "Shop Collection",
            "hero_cta_link": form.get("hero_cta_link") or "#storefront",
        },
        "shop": {
            "shop_products_per_page": _int("shop_products_per_page", 12),
            "shop_default_sort": _val("shop_default_sort", "newest", 30),
        },
        "lookbook": {
            "lookbook_title": form.get("lookbook_title") or "The Lookbook",
            "lookbook_subtitle": form.get("lookbook_subtitle") or "",
        },
        "about": {
            "about_title": form.get("about_title") or "ASIKO Boutique",
            "about_tagline": form.get("about_tagline") or "",
            "about_story": form.get("about_story") or "",
            "about_location": form.get("about_location") or "",
            "about_email": form.get("about_email") or "",
            "about_founded_year": _int("about_founded_year", 2024),
        },
        "customer_dashboard": {
            "customer_welcome_title": form.get("customer_welcome_title") or "Welcome back",
            "customer_welcome_subtitle": form.get("customer_welcome_subtitle") or "",
        },
        "currency_locale": {
            "currency": _val("currency", "NGN", 8),
            "timezone": _val("timezone", "Africa/Lagos", 64),
            "locale": _val("locale", "en", 8),
        },
        "shipping": {
            "shipping_domestic": _float("shipping_domestic"),
            "shipping_international": _float("shipping_international"),
            "free_shipping_threshold": _float("free_shipping_threshold"),
        },
        "security": {
            "admin_auth": _bool("admin_auth"),
            "session_timeout": _int("session_timeout", 60),
        },
        "notifications": {
            "notif_new_order": _bool("notif_new_order", True),
            "notif_review": _bool("notif_review", True),
            "notif_low_stock": _bool("notif_low_stock", True),
        },
        "email_config": {
            "brevo_api_key": _val("brevo_api_key", "", 500),
            "sender_email": _val("sender_email", "orders@asikoboutique.com", 200),
            "sender_name": _val("sender_name", "ASIKO Boutique", 100),
            "admin_email": _val("admin_email", "hello@asikoboutique.com", 200),
        },
        "email_notifications": {
            "email_welcome_enabled": _bool("email_welcome_enabled", True),
            "email_order_enabled": _bool("email_order_enabled", True),
            "email_shipping_enabled": _bool("email_shipping_enabled", True),
            "email_newsletter_enabled": _bool("email_newsletter_enabled", True),
            "email_password_reset_enabled": _bool("email_password_reset_enabled", True),
        },
        "brand": {
            "brand_name": _val("brand_name", "ASIKO Boutique", 100),
            "brand_tagline": _val("brand_tagline", "Authentic Nigerian Fashion", 200),
            "brand_footer_text": _val("brand_footer_text", "© 2026 ASIKO Boutique. All rights reserved.", 300),
            "brand_currency_symbol": _val("brand_currency_symbol", "&#8358;", 10),
            "brand_currency_code": _val("brand_currency_code", "NGN", 10),
        },
        "seo": {
            "seo_title": _val("seo_title", "", 200),
            "seo_description": form.get("seo_description") or "",
            "seo_keywords": form.get("seo_keywords") or "",
            "seo_og_image": _val("seo_og_image", "", 500),
            "seo_twitter_handle": _val("seo_twitter_handle", "", 100),
            "seo_google_analytics": _val("seo_google_analytics", "", 100),
            "seo_google_tag_manager": _val("seo_google_tag_manager", "", 100),
            "seo_structured_data": _bool("seo_structured_data", True),
            "seo_sitemap_enabled": _bool("seo_sitemap_enabled", True),
            "seo_robots_enabled": _bool("seo_robots_enabled", True),
            "geo_enabled": _bool("geo_enabled", True),
            "aeo_faq_schema": _bool("aeo_faq_schema", True),
            "aeo_product_schema": _bool("aeo_product_schema", True),
            "smo_twitter_card": _val("smo_twitter_card", "summary_large_image", 50),
            "smo_facebook_app_id": _val("smo_facebook_app_id", "", 50),
            "sem_conversion_id": _val("sem_conversion_id", "", 100),
            "sem_conversion_label": _val("sem_conversion_label", "", 100),
            "sem_remarketing_tag": form.get("sem_remarketing_tag") or "",
            "geo_local_business": {
                "name": form.get("geo_business_name") or "",
                "street": form.get("geo_street") or "",
                "city": form.get("geo_city") or "Lagos",
                "region": form.get("geo_region") or "Lagos",
                "country": form.get("geo_country") or "NG",
                "postal": form.get("geo_postal") or "",
                "phone": form.get("geo_phone") or "",
                "lat": form.get("geo_lat") or "6.5244",
                "lng": form.get("geo_lng") or "3.3792",
            },
        },
    }

    # Chatbot widget settings
    SECTION_PAYLOADS["chatbot"] = {
        "chatbot_enabled": _bool("chatbot_enabled", True),
        "chatbot_welcome": form.get("chatbot_welcome") or "Hello! I'm ASIKO's fashion assistant. How can I help you find the perfect outfit?",
        "chatbot_color_primary": _val("chatbot_color_primary", "#0D2A22", 20),
        "chatbot_color_accent": _val("chatbot_color_accent", "#D4AF37", 20),
    }

    # Pages & blog settings
    SECTION_PAYLOADS["pages_blog"] = {
        "blog_enabled": _bool("blog_enabled", True),
        "blog_posts_per_page": _int("blog_posts_per_page", 9),
    }

    try:
        from app.settings_service import (
            save_store_profile, save_brand_settings, save_ai_settings,
            save_chatbot_settings, save_page_settings, save_shop_settings,
            save_notification_settings, save_seo_settings,
        )

        # Handle brand_logo file upload (multipart/form-data)
        if section == "brand":
            logo_file = form.get("brand_logo")
            if logo_file and hasattr(logo_file, "filename") and logo_file.filename:
                import base64
                contents = await logo_file.read()
                if len(contents) > 2 * 1024 * 1024:
                    raise ValueError("Logo file too large (max 2MB)")
                ext = logo_file.filename.rsplit(".", 1)[-1].lower() if "." in logo_file.filename else "png"
                mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "svg": "image/svg+xml", "webp": "image/webp"}
                mime = mime_map.get(ext, "image/png")
                b64 = base64.b64encode(contents).decode("ascii")
                SECTION_PAYLOADS["brand"]["brand_logo"] = f"data:{mime};base64,{b64}"

        # Section → save function routing
        _SAVE路由 = {
            "store_profile": save_store_profile,
            "brand": save_brand_settings,
            "ai_provider": save_ai_settings,
            "ai_stylist_page": save_ai_settings,
            "chatbot": save_chatbot_settings,
            "hero": save_page_settings,
            "shop": save_shop_settings,
            "lookbook": save_page_settings,
            "about": save_page_settings,
            "customer_dashboard": save_page_settings,
            "currency_locale": save_page_settings,
            "shipping": save_shop_settings,
            "pages_blog": save_page_settings,
            "security": save_page_settings,
            "notifications": save_notification_settings,
            "email_config": save_notification_settings,
            "email_notifications": save_notification_settings,
            "seo": save_seo_settings,
        }

        if section and section in SECTION_PAYLOADS:
            save_fn = _SAVE路由.get(section)
            if save_fn:
                await save_fn(pool, SECTION_PAYLOADS[section])
        else:
            # Save all sections to their respective tables
            saved_tables = set()
            for sec_key, sec_payload in SECTION_PAYLOADS.items():
                save_fn = _SAVE路由.get(sec_key)
                if save_fn and save_fn not in saved_tables:
                    await save_fn(pool, sec_payload)
                    saved_tables.add(save_fn)

        # Success — return with HX-Trigger toast
        from starlette.responses import HTMLResponse
        body = await _render_settings_section(request)
        resp = HTMLResponse(body, headers={
            "HX-Trigger": "settingsToast",
        })
        return resp
    except Exception as exc:
        logger.error("[admin] settings save failed: %s", exc)
        from starlette.responses import HTMLResponse
        body = await _render_settings_section(request)
        resp = HTMLResponse(body, headers={
            "HX-Trigger": "settingsError",
        })
        return resp


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
    pool = request.app.state.db_pool
    from app.settings_service import get_settings
    settings = await get_settings(pool)
    return templates.TemplateResponse(
        request, "admin/base.html",
        {"request": request, "settings": settings},
    )


# ===========================================================================
# 10. OPERATIONS (production ledger + waitlist + reservation feeds)
# Migrated from app/routes/admin_dashboard.py admin_dashboard_home.
# The HTMX endpoints (/admin/dashboard/update-stock, /admin/dashboard/notify-waitlist)
# are still served by the legacy module.
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
    recent_orders: List[Dict[str, Any]] = []
    low_stock_items: List[Dict[str, Any]] = []

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
                    SELECT p.id AS product_id, p.name,
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

            try:
                rows = await conn.fetch(
                    """
                    SELECT o.id, o.customer_email, o.total_amount, o.status, o.created_at,
                           STRING_AGG(p.name, ', ') AS item_names
                    FROM orders o
                    LEFT JOIN order_items oi ON o.id = oi.order_id
                    LEFT JOIN products p ON oi.product_id = p.id
                    GROUP BY o.id
                    ORDER BY o.created_at DESC
                    LIMIT 10
                    """
                )
                for r in rows:
                    d = dict(r)
                    d["id"] = str(d.get("id") or "")
                    d["total_amount"] = float(d.get("total_amount") or 0)
                    d["created_at_human"] = _humanize_dt(d.get("created_at"))
                    d["status_key"] = (d.get("status") or "pending").lower()
                    d["status_label"] = d["status_key"].title()
                    email = d.get("customer_email") or ""
                    name_part = email.split("@")[0] if "@" in email else email
                    d["customer_name"] = name_part.replace(".", " ").replace("_", " ").replace("-", " ").title()
                    d["customer_initials"] = _initials(email)
                    recent_orders.append(d)
            except Exception as exc:
                logger.warning("[admin] recent orders fetch failed: %s", exc)

            try:
                rows = await conn.fetch(
                    """
                    SELECT p.id AS product_id, p.name, p.base_image,
                           v.id AS variant_id, v.size, v.color, v.stock_qty
                    FROM product_variants v
                    JOIN products p ON v.product_id = p.id
                    WHERE v.stock_qty <= 3
                    ORDER BY v.stock_qty ASC
                    LIMIT 10
                    """
                )
                low_stock_items = [dict(r) for r in rows]
            except Exception as exc:
                logger.warning("[admin] low stock fetch failed: %s", exc)

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
        "recent_orders": recent_orders,
        "low_stock": low_stock_items,
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
        "this_month_revenue": 0.0,
        "last_month_revenue": 0.0,
        "revenue_change_pct": 0,
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

            # This month vs last month revenue
            try:
                month_stats = await conn.fetchrow("""
                    SELECT
                        COALESCE(SUM(CASE WHEN created_at >= date_trunc('month', NOW()) THEN total_amount ELSE 0 END), 0) AS this_month,
                        COALESCE(SUM(CASE WHEN created_at >= date_trunc('month', NOW()) - interval '1 month'
                                           AND created_at <  date_trunc('month', NOW()) THEN total_amount ELSE 0 END), 0) AS last_month
                    FROM orders WHERE status IN ('paid','shipped','delivered')
                """)
                metrics["this_month_revenue"] = float(month_stats["this_month"] or 0)
                metrics["last_month_revenue"] = float(month_stats["last_month"] or 0)
                if metrics["last_month_revenue"] > 0:
                    metrics["revenue_change_pct"] = round(
                        ((metrics["this_month_revenue"] - metrics["last_month_revenue"]) / metrics["last_month_revenue"]) * 100
                    )
            except Exception:
                pass
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
        "pages_per_session": 0.0,
        "this_week_orders": 0,
        "this_week_revenue": 0.0,
        "last_week_orders": 0,
        "last_week_revenue": 0.0,
        "revenue_change_pct": 0,
        "orders_change_pct": 0,
    }
    daily: List[Dict[str, Any]] = []
    top_pages: List[Dict[str, Any]] = []
    funnel: List[Dict[str, Any]] = []
    sources: List[Dict[str, Any]] = []

    try:
        async with pool.acquire() as conn:
            # Single query for all KPI stats
            try:
                stats = await conn.fetchrow("""
                    SELECT
                        (SELECT COUNT(*) FROM page_views) AS page_views,
                        (SELECT COUNT(DISTINCT session_id) FROM page_views) AS sessions,
                        (SELECT COUNT(*) FROM orders WHERE status IN ('paid','shipped','delivered')) AS paid_count
                """)
                page_views_count = int(stats["page_views"] or 0)
                sessions_count = int(stats["sessions"] or 0)
                paid_count = int(stats["paid_count"] or 0)
            except Exception:
                page_views_count = sessions_count = paid_count = 0

            # Pages per session
            pages_per_session = round(page_views_count / max(sessions_count, 1), 2) if sessions_count else 0

            totals = {
                "sessions": sessions_count,
                "page_views": page_views_count,
                "conversion_rate": round((paid_count / max(sessions_count, 1)) * 100, 2) if sessions_count else 0,
                "avg_session_sec": 0,
                "pages_per_session": pages_per_session,
                "this_week_orders": 0,
                "this_week_revenue": 0.0,
                "last_week_orders": 0,
                "last_week_revenue": 0.0,
                "revenue_change_pct": 0,
                "orders_change_pct": 0,
            }

            # This week vs last week revenue/orders
            try:
                week_stats = await conn.fetchrow("""
                    SELECT
                        COALESCE(SUM(CASE WHEN created_at >= date_trunc('week', NOW()) THEN total_amount ELSE 0 END), 0) AS this_week_rev,
                        COALESCE(SUM(CASE WHEN created_at >= date_trunc('week', NOW()) - interval '7 days'
                                           AND created_at <  date_trunc('week', NOW()) THEN total_amount ELSE 0 END), 0) AS last_week_rev,
                        COUNT(CASE WHEN created_at >= date_trunc('week', NOW()) THEN 1 END) AS this_week_cnt,
                        COUNT(CASE WHEN created_at >= date_trunc('week', NOW()) - interval '7 days'
                                    AND created_at <  date_trunc('week', NOW()) THEN 1 END) AS last_week_cnt
                    FROM orders WHERE status IN ('paid','shipped','delivered')
                """)
                totals["this_week_revenue"] = float(week_stats["this_week_rev"] or 0)
                totals["last_week_revenue"] = float(week_stats["last_week_rev"] or 0)
                totals["this_week_orders"] = int(week_stats["this_week_cnt"] or 0)
                totals["last_week_orders"] = int(week_stats["last_week_cnt"] or 0)
                if totals["last_week_revenue"] > 0:
                    totals["revenue_change_pct"] = round(
                        ((totals["this_week_revenue"] - totals["last_week_revenue"]) / totals["last_week_revenue"]) * 100
                    )
                if totals["last_week_orders"] > 0:
                    totals["orders_change_pct"] = round(
                        ((totals["this_week_orders"] - totals["last_week_orders"]) / totals["last_week_orders"]) * 100
                    )
            except Exception:
                pass

            # 7-day revenue series
            try:
                rows = await conn.fetch(
                    """SELECT date_trunc('day', created_at) AS day,
                              COUNT(*) AS orders, COALESCE(SUM(total_amount), 0) AS revenue
                       FROM orders WHERE created_at >= now() - interval '7 days'
                       GROUP BY day ORDER BY day"""
                )
                for r in rows:
                    daily.append({
                        "day": r["day"].strftime("%a"),
                        "orders": int(r["orders"]),
                        "revenue": float(r["revenue"]),
                    })
            except Exception:
                pass

            max_rev = max((d["revenue"] for d in daily), default=1) or 1

            # Funnel — real data from funnel_events table
            try:
                funnel_rows = await conn.fetch(
                    """SELECT event_step, COUNT(DISTINCT session_id) AS cnt
                       FROM funnel_events
                       WHERE event_step IN ('landing','product_view','add_to_cart','checkout_start','payment_success')
                       GROUP BY event_step"""
                )
                funnel_map = {r["event_step"]: int(r["cnt"]) for r in funnel_rows}
                funnel = [
                    {"label": "Visitors",      "count": funnel_map.get("landing", 0), "pct": 0},
                    {"label": "Product views", "count": funnel_map.get("product_view", 0), "pct": 0},
                    {"label": "Add to cart",   "count": funnel_map.get("add_to_cart", 0), "pct": 0},
                    {"label": "Checkout",      "count": funnel_map.get("checkout_start", 0), "pct": 0},
                    {"label": "Purchased",     "count": funnel_map.get("payment_success", paid_count), "pct": 0},
                ]
                visitors = funnel[0]["count"] or 1
                for f in funnel:
                    f["pct"] = int((f["count"] / visitors) * 100)
            except Exception:
                funnel = [{"label": l, "count": 0, "pct": 0} for l in ("Visitors","Product views","Add to cart","Checkout","Purchased")]

            # Top products + traffic sources
            try:
                top_rows = await conn.fetch(
                    """SELECT p.name, p.base_image, p.price,
                              COALESCE(pv.view_count, 0) as views,
                              COALESCE(oi.units_sold, 0) as units_sold
                       FROM products p
                       LEFT JOIN (SELECT product_id, COUNT(*) as view_count FROM page_views GROUP BY product_id) pv ON pv.product_id = p.id
                       LEFT JOIN (SELECT product_id, SUM(quantity) as units_sold FROM order_items oi JOIN orders o ON o.id = oi.order_id WHERE o.status IN ('paid','shipped','delivered') GROUP BY product_id) oi ON oi.product_id = p.id
                       ORDER BY views DESC, units_sold DESC LIMIT 5"""
                )
                for r in top_rows:
                    top_pages.append({
                        "name": r["name"],
                        "image": r["base_image"] or "/static/img/placeholder-product.jpg",
                        "views": int(r["views"]),
                        "value": float(r["price"] or 0) * int(r["units_sold"] or 0),
                    })
            except Exception:
                pass

            try:
                source_rows = await conn.fetch(
                    """SELECT COALESCE(source, 'Direct') as source, COUNT(*) as count
                       FROM traffic_sources GROUP BY source ORDER BY count DESC LIMIT 5"""
                )
                total_src = sum(int(r["count"]) for r in source_rows) or 1
                src_colors = ["bg-blue-500", "bg-purple-500", "bg-emerald-500", "bg-amber-500", "bg-gray-400"]
                for i, r in enumerate(source_rows):
                    sources.append({
                        "name": r["source"],
                        "share": int(int(r["count"]) / total_src * 100),
                        "color": src_colors[i % len(src_colors)],
                    })
            except Exception:
                pass

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
                    SELECT c.id,
                           c.email,
                           COALESCE(c.full_name, '')        AS full_name,
                           c.created_at                     AS registered_at,
                           COUNT(o.id)                      AS order_count,
                           COALESCE(SUM(o.total_amount), 0) AS lifetime_value,
                           MAX(o.created_at)                AS last_order_at
                    FROM customers c
                    LEFT JOIN orders o
                        ON o.customer_email = c.email
                    GROUP BY c.id, c.email, c.full_name, c.created_at
                    ORDER BY last_order_at DESC NULLS LAST, c.created_at DESC
                    LIMIT 80
                    """
                )
            except Exception as exc:
                logger.warning("[admin] members fetch failed: %s", exc)
                rows = []

            for r in rows:
                email = r["email"] or ""
                name = r["full_name"] or ""
                display = name if name else email.split("@")[0].replace(".", " ").title()
                order_count = int(r["order_count"] or 0)
                lifetime_value = float(r["lifetime_value"] or 0)
                last_order_at = r["last_order_at"]

                # Status logic
                status_key = "no_orders"
                if order_count > 0:
                    status_key = "returning"
                    if order_count == 1 and last_order_at:
                        from datetime import timedelta
                        if (datetime.now(timezone.utc) - last_order_at).days <= 7:
                            status_key = "new"
                    if last_order_at:
                        from datetime import timedelta
                        if (datetime.now(timezone.utc) - last_order_at).days <= 30:
                            status_key = "active"

                status_label = {
                    "active": "Active",
                    "new": "New",
                    "returning": "Returning",
                    "no_orders": "No orders",
                }[status_key]

                d = {
                    "email": email,
                    "name": display,
                    "initials": _initials(email),
                    "order_count": order_count,
                    "lifetime_value": lifetime_value,
                    "last_order_at_human": _humanize_dt(last_order_at) if last_order_at else "—",
                    "status_key": status_key,
                    "status_label": status_label,
                }
                members.append(d)
                totals["total"] += 1
                if order_count > 0:
                    totals["with_orders"] += 1
                    totals["lifetime_revenue"] += lifetime_value
                if status_key == "new":
                    totals["new_this_month"] += 1
    except Exception as exc:
        logger.warning("[admin] members section fetch failed: %s", exc)

    status_styles = {
        "active":    ("bg-emerald-50", "text-emerald-700", "ring-emerald-200"),
        "new":       ("bg-blue-50",    "text-blue-700",    "ring-blue-200"),
        "returning": ("bg-gray-100",   "text-gray-600",    "ring-gray-200"),
        "no_orders": ("bg-gray-50",    "text-gray-400",    "ring-gray-200"),
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

async def rt_dashboard_activity(request: Request) -> HTMLResponse:
    """Return the recent activity feed as an HTMX fragment."""
    pool = request.app.state.db_pool
    activity: List[Dict[str, str]] = []

    try:
        async with pool.acquire() as conn:
            # Recent orders
            try:
                order_rows = await conn.fetch(
                    """SELECT customer_email, total_amount, status, created_at
                       FROM orders ORDER BY created_at DESC LIMIT 5"""
                )
                for o in order_rows:
                    email = o["customer_email"] or "Guest"
                    name = email.split("@")[0].replace(".", " ").title()
                    activity.append(_activity_item(
                        "sale",
                        f"New order from {name}",
                        f"₦{o['total_amount']:,.0f} · {o['status']}",
                        _humanize_dt(o["created_at"]),
                    ))
            except Exception:
                pass

            # Recent reviews
            try:
                review_rows = await conn.fetch(
                    """SELECT r.rating, r.title, p.name, r.created_at
                       FROM product_reviews r JOIN products p ON r.product_id = p.id
                       WHERE r.deleted_at IS NULL ORDER BY r.created_at DESC LIMIT 3"""
                )
                for rev in review_rows:
                    activity.append(_activity_item(
                        "review",
                        f"{rev['rating']}★ review on {rev['name']}",
                        f'"{rev["title"][:40]}"' if rev["title"] else "",
                        _humanize_dt(rev["created_at"]),
                    ))
            except Exception:
                pass

            # Recent new customers
            try:
                customer_rows = await conn.fetch(
                    """SELECT email, full_name, created_at
                       FROM customers ORDER BY created_at DESC LIMIT 3"""
                )
                for c in customer_rows:
                    name = c["full_name"] or c["email"].split("@")[0].replace(".", " ").title()
                    activity.append(_activity_item(
                        "customer",
                        f"New customer: {name}",
                        c["email"],
                        _humanize_dt(c["created_at"]),
                    ))
            except Exception:
                pass

    except Exception:
        pass

    # Sort by recency (approximate via order) and limit
    activity = activity[:8]

    return templates.TemplateResponse(
        request, "admin/sections/_rt_activity_feed.html",
        {"request": request, "recent_activity": activity},
    )


async def rt_dashboard_kpi(request: Request) -> HTMLResponse:
    """Return the 4 KPI cards as an HTMX fragment."""
    pool = request.app.state.db_pool
    products = await _safe_fetch_products(pool)
    kpi_total_sales = 0
    kpi_active_users = 0
    kpi_orders = 0
    kpi_total_products = len(products)
    try:
        async with pool.acquire() as conn:
            try:
                kpi_total_sales = float(
                    await conn.fetchval(
                        "SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status IN ('paid','shipped','delivered')"
                    ) or 0
                )
            except Exception:
                kpi_total_sales = 0
            try:
                kpi_orders = int(await conn.fetchval("SELECT COUNT(*) FROM orders") or 0)
            except Exception:
                kpi_orders = 0
            try:
                kpi_active_users = int(await conn.fetchval("SELECT COUNT(DISTINCT session_id) FROM page_views") or 0)
            except Exception:
                kpi_active_users = 0
    except Exception:
        pass
    kpi_total_sales = int(kpi_total_sales // 10 * 10)
    return templates.TemplateResponse(
        request, "admin/sections/_rt_kpi_cards.html",
        {"request": request, "kpi_total_sales": kpi_total_sales,
         "kpi_active_users": kpi_active_users, "kpi_orders": kpi_orders, "kpi_total_products": kpi_total_products},
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
# Notifications (bell icon dropdown)
# ===========================================================================

async def rt_notifications(request: Request) -> HTMLResponse:
    """Return recent notifications as an HTMX fragment for the bell dropdown."""
    pool = request.app.state.db_pool
    notifications: List[Dict[str, str]] = []
    unread_count = 0
    try:
        async with pool.acquire() as conn:
            # Recent orders
            try:
                rows = await conn.fetch(
                    """SELECT customer_email, total_amount, status, created_at
                       FROM orders ORDER BY created_at DESC LIMIT 5"""
                )
                for o in rows:
                    name = (o["customer_email"] or "Guest").split("@")[0].replace(".", " ").title()
                    notifications.append({
                        "icon": "sale",
                        "color": "bg-emerald-50 text-emerald-600",
                        "title": f"New order from {name}",
                        "subtitle": f"₦{o['total_amount']:,.0f} · {o['status'].title()}",
                        "time": _humanize_dt(o["created_at"]),
                    })
            except Exception:
                pass

            # Recent reviews
            try:
                reviews = await conn.fetch(
                    """SELECT r.rating, r.title, p.name, r.created_at
                       FROM product_reviews r JOIN products p ON r.product_id = p.id
                       WHERE r.deleted_at IS NULL ORDER BY r.created_at DESC LIMIT 3"""
                )
                for rev in reviews:
                    notifications.append({
                        "icon": "review",
                        "color": "bg-amber-50 text-amber-600",
                        "title": f"{rev['rating']}★ review on {rev['name']}",
                        "subtitle": (rev["title"] or "")[:40],
                        "time": _humanize_dt(rev["created_at"]),
                    })
            except Exception:
                pass

    except Exception:
        pass

    # Sort by time (newest first) and count unread
    notifications = notifications[:10]
    unread_count = len([n for n in notifications if n["time"] not in ("just now", "1m ago", "2m ago", "3m ago", "4m ago", "5m ago")])

    return templates.TemplateResponse(
        request, "admin/sections/_rt_notifications.html",
        {"request": request, "notifications": notifications, "unread_count": unread_count},
    )


# ===========================================================================
# Order Status Update
# ===========================================================================

async def update_order_status(request: Request) -> HTMLResponse:
    """POST /admin/orders/{order_id}/status — update order status."""
    order_id = request.path_params["order_id"]
    form = await request.form()
    new_status = (form.get("status") or "").strip()

    valid_statuses = {"pending", "paid", "processing", "shipped", "delivered", "cancelled"}
    if new_status not in valid_statuses:
        return HTMLResponse("Invalid status", status_code=400)

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE orders SET status = $1 WHERE id = $2",
            new_status, order_id,
        )

    status_labels = {
        "pending": ("Pending", "bg-amber-50 text-amber-700 border-amber-200"),
        "paid": ("Paid", "bg-emerald-50 text-emerald-700 border-emerald-200"),
        "processing": ("Processing", "bg-blue-50 text-blue-700 border-blue-200"),
        "shipped": ("Shipped", "bg-purple-50 text-purple-700 border-purple-200"),
        "delivered": ("Delivered", "bg-emerald-50 text-emerald-800 border-emerald-200"),
        "cancelled": ("Cancelled", "bg-red-50 text-red-700 border-red-200"),
    }
    label, cls = status_labels.get(new_status, ("Unknown", "bg-gray-50 text-gray-700 border-gray-200"))
    return HTMLResponse(f'<span class="text-[10px] font-mono px-2 py-0.5 rounded border {cls}">{label}</span>')


# ===========================================================================
# 12. LOGISTICS (delivery providers + shipments + tracking)
# ===========================================================================
async def section_logistics(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    providers: List[Dict[str, Any]] = []
    shipments: List[Dict[str, Any]] = []
    stats = {"total_shipments": 0, "in_transit": 0, "delivered": 0, "pending": 0}

    try:
        async with pool.acquire() as conn:
            try:
                rows = await conn.fetch(
                    "SELECT id, name, slug, is_active, base_rate, supports_tracking, "
                    "states_served, created_at FROM delivery_providers ORDER BY name"
                )
                providers = [dict(r) for r in rows]
            except Exception as exc:
                logger.warning("[admin] logistics providers fetch failed: %s", exc)

            try:
                stats["total_shipments"] = int(await conn.fetchval("SELECT COUNT(*) FROM shipments") or 0)
                stats["in_transit"] = int(
                    await conn.fetchval("SELECT COUNT(*) FROM shipments WHERE status IN ('in_transit','out_for_delivery')") or 0
                )
                stats["delivered"] = int(
                    await conn.fetchval("SELECT COUNT(*) FROM shipments WHERE status = 'delivered'") or 0
                )
                stats["pending"] = int(
                    await conn.fetchval("SELECT COUNT(*) FROM shipments WHERE status = 'pending'") or 0
                )
            except Exception:
                pass

            try:
                rows = await conn.fetch(
                    """SELECT s.id, s.tracking_number, s.status, s.receiver_name,
                              s.receiver_state, s.shipping_cost, s.estimated_delivery,
                              s.created_at, dp.name as provider_name
                       FROM shipments s
                       LEFT JOIN delivery_providers dp ON dp.id = s.provider_id
                       ORDER BY s.created_at DESC LIMIT 30"""
                )
                for r in rows:
                    d = dict(r)
                    d["id"] = str(d["id"])
                    d["shipping_cost"] = float(d.get("shipping_cost") or 0)
                    d["status_label"] = (d.get("status") or "pending").replace("_", " ").title()
                    d["created_at_human"] = _humanize_dt(d.get("created_at"))
                    shipments.append(d)
            except Exception as exc:
                logger.warning("[admin] logistics shipments fetch failed: %s", exc)
    except Exception as exc:
        logger.warning("[admin] logistics fetch failed: %s", exc)

    return _section_response(
        request, "admin/sections/logistics.html",
        {"providers": providers, "shipments": shipments, "stats": stats},
    )


# ===========================================================================
# 12b. LOGISTICS POST — manage providers + shipment status
# ===========================================================================
async def section_logistics_post(request: Request) -> HTMLResponse:
    """Handle logistics CRUD actions: add/toggle/delete providers, update shipment status."""
    pool = request.app.state.db_pool
    form = await request.form()
    action = form.get("action", "")

    try:
        async with pool.acquire() as conn:
            if action == "add_provider":
                name = (form.get("name") or "").strip()
                slug = (form.get("slug") or "").strip().lower().replace(" ", "-")
                base_rate = form.get("base_rate") or "0"
                supports_tracking = form.get("supports_tracking") == "on"
                supports_pickup = form.get("supports_pickup") == "on"
                states_raw = (form.get("states_served") or "").strip()
                states_list = [s.strip().lower() for s in states_raw.split(",") if s.strip()]
                if name and slug:
                    await conn.execute(
                        """INSERT INTO delivery_providers
                           (name, slug, base_rate, supports_tracking, supports_pickup, states_served)
                           VALUES ($1, $2, $3, $4, $5, $6)
                           ON CONFLICT (slug) DO NOTHING""",
                        name, slug, float(base_rate or 0),
                        supports_tracking, supports_pickup, states_list,
                    )

            elif action == "toggle_provider":
                provider_id = form.get("provider_id")
                if provider_id:
                    await conn.execute(
                        "UPDATE delivery_providers SET is_active = NOT is_active WHERE id = $1",
                        provider_id,
                    )

            elif action == "delete_provider":
                provider_id = form.get("provider_id")
                if provider_id:
                    await conn.execute("DELETE FROM delivery_providers WHERE id = $1", provider_id)

            elif action == "update_shipment_status":
                shipment_id = form.get("shipment_id")
                new_status = form.get("new_status") or "pending"
                if shipment_id:
                    await conn.execute(
                        """UPDATE shipments SET status = $1, updated_at = now() WHERE id = $2""",
                        new_status, shipment_id,
                    )

            elif action == "delete_shipment":
                shipment_id = form.get("shipment_id")
                if shipment_id:
                    await conn.execute("DELETE FROM shipments WHERE id = $1", shipment_id)

    except Exception as exc:
        logger.error("[admin] logistics save failed: %s", exc)

    return await section_logistics(request)


# ===========================================================================
# 13. SOCIAL COMMERCE (feed + influencers + outfit boards)
# ===========================================================================
async def section_social(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    posts: List[Dict[str, Any]] = []
    influencers: List[Dict[str, Any]] = []
    outfit_boards: List[Dict[str, Any]] = []
    stats = {"total_posts": 0, "total_likes": 0, "total_comments": 0, "featured_posts": 0}

    try:
        async with pool.acquire() as conn:
            try:
                stats["total_posts"] = int(await conn.fetchval("SELECT COUNT(*) FROM fashion_feed_posts") or 0)
                stats["total_likes"] = int(await conn.fetchval("SELECT SUM(likes_count) FROM fashion_feed_posts") or 0)
                stats["total_comments"] = int(await conn.fetchval("SELECT SUM(comments_count) FROM fashion_feed_posts") or 0)
                stats["featured_posts"] = int(await conn.fetchval("SELECT COUNT(*) FROM fashion_feed_posts WHERE is_featured") or 0)
            except Exception:
                pass

            try:
                rows = await conn.fetch(
                    """SELECT id, post_type, title, content, likes_count, comments_count,
                              shares_count, is_featured, is_public, created_at
                       FROM fashion_feed_posts
                       ORDER BY created_at DESC LIMIT 20"""
                )
                for r in rows:
                    d = dict(r)
                    d["id"] = str(d["id"])
                    d["post_type_label"] = (d.get("post_type") or "outfit").title()
                    d["created_at_human"] = _humanize_dt(d.get("created_at"))
                    posts.append(d)
            except Exception as exc:
                logger.warning("[admin] social posts fetch failed: %s", exc)

            try:
                rows = await conn.fetch(
                    """SELECT id, display_name, follower_count, engagement_rate,
                              total_posts, total_referrals, tier, is_verified, created_at
                       FROM influencer_profiles
                       ORDER BY follower_count DESC LIMIT 10"""
                )
                for r in rows:
                    d = dict(r)
                    d["id"] = str(d["id"])
                    d["engagement_rate"] = float(d.get("engagement_rate") or 0)
                    d["created_at_human"] = _humanize_dt(d.get("created_at"))
                    influencers.append(d)
            except Exception as exc:
                logger.warning("[admin] social influencers fetch failed: %s", exc)

            try:
                rows = await conn.fetch(
                    """SELECT id, title, description, occasion, cover_image,
                              likes_count, is_public, created_at
                       FROM outfit_boards
                       ORDER BY created_at DESC LIMIT 10"""
                )
                for r in rows:
                    d = dict(r)
                    d["id"] = str(d["id"])
                    d["created_at_human"] = _humanize_dt(d.get("created_at"))
                    outfit_boards.append(d)
            except Exception as exc:
                logger.warning("[admin] social outfit boards fetch failed: %s", exc)
    except Exception as exc:
        logger.warning("[admin] social fetch failed: %s", exc)

    return _section_response(
        request, "admin/sections/social.html",
        {"posts": posts, "influencers": influencers, "outfit_boards": outfit_boards, "stats": stats},
    )


# ===========================================================================
# 14. LOYALTY (points + referrals + VIP + rewards)
# ===========================================================================
async def section_loyalty(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    accounts: List[Dict[str, Any]] = []
    referrals: List[Dict[str, Any]] = []
    rewards: List[Dict[str, Any]] = []
    tiers: List[Dict[str, Any]] = []
    stats = {"total_customers": 0, "total_points_issued": 0, "total_referrals": 0, "active_rewards": 0}

    try:
        async with pool.acquire() as conn:
            try:
                stats["total_customers"] = int(await conn.fetchval("SELECT COUNT(*) FROM loyalty_accounts") or 0)
                stats["total_points_issued"] = int(await conn.fetchval("SELECT COALESCE(SUM(total_points_earned), 0) FROM loyalty_accounts") or 0)
                stats["total_referrals"] = int(await conn.fetchval("SELECT COUNT(*) FROM referrals") or 0)
                stats["active_rewards"] = int(await conn.fetchval("SELECT COUNT(*) FROM rewards_catalog WHERE is_active") or 0)
            except Exception:
                pass

            try:
                rows = await conn.fetch(
                    """SELECT la.id, la.customer_id, la.current_balance, la.vip_tier,
                              la.total_referrals, la.referral_code, la.lifetime_spend,
                              la.lifetime_orders, la.vip_since, la.created_at
                       FROM loyalty_accounts la
                       ORDER BY la.current_balance DESC LIMIT 20"""
                )
                for r in rows:
                    d = dict(r)
                    d["id"] = str(d["id"])
                    d["lifetime_spend"] = float(d.get("lifetime_spend") or 0)
                    d["created_at_human"] = _humanize_dt(d.get("created_at"))
                    accounts.append(d)
            except Exception as exc:
                logger.warning("[admin] loyalty accounts fetch failed: %s", exc)

            try:
                rows = await conn.fetch(
                    """SELECT id, status, referral_code, reward_points,
                              first_purchase_amount, created_at
                       FROM referrals
                       ORDER BY created_at DESC LIMIT 15"""
                )
                for r in rows:
                    d = dict(r)
                    d["id"] = str(d["id"])
                    d["status_label"] = (d.get("status") or "pending").title()
                    d["first_purchase_amount"] = float(d.get("first_purchase_amount") or 0)
                    d["created_at_human"] = _humanize_dt(d.get("created_at"))
                    referrals.append(d)
            except Exception as exc:
                logger.warning("[admin] loyalty referrals fetch failed: %s", exc)

            try:
                rows = await conn.fetch(
                    """SELECT id, name, description, points_cost, reward_type,
                              reward_value, is_active, stock
                       FROM rewards_catalog
                       ORDER BY points_cost ASC"""
                )
                for r in rows:
                    d = dict(r)
                    d["id"] = str(d["id"])
                    d["reward_value"] = float(d.get("reward_value") or 0)
                    rewards.append(d)
            except Exception as exc:
                logger.warning("[admin] loyalty rewards fetch failed: %s", exc)

            try:
                rows = await conn.fetch(
                    """SELECT id, tier_name, min_spend, points_multiplier,
                              discount_percent, free_shipping, early_access, benefits
                       FROM vip_tiers
                       ORDER BY min_spend ASC"""
                )
                for r in rows:
                    d = dict(r)
                    d["id"] = str(d["id"])
                    d["min_spend"] = float(d.get("min_spend") or 0)
                    d["discount_percent"] = float(d.get("discount_percent") or 0)
                    tiers.append(d)
            except Exception as exc:
                logger.warning("[admin] loyalty tiers fetch failed: %s", exc)
    except Exception as exc:
        logger.warning("[admin] loyalty fetch failed: %s", exc)

    return _section_response(
        request, "admin/sections/loyalty.html",
        {"accounts": accounts, "referrals": referrals, "rewards": rewards,
         "tiers": tiers, "stats": stats},
    )


# ===========================================================================
# 14. AI TRAINING — manage AI Stylist knowledge base
# ===========================================================================
async def section_ai_training_get(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    items = []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM ai_training_data ORDER BY category, sort_order, created_at DESC"
            )
            items = [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("[admin] ai_training fetch failed: %s", exc)

    # Fetch current AI settings
    settings = {}
    try:
        from app.settings_service import get_settings
        settings = await get_settings(pool)
    except Exception:
        pass

    return _section_response(
        request, "admin/sections/ai_training.html",
        {"items": items, "settings": settings},
    )


async def section_ai_training_post(request: Request) -> HTMLResponse:
    """Handle AI training data CRUD actions."""
    pool = request.app.state.db_pool
    form = await request.form()
    action = form.get("action", "")

    try:
        async with pool.acquire() as conn:
            if action == "add":
                category = (form.get("category") or "faq").strip()
                question = (form.get("question") or "").strip()
                answer = (form.get("answer") or "").strip()
                if question and answer:
                    await conn.execute(
                        """INSERT INTO ai_training_data (category, question, answer, sort_order)
                           VALUES ($1, $2, $3, $4)""",
                        category, question, answer,
                        int(form.get("sort_order") or 0),
                    )

            elif action == "delete":
                item_id = form.get("item_id")
                if item_id:
                    await conn.execute("DELETE FROM ai_training_data WHERE id = $1", item_id)

            elif action == "toggle":
                item_id = form.get("item_id")
                if item_id:
                    await conn.execute(
                        "UPDATE ai_training_data SET is_active = NOT is_active WHERE id = $1",
                        item_id,
                    )

            elif action == "update":
                item_id = form.get("item_id")
                if item_id:
                    await conn.execute(
                        """UPDATE ai_training_data
                           SET category=$1, question=$2, answer=$3, sort_order=$4, updated_at=NOW()
                           WHERE id=$5""",
                        (form.get("category") or "faq").strip(),
                        (form.get("question") or "").strip(),
                        (form.get("answer") or "").strip(),
                        int(form.get("sort_order") or 0),
                        item_id,
                    )

    except Exception as exc:
        logger.error("[admin] ai_training save failed: %s", exc)

    return await section_ai_training_get(request)


# ===========================================================================
# Pages & Blog Management
# ===========================================================================

async def section_pages_get(request: Request) -> HTMLResponse:
    """Pages management: list all custom pages with go-live toggle."""
    pool = request.app.state.db_pool
    pages: List[Dict] = []
    blog_counts: Dict[str, int] = {}
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM custom_pages ORDER BY sort_order ASC, created_at DESC"
            )
            pages = [dict(r) for r in rows]
            for p in pages:
                cnt = await conn.fetchval(
                    "SELECT COUNT(*) FROM blog_posts WHERE page_id=$1", p["id"]
                )
                blog_counts[str(p["id"])] = cnt or 0
    except Exception as exc:
        logger.error("[admin] pages list failed: %s", exc)
    return _section_response(request, "admin/sections/pages.html", {
        "pages": pages, "blog_counts": blog_counts,
    })


async def section_pages_post(request: Request) -> HTMLResponse:
    """Create/update/delete custom pages and toggle go-live."""
    form = await request.form()
    action = form.get("action", "create")
    pool = request.app.state.db_pool

    try:
        async with pool.acquire() as conn:
            if action == "create":
                title = (form.get("title") or "Untitled Page").strip()
                slug = (form.get("slug") or title.lower().replace(" ", "-").replace("'", "")).strip()
                page_type = (form.get("page_type") or "content").strip()
                await conn.execute(
                    """INSERT INTO custom_pages (title, slug, page_type)
                       VALUES ($1, $2, $3)""",
                    title, slug, page_type,
                )

            elif action == "update":
                page_id = form.get("page_id")
                if page_id:
                    fields = {}
                    for key in ("title", "slug", "page_type", "body_html", "excerpt",
                                "meta_description", "featured_image", "sort_order"):
                        if key in form:
                            fields[key] = form[key]
                    if "show_in_nav" in form:
                        fields["show_in_nav"] = form["show_in_nav"] == "on"
                    if "show_in_footer" in form:
                        fields["show_in_footer"] = form["show_in_footer"] == "on"
                    if "is_live" in form:
                        fields["is_live"] = form["is_live"] == "on"
                    sets = ", ".join(f"{k}=${i+2}" for i, k in enumerate(fields))
                    vals = list(fields.values()) + [page_id]
                    if fields:
                        await conn.execute(
                            f"UPDATE custom_pages SET {sets}, updated_at=NOW() WHERE id=$1",
                            *vals,
                        )

            elif action == "toggle_live":
                page_id = form.get("page_id")
                if page_id:
                    await conn.execute(
                        "UPDATE custom_pages SET is_live = NOT is_live, updated_at=NOW() WHERE id=$1",
                        page_id,
                    )

            elif action == "delete":
                page_id = form.get("page_id")
                if page_id:
                    await conn.execute("DELETE FROM custom_pages WHERE id=$1", page_id)

    except Exception as exc:
        logger.error("[admin] pages save failed: %s", exc)

    return await section_pages_get(request)


async def section_blog_get(request: Request) -> HTMLResponse:
    """Blog posts management for a specific page."""
    page_id = request.query_params.get("page_id", "")
    pool = request.app.state.db_pool
    page_info: Optional[Dict] = None
    posts: List[Dict] = []
    try:
        async with pool.acquire() as conn:
            if page_id:
                page_info = await conn.fetchrow(
                    "SELECT * FROM custom_pages WHERE id=$1", page_id
                )
                if page_info:
                    page_info = dict(page_info)
                    rows = await conn.fetch(
                        "SELECT * FROM blog_posts WHERE page_id=$1 ORDER BY created_at DESC",
                        page_id,
                    )
                    posts = [dict(r) for r in rows]
    except Exception as exc:
        logger.error("[admin] blog list failed: %s", exc)
    return _section_response(request, "admin/sections/blog_posts.html", {
        "page_info": page_info, "posts": posts, "page_id": page_id,
    })


async def section_blog_post(request: Request) -> HTMLResponse:
    """Create/update/delete/publish blog posts."""
    form = await request.form()
    action = form.get("action", "create")
    pool = request.app.state.db_pool
    page_id = form.get("page_id", "")

    try:
        async with pool.acquire() as conn:
            if action == "create":
                title = (form.get("title") or "Untitled Post").strip()
                slug = (form.get("slug") or title.lower().replace(" ", "-").replace("'", "")).strip()
                await conn.execute(
                    """INSERT INTO blog_posts (page_id, title, slug, content_html, excerpt, author_name)
                       VALUES ($1, $2, $3, $4, $5, $6)""",
                    page_id, title, slug,
                    (form.get("content_html") or "").strip(),
                    (form.get("excerpt") or "").strip(),
                    (form.get("author_name") or "ASIKO Team").strip(),
                )

            elif action == "update":
                post_id = form.get("post_id")
                if post_id:
                    fields = {}
                    for key in ("title", "slug", "content_html", "excerpt", "featured_image", "author_name"):
                        if key in form:
                            fields[key] = form[key]
                    if "is_published" in form:
                        fields["is_published"] = form["is_published"] == "on"
                        if fields["is_published"]:
                            fields["published_at"] = "NOW()"
                    sets_parts = []
                    vals = [post_id]
                    for i, (k, v) in enumerate(fields.items()):
                        if v == "NOW()":
                            sets_parts.append(f"{k}=NOW()")
                        else:
                            sets_parts.append(f"{k}=${len(vals)+1}")
                            vals.append(v)
                    if sets_parts:
                        await conn.execute(
                            f"UPDATE blog_posts SET {', '.join(sets_parts)}, updated_at=NOW() WHERE id=$1",
                            *vals,
                        )

            elif action == "publish_toggle":
                post_id = form.get("post_id")
                if post_id:
                    await conn.execute(
                        """UPDATE blog_posts
                           SET is_published = NOT is_published,
                               published_at = CASE WHEN is_published THEN published_at ELSE NOW() END,
                               updated_at=NOW()
                           WHERE id=$1""",
                        post_id,
                    )

            elif action == "delete":
                post_id = form.get("post_id")
                if post_id:
                    await conn.execute("DELETE FROM blog_posts WHERE id=$1", post_id)

    except Exception as exc:
        logger.error("[admin] blog save failed: %s", exc)

    return await section_blog_get(request) if page_id else await section_pages_get(request)


# ===========================================================================
# 15. SOCIAL COMMERCE POST — manage influencers, posts, outfit boards
# ===========================================================================
async def section_social_post(request: Request) -> HTMLResponse:
    """Handle social commerce CRUD actions."""
    pool = request.app.state.db_pool
    form = await request.form()
    action = form.get("action", "")

    try:
        async with pool.acquire() as conn:
            if action == "add_influencer":
                display_name = (form.get("display_name") or "").strip()
                bio = (form.get("bio") or "").strip()
                tier = form.get("tier") or "micro"
                if display_name:
                    await conn.execute(
                        """INSERT INTO influencer_profiles (customer_id, display_name, bio, tier)
                           VALUES (NULL, $1, $2, $3)""",
                        display_name, bio, tier,
                    )

            elif action == "delete_influencer":
                inf_id = form.get("influencer_id")
                if inf_id:
                    await conn.execute("DELETE FROM influencer_profiles WHERE id=$1", inf_id)

            elif action == "toggle_featured":
                post_id = form.get("post_id")
                if post_id:
                    await conn.execute(
                        "UPDATE fashion_feed_posts SET is_featured = NOT is_featured WHERE id=$1",
                        post_id,
                    )

            elif action == "delete_post":
                post_id = form.get("post_id")
                if post_id:
                    await conn.execute("DELETE FROM fashion_feed_posts WHERE id=$1", post_id)

            elif action == "add_board":
                title = (form.get("title") or "").strip()
                occasion = (form.get("occasion") or "").strip()
                description = (form.get("description") or "").strip()
                if title:
                    await conn.execute(
                        """INSERT INTO outfit_boards (customer_id, title, description, occasion, products)
                           VALUES (NULL, $1, $2, $3, '[]'::jsonb)""",
                        title, description, occasion,
                    )

            elif action == "delete_board":
                board_id = form.get("board_id")
                if board_id:
                    await conn.execute("DELETE FROM outfit_boards WHERE id=$1", board_id)

    except Exception as exc:
        logger.error("[admin] social save failed: %s", exc)

    return await section_social(request)


# ===========================================================================
# 16. LOYALTY POST — manage tiers, rewards
# ===========================================================================
async def section_loyalty_post(request: Request) -> HTMLResponse:
    """Handle loyalty system CRUD actions."""
    pool = request.app.state.db_pool
    form = await request.form()
    action = form.get("action", "")

    try:
        async with pool.acquire() as conn:
            if action == "update_tier":
                tier_id = form.get("tier_id")
                min_spend = form.get("min_spend")
                discount = form.get("discount_percent")
                points_mult = form.get("points_multiplier")
                free_shipping = form.get("free_shipping") == "on"
                early_access = form.get("early_access") == "on"
                if tier_id:
                    await conn.execute(
                        """UPDATE vip_tiers
                           SET min_spend=$1, discount_percent=$2, points_multiplier=$3,
                               free_shipping=$4, early_access=$5
                           WHERE id=$6""",
                        float(min_spend or 0), float(discount or 0),
                        float(points_mult or 1), free_shipping, early_access, tier_id,
                    )

            elif action == "add_reward":
                name = (form.get("name") or "").strip()
                description = (form.get("description") or "").strip()
                points_cost = form.get("points_cost")
                reward_type = form.get("reward_type") or "discount"
                reward_value = form.get("reward_value")
                if name and points_cost:
                    await conn.execute(
                        """INSERT INTO rewards_catalog (name, description, points_cost, reward_type, reward_value)
                           VALUES ($1, $2, $3, $4, $5)""",
                        name, description, int(points_cost), reward_type, float(reward_value or 0),
                    )

            elif action == "delete_reward":
                reward_id = form.get("reward_id")
                if reward_id:
                    await conn.execute("DELETE FROM rewards_catalog WHERE id=$1", reward_id)

            elif action == "toggle_reward":
                reward_id = form.get("reward_id")
                if reward_id:
                    await conn.execute(
                        "UPDATE rewards_catalog SET is_active = NOT is_active WHERE id=$1",
                        reward_id,
                    )

            elif action == "adjust_points":
                customer_id = form.get("customer_id")
                points = form.get("points_adjust")
                description = (form.get("description") or "Admin adjustment").strip()
                if customer_id and points:
                    pts = int(points)
                    # Get current balance
                    bal = await conn.fetchval(
                        "SELECT current_balance FROM loyalty_accounts WHERE customer_id=$1",
                        customer_id,
                    )
                    if bal is not None:
                        new_bal = int(bal) + pts
                        await conn.execute(
                            """UPDATE loyalty_accounts
                               SET current_balance=$1, total_points_earned = total_points_earned + $2,
                                   updated_at=NOW()
                               WHERE customer_id=$3""",
                            new_bal, max(pts, 0), customer_id,
                        )
                        await conn.execute(
                            """INSERT INTO loyalty_points (customer_id, points, source, description, balance_after)
                               VALUES ($1, $2, 'admin_adjust', $3, $4)""",
                            customer_id, pts, description, new_bal,
                        )

    except Exception as exc:
        logger.error("[admin] loyalty save failed: %s", exc)

    return await section_loyalty(request)


# ===========================================================================
# HELP & SUPPORT
# ===========================================================================
async def section_help(request: Request) -> HTMLResponse:
    return _section_response(request, "admin/sections/help.html", {})


# ===========================================================================
# Route registration
# ===========================================================================
routes = [
    Route("/admin",                       endpoint=admin_index,           methods=["GET"]),
    Route("/admin/section/dashboard",     endpoint=section_dashboard,     methods=["GET"]),
    Route("/admin/section/sales",         endpoint=section_sales,         methods=["GET"]),
    Route("/admin/section/view-site",     endpoint=section_view_site,     methods=["GET"]),
    Route("/admin/section/products",      endpoint=section_products,      methods=["GET"]),
    Route("/admin/section/product/{id}", endpoint=section_product_detail, methods=["GET"]),
    Route("/admin/section/categories",    endpoint=section_categories,    methods=["GET"]),
    Route("/admin/section/analytics",     endpoint=section_analytics,     methods=["GET"]),
    Route("/admin/section/members",       endpoint=section_members,       methods=["GET"]),
    Route("/admin/section/operations",    endpoint=section_operations,    methods=["GET"]),
    Route("/admin/section/settings",      endpoint=section_settings_get,  methods=["GET"]),
    Route("/admin/section/settings",      endpoint=section_settings_post, methods=["POST"]),
    Route("/admin/section/logistics",     endpoint=section_logistics,     methods=["GET"]),
    Route("/admin/section/logistics",     endpoint=section_logistics_post, methods=["POST"]),
    Route("/admin/section/social",        endpoint=section_social,        methods=["GET"]),
    Route("/admin/section/social",        endpoint=section_social_post,   methods=["POST"]),
    Route("/admin/section/loyalty",       endpoint=section_loyalty,       methods=["GET"]),
    Route("/admin/section/loyalty",       endpoint=section_loyalty_post,  methods=["POST"]),
    Route("/admin/section/ai-training",   endpoint=section_ai_training_get,  methods=["GET"]),
    Route("/admin/section/ai-training",   endpoint=section_ai_training_post, methods=["POST"]),
    Route("/admin/section/about",         endpoint=section_about_get,     methods=["GET"]),
    Route("/admin/section/about",         endpoint=section_about_post,    methods=["POST"]),
    Route("/admin/section/help",          endpoint=section_help,          methods=["GET"]),
    Route("/admin/section/pages",         endpoint=section_pages_get,     methods=["GET"]),
    Route("/admin/section/pages",         endpoint=section_pages_post,    methods=["POST"]),
    Route("/admin/section/blog",          endpoint=section_blog_get,      methods=["GET"]),
    Route("/admin/section/blog",          endpoint=section_blog_post,     methods=["POST"]),
    Route("/admin/orders/{order_id}/status", endpoint=update_order_status, methods=["POST"]),
    # Legacy sections retained for direct URL access (sidebar no longer links to these)
    Route("/admin/section/all-products",  endpoint=section_all_products,  methods=["GET"]),
    Route("/admin/section/reviews",       endpoint=section_reviews,       methods=["GET"]),
    Route("/admin/section/ads",           endpoint=section_ads,           methods=["GET"]),
    # Real-time fragment endpoints (called by HTMX when WS triggers fire)
    Route("/admin/rt/activity",           endpoint=rt_dashboard_activity, methods=["GET"]),
    Route("/admin/rt/kpi",                endpoint=rt_dashboard_kpi,      methods=["GET"]),
    Route("/admin/rt/reviews",            endpoint=rt_reviews_summary,    methods=["GET"]),
    Route("/admin/rt/notifications",      endpoint=rt_notifications,      methods=["GET"]),
]
