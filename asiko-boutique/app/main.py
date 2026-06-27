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
    Manages global application lifecycle resource allocation.
    For Vercel serverless: lightweight startup, migrations batched into single connection.
    For long-running servers: same behavior, just faster due to batching.
    """
    from app.database import init_db_pool, close_db_pool
    from app.realtime import manager as realtime_manager
    from app.migrations import run_migrations

    # 1. Initialize connection pool
    app.state.db_pool = await init_db_pool()
    logger.info("Database pool bound to app.state.db_pool.")

    # 2. Run schema enum + column additions (fast, single connection)
    async with app.state.db_pool.acquire() as conn:
        await conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'asset_category_type') THEN
                    CREATE TYPE asset_category_type AS ENUM ('apparel', 'footwear');
                END IF;
            END $$;
        """)
        await conn.execute("""
            ALTER TABLE products
            ADD COLUMN IF NOT EXISTS asset_category asset_category_type DEFAULT 'apparel';
        """)
    logger.info("LOG_SYSTEM: Database schema structural validation completed successfully.")

    # 3. Run all pending migrations in a single connection (batched for speed)
    await run_migrations(app.state.db_pool)

    # 4. Start Postgres LISTEN/NOTIFY listeners for real-time WebSocket broadcast
    realtime_manager.start_listeners(app.state.db_pool)
    logger.info("LOG_SYSTEM: Real-time WebSocket listeners started (pipeline, reviews, orders, stock).")

    try:
        yield
    finally:
        logger.info("LOG_SYSTEM: Shutting down web instance. Dismantling background processes safely...")
        await realtime_manager.stop_listeners()
        logger.info("LOG_SYSTEM: Real-time WebSocket listeners stopped.")
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
    from app.routes.admin_email import routes as admin_email_routes
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
    from app.routes.search import routes as search_routes
    from app.routes.seo import routes as seo_routes

    for route_list in [
        search_routes,
        seo_routes,
        storefront_routes,
        cart_routes,
        checkout_routes,
        webhook_routes,
        sse_routes,
        admin_auth_routes,
        admin_inventory_routes,
        admin_dashboard_routes,
        admin_sections_routes,
        admin_email_routes,
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
