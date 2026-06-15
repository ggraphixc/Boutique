# app/settings_service.py
# Centralized store settings — reads from 9 DB tables with defaults.
# Uses in-memory TTL cache to avoid DB queries on every page load.

import json as _json
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("asiko.settings")

# ---------------------------------------------------------------------------
# In-memory TTL cache — settings rarely change, no need to hit DB every request
# ---------------------------------------------------------------------------
CACHE_TTL: int = 30  # seconds

_caches: Dict[str, Optional[Dict[str, Any]]] = {
    "store_profile": None, "brand": None, "ai": None, "chatbot": None,
    "page": None, "shop": None, "notification": None, "seo": None,
}
_cache_ts: Dict[str, float] = {k: 0.0 for k in _caches}


def invalidate_settings_cache() -> None:
    """Call after any save to force a fresh DB read."""
    for k in _caches:
        _caches[k] = None
        _cache_ts[k] = 0.0


# ---------------------------------------------------------------------------
# Per-table defaults
# ---------------------------------------------------------------------------
STORE_PROFILE_DEFAULTS: Dict[str, Any] = {
    "store_name": "ASIKO Boutique",
    "contact_email": "",
    "store_description": "",
    "phone": "",
    "store_address": "",
}

BRAND_DEFAULTS: Dict[str, Any] = {
    "brand_name": "ASIKO Boutique",
    "brand_tagline": "Authentic Nigerian Fashion",
    "brand_footer_text": "© 2026 ASIKO Boutique. All rights reserved.",
    "brand_currency_symbol": "&#8358;",
    "brand_currency_code": "NGN",
    "brand_logo": "",
}

AI_DEFAULTS: Dict[str, Any] = {
    "ai_provider": "openrouter",
    "ai_api_key": "",
    "ai_model": "google/gemini-2.0-flash-001",
    "ai_system_prompt": "",
    "ai_max_tokens": 1024,
    "ai_temperature": 0.7,
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
    "mesh_provider": "hunyuan3d2",
    "auto_mesh": True,
}

CHATBOT_DEFAULTS: Dict[str, Any] = {
    "chatbot_enabled": True,
    "chatbot_welcome": "Hi! I'm your personal ASIKO stylist. How can I help you find the perfect look today?",
    "chatbot_color_primary": "#0D2A22",
    "chatbot_color_accent": "#D4AF37",
}

PAGE_DEFAULTS: Dict[str, Any] = {
    "hero_title": "Authentic",
    "hero_title_accent": "Nigerian Fashion",
    "hero_subtitle": "Shop curated styles with transparent pricing. Every piece crafted with verified provenance and fair-trade standards.",
    "hero_badge_text": "New Collection Available",
    "hero_cta_text": "Shop Collection",
    "hero_cta_link": "#storefront",
    "lookbook_title": "The Lookbook",
    "lookbook_subtitle": "Curated ensembles and styling inspiration from ASIKO's collection.",
    "about_title": "ASIKO Boutique",
    "about_tagline": "Authentic Nigerian Fashion",
    "about_story": "ASIKO was founded with a mission to bring transparent, verified Nigerian fashion to the world. Every piece in our collection is crafted with care, using traditional techniques and modern design.",
    "about_location": "Lagos, Nigeria",
    "about_email": "hello@asikoboutique.com",
    "about_founded_year": 2024,
    "customer_welcome_title": "Welcome back",
    "customer_welcome_subtitle": "Manage your orders and discover new styles.",
    "currency": "NGN",
    "timezone": "Africa/Lagos",
    "locale": "en",
    "blog_enabled": True,
    "blog_posts_per_page": 6,
    "session_timeout": 30,
    "page_contact_visible": True,
    "page_faq_visible": True,
    "page_shipping_visible": True,
    "page_size_guide_visible": True,
    "page_stylist_visible": True,
    "page_lookbook_visible": True,
}

SHOP_DEFAULTS: Dict[str, Any] = {
    "shop_products_per_page": 12,
    "shop_default_sort": "newest",
    "shop_show_3d_badge": True,
    "shipping_domestic": 0,
    "shipping_international": 0,
    "free_shipping_threshold": 0,
}

NOTIFICATION_DEFAULTS: Dict[str, Any] = {
    "notif_new_order": True,
    "notif_pipeline": True,
    "notif_review": True,
    "notif_low_stock": True,
    "email_from_name": "ASIKO Boutique",
    "email_reply_to": "support@asikoboutique.com",
    "email_tracking_enabled": True,
    "email_unsubscribe_link": True,
    "email_footer_text": "ASIKO Boutique — Authentic Nigerian Fashion",
}

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

