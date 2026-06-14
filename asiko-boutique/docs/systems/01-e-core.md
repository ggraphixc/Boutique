# A. E-CORE SYSTEMS

## Overview

The E-Core systems form the foundation of ASIKO Boutique — the application runtime, database connectivity, settings management, shopping cart, checkout flow, and waitlist. Every other system depends on these 7 modules.

---

## 1. Application Core & Lifespan

**File:** `app/main.py` (337 lines)

### What It Does
The central Starlette ASGI application that boots the entire platform. Manages startup/shutdown lifecycle, registers all route modules, configures middleware, and serves static files.

### Key Components

#### App Factory
```python
app = Starlette(
    debug=True,
    lifespan=lifespan,
    routes=global_routes,
    middleware=global_middleware,
)
```
- Creates the ASGI application instance
- Binds lifespan handler for startup/shutdown
- Attaches session middleware (7-day signed cookie)
- Registers 17 route modules via `_register_route_modules()`

#### Lifespan Handler
```python
@asynccontextmanager
async def lifespan(app: Starlette):
    # STARTUP
    app.state.db_pool = await init_db_pool()           # 1. DB pool
    # Schema guard: auto-create asset_category_type     # 2. Schema validation
    # Migration 23: password_reset_tokens               # 3. Inline migration
    # Migration 24: email settings columns              # 4. Inline migration
    realtime_manager.start_listeners(app.state.db_pool) # 5. WebSocket listeners
    
    yield
    
    # SHUTDOWN
    await realtime_manager.stop_listeners()             # 1. Stop listeners
    await close_db_pool()                               # 2. Close DB pool
```

**Startup sequence:**
1. Initialize asyncpg connection pool (4-retry with exponential backoff)
2. Run schema guard — auto-create `asset_category_type` enum and column
3. Run inline migration 23 — create `password_reset_tokens` table
4. Run inline migration 24 — add email settings columns to `store_settings`
5. Start Postgres LISTEN/NOTIFY listeners for realtime WebSocket broadcast

**Shutdown sequence:**
1. Stop all Postgres LISTEN/NOTIFY background tasks
2. Close all database connections in the pool

#### Route Registration
```python
def _register_route_modules(app):
    # 17 route modules imported and attached:
    storefront, cart, checkout, webhooks, sse_streams,
    admin_inventory, admin_dashboard, admin_sections, admin,
    waitlist, dpp_verification, customer, settlement,
    ws_admin, ws_store, fashion_chat, wardrobe
```

#### NoCacheStaticFiles
```python
class NoCacheStaticFiles(StaticFiles):
    """Debug mode: forces fresh fetch (no 304). Production: normal caching."""
```
- Controlled by `ASIKO_DEBUG` env var
- Debug: Sets `Cache-Control: no-cache, no-store, must-revalidate`
- Production: Standard browser caching

#### CustomPagesMiddleware
```python
class CustomPagesMiddleware:
    """Caches custom pages in-memory — 1 DB query every 30s."""
    _nav_pages: list = []
    _footer_pages: list = []
    CACHE_TTL: int = 30
```
- Single DB query every 30 seconds (not per-request)
- Fetches live custom pages from `custom_pages` table
- Attaches `request.state.nav_pages` and `request.state.footer_pages`
- Templates use these to render dynamic nav/footer links

### Why It Matters
Without this module, nothing runs. It's the entry point that connects every other system together.

---

## 2. Shared Core Module

**File:** `app/core.py`

### What It Does
Single source of truth for template loading, Jinja2 custom filters, and session cart helpers used across all routes.

### Key Components

#### Template Engine
```python
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
```
- Loads all HTML templates from `app/templates/`
- Used by every route handler to render pages

#### Naira Currency Filter
```python
def naira(value):
    return f"₦{value:,.0f}"
```
- Custom Jinja2 filter: `{{ price|naira }}` → `₦25,000`
- Used in all product prices, order totals, shipping costs
- Always displays in Naira — never USD

#### Session Cart Helpers
```python
def get_cart_from_session(request) -> dict:
    """Returns cart from session or empty cart dict."""
    return request.session.get("cart", {"lines": [], "total": 0.0, "item_count": 0})

def save_cart_to_session(request, cart: dict):
    """Saves cart to session."""
    request.session["cart"] = cart
```

**Cart data shape:**
```python
{
    "lines": [
        {
            "product_id": "uuid",
            "variant_id": "uuid",
            "name": "Product Name",
            "price": 25000.0,
            "quantity": 2,
            "image": "/static/uploads/product.jpg"
        }
    ],
    "total": 50000.0,
    "item_count": 2
}
```

**Why `lines` not `items`?** Python's `dict.items()` method would collide with a key named `items`.

