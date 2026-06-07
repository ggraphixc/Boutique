# ASIKO Boutique - Starlette Application Core
# Lifespan manages async pool lifecycle; Mount-based routing for all modules.

import os
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

from app.core import templates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("asiko")

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


# ---------------------------------------------------------------------------
# NO-CACHE STATIC FILES HANDLER (anti-304 bypass for local dev hot-reload)
# ---------------------------------------------------------------------------
class NoCacheStaticFiles(StaticFiles):
    """
    Custom StaticFiles handler that completely intercepts caching handshakes,
    forcing the browser to drop 304 validations and fetch fresh code updates
    on every request. Used in development to prevent stale 3D engine code
    (atelier-3d.js) and CSS from being served from the browser cache after
    edits.

    Two-layer enforcement:
      1. is_not_modified() always returns False → disables Starlette's
         If-Modified-Since / If-None-Match 304 short-circuit
      2. __call__() intercepts the http.response.start message and injects
         aggressive cache-invalidation headers (Cache-Control, Pragma,
         Expires) on every response
    """
    def is_not_modified(self, response_headers: dict, request_headers: dict) -> bool:
        # Forcing False completely deactivates the 304 Not Modified optimization path
        return False

    async def __call__(self, scope, receive, send) -> None:
        async def intercepted_send(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                # Inject aggressive cache invalidation control vectors
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
# Binds the 3D pipeline daemon to application lifecycle.
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: Starlette) -> AsyncGenerator[None, None]:
    """
    Manages global application lifecycle resource allocation,
    guaranteeing relational schema structural sync loops on startup.
    """
    import asyncio
    from app.database import init_db_pool, close_db_pool
    from app.workers.pipeline_daemon import AsikoPipelineDaemon

    # 1. Initialize our high-throughput Neon Postgres connection cluster pool
    app.state.db_pool = await init_db_pool()
    logger.info("Database pool bound to app.state.db_pool.")

    # 2. SELF-HEALING SCHEMA GUARD: Verify and inject missing tracking definitions
    print("LOG_SYSTEM: Running database structural validation checks...")
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
    print("LOG_SYSTEM: Database schema structural validation completed successfully.")

    # 3. Instantiate and launch our autonomous 3D pipeline background daemon
    daemon = AsikoPipelineDaemon(db_pool=app.state.db_pool)
    app.state.pipeline_daemon = daemon

    # Spawn the persistent loop as a non-blocking concurrent task on the event loop
    daemon_task = asyncio.create_task(daemon.start_loop(check_interval_seconds=10))
    print("LOG_SYSTEM: ÀSÌKÒ 3D Pipeline Daemon successfully mounted to application lifespan thread.")

    try:
        yield
    finally:
        # 4. Graceful teardown sequences on web application shutdown
        print("LOG_SYSTEM: Shutting down web instance. Dismantling background processes safely...")
        daemon.is_running = False
        daemon_task.cancel()
        try:
            await daemon_task
        except asyncio.CancelledError:
            pass

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
    from app.routes.waitlist import routes as waitlist_routes
    from app.routes.virtual import routes as virtual_routes
    from app.routes.virtual_experience import routes as virtual_experience_routes
    from app.routes.dpp_verification import routes as dpp_routes
    from app.services.settlement import routes as settlement_routes

    for route_list in [
        storefront_routes,
        cart_routes,
        checkout_routes,
        webhook_routes,
        sse_routes,
        admin_inventory_routes,
        admin_dashboard_routes,
        admin_sections_routes,
        admin_crud_routes,
        waitlist_routes,
        virtual_routes,
        virtual_experience_routes,
        dpp_routes,
        settlement_routes,
    ]:
        app.routes.extend(route_list)


# ---------------------------------------------------------------------------
# Session Middleware
# ---------------------------------------------------------------------------

global_middleware = [
    Middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY", "ASIKO_FALLBACK_SECURE_KEY_770X"),
        session_cookie="asiko_session",
        max_age=3600 * 24 * 7,
    )
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

_register_route_modules(app)
app.routes.append(Mount("/static", app=NoCacheStaticFiles(directory=str(STATIC_DIR)), name="static"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