# Union of all defaults — used by templates via settings.X
DEFAULTS: Dict[str, Any] = {}
for _d in [STORE_PROFILE_DEFAULTS, BRAND_DEFAULTS, AI_DEFAULTS, CHATBOT_DEFAULTS,
           PAGE_DEFAULTS, SHOP_DEFAULTS, NOTIFICATION_DEFAULTS, SEO_DEFAULTS]:
    DEFAULTS.update(_d)


# ---------------------------------------------------------------------------
# Table config: name → (defaults_dict, cache_key)
# ---------------------------------------------------------------------------
_TABLES = {
    "store_profile": ("store_profile", STORE_PROFILE_DEFAULTS),
    "brand":         ("brand_settings",  BRAND_DEFAULTS),
    "ai":            ("ai_settings",     AI_DEFAULTS),
    "chatbot":       ("chatbot_settings", CHATBOT_DEFAULTS),
    "page":          ("page_settings",   PAGE_DEFAULTS),
    "shop":          ("shop_settings",   SHOP_DEFAULTS),
    "notification":  ("notification_settings", NOTIFICATION_DEFAULTS),
    "seo":           ("seo_settings",    SEO_DEFAULTS),
}

# Boolean keys per table (for type coercion on save)
_BOOL_KEYS: Dict[str, set] = {
    "store_profile": set(),
    "brand": set(),
    "ai": {"ai_stylist_enabled", "auto_mesh"},
    "chatbot": {"chatbot_enabled"},
    "page": {
        "blog_enabled", "page_contact_visible", "page_faq_visible",
        "page_shipping_visible", "page_size_guide_visible",
        "page_stylist_visible", "page_lookbook_visible",
    },
    "shop": {"shop_show_3d_badge"},
    "notification": {
        "notif_new_order", "notif_pipeline", "notif_review", "notif_low_stock",
        "email_tracking_enabled", "email_unsubscribe_link",
    },
    "seo": {
        "seo_structured_data", "seo_sitemap_enabled", "seo_robots_enabled",
        "geo_enabled", "aeo_faq_schema", "aeo_product_schema",
    },
}

_INT_KEYS: Dict[str, set] = {
    "ai": {"ai_max_tokens"},
    "page": {"about_founded_year", "blog_posts_per_page", "session_timeout"},
    "shop": {"shop_products_per_page"},
}

_FLOAT_KEYS: Dict[str, set] = {
    "ai": {"ai_temperature"},
    "shop": {"shipping_domestic", "shipping_international", "free_shipping_threshold"},
}


# ---------------------------------------------------------------------------
# PG literal helper
# ---------------------------------------------------------------------------
def _pg_literal(val: Any) -> str:
    """Convert a Python value to a PostgreSQL literal for embedding in SQL."""
    if val is True:
        return "TRUE"
    if val is False:
        return "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, dict):
        s = _json.dumps(val).replace("'", "''")
        return f"'{s}'::jsonb"
    s = str(val).replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


# ---------------------------------------------------------------------------
# Generic per-table read
# ---------------------------------------------------------------------------
async def _get_table(db_pool, table_key: str) -> Dict[str, Any]:
    """Read a single settings table into a dict, with TTL cache."""
    table_name, defaults = _TABLES[table_key]
    cache_key = table_key
    now = time.monotonic()
    if _caches[cache_key] is not None and (now - _cache_ts[cache_key]) < CACHE_TTL:
        return _caches[cache_key]

    result = dict(defaults)
    for attempt in range(2):
        try:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(f"SELECT * FROM {table_name} WHERE id = 1")
                if row:
                    row_dict = dict(row)
                    for key in defaults:
                        if key in row_dict and row_dict[key] is not None:
                            result[key] = row_dict[key]
            _caches[cache_key] = result
            _cache_ts[cache_key] = now
            return result
        except Exception as exc:
            if attempt == 0 and "cached statement" in str(exc).lower():
                continue
            logger.warning("[%s] DB fetch failed, using defaults: %s", table_name, exc)
            return result
    return result