### Why It Matters
Every template render and every cart operation flows through this module. It's the shared utility layer.

---

## 3. Database Pool Manager

**File:** `app/database.py` (213 lines)

### What It Does
Manages the async PostgreSQL connection pool via asyncpg. Provides generic query executors and domain-specific query functions for products, orders, and shipping.

### Key Components

#### Pool Initialization (with Retry)
```python
async def init_db_pool() -> asyncpg.Pool:
    for attempt in range(4):
        try:
            _pool = await asyncpg.create_pool(
                dsn=database_url,
                min_size=2,           # Minimum connections
                max_size=10,          # Maximum connections
                command_timeout=60.0, # 60-second query timeout
                max_inactive_connection_lifetime=300.0,  # 5-minute idle timeout
            )
            return _pool
        except Exception as e:
            wait = 2 ** attempt * 2  # 2s, 4s, 8s, 16s
            await asyncio.sleep(wait)
```

**Why retry?** Neon Postgres serverless has cold starts. First connection may timeout. 4 attempts with exponential backoff handles this gracefully.

#### Generic Query Executors
```python
async def fetch_all(query, *args) -> list[Record]:    # SELECT multiple rows
async def fetch_one(query, *args) -> Optional[Record]: # SELECT single row
async def execute(query, *args) -> str:                 # INSERT/UPDATE/DELETE
async def execute_returning(query, *args) -> Optional[Record]: # INSERT/UPDATE RETURNING
```

#### Product Queries
```python
async def fetch_products() -> list[dict]           # All products
async def fetch_product_by_id(product_id) -> dict  # Single product
async def decrement_stock(product_id, qty) -> bool # Atomic stock decrement
```

#### Order Queries
```python
async def create_order(email, total, state, shipping, ref, metadata) -> dict
async def create_order_item(order_id, product_id, qty, price) -> bool
async def fetch_order_by_id(order_id) -> dict
async def fetch_order_items(order_id) -> list[dict]
async def update_order_status(order_id, status) -> bool
```

#### Shipping Queries
```python
async def fetch_shipping_cost(state_code) -> dict    # Single state cost
async def fetch_all_states() -> list[dict]           # All 37 states
```

### Connection Lifecycle
```
Startup: init_db_pool() → pool created (min=2, max=10)
Request: pool.acquire() → connection borrowed → query executed → connection released
Shutdown: close_db_pool() → all connections terminated
```

### Why It Matters
Every database operation in the entire application goes through this module. It's the data access layer.

---

## 4. Settings Service

**File:** `app/settings_service.py` (224 lines)

### What It Does
Centralized store settings with in-memory TTL cache. Reads from the `store_settings` singleton row (id=1) with comprehensive defaults for every configurable option.

### Key Components

#### Cache Layer
```python
_cache: Optional[Dict[str, Any]] = None
_cache_ts: float = 0.0
CACHE_TTL: int = 30  # seconds

def invalidate_settings_cache():
    global _cache, _cache_ts
    _cache = None
    _cache_ts = 0.0
```

#### Defaults Dictionary (60+ settings)
```python
DEFAULTS = {
    # Store profile
    "store_name": "ASIKO Boutique",
    "contact_email": "",
    "store_description": "",
    "phone": "",
    "store_address": "",
    
    # Currency / locale
    "currency": "NGN",
    "timezone": "Africa/Lagos",
    "locale": "en",
    
    # Shipping
    "shipping_domestic": 0,
    "shipping_international": 0,
    "free_shipping_threshold": 0,
    
    # AI provider
    "ai_provider": "openrouter",
    "ai_api_key": "",
    "ai_model": "google/gemini-2.0-flash-001",
    "ai_system_prompt": "",
    "ai_max_tokens": 1024,
    "ai_temperature": 0.7,
    
    # AI Stylist page
    "ai_stylist_enabled": True,
    "ai_stylist_welcome": "Hello! I'm your personal ASIKO fashion stylist...",
    "ai_stylist_suggestions": "What should I wear to a wedding?,...",
    
    # Homepage hero
    "hero_title": "Authentic",
    "hero_title_accent": "Nigerian Fashion",
    "hero_subtitle": "Shop curated styles...",
    "hero_badge_text": "New Collection Available",
    "hero_cta_text": "Shop Collection",
    "hero_cta_link": "#storefront",
    
    # Shop
    "shop_products_per_page": 12,
    "shop_default_sort": "newest",
    "shop_show_3d_badge": True,
    
    # Lookbook
    "lookbook_title": "The Lookbook",
    "lookbook_subtitle": "Curated ensembles...",
    
    # About
    "about_title": "ASIKO Boutique",
    "about_tagline": "Authentic Nigerian Fashion",
    "about_story": "ASIKO was founded with a mission...",
    "about_location": "Lagos, Nigeria",
    "about_email": "hello@asikoboutique.com",
    "about_founded_year": 2024,
    
    # Customer dashboard
    "customer_welcome_title": "Welcome back",
    "customer_welcome_subtitle": "Manage your orders...",
    
    # Chatbot widget
    "chatbot_enabled": True,
    "chatbot_welcome": "Hi! I'm your personal ASIKO stylist...",
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
}
```

