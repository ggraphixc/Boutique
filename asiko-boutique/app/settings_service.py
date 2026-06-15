# app/settings_service.py
# Centralized store settings — reads from DB with defaults.
# Uses in-memory TTL cache to avoid DB queries on every page load.

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("asiko.settings")

# ---------------------------------------------------------------------------
# In-memory TTL cache — settings rarely change, no need to hit DB every request
# ---------------------------------------------------------------------------
_cache: Optional[Dict[str, Any]] = None
_cache_ts: float = 0.0
CACHE_TTL: int = 30  # seconds — settings refresh at most every 30s

# SEO settings cache (separate table)
_seo_cache: Optional[Dict[str, Any]] = None
_seo_cache_ts: float = 0.0
SEO_CACHE_TTL: int = 30

SEO_DEFAULTS: Dict[str, Any] = {
    "seo_title": "",
    "seo_description": "",
    "seo_keywords": "",
    "seo_og_image": "",
    "seo_twitter_handle": "",
    "seo_google_analytics": "",
    "seo_google_tag_manager": "",
    "seo_structured_data": True,
    "seo_sitemap_enabled": True,
    "seo_robots_enabled": True,
    "geo_enabled": True,
    "geo_local_business": {},
    "aeo_faq_schema": True,
    "aeo_product_schema": True,
    "smo_twitter_card": "summary_large_image",
    "smo_facebook_app_id": "",
    "sem_conversion_id": "",
    "sem_conversion_label": "",
    "sem_remarketing_tag": "",
}


def invalidate_settings_cache() -> None:
    """Call after save_settings() to force a fresh DB read."""
    global _cache, _cache_ts, _seo_cache, _seo_cache_ts
    _cache = None
    _cache_ts = 0.0
    _seo_cache = None
    _seo_cache_ts = 0.0

# Default settings — used when DB row is missing or column doesn't exist
DEFAULTS: Dict[str, Any] = {
    # Store profile
    "store_name": "ASIKO Boutique",
    "contact_email": "",
    "store_description": "",
    "phone": "",
    "store_address": "",
    # Global brand identity
    "brand_name": "ASIKO Boutique",
    "brand_tagline": "Authentic Nigerian Fashion",
    "brand_footer_text": "© 2026 ASIKO Boutique. All rights reserved.",
    "brand_currency_symbol": "&#8358;",
    "brand_currency_code": "NGN",
    "brand_logo": "",
    # Currency / locale
    "currency": "NGN",
    "timezone": "Africa/Lagos",
    "locale": "en",
    # Shipping
    "shipping_domestic": 0,
    "shipping_international": 0,
    "free_shipping_threshold": 0,
    # 3D pipeline
    "mesh_provider": "hunyuan3d2",
    "auto_mesh": True,
    # AI provider
    "ai_provider": "openrouter",
    "ai_api_key": "",
    "ai_model": "google/gemini-2.0-flash-001",
    "ai_system_prompt": "",
    "ai_max_tokens": 1024,
    "ai_temperature": 0.7,
    # AI Stylist page
    "ai_stylist_enabled": True,
    "ai_stylist_welcome": (
        "Hello! I'm your personal ASIKO fashion stylist. "
        "I can help you find the perfect outfit, suggest color combinations, "
        "and keep you on trend. What can I help you with today?"
    ),
    "ai_stylist_suggestions": (
        "What should I wear to a wedding?,"
        "Recommend something casual,"
        "What colors match my skin tone?,"
        "What is trending in Nigerian fashion?"
    ),
    # Homepage hero
    "hero_title": "Authentic",
    "hero_title_accent": "Nigerian Fashion",
    "hero_subtitle": "Shop curated styles with transparent pricing. Every piece crafted with verified provenance and fair-trade standards.",
    "hero_badge_text": "New Collection Available",
    "hero_cta_text": "Shop Collection",
    "hero_cta_link": "#storefront",
    # Shop
    "shop_products_per_page": 12,
    "shop_default_sort": "newest",
    "shop_show_3d_badge": True,
    # Lookbook
    "lookbook_title": "The Lookbook",
    "lookbook_subtitle": "Curated ensembles and styling inspiration from ASIKO's collection.",
    # About
    "about_title": "ASIKO Boutique",
    "about_tagline": "Authentic Nigerian Fashion",
    "about_story": "ASIKO was founded with a mission to bring transparent, verified Nigerian fashion to the world. Every piece in our collection is crafted with care, using traditional techniques and modern design.",
    "about_location": "Lagos, Nigeria",
    "about_email": "hello@asikoboutique.com",
    "about_founded_year": 2024,
    # Customer dashboard
    "customer_welcome_title": "Welcome back",
    "customer_welcome_subtitle": "Manage your orders and discover new styles.",
    # Chatbot widget
    "chatbot_enabled": True,
    "chatbot_welcome": "Hi! I'm your personal ASIKO stylist. How can I help you find the perfect look today?",
    "chatbot_color_primary": "#0D2A22",
    "chatbot_color_accent": "#D4AF37",
    # Pages & blog
    "blog_enabled": True,
    "blog_posts_per_page": 6,
    # Email / Brevo
    "brevo_api_key": "",
    "sender_email": "orders@asikoboutique.com",
    "sender_name": "ASIKO Boutique",
    "admin_email": "hello@asikoboutique.com",
    "email_welcome_enabled": True,
    "email_order_enabled": True,
    "email_shipping_enabled": True,
    "email_newsletter_enabled": True,
    "email_password_reset_enabled": True,
    # Notification toggles
    "notif_new_order": True,
    "notif_pipeline": True,
    "notif_review": True,
    "notif_low_stock": True,
    # Session
    "session_timeout": 30,
    # Page visibility
    "page_contact_visible": True,
    "page_faq_visible": True,
    "page_shipping_visible": True,
    "page_size_guide_visible": True,
    "page_stylist_visible": True,
    "page_lookbook_visible": True,
    # Email campaign
    "email_from_name": "ASIKO Boutique",
    "email_reply_to": "support@asikoboutique.com",
    "email_tracking_enabled": True,
    "email_unsubscribe_link": True,
    "email_footer_text": "ASIKO Boutique — Authentic Nigerian Fashion",
}


