# ASIKO Boutique - Starlette Application Core
# Lifespan manages async pool lifecycle; Mount-based routing for all modules.

import os
import time
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
load_dotenv()

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.types import ASGIApp

from app.core import templates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("asiko")

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


# ---------------------------------------------------------------------------
# NO-CACHE STATIC FILES HANDLER (anti-304 bypass for local dev hot-reload)
# ---------------------------------------------------------------------------
class NoCacheStaticFiles(StaticFiles):
    """StaticFiles with optional no-cache mode for development.

    In debug mode: forces fresh fetch on every request (no 304).
    In production: normal browser caching applies.
    """
    def __init__(self, *args, debug: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self._debug = debug

    def is_not_modified(self, response_headers: dict, request_headers: dict) -> bool:
        if self._debug:
            return False
        return super().is_not_modified(response_headers, request_headers)

    async def __call__(self, scope, receive, send) -> None:
        if not self._debug:
            return await super().__call__(scope, receive, send)
        async def intercepted_send(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"cache-control"] = b"no-cache, no-store, must-revalidate, max-age=0"
                headers[b"pragma"] = b"no-cache"
                headers[b"expires"] = b"0"
                message["headers"] = list(headers.items())
            await send(message)
        await super().__call__(scope, receive, intercepted_send)


# ---------------------------------------------------------------------------
# Homepage is defined in app/routes/storefront.py and registered via
# _register_route_modules(). The global_routes "/" entry is kept for
# backward compatibility but will be superseded by the module route.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Debug PDP endpoint — verifies template rendering with mock data
# ---------------------------------------------------------------------------

async def debug_root(request: Request):
    """Fallback root endpoint for local PDP testing verification."""
    mock_context = {
        "request": request,
        "concierge_token": "TEST_TOKEN_XYZ",
        "product": {
            "name": "The Architectural Blazer",
            "slug": "architectural-blazer",
            "collection_name": "Harmattan 2026",
            "base_price": 250000,
            "description": "A structural, sharp-shouldered silhouette crafted from hand-woven textiles.",
            "base_image": "https://placehold.co/600x800",
            "gallery_images": [
                {"url": "https://placehold.co/300x400"},
                {"url": "https://placehold.co/300x400"},
            ],
            "capsule_look": {
                "items": [
                    {
                        "default_variant_id": "var_123",
                        "name": "Tailored Column Trouser",
                        "price": 180000,
                        "image_url": "https://placehold.co/150x200",
                        "type": "Bottoms",
                    }
                ]
            },
        },
        "cart": {"item_count": 2, "total": 50000, "lines": []},
    }
    return templates.TemplateResponse(
        request, "storefront/product_detail.html", mock_context
    )


# ---------------------------------------------------------------------------
# Application Lifespan
# Sets app.state.db_pool from init_db_pool(); closes cleanly on shutdown.
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: Starlette) -> AsyncGenerator[None, None]:
    """
    Manages global application lifecycle resource allocation,
    guaranteeing relational schema structural sync loops on startup.
    """
    from app.database import init_db_pool, close_db_pool
    from app.realtime import manager as realtime_manager

    # 1. Initialize our high-throughput Neon Postgres connection cluster pool
    app.state.db_pool = await init_db_pool()
    logger.info("Database pool bound to app.state.db_pool.")

    # 2. SELF-HEALING SCHEMA GUARD: Verify and inject missing tracking definitions
    logger.info("LOG_SYSTEM: Running database structural validation checks...")
    async with app.state.db_pool.acquire() as conn:
        # Create asset_category enum type if it does not exist
        await conn.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'asset_category_type') THEN
                    CREATE TYPE asset_category_type AS ENUM ('apparel', 'footwear');
                END IF;
            END $$;
        """)
        
        # Inject the asset_category column into the products relation matrix safely
        await conn.execute("""
            ALTER TABLE products 
            ADD COLUMN IF NOT EXISTS asset_category asset_category_type DEFAULT 'apparel';
        """)
    logger.info("LOG_SYSTEM: Database schema structural validation completed successfully.")

    # Migration 23: password reset tokens table
    async with app.state.db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                token VARCHAR(64) NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS idx_prt_token ON password_reset_tokens(token);
            CREATE INDEX IF NOT EXISTS idx_prt_customer ON password_reset_tokens(customer_id);
        """)
    logger.info("LOG_SYSTEM: Migration 23 — password_reset_tokens table ready.")

    # Migration 24: add email settings columns to store_settings
    async with app.state.db_pool.acquire() as conn:
        for col in ["brevo_api_key", "sender_email", "sender_name", "admin_email"]:
            await conn.execute(
                f"ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS {col} VARCHAR(500) DEFAULT ''"
            )
        for col in ["email_welcome_enabled", "email_order_enabled", "email_shipping_enabled",
                     "email_newsletter_enabled", "email_password_reset_enabled"]:
            await conn.execute(
                f"ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT TRUE"
            )
    logger.info("LOG_SYSTEM: Migration 24 — email settings columns added.")

    # Migration 25: admin_users table for admin authentication
    async with app.state.db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255) DEFAULT '',
                role VARCHAR(50) DEFAULT 'admin',
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_admin_users_email ON admin_users(email);
        """)
        # Seed default admin account if none exists
        import hashlib, os as _os
        _salt = _os.environ.get("AUTH_SALT", "asiko-boutique-salt-2024")
        _hash = hashlib.sha256(f"{_salt}zerupthcode".encode()).hexdigest()
        await conn.execute("""
            INSERT INTO admin_users (email, password_hash, full_name, role)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (email) DO NOTHING
        """, "zerupth@gmail.com", _hash, "ASIKO Admin", "owner")
    logger.info("LOG_SYSTEM: Migration 25 — admin_users table ready. Default admin seeded.")

    # Migration 26: Add missing store_profile + notification columns to store_settings
    async with app.state.db_pool.acquire() as conn:
        for col, typ, default in [
            ("store_name",        "VARCHAR(255)", "'ASIKO Boutique'"),
            ("contact_email",     "VARCHAR(255)", "''"),
            ("store_description", "TEXT",         "''"),
            ("phone",             "VARCHAR(50)",  "''"),
            ("store_address",     "TEXT",         "''"),
            ("notif_new_order",   "BOOLEAN",      "TRUE"),
            ("notif_pipeline",    "BOOLEAN",      "TRUE"),
            ("notif_review",      "BOOLEAN",      "TRUE"),
            ("notif_low_stock",   "BOOLEAN",      "TRUE"),
            ("session_timeout",   "INT",          "60"),
        ]:
            try:
                await conn.execute(
                    f"ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS {col} {typ} DEFAULT {default}"
                )
            except Exception:
                pass
    logger.info("LOG_SYSTEM: Migration 26 — store_profile + notification columns added to store_settings.")

    # Migration 27: Seed AI Stylist training data
    try:
        async with app.state.db_pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM ai_training_data")
            if count == 0:
                await conn.execute("""
                    INSERT INTO ai_training_data (category, question, answer, is_active, sort_order) VALUES
                    ('brand', 'What is ASIKO?', 'ASIKO Boutique is a Nigerian fashion brand offering authentic, curated styles with transparent pricing. Every piece is crafted with verified provenance and fair-trade standards.', TRUE, 1),
                    ('brand', 'What does ASIKO mean?', 'ASIKO means "time" or "era" in Yoruba. It represents timeless fashion that transcends trends.', TRUE, 2),
                    ('brand', 'Where is ASIKO located?', 'ASIKO Boutique is based in Lagos, Nigeria. We ship nationwide across all 36 states and the FCT.', TRUE, 3),
                    ('brand', 'What makes ASIKO different?', 'We combine verified provenance, transparent pricing (no "DM for price"), and fair-trade standards. Every product shows its real price upfront.', TRUE, 4),
                    ('faq', 'Do you have physical stores?', 'Currently ASIKO operates online only at asikoboutique.com. We''re working on pop-up events in Lagos.', TRUE, 10),
                    ('faq', 'What sizes do you carry?', 'We carry sizes XS through XXL. Each product has a detailed size guide. Our AI Stylist can recommend the best size for your body type.', TRUE, 11),
                    ('faq', 'How do I track my order?', 'Once your order ships, you''ll receive an email with a tracking number. Check My Orders in your account anytime.', TRUE, 12),
                    ('faq', 'Can I return or exchange?', 'Yes! Returns and exchanges within 7 days of delivery. Items must be unworn with tags. Contact support@asikoboutique.com.', TRUE, 13),
                    ('style', 'What styles does ASIKO specialize in?', 'Contemporary Nigerian fashion: Ankara prints, Aso-Oke, Adire (tie-dye), solid-color modern pieces, and fusion styles blending heritage with global trends.', TRUE, 20),
                    ('style', 'How do I style for Nigerian weather?', 'Lightweight cotton/linen for dry season, breathable fabrics for rainy season, layerable pieces for harmattan. Our AI Stylist suggests outfits by location and season.', TRUE, 21),
                    ('style', 'What are popular outfit combinations?', 'Ankara top + solid skirt/trousers, Adire dress + leather accessories, Aso-Oke wrapper + modern blouse, solid agbada for men, mix-and-match separates.', TRUE, 22),
                    ('voice', 'How should the AI communicate?', 'Warm, friendly, knowledgeable — like a trusted fashion friend. Use Nigerian English naturally. Reference specific products. Use ₦ for prices.', TRUE, 30),
                    ('voice', 'What tone should the AI use?', 'Conversational, helpful, confident. Not robotic. Think of a knowledgeable boutique owner who genuinely cares about helping customers look their best.', TRUE, 31)
                """)
                logger.info("LOG_SYSTEM: Migration 27 — AI Stylist training data seeded (14 entries).")
            else:
                logger.info("LOG_SYSTEM: Migration 27 — AI Stylist training data already exists (%d entries).", count)
    except Exception as exc:
        logger.warning("LOG_SYSTEM: Migration 27 failed (non-fatal): %s", exc)

    # 3. Start Postgres LISTEN/NOTIFY listeners for real-time WebSocket broadcast
    realtime_manager.start_listeners(app.state.db_pool)
    logger.info("LOG_SYSTEM: Real-time WebSocket listeners started (pipeline, reviews, orders, stock).")

    try:
        yield
    finally:
        # Graceful teardown sequences on web application shutdown
        logger.info("LOG_SYSTEM: Shutting down web instance. Dismantling background processes safely...")

        # Stop real-time listeners
        await realtime_manager.stop_listeners()
        logger.info("LOG_SYSTEM: Real-time WebSocket listeners stopped.")

        # Close connection boundaries
        await close_db_pool()
        logger.info("Concurrency channels and database pools cleanly released.")


# ---------------------------------------------------------------------------
# Routing — Mount-based, all modules consolidated
# ---------------------------------------------------------------------------

from app.catalog.routes import routes as catalog_routes
from app.routes.luxury_extensions import luxury_routes as _all_luxury

# Split luxury routes: /catalog/* goes into Mount (strip prefix), others stay flat
_catalog_luxury = [
    Route(r.path[len("/catalog"):], endpoint=r.endpoint, methods=r.methods)
    for r in _all_luxury if r.path.startswith("/catalog")
]
_flat_luxury = [r for r in _all_luxury if not r.path.startswith("/catalog")]

global_routes = [
    Route("/test-pdp", debug_root, methods=["GET"]),
    Mount("/catalog", routes=catalog_routes + _catalog_luxury),
] + _flat_luxury


# ---------------------------------------------------------------------------
# Modular Route Registration
# ---------------------------------------------------------------------------

def _register_route_modules(app: Starlette) -> None:
    """Import and attach all route modules to the application after factory creation."""
    from app.routes.storefront import routes as storefront_routes
    from app.routes.cart import routes as cart_routes
    from app.routes.checkout import routes as checkout_routes
    from app.routes.webhooks import webhook_routes
    from app.routes.sse_streams import sse_routes
    from app.routes.admin_inventory import routes as admin_inventory_routes
    from app.routes.admin_dashboard import routes as admin_dashboard_routes
    from app.routes.admin_sections import routes as admin_sections_routes
    from app.routes.admin import routes as admin_crud_routes
    from app.routes.admin_auth import routes as admin_auth_routes
    from app.routes.waitlist import routes as waitlist_routes
    from app.routes.dpp_verification import routes as dpp_routes
    from app.routes.customer import routes as customer_routes
    from app.services.settlement import routes as settlement_routes
    from app.routes.ws_admin import ws_admin_routes
    from app.routes.ws_store import ws_store_routes
    from app.routes.fashion_chat import routes as fashion_chat_routes
    from app.routes.wardrobe import routes as wardrobe_routes

    for route_list in [
        storefront_routes,
        cart_routes,
        checkout_routes,
        webhook_routes,
        sse_routes,
        admin_auth_routes,
        admin_inventory_routes,
        admin_dashboard_routes,
        admin_sections_routes,
        admin_crud_routes,
        waitlist_routes,
        dpp_routes,
        customer_routes,
        settlement_routes,
        ws_admin_routes,
        ws_store_routes,
        fashion_chat_routes,
        wardrobe_routes,
    ]:
        app.routes.extend(route_list)


# ---------------------------------------------------------------------------
# Session Middleware
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Custom Pages Middleware — injects nav/footer pages into every request
# ---------------------------------------------------------------------------

class CustomPagesMiddleware:
    """Caches custom pages in-memory — 1 DB query every 30s instead of 2 per request."""

    _nav_pages: list = []
    _footer_pages: list = []
    _cache_ts: float = 0.0
    CACHE_TTL: int = 30

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope, receive, send)
        now = time.monotonic()
        if (now - self._cache_ts) >= self.CACHE_TTL:
            pool = getattr(request.app.state, "db_pool", None)
            if pool:
                try:
                    async with pool.acquire() as conn:
                        rows = await conn.fetch(
                            "SELECT title, slug, show_in_nav, show_in_footer FROM custom_pages "
                            "WHERE is_live = TRUE ORDER BY sort_order, title"
                        )
                    self._nav_pages = [{"title": r["title"], "slug": r["slug"]} for r in rows if r["show_in_nav"]]
                    self._footer_pages = [{"title": r["title"], "slug": r["slug"]} for r in rows if r["show_in_footer"]]
                    self._cache_ts = now
                except Exception:
                    pass
        request.state.nav_pages = self._nav_pages
        request.state.footer_pages = self._footer_pages
        return await self.app(scope, receive, send)

    def __init__(self, app: ASGIApp):
        self.app = app


# ---------------------------------------------------------------------------
# Admin Auth Middleware — redirects unauthenticated users to /admin/login
# ---------------------------------------------------------------------------

class AdminAuthMiddleware:
    """Protects /admin/* routes except /admin/login and /static/*."""

    _PUBLIC_PATHS = frozenset({"/admin/login", "/admin/logout"})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")

        # Only protect /admin/* routes
        if not path.startswith("/admin"):
            return await self.app(scope, receive, send)

        # Allow public admin paths (login page, logout)
        if path in self._PUBLIC_PATHS:
            return await self.app(scope, receive, send)

        # Allow static files under /admin
        if path.startswith("/static"):
            return await self.app(scope, receive, send)

        # Check session for admin_id
        request = Request(scope, receive, send)
        session = request.scope.get("session", {})
        if session.get("admin_id"):
            return await self.app(scope, receive, send)

        # Not authenticated — redirect to login
        from starlette.responses import RedirectResponse
        response = RedirectResponse("/admin/login", status_code=302)
        return await response(scope, receive, send)

    def __init__(self, app: ASGIApp):
        self.app = app


# ---------------------------------------------------------------------------
# Session Middleware + Admin Auth Middleware
# SessionMiddleware FIRST so it populates scope["session"] before AdminAuth reads it.
# In Starlette global_middleware list, first item = outermost (runs first).
# ---------------------------------------------------------------------------

global_middleware = [
    Middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY", "ASIKO_FALLBACK_SECURE_KEY_770X"),
        session_cookie="asiko_session",
        max_age=3600 * 24 * 7,
    ),
    Middleware(AdminAuthMiddleware),
]


# ---------------------------------------------------------------------------
# Initialize Starlette App Instance
# ---------------------------------------------------------------------------

app = Starlette(
    debug=True,
    lifespan=lifespan,
    routes=global_routes,
    middleware=global_middleware,
)

# Inject custom pages middleware after app creation
app.add_middleware(CustomPagesMiddleware)

_register_route_modules(app)
_is_debug = os.getenv("ASIKO_DEBUG", "true").lower() in ("true", "1", "yes")
app.routes.append(Mount("/static", app=NoCacheStaticFiles(directory=str(STATIC_DIR), debug=_is_debug), name="static"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