#### Get Settings
```python
async def get_settings(db_pool) -> Dict[str, Any]:
    # 1. Check cache (30s TTL)
    # 2. If stale, fetch from DB
    # 3. Merge DB values over defaults
    # 4. Cache and return
```

#### Save Settings
```python
async def save_settings(db_pool, payload, partial=False):
    # Uses _pg_literal() for SQL embedding (not $N parameters)
    # Handles BOOLEAN_KEYS, INT_KEYS, FLOAT_KEYS type coercion
    # Upsert: INSERT ... ON CONFLICT (id) DO UPDATE SET ...
    # Invalidates cache after save
```

**Why raw SQL embedding?** asyncpg's prepared statement cache breaks with dynamic column INSERT/UPDATE. Column names are code-controlled (safe), string values are single-quote-escaped.

### Settings Categories
| Category | Settings | Configurable From |
|----------|----------|-------------------|
| Store Profile | name, email, description, phone, address | Admin Settings |
| Currency/Locale | currency, timezone, locale | Admin Settings |
| Shipping | domestic, international, free threshold | Admin Settings |
| AI Provider | provider, API key, model, prompt, tokens, temperature | Admin Settings |
| AI Stylist | enabled, welcome message, suggestions | Admin Settings |
| Homepage | title, accent, subtitle, badge, CTA text/link | Admin Settings |
| Shop | products per page, default sort, 3D badge | Admin Settings |
| Lookbook | title, subtitle | Admin Settings |
| About | title, tagline, story, location, email, year | Admin Settings |
| Customer Dashboard | welcome title/subtitle | Admin Settings |
| Chatbot | enabled, welcome, colors | Admin Settings |
| Pages/Blog | enabled, posts per page | Admin Settings |
| Email/Brevo | API key, sender, admin email, 5 toggles | Admin Settings |

### Why It Matters
Every page render reads settings. Without caching, every request would hit the database. The 30s TTL cache eliminates this overhead.

---

## 5. Shopping Cart System

**File:** `app/routes/cart.py`

### What It Does
Session-based HTMX cart with variant-level stock validation. Supports add, increment, decrement, remove, and drawer rendering.

### Routes
| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/cart/add` | `cart_add` | Add variant to cart |
| POST | `/cart/update` | `cart_update` | Modify quantity |
| GET | `/cart/drawer` | `cart_drawer` | Render cart sidebar |
| GET | `/cart/badge` | `cart_badge` | Render cart count badge |

### Add to Cart Flow
```
1. User clicks "Add to Cart" on product card
2. Form submits: product_id + variant_id (optional) + quantity
3. Cart handler:
   a. If variant_id missing → auto-select first in-stock variant
   b. Validate stock: SELECT stock_qty FROM product_variants WHERE id = $1
   c. If variant exists in cart → increment quantity
   d. Else → add new line
   e. Recalculate total and item_count
4. Save to session
5. Return HTMX response:
   - Swap #cart-badge (OOB swap)
   - Swap #cart-drawer-content
```

### Cart Data Shape
```python
{
    "lines": [
        {
            "product_id": "uuid",
            "variant_id": "uuid",
            "name": "Lagos Silk Blazer",
            "price": 85000.0,
            "quantity": 1,
            "image": "/static/uploads/prod_1.jpg"
        }
    ],
    "total": 85000.0,
    "item_count": 1
}
```

### Stock Validation
```python
# Before add/increment:
stock = await conn.fetchval(
    "SELECT stock_qty FROM product_variants WHERE id = $1",
    variant_id
)
if stock < requested_qty:
    return error response
```

### Cart Badge Fix
```html
<!-- Uses id="cart-badge" on <span> wrapper -->
<span id="cart-badge" class="...">
  {{ cart.item_count }}
</span>
```
- HTMX `hx-swap="outerHTML"` replaces entire element
- Renamed from `cart-counter` to avoid conflicts

### Why It Matters
The cart is the conversion funnel. Every sale flows through this system.

---

## 6. Checkout System

**File:** `app/routes/checkout.py` (239 lines)

### What It Does
Full checkout flow with atomic database transactions, 36-state Nigerian shipping, OPay payment initialization, and Brevo email dispatch.

### Routes
| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/checkout` | `checkout_page` | Render checkout form |
| GET | `/checkout/shipping-summary` | `shipping_summary` | HTMX dynamic shipping cost |
| POST | `/checkout/submit` | `checkout_submit` | Process order |
| GET | `/checkout/confirmation` | `checkout_confirmation` | Order confirmation |