# ---------------------------------------------------------------------------
# Generic per-table write — INSERT defaults + UPDATE payload columns only
# ---------------------------------------------------------------------------
def _coerce_literal(v: Any, is_bool: bool = False, is_int: bool = False,
                    is_float: bool = False) -> str:
    """Coerce a value to its PostgreSQL literal string."""
    if is_bool:
        bval = bool(str(v).lower() in ("true", "1", "on", "yes")) if v not in (None, "") else False
        return _pg_literal(bval)
    if is_int:
        try:
            return _pg_literal(int(v))
        except (ValueError, TypeError):
            return _pg_literal(0)
    if is_float:
        try:
            return _pg_literal(float(v))
        except (ValueError, TypeError):
            return _pg_literal(0.0)
    return _pg_literal(str(v) if v is not None else "")


async def _save_table(db_pool, table_key: str, payload: Dict[str, Any]) -> None:
    """Save settings to a table.  Two-step write:
    1. INSERT the singleton row with ALL column defaults (ON CONFLICT DO NOTHING).
    2. UPDATE only the columns present in *payload*.

    This prevents one section's save from resetting columns owned by another
    section that shares the same table (e.g. hero / lookbook / about all write
    to page_settings).
    """
    if not payload:
        return
    table_name, defaults = _TABLES[table_key]
    bool_keys = _BOOL_KEYS.get(table_key, set())
    int_keys = _INT_KEYS.get(table_key, set())
    float_keys = _FLOAT_KEYS.get(table_key, set())

    # --- Build UPDATE SET clauses (payload columns only) ---
    set_parts: list[str] = []
    for k, v in payload.items():
        lit = _coerce_literal(v, k in bool_keys, k in int_keys, k in float_keys)
        set_parts.append(f"{k} = {lit}")

    if not set_parts:
        return

    # --- Build INSERT with ALL defaults (ensures row exists) ---
    all_cols = list(defaults.keys())
    all_lits = []
    for k in all_cols:
        v = defaults[k]
        all_lits.append(_coerce_literal(v, k in bool_keys, k in int_keys, k in float_keys))

    cols_str = ", ".join(["id"] + all_cols)
    vals_str = ", ".join(["1"] + all_lits)
    sets_str = ", ".join(set_parts)

    insert_sql = (
        f"INSERT INTO {table_name} ({cols_str}, updated_at) "
        f"VALUES ({vals_str}, now()) ON CONFLICT (id) DO NOTHING"
    )
    update_sql = (
        f"UPDATE {table_name} SET {sets_str}, updated_at = now() WHERE id = 1"
    )

    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(insert_sql)
                await conn.execute(update_sql)
        invalidate_settings_cache()
    except Exception as exc:
        logger.error("[%s] save failed: %s", table_name, exc)
        raise


# ---------------------------------------------------------------------------
# Public API — get_settings() merges all tables
# ---------------------------------------------------------------------------
async def get_settings(db_pool) -> Dict[str, Any]:
    """Fetch all settings from all tables, merged into a single dict."""
    result = dict(DEFAULTS)
    for table_key in _TABLES:
        table_data = await _get_table(db_pool, table_key)
        result.update(table_data)
    return result


async def get_setting(db_pool, key: str) -> Any:
    """Fetch a single setting by key."""
    settings = await get_settings(db_pool)
    return settings.get(key)


# ---------------------------------------------------------------------------
# Public API — per-table save (called by admin_sections.py)
# ---------------------------------------------------------------------------
async def save_store_profile(db_pool, payload: Dict[str, Any]) -> None:
    await _save_table(db_pool, "store_profile", payload)

async def save_brand_settings(db_pool, payload: Dict[str, Any]) -> None:
    await _save_table(db_pool, "brand", payload)

async def save_ai_settings(db_pool, payload: Dict[str, Any]) -> None:
    await _save_table(db_pool, "ai", payload)

async def save_chatbot_settings(db_pool, payload: Dict[str, Any]) -> None:
    await _save_table(db_pool, "chatbot", payload)

async def save_page_settings(db_pool, payload: Dict[str, Any]) -> None:
    await _save_table(db_pool, "page", payload)

async def save_shop_settings(db_pool, payload: Dict[str, Any]) -> None:
    await _save_table(db_pool, "shop", payload)

async def save_notification_settings(db_pool, payload: Dict[str, Any]) -> None:
    await _save_table(db_pool, "notification", payload)

async def save_seo_settings(db_pool, payload: Dict[str, Any]) -> None:
    await _save_table(db_pool, "seo", payload)