async def get_settings(db_pool) -> Dict[str, Any]:
    """Fetch all store settings from DB with in-memory TTL cache."""
    global _cache, _cache_ts
    now = time.monotonic()
    if _cache is not None and (now - _cache_ts) < CACHE_TTL:
        return _cache

    result = dict(DEFAULTS)
    for attempt in range(2):
        try:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM store_settings WHERE id = 1")
                if row:
                    row_dict = dict(row)
                    for key in DEFAULTS:
                        if key in row_dict and row_dict[key] is not None:
                            result[key] = row_dict[key]
                # Merge seo_settings into result
                seo_row = await conn.fetchrow("SELECT * FROM seo_settings WHERE id = 1")
                if seo_row:
                    seo_dict = dict(seo_row)
                    for key in SEO_DEFAULTS:
                        if key in seo_dict and seo_dict[key] is not None:
                            result[key] = seo_dict[key]
                _cache = result
                _cache_ts = now
                return result
        except Exception as exc:
            if attempt == 0 and "cached statement" in str(exc).lower():
                continue
            logger.warning("[settings] DB fetch failed, using defaults: %s", exc)
            return result
    return result


async def get_setting(db_pool, key: str) -> Any:
    """Fetch a single setting by key."""
    defaults = await get_settings(db_pool)
    return defaults.get(key)