### Checkout Submit Flow
```
1. Validate form data (name, email, phone, address, state)
2. Validate cart is not empty
3. Acquire DB connection
4. Resolve shipping cost from nigerian_states table
5. BEGIN ATOMIC TRANSACTION:
   a. SELECT FOR UPDATE on each variant (row-level lock)
   b. Validate stock for all items
   c. INSERT INTO orders (total, shipping, status='pending', email, metadata)
   d. INSERT INTO order_items for each line
   e. UPDATE product_variants SET stock_qty = stock_qty - qty
   f. COMMIT
6. Initialize OPay payment (card or bank transfer)
7. Send order confirmation email (async, Brevo)
8. Flush cart from session
9. Redirect to OPay payment page
```

### Atomic Stock Validation
```python
async with conn.transaction():
    for line in cart["lines"]:
        current_stock = await conn.fetchval(
            "SELECT stock_qty FROM product_variants WHERE id = $1 FOR UPDATE;",
            line["variant_id"]
        )
        if current_stock < line["quantity"]:
            return error  # Insufficient stock
```

**Why SELECT FOR UPDATE?** Prevents oversell when two customers buy the same variant simultaneously. Row-level lock ensures only one transaction can decrement at a time.

### 36-State Shipping Matrix
| State | Shipping Cost |
|-------|--------------|
| Lagos | ₦1,500 |
| Ogun, Oyo, Ondo, Osun, Ekiti | ₦2,000 |
| Abuja (FCT) | ₦2,000 |
| Enugu, Anambra, Imo, Abia, Ebonyi | ₦2,500 |
| Rivers, Delta, Bayelsa, Akwa Ibom, Cross River | ₦2,500 |
| Kano, Kaduna, Jigawa, Katsina, Kebbi, Sokoto, Zamfara | ₦3,000 |
| Borno, Yobe, Adamawa | ₦4,000 |

### Order Confirmation Email
```python
# After order creation:
try:
    await send_transactional_email(
        to_email=email,
        subject=f"ASIKO Boutique Confirmation - Order #{order_id}",
        html_content=email_body,
    )
except Exception:
    pass  # Never block checkout for email failure
```

### Why It Matters
This is where money changes hands. The atomic transaction ensures inventory integrity. The OPay integration enables real payments.

---

## 7. Waitlist System

**File:** `app/routes/waitlist.py`

### What It Does
Captures demand for out-of-stock variants. When a product goes out of stock, customers can join a waitlist to be notified when it's back.

### Route
| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/waitlist/join` | `waitlist_join` | Join waitlist for variant |

### Flow
```
1. Customer views out-of-stock product
2. Clicks "Join Waitlist"
3. Submits email
4. Handler:
   a. Validate email format
   b. INSERT INTO product_waitlists (variant_id, email)
      ON CONFLICT DO NOTHING (idempotent)
   c. Send confirmation email via Brevo
5. Show success message
```

### Idempotency
```sql
INSERT INTO product_waitlists (variant_id, email)
VALUES ($1, $2)
ON CONFLICT DO NOTHING
```
- Same email + same variant → no duplicate entry
- Safe to click "Join Waitlist" multiple times

### Batch Restock Notification
```python
# Admin triggers via POST /admin/dashboard/notify-waitlist
async def notify_waitlist(variant_id):
    waitlisted = await conn.fetch(
        "SELECT email FROM product_waitlists WHERE variant_id = $1",
        variant_id
    )
    for entry in waitlisted:
        await send_brevo_email(
            to_email=entry["email"],
            subject="Back in Stock!",
            html_content=restock_html
        )
```

### Why It Matters
Captures lost sales. Without a waitlist, out-of-stock items just lose customers. With it, you have a list of warm leads ready to buy.

---

## Summary

| System | File | Lines | Key Feature |
|--------|------|-------|-------------|
| Application Core | `app/main.py` | 337 | Lifespan, middleware, route registration |
| Shared Core | `app/core.py` | ~50 | Templates, ₦ filter, session helpers |
| Database Pool | `app/database.py` | 213 | asyncpg pool with retry, query executors |
| Settings Service | `app/settings_service.py` | 224 | 60+ settings, 30s TTL cache |
| Shopping Cart | `app/routes/cart.py` | ~150 | Session-based HTMX cart with stock validation |
| Checkout | `app/routes/checkout.py` | 239 | Atomic transactions, OPay, Brevo email |
| Waitlist | `app/routes/waitlist.py` | ~50 | Idempotent demand capture |

**Total: ~1,200 lines of code powering the e-commerce foundation.**