async def save_settings(db_pool, payload: Dict[str, Any], partial: bool = False) -> None:
    """Upsert settings into the store_settings singleton row.

    Embeds values directly in SQL (no $N parameters) to avoid asyncpg's
    prepared-statement type-inference issue with dynamic column lists.
    Safe because: single-table upsert, column names are code-controlled,
    string values are single-quote-escaped."""
    if not payload:
        return

    BOOLEAN_KEYS = {
        "auto_mesh", "ai_stylist_enabled", "shop_show_3d_badge",
        "chatbot_enabled", "blog_enabled",
        "notif_new_order", "notif_pipeline",
        "notif_review", "notif_low_stock",
        "email_welcome_enabled", "email_order_enabled", "email_shipping_enabled",
        "email_newsletter_enabled", "email_password_reset_enabled",
        "page_contact_visible", "page_faq_visible", "page_shipping_visible",
        "page_size_guide_visible", "page_stylist_visible", "page_lookbook_visible",
        "email_tracking_enabled", "email_unsubscribe_link",
    }
    INT_KEYS = {
        "shipping_domestic", "shipping_international", "free_shipping_threshold",
        "ai_max_tokens", "shop_products_per_page", "about_founded_year",
        "blog_posts_per_page", "session_timeout",
    }
    FLOAT_KEYS = {"ai_temperature"}

    def _pg_literal(val: Any) -> str:
        """Convert a Python value to a PostgreSQL literal for embedding in SQL."""
        if val is True:
            return "TRUE"
        if val is False:
            return "FALSE"
        if isinstance(val, (int, float)):
            return str(val)
        s = str(val).replace("\\", "\\\\").replace("'", "''")
        return f"'{s}'"

    # Sanitize to correct Python types, then to PG literals
    columns = []
    literals = []
    set_clauses = []

    for k, v in payload.items():
        columns.append(k)
        if k in BOOLEAN_KEYS:
            bval = bool(str(v).lower() in ("true", "1", "on", "yes")) if v not in (None, "") else False
            lit = _pg_literal(bval)
        elif k in INT_KEYS:
            try:
                ival = int(v)
            except (ValueError, TypeError):
                ival = 0
            lit = _pg_literal(ival)
        elif k in FLOAT_KEYS:
            try:
                fval = float(v)
            except (ValueError, TypeError):
                fval = 0.0
            lit = _pg_literal(fval)
        else:
            lit = _pg_literal(str(v) if v is not None else "")
        literals.append(lit)
        set_clauses.append(f"{k} = {lit}")

    cols_str = ", ".join(["id"] + columns)
    vals_str = ", ".join(["1"] + literals)
    sets_str = ", ".join(set_clauses)

    query = f"""
        INSERT INTO store_settings ({cols_str}, updated_at)
        VALUES ({vals_str}, now())
        ON CONFLICT (id) DO UPDATE SET
            {sets_str},
            updated_at = now()
    """

    try:
        async with db_pool.acquire() as conn:
            await conn.execute(query)
        invalidate_settings_cache()
    except Exception as exc:
        logger.error("[settings] save failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# SEO Settings — separate table (seo_settings)
# ---------------------------------------------------------------------------

async def get_seo_settings(db_pool) -> Dict[str, Any]:
    """Fetch SEO settings from the dedicated seo_settings table."""
    global _seo_cache, _seo_cache_ts
    now = time.monotonic()
    if _seo_cache is not None and (now - _seo_cache_ts) < SEO_CACHE_TTL:
        return _seo_cache

    result = dict(SEO_DEFAULTS)
    for attempt in range(2):
        try:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM seo_settings WHERE id = 1")
                if row:
                    row_dict = dict(row)
                    for key in SEO_DEFAULTS:
                        if key in row_dict and row_dict[key] is not None:
                            result[key] = row_dict[key]
                _seo_cache = result
                _seo_cache_ts = now
                return result
        except Exception as exc:
            if attempt == 0 and "cached statement" in str(exc).lower():
                continue
            logger.warning("[seo_settings] DB fetch failed, using defaults: %s", exc)
            return result
    return result


async def save_seo_settings(db_pool, payload: Dict[str, Any]) -> None:
    """Upsert SEO settings into the seo_settings singleton row."""
    if not payload:
        return

    SEO_BOOL_KEYS = {
        "seo_structured_data", "seo_sitemap_enabled", "seo_robots_enabled",
        "geo_enabled", "aeo_faq_schema", "aeo_product_schema",
    }

    def _pg_literal(val: Any) -> str:
        if val is True:
            return "TRUE"
        if val is False:
            return "FALSE"
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, dict):
            import json as _json
            s = _json.dumps(val).replace("'", "''")
            return f"'{s}'::jsonb"
        s = str(val).replace("\\", "\\\\").replace("'", "''")
        return f"'{s}'"

    columns = []
    literals = []
    set_clauses = []

    for k, v in payload.items():
        columns.append(k)
        if k in SEO_BOOL_KEYS:
            bval = bool(str(v).lower() in ("true", "1", "on", "yes")) if v not in (None, "") else False
            lit = _pg_literal(bval)
        else:
            lit = _pg_literal(str(v) if v is not None else "")
        literals.append(lit)
        set_clauses.append(f"{k} = {lit}")

    cols_str = ", ".join(["id"] + columns)
    vals_str = ", ".join(["1"] + literals)
    sets_str = ", ".join(set_clauses)

    query = f"""
        INSERT INTO seo_settings ({cols_str}, updated_at)
        VALUES ({vals_str}, now())
        ON CONFLICT (id) DO UPDATE SET
            {sets_str},
            updated_at = now()
    """

    try:
        async with db_pool.acquire() as conn:
            await conn.execute(query)
        invalidate_settings_cache()
    except Exception as exc:
        logger.error("[seo_settings] save failed: %s", exc)
        raise
