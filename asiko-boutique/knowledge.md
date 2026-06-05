# ASIKO Boutique - Project Knowledge Base

## Overview

ASIKO Boutique is a single-brand luxury e-commerce platform for Nigerian fashion retail. Built with Python/Starlette (edge) + Django (data ledger), it eliminates physical commercial lease costs, generator fuel expenses, and manual social-commerce transfer fraud.

---

## Architecture

### Tech Stack
- **Edge Runtime:** Python 3.14 with Starlette 1.0 (async HTTP, Jinja2, HTMX, Alpine.js)
- **Data Ledger:** Django 6.0 (ORM models, admin, cryptographic signing, validations)
- **Database:** PostgreSQL via asyncpg (edge) + psycopg2 (Django) sharing single Neon cluster
- **Templates:** Jinja2 with HTMX for server-driven interactivity, Alpine.js for client state
- **Styling:** Tailwind CSS via CDN (design tokens: `#0D2A22`, `#D4AF37`, `#FBF9F6`)
- **Sessions:** Server-side with Starlette SessionMiddleware
- **Email:** Brevo SMTP API for transactional notifications + waitlist alerts
- **Payments:** Paystack webhook integration (HMAC-SHA512 verification)

### Directory Structure
```
asiko-boutique/
├ .env                              # DATABASE_URL, BREVO_API_KEY, PAYSTACK_SECRET_KEY
├ manage.py                         # Django CLI entry point
├ requirements.txt                  # starlette, django, asyncpg, httpx, python-dotenv, etc.
├ knowledge.md
├ design.md
├ config/
│   ├── __init__.py                 # DJANGO_SETTINGS_MODULE env setup
│   └── settings.py                 # Django config (DB, apps, timezone)
├ apps/
│   ├── __init__.py
│   └── boutique_core/
│       ├── __init__.py
│       └── models.py               # MeasurementVault, AllocationWindow, concierge signer
├ supabase/
│   └── migrations/
│       ├── 01_init_schema.sql      # stores, products, orders, order_items, nigerian_states
│       ├── 02_reservations.sql     # product_variants, product_reservations
│       ├── 03_waitlist.sql         # product_waitlists (out-of-stock enrollment)
│       ├── 04_luxury_core.sql      # measurement_vault, concierge telemetry, capsule, allocation
│       ├── 04_dpp_ledger.sql       # Digital Product Passport provenance columns + serialized passports
│       ├── 05_single_brand.sql     # Consolidated to single ASIKO store
│       ├── 06_schema_alignment.sql # payload_metadata, session_identifier, mock tables
│       └── 07_gltf_columns.sql      # model_3d_url, mesh_node_identifier, custom_shader_color
├ run_migration_07.py                # Migration 07 runner (DATABASE_URL from .env)
├ run_migration_all.py               # Consolidated runner for migrations 01-07
├ static/
│   ├── js/
│   │   └── atelier-3d.js              # Full Three.js engine: body-morph, multi-layer garment rendering, GLTFLoader, WebXR/AR, procedural fallbacks
│   ├── models/
│   │   ├── architectural-blazer.glb   # Procedural blazer (16-34 KB)
│   │   ├── draped-silhouette-gown.glb # Procedural gown
│   │   ├── tailored-column-trouser.glb # Procedural trouser
│   │   ├── mesh_dress_lux.glb         # Dressing room dress
│   │   ├── mesh_jacket_cyber.glb      # Dressing room cyber blazer
│   │   ├── mesh_trouser_tapered.glb   # Dressing room trouser
│   │   ├── mesh_top_structural.glb    # Dressing room shell top
│   │   ├── PIPELINE.md                # 3D model pipeline docs (export specs, tools, verification)
│   │   └── README.md                  # Model naming conventions
│   ├── css/
│   └── images/
├ scripts/
│   └── generate_glb_models.py         # Pure-stdlib Python GLB generator (7 garment shapes, _lathe_profile revolve)
├ app/
│   ├── __init__.py
│   ├── core.py                     # Templates, naira filter, session helpers (single source of truth)
│   ├── main.py                     # App factory: load_dotenv, Mount-based routing, lifespan, middleware
│   ├── database.py                 # os.getenv, asyncpg pool lifecycle + SQL queries (min=2, max=10)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── brevo.py                # Brevo API wrapper (send_transactional_email, sync_to_audience)
│   │   ├── settlement.py           # Paystack HMAC, 36-state matrix, reservation worker, Brevo dispatch
│   │   └── dpp_crypto.py           # Digital Product Passport signing service (Signer salt: asiko.concierge.vector)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── storefront.py           # Homepage, PDP with capsule lookups, concierge signing, HTMX grid
│   │   ├── cart.py                 # HTMX cart add/update/drawer (uses "lines" key)
│   │   ├── checkout.py             # 36-state shipping, order creation, email triggers
│   │   ├── webhooks.py             # Order status webhook, Brevo email orchestration, test-email
│   │   ├── admin.py                # Admin CRUD: products table, delete, detail view, settings panel
│   │   ├── admin_inventory.py      # Omnichannel Stock Sentinel (SELECT FOR UPDATE)
│   │   ├── admin_dashboard.py      # Executive dashboard: metrics, inline stock, waitlist trigger
│   │   ├── waitlist.py             # Out-of-stock waitlist enrollment + restock worker
│   │   ├── luxury_extensions.py    # Atelier, Concierge, Capsule, Allocation endpoints (DB-backed)
│   │   ├── dpp_verification.py     # Avatar profile binding endpoint (target_skeleton_fit)
│   │   └── catalog/               # Session-based catalog interaction engine
│   │       ├── __init__.py
│   │       └── routes.py           # 4 PDP endpoints: allocation, atelier, concierge, capsule
│   ├── templates/
│   │   ├── base.html               # Global layout (Tailwind/HTMX/Alpine CDN, nav, #cart-counter OOB target, cart drawer)
│   │   ├── admin/
│   │   │   ├── base.html           # Control Center sidebar + workspace layout
│   │   │   └── products_table.html   # Catalog assets ledger with edit/delete actions
│   │   ├── storefront/
│   │   │   ├── index.html          # Homepage product grid
│   │   │   ├── product_detail.html # Editorial PDP: allocation, atelier, capsule, concierge (catalog routes)
│   │   │   └── product_grid.html   # HTMX fragment for product cards
│   │   ├── storefront/
│   │   │   └── dpp_verification.html  # Digital Product Passport verification page
│   │   ├── cart/
│   │   │   ├── cart_badge.html     # HTMX fragment for cart count badge
│   │   │   └── cart_content.html   # HTMX fragment for cart drawer content
│   │   ├── checkout/
│   │   │   ├── index.html          # Checkout form (36-state dropdown)
│   │   │   ├── shipping_summary.html  # HTMX fragment for shipping calc
│   │   │   └── confirmation.html   # Order confirmation page
│   │   └── components/
│   │       └── shoppable_lookbook.html  # Interactive lookbook with hotspots
│   └── tests/
│       ├── __init__.py
│       ├── test_catalog.py         # 12 integration tests for all 4 PDP features
│       ├── test_flow.py          # 15 tests covering lifespan, storefront, cart, dashboard, admin, waitlist, checkout
│       ├── test_dpp.py           # Digital Product Passport cryptographic verification suite (13 tests)
│       ├── test_avatar_flows.py  # Avatar fit axis integration tests (12 tests)
│       └── test_admin_crud.py    # Admin panel security and lifecycle tests (9 tests)
```

---

## Core Systems

### 1. Cart Session Management
- **Storage:** Server-side session (signed cookie via SessionMiddleware)
- **Data Shape:** `{"lines": [...], "total": float, "item_count": int}`
  - Uses `lines` key (not `items`) to avoid conflict with Python's `dict.items()`
  - Line item shape: `{"variant_id", "product_id", "name", "price", "quantity", "size", "color", "image_url"}`
- **Functions (app/core.py):**
  - `get_cart_from_session(request)` - Retrieve cart from session
  - `save_cart_to_session(request, cart)` - Persist cart to session
- **Handlers (app/routes/cart.py):**
  - `_recalculate_cart(cart)` - Recalculate total and item_count from lines
  - `cart_add(request)` - POST: validates stock via `product_variants.stock_qty`, adds variant, returns badge fragment with OOB error on oversell
  - `cart_update(request)` - POST: increment/decrement/remove by `variant_id`, validates stock on increment
  - `cart_drawer(request)` - GET: HTMX fragment for cart drawer content
- **HTMX Pattern:** `hx-post="/cart/add"` → `hx-target="#cart-badge"` → `hx-swap="outerHTML"`
- **Stock Validation:** Queries `product_variants.stock_qty` before add/increment; rejects with OOB error div if insufficient

### 2. Single-Brand Product Catalog
- **Stores table:** 1 row — ASIKO (slug: `asiko`, email: `hello@asikoboutique.com`)
- **Products table:** id, store_id (FK → stores), name, description, price, stock_quantity, base_image
- **Product Variants table:** id, product_id (FK), size, color, stock_qty
- **Queries:**
  - `fetch_products()` - All products (no store JOIN needed)
  - `fetch_product_by_id(product_id)` - Single product by ID

### 3. Omnichannel Stock Sentinel
- **Reservation table:** `product_reservations` (variant_id, quantity, status, created_at, session_identifier)
- **Atomic operations:** `SELECT FOR UPDATE` row locking on `product_variants.stock_qty` prevents oversell
- **Endpoints (app/routes/admin_inventory.py):**
  - `POST /admin/reserve` - Admin stock hold with row-level lock, inserts reservation with status='staged'
  - `POST /admin/settle` - Flush stale holds: `UPDATE ... WHERE status='staged' AND created_at < NOW() - INTERVAL '60 minutes'`
  - `GET /admin/reservations` - Live HTML ledger of last 25 reservations with status colors
- **Direct pool access:** Uses `request.app.state.db_pool` directly (not `database.py` helpers)

### 4. Out-of-Stock Waitlist Engine
- **Table:** `product_waitlists` (email, variant_id, notified, created_at) with `UNIQUE(email, variant_id)`
- **Endpoint (app/routes/waitlist.py):** `POST /waitlist/join` - Idempotent enrollment via `ON CONFLICT (email, variant_id) DO NOTHING`
- **Email validation:** Regex pattern before database staging
- **Brevo Integration:** `send_transactional_email()` with graceful fallback on network failures
- **Response:** HTML-only inline swap replacing the "Sold Out" form with confirmation message
- **Direct pool access:** Uses `request.app.state.db_pool` directly

### 5. 36-State Shipping Matrix
- **Database table:** `nigerian_states` (code, name, shipping_cost, weight_factor)
- **Shipping costs range:** ₦1,500 (Lagos) to ₦4,000 (Borno, Yobe)
- **HTMX integration:** State dropdown → `hx-get="/checkout/shipping-summary"` → swaps cost span

### 6. Checkout Flow
- **Form fields:** first_name, last_name, email, phone, address, state (dropdown)
- **Atomic transaction:** `async with conn.transaction()` → `SELECT ... FOR UPDATE` row locking on `product_variants.stock_qty` before order creation
- **Order creation:** INSERT order → INSERT order_items → UPDATE product_variants (stock_qty decrement) → flush cart → redirect
- **Email triggers:** Customer confirmation via Brevo `send_transactional_email()` with graceful fallback on placeholder API keys
- **Metadata:** Stored as JSONB `{"customer_name", "phone", "address", "state"}`
- **Confirmation:** Order ID stored in `request.session["last_order_id"]`, rendered on `/checkout/confirmation`

### 7. Brevo Email Integration
- **Config:** `BREVO_API_KEY` and `SENDER_EMAIL` in .env
- **Email types:** Order confirmation, admin notification, status change, waitlist confirmation, restock notification
- **Graceful degradation:** Emails skipped if API key is placeholder
- **Debug endpoint:** `POST /webhooks/test-email` with `{"email": "..."}`

### 8. Settlement Engine & Payment Processing
- **Package:** `app/services/settlement.py` — payment verification, shipping matrix, background workers
- **Paystack Webhook:** `POST /payments/webhook` — HMAC-SHA512 signature verification against raw body
- **36-State Shipping Matrix:** `SHIPPING_MATRIX` dict — Lagos/Abuja ₦1,500; regional ₦2,500–₦4,000
- **Background Worker:** `purge_expired_reservations()` via `asyncio.create_task` (not Starlette BackgroundTasks) to avoid TestClient hangs
- **Brevo Dispatch:** `dispatch_luxury_alert_email()` — graceful fallback when API key is placeholder
- **Flow:** Verify HMAC → parse charge.success → update reservations to 'paid' → async email dispatch

### 9. Catalog Interaction Engine (Session-Based)
- **Package:** `app/catalog/routes.py` — standalone PDP feature endpoints, zero DB dependency
- **State:** All stored in encrypted cookies via `request.session` (no Redis, no DB)
- **OOB Pattern:** Capsule endpoint returns inline `<div>` + `hx-swap-oob="true"` `<div>` to update nav cart counter without page reflow
- **Endpoints:**
  - `GET /catalog/allocation/{slug}` - Mock 3-unit allocation gatekeeper with gold `animate-ping` pulse
  - `POST /catalog/atelier/bind` - Session-bound body measurements (chest/waist/hips + unit)
  - `GET /catalog/concierge/redirect` - WhatsApp API 303 redirect with token in URL
  - `POST /catalog/cart/capsule` - Bulk variant add with deduplication, OOB cart counter swap
- **Path Note:** Atelier uses `/catalog/atelier/bind` (not `/catalog/waitlist`) to avoid collision with the DB-backed waitlist enrollment endpoint

---

## Luxury Extensions (4 Features)

**Shared Architecture:** All endpoints use `request.app.state.db_pool` (set in main.py lifespan). Django `Signer(salt="asiko.concierge.vector")` initialized at module level with `django.setup()`.

### Feature 1: Digital Atelier
- **DB Table:** `asiko_measurement_vault` (session_key UNIQUE, chest/waist/hips with CHECK constraints)
- **DB Endpoint:** `POST /atelier/measurements` - Accepts cm/in, converts to cm, upserts by session cookie (luxury_extensions.py)
- **Session Endpoint:** `POST /catalog/atelier/bind` - Session-bound measurements, zero DB (catalog/routes.py)
- **PDP Integration:** Alpine.js accordion (`x-data="{ open: false, display_unit: 'cm' }"`), `x-collapse`, dynamic placeholders (cm: 96/82/102, in: 38/32/40), `hx-post="/catalog/atelier/bind"` → `hx-swap="outerHTML"`

### Feature 2: WhatsApp Concierge Bridge
- **DB Telemetry:** `telemetry_concierge_clicks` table logs every redirect
- **DB Endpoint:** `GET /catalog/concierge/bridge?token=<signed>` - Django Signer verification + DB telemetry (luxury_extensions.py)
- **Session Endpoint:** `GET /catalog/concierge/redirect?token=<token>` - WhatsApp 303 redirect, no DB (catalog/routes.py)
- **Signing:** Module-level `Signer(salt="asiko.concierge.vector")` with `django.setup()` at import time
- **PDP Integration:** `<a href="/catalog/concierge/redirect?token={{ concierge_token }}">` — standard link with 303 redirect

### Feature 3: Capsule Matrix ("Complete the Ensemble")
- **DB Table:** `product_reservations` (variant_id, quantity, status, created_at)
- **DB Endpoint:** `POST /catalog/capsule/add-bundle` - Atomic bulk variant reservation via `conn.transaction()` (luxury_extensions.py)
- **Session Endpoint:** `POST /catalog/cart/capsule` - Session `cart_items` list with deduplication, OOB swap
- **PDP Integration:** Form with `{% for item in product.capsule_look['items'] %}` loop, checked checkboxes (`name="variant_ids"`), `hx-target="#capsule-status-msg"`, button text "Deploy Selected Wardrobe Elements to Bag"

### Feature 4: Tiered Allocation Engine
- **DB Table:** `asiko_allocation_windows` (target_product_id UNIQUE, tier_level_required, start/end_time, max/allocated_units)
- **Gatekeeper Endpoint:** `GET /products/{slug}/preorder` - Checks tier, time window, remaining capacity
- **Secure Endpoint:** `POST /catalog/preorder/secure` - `SELECT FOR UPDATE` → increment allocated_units (slug from form data)
- **PDP Integration:** HTMX `hx-trigger="load"` on page load → shows skeleton → swaps to allocation status
- **Django Model:** `AllocationWindow` with `is_active` and `spots_remaining` properties

### PDP Template Context Shape
The `product_detail.html` template expects this context from the route handler:
```python
{
    "product": {
        "name": str,
        "slug": str,                    # Used in allocation hx-get
        "collection_name": str,         # Displayed as gold mono label
        "base_price": int,              # Formatted as ₦{:,}
        "description": str,
        "base_image": str,              # Hero image URL
        "gallery_images": [{"url": str}],  # 2-col thumbnail loop
        "capsule_look": {
            "items": [{"default_variant_id": str, "name": str, "price": int, "image_url": str, "type": str}]
        }
    },
    "concierge_token": str,             # Pre-signed token for WhatsApp redirect
    "cart": {"item_count": int, "total": float, "lines": list}
}
```
Note: Template uses `product.base_price if product.base_price is defined else product.price` for backward compatibility with the legacy products table.

---

## Database Schema

### Migration 01: Core Tables
- **stores** - Multi-vendor store definitions
- **products** - Product catalog with store FK
- **orders** - Customer orders with JSONB metadata
- **order_items** - Line items with product FK
- **nigerian_states** - 37 rows (36 states + FCT) with shipping costs

### Migration 02: Reservations
- **product_variants** - Size/color variants per product (48 seeded variants)
- **product_reservations** - Active stock holds with status tracking

### Migration 03: Waitlist
- **product_waitlists** - Email + variant enrollment, UNIQUE(email, variant_id), notified flag

### Migration 04: Luxury Core
- **asiko_measurement_vault** - Body measurements with session_key UNIQUE, CHECK constraints
- **telemetry_concierge_clicks** - Click analytics for WhatsApp bridge
- **asiko_capsule_looks** - Curated look definitions
- **asiko_capsule_assignments** - Product-to-look mappings
- **asiko_allocation_windows** - Tiered pre-order gates with time windows

### Migration 05: Single Brand Refactor
- **stores** - Consolidated to single ASIKO store (slug: `asiko`)
- **products** - All products reassigned to ASIKO store
- **Removed:** Multi-vendor architecture, store owner notifications, `/stores` and `/store/{slug}` routes

### Migration 06: Schema Alignment
- **telemetry_concierge_clicks** - Added `payload_metadata` column (TEXT)
- **product_reservations** - Added `session_identifier` column (VARCHAR)
- **mock_products** - SERIAL products table for allocation test suite
- **mock_allocation_windows** - SERIAL allocation windows with seed data
- **mock_product_reservations** - VARCHAR-based reservations for test suite

### Migration 07: 3D GLTF Columns
- **products** — Added `model_3d_url` (VARCHAR 512) — path to `.glb` asset in `static/models/`
- **product_variants** — Added `mesh_node_identifier` (VARCHAR 100) — sub-mesh node name for GLTFLoader material binding
- **product_variants** — Added `custom_shader_color` (VARCHAR 7) — hex color override for WebGL custom materials
- **product_variants** — Added `morph_target_index` (INTEGER, default 0) — target parametric coordinate maps for morph animations
- **products** — Added `apparel_layer_depth` (INTEGER, default 1) — multi-layer sorting sequences for capsule looks
- **products** — Added `model_usdz_url` (VARCHAR 512, nullable) — standalone spatial binary for Apple AR Quick Look
- **Seed:** Sets `model_3d_url` on 4 products (Lagos Silk Blazer → `architectural-blazer.glb`, Aba Handloomed Trousers → `tailored-column-trouser.glb`, Adire Tie-Dye Dress + Atelier Drape Dress → `draped-silhouette-gown.glb`)
- **Variant metadata:** Seeds `mesh_node_identifier` and `custom_shader_color` on all variants of those 4 products, with color-dependent shader colors
- **Runner:** `python run_migration_07.py` or `python run_migration_all.py` (runs 01-07 in order)

### Phase 8: Gradio OSS Pipeline Migration (June 2026)
- **Open-Source Infrastructure:** Replaced paid Meshy API with free Hugging Face Gradio client (`TencentARC/InstantMesh`)
- **No API Keys Required:** Zero-cost 3D pipeline using public HF inference endpoints
- **Pipeline Daemon (`app/workers/pipeline_daemon.py`):**
  - Connects to `TencentARC/InstantMesh` Gradio space on initialization
  - Polls `products WHERE pipeline_status = 'queued'` every 5 seconds
  - Uses positional parameters: `image`, `Remove Background=true`, `Seed=42`, `Steps=30`
  - Fallback to `static/models/avatar_female.glb` when HF endpoint is unavailable
- **SSE Stream (`app/routes/sse_streams.py`):** Real-time pipeline status via `/api/v1/streams/pipeline/{product_id:uuid}`
  - 2-second polling loop for DB status updates
  - Breaks on terminal states (`completed`, `failed`)
- **Auto-Framing Avatar (`static/js/atelier-3d.js`):**
  - `loadBaseAvatar(avatarUrl)` method computes bounding box on GLTF load
  - Enforces uniform 1.8-unit height scale normalization
  - Centers model at origin (y=0 ground alignment)
  - Camera auto-framed at 1.4x distance buffer for clean canvas bounds
- **Deprecated Endpoints:**
  - `/api/v1/webhooks/meshy` — Returns acknowledgment only (Gradio pipeline is synchronous, no webhook needed)
- **Self-Healing Schema Guard (`app/main.py` lifespan):**
  - Auto-creates `asset_category_type` enum (values: `apparel`, `footwear`)
  - Auto-adds `asset_category` column to `products` table if missing

### Seed Data
- **1 store:** ASIKO (slug: `asiko`, email: `hello@asikoboutique.com`)
- **6 products:** ₦8,500 - ₦85,000 price range
- **37 states:** All Nigerian states + FCT with shipping costs
- **48 variants:** 6 products × 4 sizes × 2 colors

---

## Digital Product Passport (DPP) Security & Authentication Suite

### I. Database Ledger Migration (supabase/migrations/04_dpp_ledger.sql)
- **DPP Columns added to products:** `fabric_lineage`, `processing_dye_vector`, `living_wage_index` for provenance tracking
- **Serialized Passports Table:** `product_serialized_passports` (serial_number PK, product_id FK, artisan_identifier, manufactured_at) with indexes on product_id and artisan_identifier
- **Purpose:** Anchors verifiable garment provenance data with unique serial tracking

### II. Cryptographic Signing Service (app/services/dpp_crypto.py)
- **DPP Service:** Singleton `DPPCryptoService` using Django `Signer(salt="asiko.concierge.vector")`
- **Token Generation:** `generate_passport_token(product_id, serial_number, artisan_id)` → JSON payload + cryptographic signature
- **Token Verification:** `verify_passport_token(token)` → Validates signature, returns decoded payload or None on tamper/BadSignature
- **Design:** Stateless class with lazy Django settings initialization; zero DB dependency

### III. Verification Suite (app/tests/test_dpp.py)
- **13 pytest tests** covering: token generation/verification, tamper resistance (suffix/prefix/corruption), empty/garbage token handling, singleton behavior, token structure validation, large IDs, special characters
- **Test Classes:** `TestDPPCryptoServiceGeneration`, `TestDPPCryptoTamperResistance`, `TestDPPSingletonBehavior`, `TestDPPTokenStructure`

### IV. Avatar Fit Axis Migration (database/migrations/05_avatar_fit_axis.sql)
- **target_skeleton_fit column:** Added to `products` table with `VARCHAR(24)` type and `DEFAULT 'female'`
- **CHECK constraint:** `chk_target_skeleton_fit` enforces values in ('male', 'female', 'unisex')
- **Performance index:** `idx_products_skeleton_fit` for efficient gender-filtered queries

### V. Avatar Profile Binding Route (app/routes/dpp_verification.py)
- **Endpoint:** `POST /api/virtual/profile/set` - JSON `{"gender": "male|female|unisex"}`
- **Session storage:** Binds to `preferred_avatar_axis` session key
- **Validation:** Returns 400 for invalid gender values, defaults to "female" if missing

### VI. Virtual Atelier Gender Integration (app/routes/virtual.py)
- **capsule_layers_fragment:** Updated to filter by `target_skeleton_fit IN ($2, 'unisex')` where $2 is gender_axis param
- **Gender sources:** Accepts `gender` query param or falls back to `preferred_avatar_axis` session value
- **Validation:** Rejects invalid gender values with 400 response before database query

### VII. Avatar Flow Tests (app/tests/test_avatar_flows.py)
- **12 pytest tests** covering: avatar profile binding (valid/invalid genders, default behavior), gender validation logic, skeleton fit constraint

### VIII. Admin Panel Tests (app/tests/test_admin_crud.py)
- **9 pytest tests** covering: admin panel security boundaries, product lifecycle operations, audit log structure validation

---

## Design Tokens

| Token | Value | Tailwind Class |
|-------|-------|----------------|
| Background | #FBF9F6 | `bg-[#FBF9F6]` |
| Primary | #0D2A22 | `bg-[#0D2A22]` / `text-[#0D2A22]` |
| Accent | #D4AF37 | `text-[#D4AF37]` / `border-[#D4AF37]` |
| Text | #1A1A1A | `text-[#1A1A1A]` |
| Success | #10B981 | `text-[#10B981]` |
| Error | #EF4444 | `text-[#EF4444]` |

### Typography
- **Display:** Playfair Display (serif) - headings, editorial titles
- **Body:** Inter (sans-serif) - UI, descriptions, forms
- **Mono:** Monospace - prices, statuses, tracking-wide uppercase labels

---

### Homepage Hero — Virtual Atelier Preview
- **Template:** `app/templates/storefront/index.html` — extends `base.html`, top of `{% block content %}`
- **Design:** Full-width dark hero (`bg-[#0D2A22]`, `min-h-[520px] lg:min-h-[600px]`) with iridescent gradient backlighting (fuchsia→cyan, amber→emerald), floating geometric CSS shapes, rotating rings, pulsing glow orbs, and a subtle grid overlay (`opacity-[0.03]`)
- **Preview Card (desktop only):** Glassmorphism card (`backdrop-blur-xl bg-white/5`) with a CSS-built mannequin silhouette on a pedestal, floating animation, rotating orbit rings with gold/cyan dots, and a live green status badge; represents the Three.js showroom scene
- **CTA:** "Enter 3D Showroom" gold button linking to `/virtual-experience` with hover glow effect and 3D cube icon; secondary "Browse Collection" anchor scrolling to `#storefront`
- **Brand pillars:** Moved below the hero as an overlapping floating card row (`-mt-6 relative z-20`, white/80 backdrop-blur chips) — displays "No DM for Price", "Fair Trade Certified", "Living Wage Employer"
- **Collection heading:** Preserved original "contemporary nigerian fashion" text below brand pillars in a dedicated `#storefront` section
- **Animations:** Pure CSS custom keyframes (`rotate-slow`, `floatGentle`, `pulseSoft`) to avoid Tailwind `animate-spin` collision; all decorative elements use `aria-hidden="true"`
- **Nav link:** `base.html` header includes a gold "3D Atelier" link with a 3D box SVG icon pointing to `/virtual-experience`

### 11. Virtual Atelier — 3D Showroom & Dressing Room
- **Template:** `app/templates/virtual_experience.html` — standalone immersive 3D page (not extending base.html)
- **Route module:** `app/routes/virtual.py` — 3 endpoints
- **Tech:** Three.js (importmap via CDN), OrbitControls, procedural 3D geometry, Alpine.js, HTMX
- **Modes:**
  - **Showroom Mode:** Interactive 3D catalog with auto-rotating mannequin on floating gold pedestal. Database-backed HTMX product cards load from `/api/virtual/showroom-items` — queries `products.model_3d_url`, `products.model_usdz_url`, `product_variants.mesh_node_identifier`, `product_variants.custom_shader_color`, `product_variants.morph_target_index`. Click cards to inspect pieces. OrbitControls for 360° viewing.
  - **Capsule Layers Mode:** Layered capsule look bundles via `/api/virtual/capsule-layers?capsule_id=N`. Queries `asiko_capsule_assignments` → `products` → `product_variants`, sorted by `apparel_layer_depth ASC`. Returns pre-compiled HTML fragments with inline Alpine.js `@click="$dispatch('layer-capsule-mesh', { layerIndex, modelUrl, modelUsdz, color, mesh, ... })"` handlers. Falls back to procedural geometry for missing assets.
  - **Dressing Room Mode:** Wardrobe selection panel with 4 procedural garment meshes (Atelier Drape Dress, Cyber Blazer, Tapered Trouser, Structural Shell Top). Real-time 3D mesh swapping via `$dispatch('swap-clothing', ...)` custom events. Animated loading progress bar during asset swaps.
- **3D Architecture:**
  - Transparent WebGL canvas with iridescent CSS gradient backlighting
  - Procedural parametric mannequin with gold accent rings
  - 4 procedural garment generators with emissive materials and clearcoat
  - Floating gold pedestal with dual neon-glow rim rings
  - Ambient particles with AdditiveBlending
  - ACESFilmic tone mapping, PCFSoftShadowMap shadows
  - OrbitControls with auto-rotate (showroom), damping, and polar angle limits
  - Proper Three.js disposal on garment swaps (geometry + material cleanup)
- **Design:** Glassmorphism panels (`backdrop-blur-2xl`), neon-glow shadows, mix-blend-difference nav header, Gen-Z iridescent color ambiance (fuchsia→cyan, amber→emerald gradients)
- **GLTF Model Pipeline:** `static/assets/models/` directory for serving `.glb` files via `/static/assets/models/`. Three.js GLTFLoader integration with fallback to procedural geometry. The showroom items endpoint queries `products.model_3d_url` and returns `model_url`, `color`, and `mesh` metadata for dynamic GLTF loading.
- **Garment-Specific 3D Models (Procedural Placeholders):**
  - Generator: `scripts/generate_glb_models.py` — pure-stdlib Python GLB generator using `_lathe_profile()` to revolve 2D garment cross-sections around Y-axis
  - 7 garment-specific shape functions replacing geometric primitives: `dress_form()` (A-line flare), `blazer_form()` (structured shoulders), `trouser_form()` (two-leg tapered with waistband bridge), `top_form()` (fitted shell), `draped_gown_form()` (floor-length), `structural_top_form()` (asymmetric), `cyber_blazer_form()` (angular shoulder pads)
  - Each model has PBR materials with brand colors, metalness/roughness, and emissive factors; flat-shaded normals
  - File sizes: 16-34 KB each (vs 2-9 KB for previous primitives)
  - Pipeline documentation: `static/models/PIPELINE.md` — covers export specs (max 50K triangles, 2MB), recommended tools (CLO 3D, Marvelous Designer, Blender), export checklist, verification steps, and troubleshooting
  - Fallback: If GLB fails to load, Three.js falls back to procedural geometry (dodecahedron for showroom, procedural meshes for dressing room)
- **Route registration:** Imported in `main.py` via `from app.routes.virtual import routes as virtual_routes` — registered in `_register_route_modules()` with all other route modules

### 11a. Avatar Normalization & Zoom Dock System
- **Purpose:** Repairs global viewport framing (camera staring at the floor, oversized GLB assets spilling past the canvas) and restores button click visibility on overlays that were being intercepted by the WebGL canvas.
- **Constructor track markers (in `AtelierEngine`):**
  - `this.defaultCamPosition = new THREE.Vector3(0, 0.95, 2.3)` — anchors camera to mid-torso height
  - `this.defaultTargetPosition = new THREE.Vector3(0, 0.85, 0)` — OrbitControls target at waist level
  - `this.avatarWrapperGroup = null` — isolated parent group for the imported GLTF
  - `window.__atelierEngine = this;` — global exposure set in constructor (after `_initScene()`) so the inline `onclick` handlers in the zoom dock can resolve to the engine instance
- **`loadBaseAvatar(avatarUrl)` rewrite (per directive, 7-step pattern):**
  1. Purges any prior `avatarWrapperGroup` via `safelyPurgeThreeAsset()` to release GPU memory
  2. Creates a fresh `THREE.Group()` parent (`this.avatarWrapperGroup`) and adds it to the scene
  3. Awaits `gltfLoader.loadAsync(avatarUrl)` to get the raw GLTF; captures `rawModel = gltf.scene`
  4. **Delegates to `this.adjustModelToFitViewport(rawModel, true)`** — the unified bounding-box framing method handles the 1.6/rawHeight scale, horizontal centering, +0.06 foot lift, and luxury textile PBR baseline
  5. Mounts the normalized `rawModel` inside `this.avatarWrapperGroup`
  6. Refreshes camera/controls (with inline `|| new THREE.Vector3(0, 0.95, 2.3)` fallback if `defaultCamPosition` is undefined); ensures damping is on
  7. Traverses mesh hierarchy setting `castShadow`, `receiveShadow` only (textile PBR is already applied by `adjustModelToFitViewport`)
  - **Error path:** catches GLB parse failures and delegates to `loadProceduralAvatarFallback()` which forwards to the existing `triggerProceduralFallbackForm(gender)` with `this.currentGender || 'female'`
- **`loadHumanAvatar(gender)` adopts the same delegation pattern:**
  - Calls `this.adjustModelToFitViewport(this.currentAvatarMesh, true)` instead of the previous inline 1.6/rawHeight algorithm + PBR traverse
  - Traverse block reduced to shadow flags only (`castShadow`, `receiveShadow`); textile PBR is applied by the unified method
  - **Memory hygiene preserved:** still calls `safelyPurgeThreeAsset(this.currentAvatarMesh)` and `scene.remove(this.currentAvatarMesh)` before creating the new mesh
  - Returns `true`/`false` from a `try/catch` instead of the prior Promise wrapper
  - Calls `triggerProceduralFallbackForm(gender)` directly on error (parameterized, unlike `loadProceduralAvatarFallback` which uses the current gender state)
- **`loadProceduralAvatarFallback()` wrapper:**
  - Parameterless public method invoked by `loadBaseAvatar` error path
  - Resolves `gender = this.currentGender || 'female'` and delegates to `triggerProceduralFallbackForm(gender)`
  - Provides the directive's "Falling back to safe procedural metrics" entry point without coupling to gender-specific state at the call site
- **Public API methods (exposed to UI overlay buttons):**
  - `zoomIn()` → `this.executeVectorZoom(0.85)` (vector-math zoom, see Section 11d)
  - `zoomOut()` → `this.executeVectorZoom(1.15)` (vector-math zoom, see Section 11d)
  - `resetView()` → snaps camera position + controls target back to the track markers
  - Distinct from `resetCamera()` (which is invoked via the `reset-camera` event listener) so the UI reset button always lands on the same baseline
- **Zoom dock overlay (in `virtual_experience.html`):**
  - Glassmorphic vertical column at `bottom-4 right-4 z-50` inside the 3D viewport container
  - Three buttons (`+` zoom in, `−` zoom out, `Reset`) with `bg-[#0D2A22]` / hover `bg-[#D4AF37]` color treatment
  - All buttons have `touch-manipulation` (disables iOS Safari double-tap zoom delay) and `select-none` (prevents text selection on long-press drag) Tailwind classes
  - Wrapper container has `select-none` to prevent accidental text selection when dragging across the dock
  - `onclick` handlers call `window.__atelierEngine.zoomIn() / zoomOut() / resetView()` directly — no Alpine.js bridge needed
  - **Reset button defensive fallback:** `onclick="if(window.__atelierEngine && typeof window.__atelierEngine.resetView === 'function'){ window.__atelierEngine.resetView(); } else if(window.__atelierEngine){ window.__atelierEngine.camera.position.set(0, 1.2, 3.5); window.__atelierEngine.controls.target.set(0, 0.8, 0); window.__atelierEngine.controls.update(); }"` — the inline JS fallback ensures the button always works even if `resetView` is undefined due to engine init race
  - Container has explicit `pointer-events-auto` so clicks land on the buttons, not the WebGL canvas underneath
- **Pointer-event isolation CSS:**
  - `.atelier-canvas-wrap > canvas` keeps `pointer-events: auto` so OrbitControls drag gestures still work
  - `.atelier-canvas-wrap .pointer-events-auto { pointer-events: auto !important; }` opt-in for all overlay HUDs (zoom dock, mode indicator, AR gate, loading overlay)
  - The existing Femme/Homme dock, AR gate, and mode switcher continue to function unchanged
- **Memory hygiene upgrade:** the previous `loadBaseAvatar` only called `scene.remove()` on the old model (latent GPU leak on every avatar swap). The new version calls `safelyPurgeThreeAsset(this.avatarWrapperGroup)` first, recursively disposing geometries and materials across the mesh hierarchy.

### 11b. Peak-Dimension Bounding-Box Framing System
- **Purpose:** Replaces hardcoded scale/position magic numbers (`scale.set(1.2, 1.2, 1.2)`, `position.y = 0.5`) in the Showroom and Dressing Room GLB loaders with a defensive peak-dimension algorithm that centers, scales, and floor-anchors any incoming mesh regardless of its source-asset scale. Fixes the "incoming garment meshes clip past the canvas bounds" distortion (image_9a6fda.jpg).
- **`adjustModelToFitViewport(incomingMesh, isAvatar = false)` algorithm (7 steps, with `isAvatar` flag):**
  1. **Bounding Box Analysis** — `new THREE.Box3().setFromObject(incomingMesh)` → `getSize` + `getCenter`
  2. **Peak Dimension Detection** — `maxDimension = Math.max(width, height, depth)`; the largest single-axis extent of the model
  3. **Normalization Pass (SCALE REPLACE, not multiply)** — `incomingMesh.scale.set(targetPeak/maxDimension, ...)` where `targetPeak = isAvatar ? 1.6 : 1.2`. Uses `.set()` to OVERRIDE any pre-existing scale (correct for incoming GLBs that may have arbitrary baked-in scale like 100x for a handbag). `.multiplyScalar()` would compound the scale, producing a runaway result
     - **Re-evaluate bounds post-matrix transform** — `boundsBox.setFromObject(incomingMesh); boundsBox.getSize(meshSize); boundsBox.getCenter(meshCenter)` (reuses the same `Vector3` instances for memory efficiency)
  4. **Center Horizontal Coordinates (IN-PLACE subtraction)** — `incomingMesh.position.x -= meshCenter.x; incomingMesh.position.z -= meshCenter.z`. Uses `-=` (in-place) to preserve any prior positional offset (e.g., a model's external coordinate system offset from a parent group). Absolute assignment `=` would clobber it
  5. **Anchor Flush with Floor (ABSOLUTE assignment)** — `incomingMesh.position.y = -boundsBox.min.y`. Uses `=` (absolute) to force the model to sit at exactly `y=0` regardless of any prior `position.y` value. This overrides the `position.y = 0.05` set in `loadAutomatedGarment` and the `position.set(0, 0, 0)` in `loadAutomatedAsset`
  6. **Refocus Camera (guarded by `if (this.controls)`)** — `controls.target.set(0, meshSize.y / 2, 0)` (vertical midpoint of re-scaled model); clamps `minDistance = 0.8` and `maxDistance = 5.0`; calls `controls.update()`. The `if (this.controls)` guard prevents errors during early construction before `OrbitControls` is initialized
- **Wired into three GLB loader success callbacks:**
  - `loadShowroomModel(modelUrl, color, meshRef)` — replaces the hardcoded `scale.set(1.2, 1.2, 1.2)` and `position.y = 0.5` (replaced for cleaner per-product framing)
  - `loadAutomatedAsset(meshUrl, layerDepth, assetCategory)` — Dressing Room path; runs after the footwear/clothing stratification scale offset is applied, dominates over the layer depth offset
  - `loadAutomatedGarment(payload)` — Dressing Room path; runs after `scale.setScalar(scaleFactor)` + `position.y = 0.05`; the `position.y = 0.05` is overridden by step 5's absolute assignment
- **Avatar loaders are exempt:** `loadBaseAvatar()` and `loadHumanAvatar()` keep their existing 1.6-unit wrapper-group normalization (Section 11a) — those loaders own the camera baseline and torso anchor, not the garment/showroom path
- **Fallback geometry is exempt:** The `DodecahedronGeometry` and `BoxGeometry` fallbacks in each loader's error callback are not GLB models, so the directive's "whenever a new .glb model finishes loading" scope excludes them

### 11c. Retail UX Re-Architecture (Admin Dashboard)
- **Purpose:** Removes AI Mesh Engine / Pipeline Sandbox jargon from the boutique operator UI; boutique owners interact only with premium, standard retail parameters (Product Info, Stock levels, clean file paths). Replaces the messy 4-column inventory table with a clean vertical card list per the "REFACTORED PREMIUM MANAGEMENT ROW" architecture.
- **Two layers of removal/refactor in `app/templates/admin/dashboard.html`:**
  - **Layer 1 — Removed (sandbox jargon):** the entire `{% if is_first_variant %}` block (was lines 125-224, ~100 lines) containing:
    - "ÀSÌKÒ AI 3D Mesh Engine" gray panel
    - "Item Category" radio selector (Apparel vs Footwear)
    - "Upload from Device" / "Paste Image Link" tabbed file picker (with `Gdress.jpg` placeholder)
    - "Synthesize" button
    - "Pipeline Sandbox Operator" row with "Simulate Success Success" and "Simulate Trigger Fault" debug utilities
  - **Layer 2 — Replaced (table → card list):** the original 4-column inventory table (`<table>` block with 4 `<th>` columns) was REPLACED with a vertical card list. Each variant now renders a `REFACTORED PREMIUM PRODUCTION ROW` card with:
    - **Image placeholder** (16x16 square) with `{{ loop.index }}` numeric badge (since the inventory table has no product image field)
    - **Brand / Product Identity** section: `Active Capsule Collection` (first variant) or `Variant Drop · Same Capsule` (subsequent) tag in gold `#D4AF37`; product name in serif; subtitle `Size X • Color Y • N Units Available` in monospace; inline `3D` badge if model URL is set
    - **Premium Operations Form Area:**
      - **Inline Stock Control** — pill-shaped input with leading "STOCK" label, `w-16` number input, and a `bg-[#0D2A22]` button (hover `bg-[#D4AF37]`); submits to `/admin/dashboard/update-stock`
      - **3D File Path** (first variant only) — pill-shaped input with leading "3D PATH" label, `w-56` text input with placeholder `tailored-column-trouser.glb`, and a `bg-[#D4AF37]` button (hover `bg-[#0D2A22]`); submits to `/admin/dashboard/update-model-url`
      - **Status indicator** — green dot + "Active" label in monospace
    - **HTMX response target containers** preserved at the bottom of each card (`#status-variant-{id}` and `#model-status-{product_id}`) for the response HTML from the two POST endpoints
- **Color tokens applied throughout:** `#0D2A22` (deep green) for primary actions and identity text; `#D4AF37` (gold) for accent labels, hover states, and path-save button; `#FBF9F6` (off-white) for input field backgrounds; borders at `border-[#0D2A22]/10` (subtle) and `border-[#0D2A22]/20` (form fields)
- **Layout responsiveness:** cards stack vertically on mobile (`flex-col`) and switch to `flex-row` on `lg+` screens (`lg:flex-row lg:items-center justify-between`)
- **No backend changes required:** the `dashboard.py` handler still populates `pipeline_status`, `source_2d_image_url`, etc. — those fields are now unused by the template (dead data, harmless). The two existing HTMX endpoints (`/admin/dashboard/update-stock`, `/admin/dashboard/update-model-url`) are still wired and functional
- **File size evolution:** 288 → 188 (Layer 1 removal) → 202 lines (Layer 2 card list adds ~14 lines per card section header but eliminates the ~30 lines of table thead/tbody structure)

### 11d. Studio Lighting + Touch Sensitivity + Vector Zoom
- **Purpose:** Replaces the flat 4-light setup (ambient + key + fill + rim + accent point light) with a focused 3-light studio rig, retunes OrbitControls for touch/mobile responsiveness, and replaces native `dollyIn`/`dollyOut` with a clamped vector-math zoom for predictable, safe camera framing on any device.
- **`initStudioLighting()` (replaces the prior `_initLights()`):**
  - **Idempotent light wipe:** first iterates `this.scene.children.filter((c) => c.isLight)` and calls `this.scene.remove(l)` for each — safe to call multiple times during development hot-reload
  - **HemisphereLight** (0xffffff sky, 0x444444 ground, intensity 1.2) — soft ambient that flattens shadowed crevices in the garment folds
  - **Key DirectionalLight** (0xfffdf6 warm white, intensity 1.8) — positioned `(2, 4, 3)` from front-right; `castShadow = true`; `shadow.mapSize = 2048×2048` (upgraded from 1024×1024 for crisp fabric weave detail at the cost of ~4MB GPU memory); `shadow.bias = -0.0001` to prevent shadow acne; `shadow.camera.near=0.1`, `shadow.camera.far=20` to cover the avatar/garment scene
  - **Rim DirectionalLight** (0xd4af37 brand gold, intensity 1.0) — positioned `(-2, 3, -3)` from back-left; matches the brand token `#D4AF37` exactly; produces a subtle silhouette glow on fabric folds and accentuates the luxury aesthetic without washing out the textile PBR sheen
  - **Removed:** the previous `fill` blue DirectionalLight (cold, broke the warm editorial mood) and the `accentLight` PointLight (created hotspots on metallic objects)
- **`initInteractionControls()` (new method, retunes OrbitControls):**
  - `rotateSpeed = 1.8` (default 1.0) — desktop drag responsiveness is 80% snappier
  - `touchRotateSpeed = 2.2` (default 1.0) — mobile single-finger spin is 120% more responsive
  - `enableDamping = true` (preserved from prior setup)
  - `dampingFactor = 0.08` (was 0.05) — slightly looser for tactile feel
  - `screenSpacePanning = false` — pan is depth-relative, prevents users from panning the camera off into infinity when the mouse reaches the canvas edge
  - Called from `_initScene()` right after `initStudioLighting()`
- **`executeVectorZoom(zoomFactor)` (replaces native `dollyIn`/`dollyOut`):**
  - Computes `offset = new THREE.Vector3().subVectors(camera.position, controls.target)` — the current camera-to-target vector
  - `offset.multiplyScalar(zoomFactor)` — scales the offset (0.85 = zoom in, 1.15 = zoom out)
  - **Safety clamp:** if `offset.length() < 0.6` (camera inside model chest) or `> 5.5` (scene blank frame), call `offset.setLength(minDistance)` or `setLength(maxDistance)` to clamp
  - `camera.position.copy(controls.target).add(offset)` — re-anchor the camera at the new offset
  - `controls.update()` — refresh OrbitControls
  - **Why vector math over native dolly:** OrbitControls.dollyIn/dollyOut have known issues with perspective cameras and target-relative framing; direct distance-vector math is more predictable and gives a single source of truth for the clamp boundaries
- **`zoomIn() / zoomOut()` now thin wrappers:**
  - `zoomIn() { this.executeVectorZoom(0.85); }`
  - `zoomOut() { this.executeVectorZoom(1.15); }`
  - Removed the `if (this.controls)` guard from these methods — the safety clamp in `executeVectorZoom` already returns early if controls are undefined
- **`window.__atelierEngine = this;` global exposure:**
  - Set in the constructor (line 93) right after `this._initScene()` returns
  - Canonical reference name: `__atelierEngine` (double underscore prefix to mark it as an internal-but-globally-accessible handle)
  - All zoom dock `onclick` handlers resolve through this global; the JS init code in `virtual_experience.html` (line 622) also assigns `window.__atelierEngine = engine;` for symmetry
- **Reset button defensive inline JS fallback (in `virtual_experience.html`):**
  - `onclick="if(window.__atelierEngine && typeof window.__atelierEngine.resetView === 'function'){ window.__atelierEngine.resetView(); } else if(window.__atelierEngine){ window.__atelierEngine.camera.position.set(0, 1.2, 3.5); window.__atelierEngine.controls.target.set(0, 0.8, 0); window.__atelierEngine.controls.update(); }"`
  - The fallback path manually snaps camera + controls to safe defaults if `resetView` is undefined (e.g., engine init race, partial page load)
  - Fallback values are slightly different from the constructor track markers (camera at `(0, 1.2, 3.5)`, target at `(0, 0.8, 0)`) — these are the "after-zoom" reset values, framed to fit the wider showroom viewport, not the mid-torso avatar framing

### 11e. Anti-304 Cache Bypass (Local Dev Hot-Reload)
- **Purpose:** Prevents Starlette and the browser from caching static assets (especially the 3D engine at `/static/js/atelier-3d.js`) by forcing 200 OK deliverables on all local dev cycles. Two-layer enforcement: server-side header injection + client-side query parameter cache-busting.
- **`NoCacheStaticFiles` class (in `app/main.py`):**
  - Subclass of `starlette.staticfiles.StaticFiles` that intercepts both the conditional-GET optimization AND the response header pipeline
  - **Layer 1 — `is_not_modified(response_headers, request_headers)` always returns `False`:** Starlette's `StaticFiles` calls this method to decide whether to short-circuit a request with a `304 Not Modified` response when the client sends `If-Modified-Since` / `If-None-Match` headers. By forcing `False`, the server always returns the full 200 OK response with the file body
  - **Layer 2 — `__call__(scope, receive, send)` intercepts `http.response.start` messages:** Defines an inner `intercepted_send(message)` that:
    - On the `http.response.start` message type, reads the existing headers, overrides three cache-control headers, and rewrites the message headers
    - Injects: `Cache-Control: no-cache, no-store, must-revalidate, max-age=0` (modern standard)
    - Injects: `Pragma: no-cache` (HTTP/1.0 backward compatibility)
    - Injects: `Expires: 0` (legacy proxy/CDN cache invalidation)
    - Delegates to the original `send` after header mutation
  - **Wired in:** `app.routes.append(Mount("/static", app=NoCacheStaticFiles(directory=str(STATIC_DIR)), name="static"))` — replaces the standard `StaticFiles(...)` in the mount
  - **Why both layers:** Layer 1 prevents the server from short-circuiting with 304 (saves bandwidth). Layer 2 prevents the browser from proactively caching the response (saves debugging time when iterating on `atelier-3d.js`). Both must be in place for the "always fetch fresh" guarantee
- **Frontend script cache-buster (in `app/templates/virtual_experience.html`):**
  - The ES module import at line 612 was updated from `import { initAtelierEngine } from '/static/js/atelier-3d.js';` to `import { initAtelierEngine } from '/static/js/atelier-3d.js?v={{ range(1000, 9999) | random }}';`
  - The Jinja2 expression `{{ range(1000, 9999) | random }}` resolves to a random integer in `[1000, 9999]` at template render time, producing a URL like `/static/js/atelier-3d.js?v=4729`
  - ES module imports DO respect query parameters for cache-busting — the browser treats `/static/js/atelier-3d.js?v=4729` as a distinct URL from `/static/js/atelier-3d.js`, so it refetches the module on every page load
  - **Why a query parameter, not a content-hashed filename:** the 3D engine is a single development file; adding a build step to hash the filename would add complexity without much benefit in dev. The random query parameter is the "fool's cache buster" — it works because the URL changes every render
- **Affected assets:** All assets served via `/static/*` (JS, CSS, .glb 3D models, fonts, images). The frontend cache-buster is currently only applied to the 3D engine import; future asset imports (CSS, additional JS) should follow the same pattern as the engine is iterated on
- **Production deployment note:** This `NoCacheStaticFiles` override is intentionally a development tool. For production, swap back to the standard `StaticFiles` to enable CDN/browser caching of the 3D assets (which can be 1-2 MB per GLB). Or add a build step that hashes filenames and removes the query parameter
- **No state pollution:** The `NoCacheStaticFiles` class doesn't modify the underlying `StaticFiles` parent class; it only intercepts the conditional-GET check and the response headers. File serving semantics are unchanged

### 11f. Defensive Lifecycle Wrapping & Spline Spotlight Card (SUPERSEDED — see 11g)
- **Purpose:** Prevents unhandled script crashes from locking the loading state, and builds a premium Spline interaction section natively using Jinja2, Alpine.js, and Tailwind CSS. The Atelier engine must complete execution and dismiss the loading overlay under any failure mode, and the Spline card is a parallel marketing surface below the primary 3D canvas wrap.
- **Status:** The defensive `loadBaseAvatar` v1 and Spline Spotlight Card described in this section were SUPERSEDED in the latest directive (Section 11g). The Spline card and its runtime script were removed entirely (redundant with the new premium dark interactive canvas wrap), and `loadBaseAvatar` was rewritten as v2 (no type guards, 300ms opacity-then-display fade, `canvas-loader` lookup, literal `Vector3(0, 1.1, 2.4)` camera). See Section 11g for the current architecture
- **Defensive `loadBaseAvatar` rewrite v1 (5 resilience layers) — SUPERSEDED:**
  1. **Memory purge wrapped in `try/catch`** — a thrown purging routine cannot block the rest of the load. The catch block logs a non-fatal warning (`console.warn("Non-blocking purge warning:", purgeError)`) and continues
  2. **Type guard on `safelyPurgeThreeAsset`** — `if (typeof this.safelyPurgeThreeAsset === 'function')` before calling. If the purger is undefined (e.g., partial init), falls back to `this.scene.remove(this.avatarWrapperGroup)` to at least drop the old wrapper from the scene graph
  3. **Type guard on `adjustModelToFitViewport`** — `if (typeof this.adjustModelToFitViewport === 'function')` before invoking the scale-normalization helper. If the helper is missing, the raw model is mounted at its native scale (graceful degradation)
  4. **`finally` block forces the loading overlay to dismiss** — uses raw DOM (`document.getElementById('loading-screen') || document.querySelector('.loader')`) instead of the engine's `setViewportLoadingState(false)` path, so the UI always unblocks even if the engine state is corrupt. Sets `display: 'none'`, `opacity: '0'`, and `classList.add('hidden')` for triplicate coverage across CSS-based and class-based loading indicator styles
  5. **Literal `Vector3(0, 0.95, 2.3)` camera values** — no dependency on `defaultCamPosition` / `defaultTargetPosition` track markers, avoiding throws on undefined if the constructor order is racy. The values match the constructor track markers exactly
  - **Error path:** now logs `console.error("Avatar asset parse failure, forcing canvas display state:", error)` and falls through to the `finally` block. The previous `loadProceduralAvatarFallback()` call is intentionally dropped — the directive prioritizes "always show the canvas" over "always show a procedural avatar"
  - **Removed:** the PBR traverse block (`roughness=0.65`, `metalness=0.1`, `castShadow`, `receiveShadow`). Textile PBR is already applied by `adjustModelToFitViewport`; the duplicate traverse was redundant
- **Spline runtime entry point (in `virtual_experience.html` `<head>`) — REMOVED:**
  - `<script type="module" src="https://unpkg.com/@splinetool/viewer@1.9.0/build/spline-viewer.js"></script>` was at line 49 in the previous directive's version
  - The runtime was loaded as an ES module from the official Spline unpkg CDN — provided the custom `<spline-viewer>` element used by the spotlight card
  - Placed in `<head>` so the runtime was available before the card markup was parsed (no race conditions on first render)
  - **Removed in 11g:** the Spline card was deemed redundant with the new premium dark interactive canvas wrap, so both the runtime script and the entire card markup (lines 412-465 in the previous version) were removed
- **Premium Interactive Spline Spotlight Card — REMOVED:**
  - **Status:** The entire card (with mouse-tracking Alpine.js state, SVG ambient spotlight, cursor-following radial gradient, left text panel, right `<spline-viewer>`) was REMOVED in Section 11g. The new directive's premium dark interactive canvas wrap is now the single primary visual surface, with mouse-tracking spotlight, gold accents, and dark editorial background — providing the same visual interest as the Spline card without requiring a separate runtime
  - See Section 11g for the current canvas wrap architecture
- **Why Spline was used (when active):** Spline is a designer-friendly 3D scene authoring tool; the marketing team can iterate on the 3D scene without engineering involvement. The `<spline-viewer>` element is a sandboxed iframe-like context — no JavaScript access to the parent's `__atelierEngine` or Alpine.js state (clean separation of marketing visuals from the configurator engine)
- **Loading indicator lookup chain (v1):** `document.getElementById('loading-screen') || document.querySelector('.loader')` — checks the conventional global IDs first, falls back to the common class name. The v2 lookup chain (in 11g) uses `document.getElementById('canvas-loader') || document.querySelector('.loader')` — the new directive's preferred canvas-specific loader ID, with `.loader` as a generic fallback

### 11g. 21st.dev Premium Dark Interactive Canvas Wrap & Defensive `loadBaseAvatar` v2
- **Purpose:** Replaces the primary 3D canvas wrap with a premium dark, interactive spotlight-themed card aligned with the 21st.dev "premium interactive" aesthetic. Simplifies the `loadBaseAvatar` defensive pattern to use direct helper calls (no type guards) and a smooth opacity-then-display fade for the loader dismissal. Establishes a single primary visual surface (no parallel Spline card)
- **New canvas wrap architecture (replaces lines 162-264 of the previous version):**
  - **Outer container:** `<div x-data="{ mouseX: 0, mouseY: 0, isHovered: false }" @mousemove="..." class="w-full h-[600px] bg-black/[0.96] border border-[#0D2A22]/30 rounded-xl relative overflow-hidden shadow-2xl">` — fixed 600px height, near-black background (`black/[0.96]`), deep-green border at 30% opacity, large drop shadow
  - **Cursor-following radial gold spotlight (500×500px):**
    - Div: `class="pointer-events-none absolute rounded-full bg-[radial-gradient(circle_at_center,rgba(212,175,55,0.15)_0%,transparent_70%)] blur-2xl transition-opacity duration-300 select-none"`
    - `bg-[radial-gradient(circle_at_center,rgba(212,175,55,0.15)_0%,transparent_70%)]` — gold radial gradient with 15% opacity at center, fading to transparent at 70% radius
    - `blur-2xl` for soft edges (Tailwind's 24px blur)
    - `:class="isHovered ? 'opacity-100' : 'opacity-0'"` — fades in on hover, out on leave (300ms transition)
    - `:style="`width: 500px; height: 500px; left: ${mouseX - 250}px; top: ${mouseY - 250}px;`"` — dynamically positions the radial centered under the cursor (250px offset to center the 500px radial at the cursor)
    - `pointer-events-none` so the gradient never blocks clicks; `select-none` prevents accidental text selection
  - **Top gradient backdrop (always-on ambient lighting):**
    - `<div class="pointer-events-none absolute top-0 inset-x-0 h-40 bg-gradient-to-b from-white/[0.03] to-transparent z-10"></div>` — soft 160px white-to-transparent gradient at the top of the card, creating a "light spilling from above" mood
    - `z-10` so it sits below interactive content but above the radial spotlight
  - **Two-column flex layout (`flex flex-col md:flex-row`):**
    - **Left column (text panel, ~50% width on desktop):** `flex-1 p-8 relative z-20 flex flex-col justify-center pointer-events-none select-none`
      - Eyebrow tag: `<span class="text-[10px] font-mono uppercase tracking-widest text-[#D4AF37] mb-2 block">ASIKO Atelier Studio</span>` — gold mono uppercase, 10px font
      - Headline: `<h1 class="text-3xl md:text-5xl font-serif font-bold text-transparent bg-clip-text bg-gradient-to-b from-white to-zinc-400 leading-tight">Interactive 3D Experience</h1>` — 5xl serif bold with white-to-zinc-400 vertical gradient
      - Body: `<p class="mt-4 text-sm text-zinc-400 max-w-sm font-sans leading-relaxed">Experience luxury fashion tailored dynamically to your posture profile. Adjust scaling configurations with continuous physics damping.</p>` — zinc-400 body copy with relaxed line height
      - `pointer-events-none` so the text panel never blocks interaction with the canvas; `select-none` prevents accidental text selection
    - **Right column (canvas wrap, ~50% width on desktop):** `<div class="flex-1 relative w-full h-full min-h-[350px] z-10 atelier-canvas-wrap">` — the new container class for the Three.js engine
      - **Loading overlay:** `<div id="canvas-loader" class="absolute inset-0 flex items-center justify-center bg-black z-30 transition-all duration-300">` — black background, flex-centered content, `z-30` so it sits above the canvas
        - Spinner: `<div class="w-8 h-8 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin"></div>` — 32px gold circle with top edge transparent, CSS spin animation
        - Label: `<span class="text-xs font-mono tracking-widest text-zinc-500 uppercase">Synchronizing Mesh Profiles...</span>` — zinc-500 mono uppercase
      - **Placeholder canvas:** `<canvas id="atelier-3d-viewport" class="w-full h-full block focus:outline-none"></canvas>` — static `<canvas>` element that is REMOVED in the init script before engine init (so the engine can create its own WebGL canvas via `container.appendChild(this.renderer.domElement)`)
- **Defensive mouse-move guard (`if($el === $event.target || $el.contains($event.target))`):** The `@mousemove` handler only updates `mouseX`/`mouseY` if the event target is the card itself OR a descendant. Prevents stray mouse events from nested elements (e.g., text spans, SVG) from updating the spotlight position. More reliable than relying on `event.target === event.currentTarget` alone (which fails when the event bubbles up through child elements)
- **Defensive `loadBaseAvatar` v2 (replaces v1 from 11f):**
  1. **Loader lookup hoisted to function top** — `const uiLoader = document.getElementById('canvas-loader') || document.querySelector('.loader');` is the FIRST statement in the function, so the `finally` block can always reference the same element (closure capture)
  2. **Loader FORCED VISIBLE at start** — `if (uiLoader) uiLoader.style.display = 'flex';` ensures the user sees feedback during load (in case the loader was hidden by a prior page state)
  3. **No type guards on helper methods** — the v1 version had `if (typeof this.safelyPurgeThreeAsset === 'function')` and `if (typeof this.adjustModelToFitViewport === 'function')` defensive checks. v2 removes these because the methods are well-defined and the type guards add noise. If a method is genuinely missing, the engine has a larger problem and a thrown error is more diagnostic than silent fallback
  4. **Direct calls to `this.safelyPurgeThreeAsset(this.avatarWrapperGroup)` and `this.adjustModelToFitViewport(rawModel, true)`** — assumes the engine is fully initialized
  5. **Literal `Vector3(0, 1.1, 2.4)` camera + `(0, 0.85, 0)` target** — updated from v1's `(0, 0.95, 2.3)` / `(0, 0.85, 0)`. The 1.1-unit y position gives a slightly higher vantage point (matches the new 600px canvas wrap height better than the 0.95 in the smaller 400px previous canvas)
  6. **Inline OrbitControls tuning:** `this.controls.rotateSpeed = 1.8; this.controls.touchRotateSpeed = 2.2; this.controls.enableDamping = true; this.controls.dampingFactor = 0.05;` — restores v1's per-call tuning (overrides the constructor's `dampingFactor=0.08` to 0.05 for a more responsive feel on the new larger canvas)
  7. **`finally` block uses 300ms opacity-then-display fade (replaces v1's triplicate dismissal):** `uiLoader.style.opacity = '0'; setTimeout(() => { uiLoader.style.display = 'none'; }, 300);` — sets opacity to 0 immediately (CSS transition fades over 300ms), then hides the element after the transition completes. The v1 triplicate (`display: 'none'` + `opacity: '0'` + `classList.add('hidden')`) was redundant and produced a jarring instant disappear
  8. **Dropped `loadProceduralAvatarFallback()` call** (carried over from v1) — error path just logs and falls through to the `finally` block
- **Init script pattern (in `virtual_experience.html` `<script>` block):**
  1. **Container lookup by class, not ID:** `const container = document.querySelector('.atelier-canvas-wrap');` — uses the new `.atelier-canvas-wrap` class on the right column of the new canvas wrap (replaces the old `document.getElementById('canvas-3d-target')` from the previous canvas wrap)
  2. **Placeholder canvas removal BEFORE engine init:** `const placeholderCanvas = document.getElementById('atelier-3d-viewport'); if (placeholderCanvas) placeholderCanvas.remove();` — removes the static `<canvas id="atelier-3d-viewport">` from the DOM before the engine creates its own WebGL canvas. If the placeholder is not removed, the engine would create a second canvas inside the container (producing a stacked-canvas visual bug)
  3. **Loader dismissal via 300ms fade (same pattern as `loadBaseAvatar`):** `const uiLoader = document.getElementById('canvas-loader'); if (uiLoader) { uiLoader.style.opacity = '0'; setTimeout(() => { uiLoader.style.display = 'none'; }, 300); }` — ensures the loader fades smoothly even if the GLB load completes faster than the 300ms transition
- **`setViewportLoadingState` updated to match v2 pattern:** Replaces v1's transitionend-listener-based dismissal with the same 300ms setTimeout pattern. The lookup chain is also updated: `document.getElementById('canvas-loader') || document.querySelector('.loader')` (replaces the v1 `'three-loading-overlay'` ID). This is the SINGLE SOURCE OF TRUTH for loader dismissal — both the init script and `loadBaseAvatar` use the same fade pattern via the same element reference
- **Spline card + runtime removal:** The premium interactive Spline spotlight card (with mouse-tracking Alpine.js state, SVG ambient spotlight, cursor-following radial gradient, `<spline-viewer>` embedded scene) and the `<script type="module" src="https://unpkg.com/@splinetool/viewer@1.9.0/build/spline-viewer.js">` runtime script in `<head>` were REMOVED entirely. They were redundant with the new premium dark interactive canvas wrap — the new wrap provides the same mouse-tracking spotlight, gold accents, and dark editorial background without requiring a separate runtime
- **Header comment in `atelier-3d.js` updated:** Line 10 was changed from `const engine = initAtelierEngine(document.getElementById('canvas-3d-target'));` to `const engine = initAtelierEngine(document.querySelector('.atelier-canvas-wrap'));` — keeps the public API documentation in sync with the new container lookup pattern
- **Why no type guards in v2 (v1 had them):** The v1 type guards (`if (typeof this.safelyPurgeThreeAsset === 'function')`) were added during a transitional period when the engine was being incrementally built. By v2, the engine's class structure is stable, the methods are all defined in the constructor, and the type guards add noise without value. If a method IS missing, the v2 design assumes the developer wants the loud failure (so they know the engine is broken), not the silent fallback (which masks the issue)
- **300ms setTimeout rationale:** The 300ms delay matches the CSS `transition-all duration-300` on the loader element. Setting `opacity: 0` triggers the CSS transition; after 300ms, the transition is guaranteed to be complete, so `display: 'none'` removes the element without a visual jump. Using `transitionend` event listener (v1 approach) is more precise but can fail to fire if the element is removed from the DOM before the transition completes
- **Container class (`.atelier-canvas-wrap`) vs container ID:** The previous canvas wrap used an ID (`#canvas-3d-target`). The new wrap uses a CLASS (`.atelier-canvas-wrap`) because the container is one of multiple elements inside a flex layout — IDs should be unique document-wide, but classes can be reused. The class is also used by the existing CSS in the `<style>` block for pointer-event isolation (`.atelier-canvas-wrap { position: absolute; inset: 0; }` and `.atelier-canvas-wrap > canvas { pointer-events: auto; }`) — preserving the existing pointer-event semantics
- **Why the new canvas wrap is 600px (not full-height):** The previous canvas wrap was `min-h-[400px] lg:min-h-0` (filled the parent grid cell). The new wrap is `h-[600px]` (fixed height) because the page layout no longer uses the fixed `inset-0 z-30 pt-20 pb-6 px-6` main element that wrapped the previous canvas — the new wrap is a self-contained card that sits in the normal document flow with a fixed 600px height for predictable layout across viewports

---

## API Endpoints

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/` | `homepage` (storefront.py) | Storefront with product grid |
| GET | `/test-pdp` | `debug_root` | Debug PDP with mock data |
| GET | `/product/{product_id}` | `product_detail` (storefront.py) | Editorial PDP with capsule lookups + concierge signing |
| GET | `/htmx/products` | `product_grid_fragment` (storefront.py) | HTMX product grid fragment |
| POST | `/cart/add` | `cart_add` | Add item to cart |
| POST | `/cart/update` | `cart_update` | Modify cart quantity |
| GET | `/cart/drawer` | `cart_drawer` | Cart drawer HTMX fragment |
| GET | `/checkout` | `checkout_page` | Checkout with 36-state dropdown |
| GET | `/checkout/shipping-summary` | `shipping_summary` | HTMX shipping calc |
| POST | `/checkout/submit` | `checkout_submit` | Process order + send emails |
| GET | `/checkout/confirmation` | `checkout_confirmation` | Order confirmation page |
| POST | `/admin/reserve` | `reserve_stock` | Reserve stock (SELECT FOR UPDATE) |
| POST | `/admin/settle` | `settle_reservations` | Release expired reservations |
| GET | `/admin/reservations` | `list_reservations` | List active reservations |
| POST | `/catalog/waitlist` | `enroll_in_waitlist` | Out-of-stock enrollment |
| POST | `/atelier/measurements` | `save_measurements` | Digital Atelier vault |
| GET | `/catalog/concierge/bridge` | `concierge_redirect` | WhatsApp concierge redirect |
| POST | `/catalog/capsule/add-bundle` | `add_capsule_bundle` | Capsule matrix bulk add |
| GET | `/products/{slug}/preorder` | `preorder_interface` | Tiered allocation gatekeeper |
| POST | `/catalog/preorder/secure` | `secure_preorder` | Pre-order lock |
| POST | `/webhooks/order-status` | `order_status_webhook` | Update order status |
| POST | `/webhooks/test-email` | `send_test_email` | Debug: test Brevo config |
| POST | `/payments/webhook` | `paystack_webhook_handler` | Paystack HMAC-SHA512 verification |
| GET | `/catalog/allocation/{slug}` | `get_allocation_status` | Session-based allocation gatekeeper |
| POST | `/catalog/atelier/bind` | `bind_atelier_dimensions` | Session-based measurement vault |
| GET | `/catalog/concierge/redirect` | `concierge_redirect` | WhatsApp 303 redirect (session) |
| POST | `/catalog/cart/capsule` | `acquire_capsule_matrix` | Session-based capsule matrix add |
| GET | `/admin/dashboard` | `admin_dashboard_home` | Executive dashboard: metrics, inventory, waitlists |
| POST | `/admin/dashboard/update-stock` | `inline_update_stock` | HTMX inline stock quantity update |
| POST | `/admin/dashboard/notify-waitlist` | `inline_trigger_restock_alert` | Batch restock emails via Brevo |
| POST | `/admin/dashboard/update-model-url` | `inline_update_model_url` | HTMX inline 3D model URL edit |
| GET | `/virtual-experience` | `virtual_experience` (virtual.py) | 3D Virtual Atelier — showroom & dressing room |
| GET | `/api/virtual/showroom-items` | `showroom_items_fragment` (virtual.py) | HTMX product cards for showroom panel |
| GET | `/api/virtual/capsule-layers` | `capsule_layers_fragment` (virtual.py) | Layered capsule look bundles sorted by apparel_layer_depth + gender filter
| GET | `/admin/products` | `get_admin_products_fragment` (admin.py) | Admin products table with inline edit/delete
| GET | `/admin/products/{id}/detail` | `get_product_detail_fragment` (admin.py) | Single product detail view with variants
| DELETE | `/admin/products/{id}` | `handle_delete_product` (admin.py) | Cascade-delete product and variants
| GET | `/admin/settings` | `get_general_settings_fragment` (admin.py) | General admin settings panel
| POST | `/api/virtual/avatar-profile` | `update_session_avatar_profile` (virtual_experience.py) | Session-bound avatar profile selection
| GET | `/static/models/{path}` | StaticFiles mount | Serve .glb 3D model files for GLTFLoader |

---

## Environment Variables

```bash
# Neon PostgreSQL (required)
DATABASE_URL="postgresql://Asiko:npg_xxx@ep-xxx.pooler.region.aws.neon.tech/boutique?sslmode=require"

# Brevo Email (required for transactional emails + waitlist)
BREVO_API_KEY="xkeysib-..."
SENDER_EMAIL="notifications@asikoboutique.com"

# Paystack (optional - enables payment verification)
PAYSTACK_SECRET_KEY="your_paystack_secret_key_here"

# Session Security (optional - falls back to hardcoded key)
SECRET_KEY="your-production-secret-key"

# Environment
ENVIRONMENT="development"
```

---

## Running

```bash
pip install -r requirements.txt
# Ensure .env is configured with DATABASE_URL and BREVO_API_KEY
python -m uvicorn app.main:app --reload --port 8000
```

### Django Admin (data ledger)
```bash
python manage.py migrate --run-syncdb   # Sync Django models
python manage.py createsuperuser        # Create admin user
python manage.py runserver 8001         # Django admin on separate port
```

### First-time Migration (against Neon)
```bash
# Individual runners (one per migration)
python run_migration_01.py   # Core schema
python run_migration_02.py   # Product variants + reservations
python run_migration_03.py   # Waitlist table
python run_migration_04.py   # Luxury core tables
python run_migration_05.py   # Single brand refactor
python run_migration_06.py   # Schema alignment + mock tables
python run_migration_07.py   # 3D GLTF columns (model_3d_url, mesh metadata)

# Or run all at once:
python run_migration_all.py  # Migrations 01-07 in order
```

### Integration Tests
```bash
python -m pytest app/tests/test_catalog.py -v   # 12 tests covering all 4 PDP features
python -m pytest app/tests/test_flow.py -v      # 15 tests covering lifespan, storefront, cart, dashboard, admin, waitlist, checkout
python -m pytest app/tests/test_dpp.py -v       # 13 tests for DPP cryptographic security
python -m pytest app/tests/test_avatar_flows.py -v  # 12 tests for avatar profile binding & gender filtering
python -m pytest app/tests/test_admin_crud.py -v  # Admin panel security and lifecycle tests
python -m pytest app/tests/ -v                  # Run all 61 tests
```
- **Test coverage:** Allocation gatekeeper, Digital atelier (cm/in), WhatsApp concierge (tamper/valid/missing), Capsule matrix (multi-value/OOB swap/deduplication), Session persistence, Lifespan pool binding, Storefront editorial, HTMX grid, Cart (empty/missing/invalid variant), Dashboard (metrics/stock update), Admin inventory (reservations/reserve), Waitlist (missing/invalid email), Checkout (empty cart/shipping summary), Debug PDP, Avatar profile binding, Gender validation, Admin security boundaries, Lifecycle operations, Audit log structure, Admin security boundaries, Lifecycle operations
- **Note:** Tests require `.env` with `DATABASE_URL` (loaded via `python-dotenv` at app startup)

---

## Design System

- **Source of truth:** `design.md` — comprehensive 8-section document covering visual tokens, typography, component archetypes, Three.js WebGL specs (rendering, PBR, lighting, disposal), HTMX/Alpine integration patterns, route registry, database schema reference, and file structure
- **Color palette:** 9-token system with iridescent Gen-Z gradient meshes (`from-fuchsia-300/30 to-cyan-200/20`, `blur-[120px]`) and glassmorphism panels (`backdrop-blur-2xl bg-white/40`)
- **Typography triad:** Playfair Display (editorial headings), Inter (UI/utility), Monospace (metrics/pricing)
- **Component library:** 6 archetypes — Luxury Product Card, Digital Product Passport (DPP), 3D Virtual Showroom Panel, 3D Virtual Dressing Room, Transfer Escrow Block, Cart Drawer
- **Three.js:** Transparent WebGL canvas, ACESFilmic tone mapping, PCFSoftShadowMap, PBR profiles (clearcoat 0.2, roughness 0.3, metalness 0.1), `safelyPurgeThreeAsset()` disposal routine
- **Event bus:** `load-showroom-model`, `swap-clothing`, `inspect-showroom-product` custom events bridging Alpine.js → Three.js
- **DB extensions:** `products.model_3d_url` (VARCHAR 512), `products.apparel_layer_depth` (INTEGER), `products.model_usdz_url` (VARCHAR 512), `product_variants.mesh_node_identifier` (VARCHAR 100), `product_variants.custom_shader_color` (VARCHAR 7), `product_variants.morph_target_index` (INTEGER) — added via migration 07, seeded with paths pointing to actual `.glb` files in `static/models/`
- **storefront.py** — Homepage, PDP, and HTMX grid queries now include `model_3d_url` and expose `has_3d_model` flag in context
- **3D badges:** Product cards (`product_grid.html`, `index.html`) show a gold "3D" badge with animate-ping dot linking to `/virtual-experience` when `product.has_3d_model` is True. PDP template (`product_detail.html`) shows a "View in 3D Atelier" button with 3D cube icon when `product.model_3d_url` is set.
- **Admin dashboard 3D column:** `admin/dashboard.html` now includes a per-product inline edit field for `model_3d_url` (shown once per product across variant rows). Powered by new `POST /admin/dashboard/update-model-url` endpoint.

## Key Design Decisions

1. **Split runtime:** Starlette handles HTTP/rendering (low latency), Django handles data/admin/signing (transactional safety)
2. **No JavaScript frameworks:** HTMX for all server communication, Alpine.js only for client UI state (accordion, unit toggle, cart drawer)
3. **`lines` not `items`:** Cart data uses `lines` key to avoid conflict with `dict.items()` in Jinja2
4. **Starlette 1.0 TemplateResponse:** `TemplateResponse(request, "name", {context})`
5. **Circular import prevention:** `app/core.py` holds shared templates/helpers, imported by all routes
6. **Graceful email:** Brevo emails skip silently when API key is placeholder
7. **Atomic stock:** SELECT FOR UPDATE row locking prevents oversell across concurrent requests
8. **HMAC concierge tokens:** Django Signer with salt prevents URL tampering without database lookup
9. **Capsule dict access:** Use `product.capsule_look['items']` (not `.items`) to avoid dict method collision
10. **Background tasks:** `asyncio.create_task` for reservation settlement (not Starlette BackgroundTasks, which blocks TestClient)
11. **Dual-route architecture:** DB-backed routes (`luxury_extensions.py`) for persistent state, session-based routes (`catalog/routes.py`) for ephemeral PDP interactions
12. **OOB cart updates:** Capsule endpoint uses `hx-swap-oob="true"` to update `#cart-counter` in nav without full page re-render
13. **Path collision avoidance:** Atelier session endpoint uses `/catalog/atelier/bind` to avoid conflict with DB-backed `/catalog/waitlist`
14. **Mount-based catalog routing:** Catalog Interaction Engine uses `Mount("/catalog", routes=...)` — routes export as `routes` (not `catalog_routes`), paths are relative (no `/catalog` prefix)
15. **Lazy route registration:** `_register_route_modules()` imports route lists after app factory creation to prevent circular dependency chain
16. **app.state.db_pool:** Database pool exposed via `app.state.db_pool` (set in lifespan) for route handlers that need direct pool access (luxury_extensions.py)
17. **Django Signer at import:** `django.setup()` called at module level in luxury_extensions.py to enable `Signer(salt="asiko.concierge.vector")` initialization
18. **Settlement service layer:** `app/services/settlement.py` owns Paystack HMAC, shipping matrix, reservation workers — extracted from webhooks.py for separation of concerns
19. **asyncio.create_task workers:** Reservation expiry uses `asyncio.create_task` (not Starlette BackgroundTasks) to prevent TestClient hangs during test runs
20. **Pool allocation via os.getenv:** `database.py` reads `DATABASE_URL` from environment directly (no Starlette Config dependency); `sys.exit(1)` on missing URL
21. **Pool settings:** min_size=2, max_size=10, command_timeout=30.0, max_inactive_connection_lifetime=300.0
22. **Lifespan pool binding:** `app.state.db_pool = await init_db_pool()` — pool returned directly from allocator, no intermediate getter call
23. **dotenv at entry:** `load_dotenv()` called at top of `main.py` before any `os.getenv` calls, ensuring `.env` is loaded for all downstream modules
24. **Storefront PDP with capsule lookups:** `storefront.py` queries `asiko_capsule_assignments` to find sibling products in the same capsule look, formats them into `product.capsule_look['items']` for Jinja2 iteration
25. **Concierge token in PDP:** `storefront.py` generates Django Signer tokens (`salt="asiko.concierge.vector"`) at render time, binding product ID + slug to the WhatsApp bridge
26. **Slug generation:** Products lack a `slug` column; slugs are generated from product names via `_slugify()` in `storefront.py`
27. **Homepage ownership:** Homepage moved from `main.py` to `storefront.py`; `global_routes` no longer defines `/` — registered via `_register_route_modules()` instead
28. **Route export convention:** `storefront.py` exports as `routes` (not `storefront_routes`); `main.py` imports as `from app.routes.storefront import routes as storefront_routes`
29. **Product data aliases:** PDP context includes both `base_price` and `price`, plus `primary_image_url` alias for `base_image`, ensuring template compatibility across schema versions
30. **Session-based cart:** PDP reads cart from `request.session.get("cart", ...)` directly, bypassing `get_cart_from_session()` helper for independence from core.py cart utilities
31. **Variant-based cart:** Cart lines use `variant_id` (not `product_id`) as the unique key; queries `product_variants` JOIN `products` to fetch size/color/stock in a single round-trip
32. **Pre-flight oversell shield:** `cart_add` validates `stock_qty` against staged + incoming quantity before modifying session; returns OOB error div (`hx-swap-oob="true"`) on failure
33. **Cart route export:** `cart.py` exports as `routes` (not `cart_routes`); `main.py` imports as `from app.routes.cart import routes as cart_routes`
34. **Atomic checkout transaction:** `checkout_submit` wraps order creation in `async with conn.transaction()` with `SELECT ... FOR UPDATE` on `product_variants.stock_qty` to prevent race-condition oversell
35. **Direct pool checkout:** `checkout.py` uses `request.app.state.db_pool` directly instead of `database.py` helpers, enabling transaction context and row-level locking
36. **Checkout route export:** `checkout.py` exports as `routes` (not `checkout_routes`); `main.py` imports as `from app.routes.checkout import routes as checkout_routes`
37. **Session-based confirmation:** Order ID stored in `request.session["last_order_id"]` after checkout; confirmation page reads from session (not query param)
38. **Admin inventory routes:** `admin_inventory.py` exports as `routes` (not `admin_inventory_routes`); `main.py` imports as `from app.routes.admin_inventory import routes as admin_inventory_routes`
39. **Simplified sentinel:** Removed background worker and HTMX/JSON switching; admin endpoints return HTML-only responses with direct pool access via `request.app.state.db_pool`
40. **Stale hold eviction:** `POST /admin/settle` uses `UPDATE ... WHERE status='staged' AND created_at < NOW() - INTERVAL '60 minutes'` to flush expired reservations in bulk
41. **Waitlist route:** `waitlist.py` exports as `routes` (not `waitlist_routes`); `main.py` imports as `from app.routes.waitlist import routes as waitlist_routes`
42. **Idempotent waitlist:** `ON CONFLICT (email, variant_id) DO NOTHING` ensures duplicate registrations are silently absorbed without database errors
43. **Simplified waitlist:** Removed `trigger_restock_notifications` worker and HTMX/JSON switching; single endpoint returns HTML-only response with direct pool access
44. **Executive dashboard:** `admin_dashboard.py` provides metrics aggregation (revenue, pending orders, active holds, waitlist volume), inline stock updates via HTMX, batch restock email triggers via Brevo, and inline `model_3d_url` editing via `POST /admin/dashboard/update-model-url`
45. **Dashboard template:** `admin/dashboard.html` is a standalone HTML document (not extending `base.html`) with its own CDN imports for HTMX, Alpine.js, Tailwind, and Google Fonts. The inventory table includes a per-product 3D model URL input field (shown once per product using Jinja2 `namespace`) with live filename preview.
46. **Dashboard route export:** `admin_dashboard.py` exports as `routes`; `main.py` imports as `from app.routes.admin_dashboard import routes as admin_dashboard_routes`
47. **3D spatial columns:** `products.apparel_layer_depth` controls capsule look sorting; `products.model_usdz_url` supports Apple AR Quick Look; `product_variants.morph_target_index` maps parametric coordinate targets for morph animations
48. **Capsule layers endpoint:** `GET /api/virtual/capsule-layers` queries `asiko_capsule_assignments` → `products` → `product_variants` sorted by `apparel_layer_depth ASC`, returns HTML fragments with inline Alpine.js `$dispatch('layer-capsule-mesh', ...)` handlers
49. **Procedural fallback safety:** `virtual.py` includes `_PROCEDURAL_DEFAULTS` dict mapping null/missing `mesh_node_identifier` to safe defaults (`dress_form`, `blazer_form`, `trouser_form`, `top_form`); `_resolve_mesh()` and `_resolve_color()` helpers validate inputs before HTML emission
50. **Standalone Three.js engine:** `static/js/atelier-3d.js` (929 lines) — `AtelierEngine` class with parametric body-morph, multi-layer garment rendering, GLTFLoader integration, OrbitControls, WebXR/AR gateway, procedural geometry fallbacks, Alpine.js event bus integration, and `safelyPurgeThreeAsset()` disposal routine
51. **Procedural GLB generator:** `scripts/generate_glb_models.py` (505 lines) — pure-stdlib Python GLB generator with 7 garment-specific shape functions (`dress_form`, `blazer_form`, `trouser_form`, `top_form`, `draped_gown_form`, `structural_top_form`, `cyber_blazer_form`), `_lathe_profile()` revolve engine, PBR materials, generates 16-34 KB `.glb` files
52. **DPP cryptographic service:** `app/services/dpp_crypto.py` — Singleton `DPPCryptoService` with lazy Django settings initialization, uses `Signer(salt="asiko.concierge.vector")` matching concierge system salt for consistent anti-tampering
53. **DPP token structure:** Compact JSON payload `{p_id, sn, artisan}` signed via Django's cryptographic Signer; tamper attempts (suffix/prefix/corruption) return None for graceful failure
54. **DPP database ledger:** Migration 04_dpp_ledger adds provenance columns (`fabric_lineage`, `processing_dye_vector`, `living_wage_index`) and `product_serialized_passports` table for unique garment serial tracking
55. **Avatar wrapper group isolation:** `loadBaseAvatar()` mounts the imported GLTF inside an isolated `THREE.Group()` (`this.avatarWrapperGroup`) so the model's external coordinate system is decoupled from the scene root — internal offsets and uniform scaling can be applied without affecting the rest of the scene graph
56. **Defensive 1.6-unit normalization:** Every GLB avatar is compressed to exactly `1.6` virtual units of height after the `Box3` bounds are computed, regardless of how oversized the source asset file is. This guarantees consistent framing across male/female avatar swaps and prevents large meshes from spilling past the canvas bounds
57. **Camera track markers:** `defaultCamPosition = (0, 0.95, 2.3)` and `defaultTargetPosition = (0, 0.85, 0)` are stored on the engine instance and reused by `_initScene`, `resetCamera`, `loadBaseAvatar`, and the new `resetView` method — guarantees a single source of truth for the camera baseline
58. **Mid-torso camera anchor:** The default camera position sits at y=0.95 with the target at y=0.85, framing the model's torso (not the floor) by default. Pre-empts the "staring down at the shoes" regression that came from prior code anchoring the target to y=0.5
59. **OrbitControls zoom clamping:** `controls.minDistance = 0.7`, `controls.maxDistance = 4.5` clamp the dolly range to prevent users from zooming inside the avatar or so far out that it disappears from the canvas. Damping tightened to `0.05` for a more responsive feel
60. **Public zoom API:** `zoomIn()` / `zoomOut()` / `resetView()` are exposed as standalone public methods on the engine (not aliases for `resetCamera`). Wired to UI buttons via `onclick="if(window.__atelierEngine){ window.__atelierEngine.zoomIn(); }"` — no Alpine.js bridge needed, keeping the engine API surface clean and independent of the front-end framework
61. **Pointer-event isolation pattern:** `.atelier-canvas-wrap` keeps `pointer-events: auto` on the WebGL canvas (so OrbitControls drag still works) while `.atelier-canvas-wrap .pointer-events-auto { pointer-events: auto !important; }` opts overlays in explicitly. Repairs the "click registers on canvas instead of button" bug without breaking the 3D gesture system
62. **GPU memory hygiene on avatar swap:** `loadBaseAvatar` calls `safelyPurgeThreeAsset(this.avatarWrapperGroup)` on the prior wrapper before creating a new one — recursively disposes geometries, materials, and texture maps. Fixes a latent GPU memory leak that the previous code had (it only called `scene.remove()`, never disposed)
63. **Conservative UI refactor scope:** The zoom dock overlay was added to the existing primary container without replacing the Alpine.js-bound showroom/dressing room panels. Preserves all existing state bindings (`virtualAtelier`, `viewportControls`, `dressingRoom`) and avoids a 300+ line markup rewrite that would have introduced regressions
64. **Peak-dimension normalization (1.2 units):** `adjustModelToFitViewport` uses peak-dimension scaling (`1.2 / max(width, height, depth)`) rather than 1.6-unit height normalization — peak dimension is the correct metric for arbitrary Showroom products (a handbag, a shoe, a dress all have different "primary" dimensions) and 1.2 units gives a slightly more intimate frame than the 1.6-unit avatar baseline
65. **MeshCenter-aligned camera target:** After re-centering the mesh to origin, the camera target is set to `(0, recenteredSize.y / 2, 0)` — the vertical midpoint of the re-scaled model. This guarantees the user's gaze lands on the model's center, not the floor or the top
66. **Per-mesh `adjustModelToFitViewport` (not a wrapper group):** Unlike `loadBaseAvatar` which uses an isolated `THREE.Group()` wrapper, the new method operates directly on the incoming mesh. This is appropriate for the Showroom and Dressing Room paths where each model is its own scene composition (avatar is the only multi-child persistent reference frame)
67. **Algorithm scope — GLB-only:** The bounding-box framing runs only in GLTFLoader success callbacks, not in the procedural geometry fallback paths (DodecahedronGeometry, BoxGeometry). Fallbacks have known dimensions and don't need bounding-box analysis; running the algorithm on them would add unnecessary overhead
68. **Stratification scale trade-off:** The 1.0125-step per-layer scale offset in `loadAutomatedAsset` (designed to prevent z-fighting between layered garments) is now dominated by the peak-dimension 1.2-unit scale. With proper 1.2-unit framing per garment, the layer offset is no longer critical — garments on different layers now have visually distinct sizes relative to the avatar, not relative to each other
69. **Retail UX scope discipline:** The `app/templates/admin/dashboard.html` refactor removed only the "AI Mesh Engine" + "Pipeline Sandbox Operator" UI clutter; the underlying HTMX endpoints (`/admin/dashboard/pipeline/link-2d`, `/admin/dashboard/pipeline/simulate`, `/admin/dashboard/pipeline-status/{id}`) remain wired in the backend but are now unreferenced. Per the directive, this is a UI-layer scope only — the endpoints can be pruned in a future housekeeping pass
70. **`scale.set()` over `scale.multiplyScalar()` for incoming GLBs:** The directive's algorithm uses `incomingMesh.scale.set(targetScale, targetScale, targetScale)` to OVERRIDE any pre-existing scale baked into a source GLB file. The alternative `multiplyScalar()` would compound with the existing scale (e.g., a 100x handbag at 1.2/100 = 0.012 multiplied by 100 = 1.2, working; but a 0.5x miniature dress at 1.2/0.5 = 2.4 multiplied by 0.5 = 1.2, also working but accidentally). With `.set()`, the result is always exactly 1.2 peak dimension regardless of source scale. `.set()` is the deterministic, correct choice for arbitrary incoming GLB content
71. **In-place `-=` for x/z vs absolute `=` for y:** The directive's algorithm uses `position.x -= meshCenter.x; position.z -= meshCenter.z` (in-place subtraction) for horizontal centering — this preserves any prior x/z offset the loader set (e.g., `position.set(0, 0, 0)` for footwear, which subtracts 0). For y, it uses absolute `position.y = -boundsBox.min.y` to force floor-anchoring at exactly y=0, regardless of any prior `position.y` value (overriding the `position.y = 0.05` in `loadAutomatedGarment`). This asymmetry is intentional: horizontal centering is a relative operation, but floor anchoring is an absolute constraint
72. **Reused `Vector3` instances in bounds re-evaluation:** Post-scale, the directive reuses the original `meshSize` and `meshCenter` Vector3 instances (`boundsBox.getSize(meshSize); boundsBox.getCenter(meshCenter)`) instead of allocating new ones. Minor memory optimization, but it signals that the directive is optimized for production Three.js workloads where hundreds of asset swaps can occur in a session
73. **`if (this.controls)` defensive guard:** The camera update at the end of `adjustModelToFitViewport` is guarded by `if (this.controls)` because `OrbitControls` is initialized asynchronously after the engine constructor. If a GLB fires its success callback before the controls are ready (rare but possible during preconnect asset prefetching), the guard prevents a `TypeError: Cannot read property 'target' of undefined`
74. **Card list replaces 4-column table:** The `Atelier Production Ledger` table (4 columns: Apparel Coordinate Name, Variant Dimensions, On-Hand/3D Model, Status) was REPLACED with a vertical card list where each variant is a standalone `REFACTORED PREMIUM PRODUCTION ROW` card. Cards stack on mobile (`flex-col`) and switch to `flex-row` on `lg+` screens, giving boutique owners a more "atelier inventory display" feel than a "spreadsheet" feel
75. **Two-form preservation per card:** The card design preserves the two existing HTMX forms (`/admin/dashboard/update-stock` and `/admin/dashboard/update-model-url`) as inline pill-shaped fields within each card, rather than consolidating them into a single "Update Ledger" button. This is a deliberate minimal-disruption choice — the backend endpoints are unchanged and the operators' muscle memory for two distinct save actions is preserved
76. **HTMX response target containers preserved at card footer:** The `#status-variant-{id}` and `#model-status-{product_id}` divs are kept at the bottom of each card (renamed from the original "inline" position to the card footer). The HTMX endpoints swap their response HTML into these containers, so the green "Saved!" feedback still works without changing the response markup on the backend side
77. **Avatar 1.6/rawHeight normalization (per directive):** The new `loadBaseAvatar` and `loadHumanAvatar` both compute `rawHeight = boundsBox.getSize().y` BEFORE any scaling, then apply `targetScaleFactor = 1.6 / rawHeight` via `rawModel.scale.set(...)`. This guarantees a uniform 1.6-unit avatar height across all incoming GLB files regardless of source asset scale (a 5m oversized source becomes 1.6 units; a 0.5m miniature source becomes 1.6 units). The previous hardcoded `scale.set(1.6, 1.6, 1.6)` would not work correctly for a source that's already 1.6 units tall (it would scale it 1.6x larger); the 1.6/rawHeight formula is scale-invariant
78. **Scale to rawModel, not avatarWrapperGroup:** The directive applies the scale transform to the raw GLTF model (`rawModel.scale.set(...)`), then re-evaluates bounds and positions. The previous implementation scaled the `avatarWrapperGroup` (the parent group) instead, which means the raw model's internal position offset for floor-anchoring was applied at the wrong scale. The directive's approach is more direct: scale the raw model first, then position it within the now-empty wrapper. The wrapper group remains a clean container with identity scale/rotation
79. **In-place `position.x -=` for avatar centering:** The directive uses `rawModel.position.x -= meshCenter.x` (in-place subtraction) for horizontal centering, which preserves any prior x/z offset the source GLB may have baked in. For the y-axis it uses absolute `position.y = -boundsBox.min.y` to force the model to sit exactly on the y=0 floor regardless of source y position. This asymmetry matches `adjustModelToFitViewport`'s strategy in Section 11b — horizontal centering is a relative operation, floor anchoring is an absolute constraint
80. **Inline camera position fallback:** The new `loadBaseAvatar` uses `this.camera.position.copy(this.defaultCamPosition || new THREE.Vector3(0, 0.95, 2.3))` and `this.controls.target.copy(this.defaultTargetPosition || new THREE.Vector3(0, 0.85, 0))` — the `||` fallback inline values match the constructor track markers exactly. This makes `loadBaseAvatar` self-sufficient: it can be called before the constructor finishes (rare but possible during preconnect) without throwing on undefined camera baselines
81. **`loadProceduralAvatarFallback()` wrapper for gender-agnostic entry:** The directive's `loadBaseAvatar` error path calls `loadProceduralAvatarFallback()` with no arguments. The existing procedural fallback is `triggerProceduralFallbackForm(gender)` (parameterized). The new `loadProceduralAvatarFallback` method (line 1380) is a thin wrapper: `const gender = this.currentGender || 'female'; this.triggerProceduralFallbackForm(gender);` — provides the parameterless call site the directive expects, with a sensible default gender
82. **`loadHumanAvatar` adopts the same 1.6/rawHeight algorithm:** Previously used `position.set(0, -1.0, 0)` and `scale.set(1.0, 1.0, 1.0)` — static values that did not adapt to source asset scale. Now uses the same `1.6 / rawHeight` algorithm as `loadBaseAvatar`. Both avatar loaders now share a unified normalization strategy; the only difference is whether the result goes into `this.avatarWrapperGroup` (loadBaseAvatar) or directly into the scene (loadHumanAvatar)
83. **`try/catch` over Promise wrappers for GLB load failures:** The new `loadBaseAvatar` and `loadHumanAvatar` use `try/catch` with `loadAsync` (modern promise-based) instead of the previous `gltfLoader.load(url, onSuccess, onProgress, onError)` callback pattern. Cleaner control flow, automatic `async`/`await` integration, and the error handler is colocated with the success path rather than split across callbacks
84. **PBR pipeline applied AFTER mount, not before:** The directive applies shadow and PBR configuration (`roughness=0.65`, `metalness=0.1`, `castShadow`, `receiveShadow`) AFTER `avatarWrapperGroup.add(rawModel)`. The previous implementation applied it before, which meant the traverse was operating on a detached subtree. Post-mount traversal guarantees the full hierarchy is reached (since the wrapper may have child nodes from prior avatar loads that need cleanup)
85. **`isAvatar` parameter on `adjustModelToFitViewport` (boolean, default false):** Unifies the 1.6-unit avatar normalization and 1.2-unit garment/showroom normalization under a single method. `isAvatar=true` → `targetPeak = 1.6`; `isAvatar=false` (default) → `targetPeak = 1.2`. The flag-driven design replaces the previous duplication where `loadBaseAvatar` and `loadHumanAvatar` had inline 1.6/rawHeight logic while `loadShowroomModel`, `loadAutomatedAsset`, and `loadAutomatedGarment` called the 1.2-unit `adjustModelToFitViewport` method. Cleaner, single source of truth, and the parameter is self-documenting at the call site
86. **Defensive foot lift +0.06 units on all models:** `position.y = -boundsBox.min.y + 0.06` (was `-boundsBox.min.y` in Task 3/4). Applied to BOTH avatar and garment paths uniformly — lifts shoe hems and garment hems 0.06 units out of the pedestal floor to prevent the "shoes sinking into the ground" visual artifact. Produces a luxury fashion "floating on a display form" aesthetic, consistent with high-end retail display fixtures
87. **Luxury textile PBR baseline (roughness 0.85, metalness 0.0, sheen 0.6, sheenRoughness 0.4):** Replaces the previous 0.65/0.1 PBR pair. `roughness=0.85` erases the "plastic shine" and produces a matte fabric look; `metalness=0.0` confirms non-metallic textile; `sheen=0.6` adds the subtle "fuzz" of woven fibers at grazing angles; `sheenRoughness=0.4` controls the falloff of the sheen. Guarded by `node.material.isMeshStandardMaterial` so the procedural fallback's `MeshPhysicalMaterial` instances are not mutated (the check is a defensive type guard, not a feature flag)
88. **Studio lighting rig (hemisphere + key + gold rim):** Replaces the previous 4-light setup (ambient + key + fill blue + rim + accent point) with a focused 3-light rig. **HemisphereLight** (sky 0xffffff, ground 0x444444, intensity 1.2) flattens shadowed crevices; **Key DirectionalLight** (0xfffdf6 warm white, intensity 1.8) is the main light source from front-right with shadow mapping; **Gold Rim DirectionalLight** (0xd4af37 brand gold, intensity 1.0) is a back-left silhouette glow that matches the brand token. The fill blue light and accent point light were removed because they created cold hotspots and broke the warm editorial mood
89. **Shadow map upgrade 1024→2048:** `key.shadow.mapSize.width = 2048` (was 1024). Higher resolution produces crisp fabric weave detail in the shadow map (you can see the texture of a denim jacket, not just a blob). Memory cost: 4× the shadow atlas size, ~4MB GPU memory. Worth the visual fidelity tradeoff for a luxury retail use case
90. **Touch-optimized OrbitControls (`rotateSpeed=1.8`, `touchRotateSpeed=2.2`):** The default 1.0 values felt sluggish on mobile. `rotateSpeed=1.8` boosts desktop drag by 80%; `touchRotateSpeed=2.2` boosts mobile single-finger spin by 120%. The asymmetric values (touch > desktop) reflect that touch users expect a more direct, less "weighty" feel — desktop drag has a long legacy of "smooth & weighted" UX that should not be replicated on touch
91. **`dampingFactor=0.08` (was 0.05):** Slightly looser damping produces a more tactile, momentum-rich feel. The previous 0.05 was so tight that drags felt "stuck" — like dragging on rubber. 0.08 still has visible momentum continuation but feels immediate. Combined with the boosted rotateSpeed values, the overall feel is "responsive but not flicky"
92. **`screenSpacePanning = false`:** Pan is depth-relative (camera moves parallel to the world XY plane at the target depth) instead of screen-space (camera moves in screen X/Y). Screen-space panning on a wide canvas can fling the camera off into infinity when the mouse reaches the canvas edge. Depth-relative panning constrains the camera to a sphere around the target — much harder to lose the model
93. **`executeVectorZoom(zoomFactor)` over native `dollyIn`/`dollyOut`:** OrbitControls.dollyIn/dollyOut have known issues with perspective cameras and target-relative framing (they scale the camera's distance to the target by a fixed factor, which can break perspective projection). Direct distance-vector math (compute `offset = camera.position - controls.target`, multiply, re-anchor) is more predictable and gives a single source of truth for the clamp boundaries. Also enables the 0.6–5.5 unit safety clamp that prevents the camera from entering the model's chest cavity (visual artifact) or zooming out into infinity (blank frame)
94. **Safety clamp 0.6 → 5.5 world units on zoom:** `minDistance=0.6` (was 0.7 in OrbitControls defaults; 0.8 in `adjustModelToFitViewport` for the garment path) prevents the camera from clipping into the avatar's chest. `maxDistance=5.5` (was 4.5 in OrbitControls defaults; 5.0 in `adjustModelToFitViewport`) prevents the camera from zooming out so far that the model becomes a single pixel. The wider clamp range vs `adjustModelToFitViewport` reflects that the zoom buttons can be pressed repeatedly, so each press should produce visible motion even at the extremes
95. **`window.__atelierEngine = this;` global exposure in the constructor:** The double-underscore prefix marks it as an internal-but-globally-accessible handle (the prefix convention comes from Python's "private by convention, accessible when needed"). Set in the constructor right after `_initScene()` returns — at this point the camera, renderer, controls, and lights are all initialized, so any external caller can use the global immediately. The `virtual_experience.html` JS init code (line 622) also assigns `window.__atelierEngine = engine;` for symmetry with the inline `onclick` handlers in the same file
96. **Reset button defensive inline JS fallback:** `if(window.__atelierEngine && typeof window.__atelierEngine.resetView === 'function'){ window.__atelierEngine.resetView(); } else if(window.__atelierEngine){ window.__atelierEngine.camera.position.set(0, 1.2, 3.5); window.__atelierEngine.controls.target.set(0, 0.8, 0); window.__atelierEngine.controls.update(); }`. The fallback path manually snaps camera + controls to safe defaults if `resetView` is undefined (e.g., engine init race, partial page load, mid-page navigation). The fallback values are slightly different from the constructor track markers — they target the wider showroom viewport `(0, 1.2, 3.5)` / `(0, 0.8, 0)` rather than the mid-torso avatar framing `(0, 0.95, 2.3)` / `(0, 0.85, 0)`. This dual-default strategy reflects the dual-mode use of the engine: showroom mode wants a wider frame, avatar mode wants a tighter mid-torso frame
97. **`touch-manipulation` Tailwind class on all zoom dock buttons:** Disables iOS Safari's 300ms double-tap zoom delay on the buttons (a common UX papercut on mobile Safari). Without this class, tapping the `+` zoom button would wait 300ms before registering, making the controls feel laggy. Combined with `select-none` (prevents text selection on long-press drag), the dock feels native on both iOS and Android
98. **`select-none` Tailwind class on the zoom dock wrapper:** Prevents accidental text selection when the user drags across the dock (e.g., rotating a model by dragging from inside the dock boundary). Without this class, the drag gesture can select text inside nearby HUD elements. The class is also applied to the brand watermark (line 192) and a few other decorative-only elements throughout `virtual_experience.html`
99. **`loadBaseAvatar`/`loadHumanAvatar` delegate to `adjustModelToFitViewport`:** The previous implementations had 18-30 lines of duplicated inline normalization logic per loader (compute bounds, scale, center, anchor). The refactored loaders replace that block with a single line: `this.adjustModelToFitViewport(rawModel, true);` (or `this.currentAvatarMesh` for the human variant). This is "delegation over duplication" — the unified method is the single source of truth, and the loaders focus on their specific concerns (wrapper group management, camera/controls refresh, shadow flags, error path)
100. **Idempotent light wipe in `initStudioLighting`:** `this.scene.children.filter((c) => c.isLight).forEach((l) => this.scene.remove(l))`. The `isLight` predicate is a duck-type check (any object with `isLight=true` is a light source — Three.js base classes set this on `Light`, `DirectionalLight`, `HemisphereLight`, etc.). The wipe is critical because `_initScene()` calls `initStudioLighting()` once at startup, but if the engine is re-initialized (e.g., HMR, navigation back to the page), the old lights would persist. The wipe guarantees a clean state on every call
101. **`NoCacheStaticFiles` anti-304 bypass:** Starlette's `StaticFiles` class has a built-in `is_not_modified()` method that short-circuits requests with `304 Not Modified` responses when the client sends `If-Modified-Since` / `If-None-Match` headers. In development, this optimization causes stale 3D engine code to be served from the browser cache after edits. The `NoCacheStaticFiles` subclass forces `is_not_modified` to return `False` (disabling the 304 short-circuit) AND intercepts the response headers to inject `Cache-Control: no-cache, no-store, must-revalidate, max-age=0`. Two-layer enforcement is needed: Layer 1 prevents server-side short-circuit, Layer 2 prevents client-side caching
102. **Three cache-busting headers (modern + legacy):** `Cache-Control: no-cache, no-store, must-revalidate, max-age=0` (modern standard, supported by all current browsers and CDNs), `Pragma: no-cache` (HTTP/1.0 backward compatibility for very old proxies and CDNs), `Expires: 0` (legacy timestamp-based cache invalidation for IIS / older Apache configurations). All three are sent together because the directive targets "all local dev cycles" — picking up older proxies in the dev toolchain is a known papercut
103. **Frontend query-parameter cache-buster for ES modules:** The `import { initAtelierEngine } from '/static/js/atelier-3d.js?v={{ range(1000, 9999) | random }}';` line uses a Jinja2 expression to append a random integer in `[1000, 9999]` to the URL. ES module imports DO respect query parameters for cache-busting — the browser treats `/static/js/atelier-3d.js?v=4729` as a distinct URL from `/static/js/atelier-3d.js`, so it refetches the module on every page load. The query parameter is regenerated on every HTML render, so the browser sees a "new" URL every time
104. **`super().__call__()` delegation in `__call__` override:** The `NoCacheStaticFiles.__call__` method defines an inner `intercepted_send` closure that mutates the headers and then calls the original `send` callback. After defining the closure, it calls `await super().__call__(scope, receive, intercepted_send)` — passing the closure as the `send` parameter. This pattern is the standard ASGI middleware approach: wrap the downstream `send` to intercept specific message types (`http.response.start` for headers, `http.response.body` for content)
105. **Why a single-file cache buster beats CDN cache invalidation:** In a production environment, a content change to `atelier-3d.js` would normally require a CDN purge (Cloudflare, CloudFront, Fastly) to force the new version to propagate. With the dev-time query parameter cache buster, the URL changes on every page load, so even a stale CDN edge node would return a "miss" and refetch from the origin. The query parameter approach is also cheaper than a CDN purge (which costs money or has rate limits)
106. **Defensive `loadBaseAvatar` rewrite with 5 resilience layers:** The new version wraps the entire flow in `try/catch/finally` with type guards on helper methods and a guaranteed loading-overlay dismiss. The five layers (purge try/catch, type guard on purger, type guard on normalizer, finally-block dismiss, literal camera vectors) ensure the canvas is always visible even if the avatar GLB fails to parse, the helper methods are missing, or the constructor initialization order is racy
107. **Type guards on helper methods (`typeof this.X === 'function'`):** Defensive `if (typeof this.safelyPurgeThreeAsset === 'function')` and `if (typeof this.adjustModelToFitViewport === 'function')` checks. JavaScript classes are dynamic — a method can be monkey-patched, deleted, or never defined (e.g., if a parent class is partially loaded). The type guard ensures the call site never throws `TypeError: this.safelyPurgeThreeAsset is not a function`. The fallback paths (`scene.remove`, "skip normalization") are degraded but safe — the canvas still shows
108. **`finally` block for guaranteed loading overlay dismiss:** Using a `finally` block (instead of relying on the success or error path) is the only way to guarantee the loading indicator is hidden regardless of which code path executes. The success path may set `setViewportLoadingState(false)` but a thrown error before that call would leave the indicator up. The `finally` block uses raw DOM (`document.getElementById`, `document.querySelector`) instead of the engine's helper, so the dismissal works even if the engine's state machine is in a corrupt state
109. **Triplicate loading indicator dismissal (`display: 'none'` + `opacity: '0'` + `classList.add('hidden')`):** Three different mechanisms to ensure the loading overlay disappears regardless of how it was hidden in the template. `display: 'none'` removes the element from the layout flow. `opacity: '0'` fades it visually (covers CSS animations that override `display`). `classList.add('hidden')` is the Tailwind utility class (covers templates using the `hidden` class for responsive visibility)
110. **Spline runtime in `<head>` for race-free mount:** The `<script type="module" src="https://unpkg.com/@splinetool/viewer@1.9.0/build/spline-viewer.js"></script>` script is placed in `<head>` so the `<spline-viewer>` custom element is defined BEFORE the card markup is parsed. If the script were at the bottom of `<body>`, the custom element would be undefined when the parser encountered `<spline-viewer>` and the element would silently no-op (browsers don't queue unrecognized custom elements)
111. **Alpine.js mouse tracking for cursor-following spotlight:** The `x-data="{ mouseX: 0, mouseY: 0, isHovered: false }"` state plus `@mousemove="const boxRect = $el.getBoundingClientRect(); mouseX = $event.clientX - boxRect.left; mouseY = $event.clientY - boxRect.top;"` handler computes the cursor's local position inside the card. The `:style` binding then positions the radial gradient at `(mouseX - 160, mouseY - 160)` to center the 320×320 radial under the cursor. The `transform: translate3d(0,0,0)` triggers GPU compositing so the position updates don't trigger layout/paint — just compositing
112. **SVG ambient spotlight with Gaussian blur 151:** The backdrop SVG uses `<feGaussianBlur stdDeviation="151">` to produce a very soft, large-radius glow. The blur is intentionally extreme (151 stdDeviation is ~1/3 of the canvas height) to create the "diffuse warm light from above" mood lighting. The ellipse is positioned at `transform="matrix(-0.822377 -0.568943 -0.568943 0.822377 3631.88 2291.09)"` (a 39° rotation with a translation) to position the hotspot in the upper-right quadrant of the card, creating a directional lighting feel
113. **Triple blend mode stack for gold spotlight glow:** `mix-blend-screen` followed by `mix-blend-plus-lighter` (the directive has both classes; the second is the more aggressive variant of the first). `mix-blend-screen` lightens the underlying pixels; `mix-blend-plus-lighter` adds the colors directly. Stacking them produces a "twice-as-bright" gold glow effect that wouldn't be possible with either alone
114. **Spline as a marketing visual sandbox:** Spline scenes run in their own sandboxed context (similar to an iframe) — the parent page's JavaScript (`__atelierEngine`, Alpine.js state) cannot be accessed by the Spline scene. This is by design: the marketing team can iterate on the 3D scene without worrying about breaking the configurator engine, and the configurator engine state cannot be polluted by the Spline scene. The trade-off is no programmatic interop (e.g., the Spline scene can't react to the avatar gender selector); use the Three.js engine for that
115. **Literal `Vector3(0, 0.95, 2.3)` over `defaultCamPosition` track markers:** The defensive `loadBaseAvatar` uses literal `this.camera.position.set(0, 0.95, 2.3)` instead of `this.camera.position.copy(this.defaultCamPosition || new THREE.Vector3(0, 0.95, 2.3))`. The literal values match the constructor track markers exactly, but don't depend on the engine instance having those markers initialized. If the loader is called before the constructor finishes (rare but possible during preconnect), the literal values still produce a sensible camera position
116. **Dropping `loadProceduralAvatarFallback()` from `loadBaseAvatar` error path:** The previous version called `this.loadProceduralAvatarFallback()` on GLB parse failure. The defensive rewrite drops this call in favor of just logging the error and falling through to the `finally` block. Rationale: the directive prioritizes "always show the canvas" over "always show a procedural avatar" — if the GLB fails, the user should see the (empty) canvas immediately rather than wait for a procedural fallback form. If the user needs an avatar, they can use the Femme/Homme dock to retry with a different GLB
117. **21st.dev premium dark interactive theme:** The new canvas wrap in Section 11g aligns with the "premium interactive" 21st.dev aesthetic — dark background (`black/[0.96]`), gold accents (`#D4AF37` for the radial gradient and eyebrow tag), white-to-zinc gradient on the headline (`from-white to-zinc-400`), and zinc-400 body copy. The 500×500px cursor-following radial gold gradient with `blur-2xl` is the signature visual — when the user moves the mouse over the card, a soft gold glow follows the cursor, creating an immediate "interactive premium" feel
118. **500×500px cursor-following radial gradient (vs 320×320px in v1):** The new canvas wrap uses a larger 500×500 radial (vs the Spline card's 320×320) to cover more of the canvas area. The larger size means the spotlight feels more "ambient" rather than "focused" — appropriate for the primary canvas wrap (which is bigger and more important than the now-removed Spline card). The position offset is also updated: `${mouseX - 250}px` (vs the Spline card's `mouseX - 160` for the 320 size) to center the 500px radial at the cursor
119. **Defensive mouse-move guard (`if($el === $event.target || $el.contains($event.target))`):** The v1 Spline card used `const boxRect = $el.getBoundingClientRect(); mouseX = $event.clientX - boxRect.left;` (no event target check). The new canvas wrap adds a defensive guard: `if($el === $event.target || $el.contains($event.target))` — only update mouse position if the event target is the card itself or a descendant. This prevents stray events (e.g., from a parent container or a sibling) from updating the spotlight state. More reliable than `event.target === event.currentTarget` (which fails when the event bubbles up through child elements)
120. **`canvas-loader` ID (new loader element, replaces `three-loading-overlay`):** The new canvas wrap uses `id="canvas-loader"` for the loading overlay (replaces the previous `three-loading-overlay` ID from the v1 architecture). The naming is more descriptive of the loader's purpose (it's loading the canvas, not just any "three" element) and follows the convention of `<context>-<role>` IDs used elsewhere in the codebase (e.g., `atelier-3d-viewport`, `canvas-3d-target` historically)
121. **300ms opacity-then-display fade (replaces v1's triplicate dismissal):** v1 used three mechanisms (`display: 'none'` + `opacity: '0'` + `classList.add('hidden')`) to dismiss the loader. v2 uses a single mechanism: `uiLoader.style.opacity = '0'; setTimeout(() => { uiLoader.style.display = 'none'; }, 300);`. The 300ms delay matches the CSS `transition-all duration-300` on the loader element, producing a smooth fade-out animation. The v1 triplicate was redundant and produced a jarring instant disappear
122. **Loader lookup hoisted to function top (closure capture):** The v2 `loadBaseAvatar` declares `const uiLoader = document.getElementById('canvas-loader') || document.querySelector('.loader');` as the FIRST statement in the function (before the try block). This means the `finally` block can reference the same element via closure capture — the lookup happens once, the reference is stable, and the dismissal always operates on the same element the visibility setting was applied to. v1 looked up the loader inside the `finally` block, which could find a different element if the DOM changed during the load
123. **Loader FORCED VISIBLE at start (not just at end dismissal):** v2 sets `uiLoader.style.display = 'flex';` at the very top of `loadBaseAvatar` to enforce the loading state. This is important if the user clicks a "retry" button after a previous load failed (the loader was dismissed to `display: 'none'`, but now needs to be visible again). v1 didn't do this — it assumed the loader was already visible. The v2 pattern guarantees the loader is visible during every load attempt
124. **No type guards in v2 (direct calls to helpers):** v1 had `if (typeof this.safelyPurgeThreeAsset === 'function')` and `if (typeof this.adjustModelToFitViewport === 'function')` defensive checks. v2 removes these because the engine is stable, the methods are all defined in the constructor, and silent fallbacks mask real bugs. If a method IS missing, v2 throws a loud `TypeError` which is more diagnostic than the silent fallback. The v1 type guards were appropriate during the engine's incremental build phase but are now over-engineering
125. **Updated camera baseline `Vector3(0, 1.1, 2.4)` (was `Vector3(0, 0.95, 2.3)`):** v2 uses a slightly higher y position (1.1 vs 0.95) and slightly farther z position (2.4 vs 2.3) for the camera. The new positions match the larger 600px canvas wrap height better than v1's positions (which were tuned for the smaller 400px previous canvas). The target remains `(0, 0.85, 0)` for the mid-torso avatar anchor
126. **`dampingFactor=0.05` in `loadBaseAvatar` (overrides constructor's 0.08):** v2 explicitly sets `this.controls.dampingFactor = 0.05` after the camera reset, overriding the constructor's `initInteractionControls` value of 0.08. The override is intentional: the constructor's 0.08 produces a more momentum-rich feel for the wider showroom viewport, but `loadBaseAvatar` needs a tighter 0.05 for the avatar-tighter framing (less momentum = more precise). Per-call tuning beats global defaults when the use case varies
127. **Placeholder canvas removal before engine init:** The new canvas wrap includes a static `<canvas id="atelier-3d-viewport">` element (used by the CSS for the `w-full h-full` styling). The init script REMOVES this placeholder before the engine init: `const placeholderCanvas = document.getElementById('atelier-3d-viewport'); if (placeholderCanvas) placeholderCanvas.remove();`. This is necessary because the engine creates its own WebGL canvas via `container.appendChild(this.renderer.domElement)` — if the placeholder is still in the container, the engine would create a second canvas (stacked-canvas bug)
128. **Container class (`.atelier-canvas-wrap`) over container ID:** The new canvas wrap uses `class="... atelier-canvas-wrap"` instead of `id="canvas-3d-target"`. The init script uses `document.querySelector('.atelier-canvas-wrap')` instead of `document.getElementById('canvas-3d-target')`. Classes are appropriate here because the container is one of multiple elements inside the flex layout (the outer card wrapper is the unique document-level element; the canvas container is a styled child). The class also enables the existing CSS pointer-event isolation rules (`.atelier-canvas-wrap { position: absolute; inset: 0; }` and `.atelier-canvas-wrap > canvas { pointer-events: auto; }`) to continue working without changes
129. **Spline card + runtime removal (simplification):** The Spline spotlight card (with mouse-tracking Alpine.js state, SVG ambient spotlight, cursor-following radial gradient, `<spline-viewer>` embedded scene) and the `<script type="module" src="https://unpkg.com/@splinetool/viewer@1.9.0/build/spline-viewer.js">` runtime script in `<head>` were REMOVED entirely in Section 11g. The new directive's premium dark interactive canvas wrap provides the same visual interest (mouse-tracking spotlight, gold accents, dark editorial background) as the Spline card without requiring a separate runtime. The removal also reduces the page's network footprint (no more Spline viewer script download) and removes a sandboxed iframe-like context from the page (simplifying the security model)
130. **Header comment in `atelier-3d.js` updated to match new container lookup:** Line 10 was changed from `const engine = initAtelierEngine(document.getElementById('canvas-3d-target'));` to `const engine = initAtelierEngine(document.querySelector('.atelier-canvas-wrap'));`. The header comment is the public API documentation — keeping it in sync with the actual init script in `virtual_experience.html` prevents confusion for future developers reading the engine
131. **`setViewportLoadingState` updated to v2 pattern (consistency):** The `setViewportLoadingState(loading)` method was updated to use the same 300ms opacity-then-display fade as `loadBaseAvatar` and the init script. v1 used `transitionend` event listener (could fail to fire if the element was removed during transition). v2 uses `setTimeout(300ms)` for guaranteed dismissal. The lookup chain is also updated: `'canvas-loader'` (with `.loader` fallback) replaces v1's `'three-loading-overlay'` (with `.loader` fallback). The single-source-of-truth approach means all three loader dismissal sites (init script, `loadBaseAvatar`, `setViewportLoadingState`) use the same fade pattern via the same element reference
132. **Why 600px height for the new canvas wrap (not full-height or auto):** The previous canvas wrap was `min-h-[400px] lg:min-h-0` (filled the parent grid cell, which was the fixed `inset-0 z-30 pt-20 pb-6 px-6` main element). The new wrap is `h-[600px]` (fixed 600px) because the page no longer uses the fixed main element — the new wrap is a self-contained card in the normal document flow. Fixed 600px gives a predictable layout across viewports (no jank on small screens, no awkward stretching on large screens) and matches the 21st.dev "premium interactive" aesthetic where cards have a deliberate height rather than filling the viewport

### 11h. Brand Restoration: Cream/Emerald Palette + Atelier-33D Canvas ID Binding + Loader Failsafe (SUPERSEDES 11g dark theme)
- **Purpose:** Reverts the canvas wrap visual theme from the 21st.dev dark interactive look (Section 11g) back to the original ASIKO brand palette — luxury cream (`#FBF9F6`) background with deep emerald (`#0D2A22`) borders and gold (`#D4AF37`) accents. Introduces a NEW canvas ID (`atelier-33d-canvas` — note the double-3) that the engine looks up by ID via the WebGLRenderer's `canvas` option (instead of appendChild-creating a new canvas). Adds a 1.5s failsafe unhook script that auto-clears the loader veil if any init script chokes
- **New canvas wrap architecture (replaces lines 160-195 of the previous 11g version):**
  - **Outer container:** `<div x-data="{ mouseX: 0, mouseY: 0, isHovered: false }" @mousemove="let rect = $el.getBoundingClientRect(); mouseX = $event.clientX - rect.left; mouseY = $event.clientY - rect.top;" @mouseenter="isHovered = true" @mouseleave="isHovered = false" class="lg:col-span-2 w-full relative min-h-[650px] bg-[#FBF9F6] border border-[#0D2A22]/20 rounded-sm overflow-hidden shadow-sm transition-all duration-300">` — ivory background (`#FBF9F6`), deep-emerald border at 20% opacity, sharp `rounded-sm` corners, `min-h-[650px]`, spans 2 grid columns via `lg:col-span-2`
  - **Cursor-following radial gold softbox (600×600px):**
    - `bg-[radial-gradient(circle_at_center,rgba(214,175,55,0.12)_0%,transparent,transparent_75%)]` — gold radial with 12% opacity at center, fading to transparent at 75% radius (more transparent than the 11g dark theme's 15% — appropriate for the bright cream background)
    - `blur-3xl` (Tailwind's 64px blur) for very soft, ambient edges — appropriate for a "golden softbox" mood on the bright background
    - Position offset: `${mouseX - 300}px` and `${mouseY - 300}px` to center the 600px radial under the cursor (vs 11g's `mouseX - 250` for the 500px size)
    - z-10 so the spotlight sits above the canvas but below the text header
  - **Text header (top of wrap):** `class="relative w-full h-full flex flex-col justify-between p-6 z-20 pointer-events-none select-none"` with a brand-eyebrow tag (`text-[10px] font-mono uppercase tracking-widest text-[#D4AF37]`) reading "ASIKO Atelier Studio" and a Playfair-display headline (`text-2xl font-serif font-medium text-[#0D2A22] tracking-tight`) reading "Virtual Fitting Room". `pointer-events-none` keeps the text purely decorative (no click interception)
  - **Canvas wrap container (background layer):** `class="absolute inset-0 w-full h-full z-0 atelier-canvas-wrap pointer-events-auto"` — absolute positioned to fill the parent, z-0 so the text header (z-20) and spotlight (z-10) layer on top
  - **Loader (inside the canvas wrap):** `<div id="canvas-loader" class="absolute inset-0 flex flex-col items-center justify-center bg-[#FBF9F6] z-50 transition-all duration-300">` — full-wrap ivory background, 6×6 spinning border (emerald with transparent top), 10px mono uppercase label "Assembling Studio Space..." in emerald-60% opacity. Cream background ensures the loader visually blends with the parent card
  - **Canvas element:** `<canvas id="atelier-33d-canvas" class="w-full h-full block focus:outline-none"></canvas>` — note the NEW ID `atelier-33d-canvas` (with double-3, replacing 11g's `atelier-3d-viewport`)
  - **Zoom dock (bottom-right, z-40):** Two square 9×9 buttons (emerald bg, cream text, gold-on-hover) with ＋ and － characters (full-width plus/minus Unicode glyphs), `select-none touch-manipulation` for touch-friendliness, inline `if(window.__atelierEngine)` guard for safe invocation
  - **`lg:col-span-2` on the outer wrapper:** Preserves the 3-column grid layout (canvas wrap takes columns A & B, control panel takes column C with `lg:col-span-1`)
- **Engine canvas binding (TASK 2 in `atelier-3d.js`):**
  - Constructor (in `_initScene()`) now looks up the canvas by ID: `const targetCanvasElement = document.getElementById('atelier-33d-canvas');`
  - If found: passes it to the WebGLRenderer constructor via the `canvas` option: `new THREE.WebGLRenderer({ canvas: targetCanvasElement, antialias: true, alpha: true, powerPreference: 'high-performance' });`
  - If NOT found: defensive fallback — creates a new WebGLRenderer and appendChild's its `domElement` to the container (logs a `console.warn` for diagnostic visibility)
  - The `container.appendChild(this.renderer.domElement)` line was REMOVED from the success path — Three.js now binds to the existing canvas via the constructor option instead
  - **`this.renderer.setClearColor(0x000000, 0);` added after renderer creation** — transparent clear color prevents black frame flashes on initial load and allows the cream background tone to bleed through the canvas (essential for the cream-palette design)
  - Header comment (L11) updated to reflect the new binding: `// The engine binds to <canvas id="atelier-33d-canvas"> via ID lookup.`
- **Init script updates in `virtual_experience.html`:**
  - REMOVED: `const placeholderCanvas = document.getElementById('atelier-3d-viewport'); if (placeholderCanvas) placeholderCanvas.remove();` — no longer needed because the engine uses the existing canvas via ID binding, not appendChild
  - Kept: the loader dismissal pattern (300ms opacity-then-display fade) for the success path
  - Kept: the `initAtelierEngine(container)` call passing the `.atelier-canvas-wrap` container
- **Loader failsafe (separate `<script>` block at end of file):**
  - New `<script>` block (NOT `type="module"`) added after the existing init module script
  - On `DOMContentLoaded`, sets a 1.5-second timeout (`setTimeout(..., 1500)`)
  - After 1.5s, checks if `#canvas-loader` exists AND is still visible (`loaderVeil.style.display !== 'none'`)
  - If still visible, logs a warning: `"Failsafe unhook sequence triggered to clear canvas loader veil."` and applies the same 300ms opacity-then-display fade used by the success path
  - **Rationale:** "Absolute insurance loop: if any initialization script chokes or assets stall, clear the loading veil automatically after 1.5 seconds so the app remains perfectly usable." — protects against the loader getting stuck and blocking the user from interacting with the canvas
  - Separate `<script>` block (not inside the module) because the failsafe must execute even if the module init fails (e.g., if the import fails, the module's DOMContentLoaded handler never runs, but the failsafe's handler still does)

133. **Cream/emerald brand restoration (revert from 21st.dev dark theme):** The Section 11g "21st.dev premium dark interactive" theme is replaced by the original ASIKO brand palette — cream background (`#FBF9F6`), emerald border (`#0D2A22` at 20% opacity), and gold accent (`#D4AF37`). The 11g dark theme was an aesthetic experiment (high-contrast editorial look) but didn't match the brand's existing visual language. The cream palette is the original brand identity (used throughout the rest of the site: product cards, admin dashboard, checkout, etc.) and reverting restores brand consistency. The new directive explicitly says "Revert the layout to the original cream/emerald design" and "We are dropping the dark card theme completely"

134. **Single-column text-on-top layout (was two-column text-left + canvas-right in 11g):** The new canvas wrap uses `flex flex-col justify-between` with the text header at the top of the wrap (vs 11g's two-column `flex flex-col md:flex-row` with text on the left and canvas on the right). The single-column layout works better with the cream background — the text header sits at the top of the card, the canvas absolutely positioned behind it, and the spotlight overlays both. This is closer to the original 11a/11b architecture (before the 21st.dev dark theme was introduced) and matches the brand's "luxury minimal" aesthetic better than the 11g editorial two-column layout

135. **New canvas ID `atelier-33d-canvas` (with double-3, replaces `atelier-3d-viewport`):** The directive introduces a new canvas ID that uses double-3 (`atelier-33d-canvas`) instead of single-3 (`atelier-3d-viewport`). The double-3 likely signals "Atelier 3D scene 3" or a sub-version indicator (the codebase has been through multiple canvas wrap iterations; the double-3 marks this as the third major version). The single-3 ID is now legacy and should not appear in any new code. The directive says to "explicitly reference the correct ID tag (atelier-33d-canvas) to establish a clean WebGL viewport rendering frame" — emphasis on "clean" suggests the previous renderer's `appendChild` pattern was creating unclean stacked-canvas artifacts that the explicit ID binding resolves

136. **Engine looks up canvas by ID via `getElementById` (replaces container-based appendChild):** The previous pattern had the engine accept a container and call `container.appendChild(this.renderer.domElement)` — creating a new canvas dynamically. The new pattern has the engine look up the canvas by ID and pass it to the WebGLRenderer constructor via the `canvas` option. This is cleaner because:
   - The HTML template now owns the canvas element (full styling control, no surprise canvas creation)
   - Three.js doesn't need to manage the DOM lifecycle of its renderer element
   - The renderer's `domElement` IS the existing canvas, no double-canvas confusion
   - If the canvas ID changes, the engine has a single, explicit place to look it up (vs appendChild's implicit creation)

137. **Transparent clear color `setClearColor(0x000000, 0)` is essential for cream palette:** With the cream background, a default black or dark clear color would create a visible black rectangle behind the 3D model — destroying the "background bleed" effect that's the whole point of the cream/emerald brand restoration. The transparent clear color allows the CSS background (`bg-[#FBF9F6]`) to show through any transparent areas of the rendered scene. The previous 11g dark theme didn't need this because black-on-black was the desired effect. The change from `alpha: true` (which alone doesn't make the clear color transparent) to `alpha: true` + `setClearColor(0x000000, 0)` is the difference between "alpha-enabled WebGL context" and "actually transparent clear"

138. **Defensive fallback for missing canvas (preserves engine robustness):** Even though the new architecture has a clean ID binding, the engine includes a defensive `else` branch: if `getElementById('atelier-33d-canvas')` returns null (canvas missing from the DOM), the engine falls back to the old `appendChild` pattern with a `console.warn` for diagnostic visibility. The fallback ensures the engine doesn't crash if the HTML template is broken or the script runs before the DOM is fully parsed. The defensive pattern is a "belt and suspenders" approach — clean architecture for the happy path, graceful degradation for the edge case

139. **Loader failsafe (1.5s unhook) protects against stuck loaders:** The new failsafe script guarantees the loader veil is dismissed within 1.5 seconds of `DOMContentLoaded`, even if every other init script chokes (e.g., Three.js fails to load, module import throws, asset preloader hangs). Without the failsafe, a stuck loader would block the user from interacting with the canvas even if the engine is technically ready. The 1.5s window is long enough for normal init to complete (asset preload + engine init + first render typically takes 200-800ms) but short enough that the user isn't waiting long if something fails. The `loaderVeil.style.display !== 'none'` check prevents the failsafe from re-firing the fade animation if the loader is already dismissed

140. **Failsafe uses non-module `<script>` block (deliberate):** The failsafe is in a separate `<script>` block WITHOUT `type="module"`, placed AFTER the existing `<script type="module">` block. This is deliberate: if the module's import statement fails (e.g., the atelier-3d.js URL is wrong, the network is down, the server returns 500), the module never executes its DOMContentLoaded handler, and the success-path loader dismissal never runs. A non-module `<script>` block executes unconditionally (no import to fail), so the failsafe always runs and ensures the loader is dismissed. The trade-off is that the failsafe can't share state with the module (it can only access globals like `document.getElementById`), but for a simple "hide the loader" operation, that's all that's needed

141. **Failsafe uses the same 300ms fade pattern as success path (consistency):** The failsafe applies the same `opacity: '0'` + `setTimeout(() => display = 'none', 300)` fade used by the success path. This ensures the user sees the same smooth fade-out animation regardless of whether the success path or the failsafe path dismissed the loader. If the failsafe used a different dismissal pattern (e.g., instant `display: 'none'`), the user would see a jarring inconsistency depending on which path fired

142. **`min-h-[650px]` on the new wrap (not `h-[600px]` like 11g):** The new directive uses `min-h-[650px]` (minimum height, not fixed height) instead of 11g's `h-[600px]` (fixed height). The 50px taller minimum gives the new layout a more vertical, breathing feel that suits the single-column text-on-top architecture. `min-h` also means the card can grow taller if the content inside is taller (e.g., on small viewports when the spotlight radius is large enough to push other content down), instead of being clipped to a fixed 600px

143. **`rounded-sm` (sharp 2px corners) on the new wrap (was `rounded-xl` in 11g):** The cream/emerald brand uses `rounded-sm` (2px corners) for sharp, editorial luxury. The 11g dark theme used `rounded-xl` (12px corners) for a softer, modern interactive look. The brand language is the sharper one — luxury editorial publications use sharp corners to signal seriousness, while consumer apps use soft corners for approachability. The `rounded-sm` choice aligns with the rest of the ASIKO site (product cards, admin tables, etc.)

144. **`border-[#0D2A22]/20` (20% opacity emerald border) vs 11g's `border-[#0D2A22]/30`:** The new wrap uses a 20% opacity emerald border, slightly lighter than 11g's 30%. On the bright cream background, a 20% border is visually present without being heavy — a 30% border would look too bold. The 10pp reduction is calibrated for the cream-on-emerald contrast: dark backgrounds absorb borders, light backgrounds make borders stand out, so the border needs to be lower opacity on light backgrounds

145. **`shadow-sm` on the new wrap (was `shadow-2xl` in 11g):** The cream wrap uses `shadow-sm` (small shadow) instead of 11g's `shadow-2xl` (extra-large shadow). The small shadow is appropriate for the editorial cream design — it lifts the card just enough to define its boundary without the dramatic "elevated widget" effect of `shadow-2xl`. The `shadow-2xl` was a signature element of the 21st.dev dark theme (helped the dark card pop on a dark page); on the cream-on-cream page, a small shadow is sufficient

146. **Container's `pointer-events-auto` (enables canvas interaction despite parent `pointer-events-none` on text):** The text header div has `pointer-events-none` (so the text doesn't block clicks on the canvas), but the canvas wrap (`.atelier-canvas-wrap`) has `pointer-events-auto` (re-enabling interaction for the canvas area). The zoom dock also has `pointer-events-auto`. The explicit re-enable is needed because `pointer-events-none` on a parent cascades to all children unless explicitly overridden. The `pointer-events: auto !important` CSS rule in the `<style>` block (L76) handles the `atelier-canvas-wrap` descendants uniformly

147. **Spotlight gradient uses gold at 12% opacity (was 15% in 11g):** The new gradient `bg-[radial-gradient(circle_at_center,rgba(214,175,55,0.12)_0%,transparent,transparent_75%)]` uses 12% opacity at the center, lower than 11g's 15%. On the bright cream background, a 12% gold tint is just visible enough to create the "softbox glow" effect without overwhelming the cream-on-emerald editorial palette. A 15% tint would be too saturated for the brand. The `,transparent,transparent_75%` syntax (transparent at 0% is replaced with the implicit center color) creates a smoother falloff than 11g's `transparent_70%`

148. **Why `min-h-[650px]` matches the cream layout (vs fixed 600px in 11g):** The 650px minimum gives the new wrap a slightly taller profile than 11g's 600px fixed height. The 50px additional height accommodates the more vertical, breathing single-column layout (text header at top + canvas below + breathing room). On viewports where the canvas is taller (e.g., 4K monitors), the wrap grows to fit. On smaller viewports, the 650px minimum ensures the canvas is always tall enough to be visually impactful — shorter would feel cramped

149. **Reverted `window.__atelierEngine` exposure (was both module and class, now just class):** The 11g init script exposed `window.__atelierEngine` twice — once in the module (L557: `window.__atelierEngine = engine;`) and once in the constructor (L93: `window.__atelierEngine = this;`). The 11h revert simplifies this: the constructor exposure (L93) is sufficient and the module-level reassignment is removed. The `if(window.__atelierEngine)` guards in the zoom dock inline handlers still work because the constructor sets the global before any user interaction. Removing the redundant module-level assignment eliminates the confusion of "which one wins" if the two ever diverge

150. **The `if(window.__atelierEngine)` zoom dock guard is a defensive pattern (preserved from 11g):** The zoom dock buttons use inline `onclick="if(window.__atelierEngine){ window.__atelierEngine.zoomIn(); }"` rather than `onclick="window.__atelierEngine.zoomIn()"`. The `if` guard prevents a `TypeError: Cannot read properties of undefined` if the engine hasn't initialized yet (e.g., the failsafe fires before the engine exposes the global). The pattern is more robust than the alternative of using Alpine.js `@click` handlers (which would require a refactor of the zoom dock's binding to the parent Alpine state) and matches the conservative "no Alpine.js state coupling" goal of the new directive ("restore full Alpine state compatibility to unfreeze the loader")

### 11i. Virtual Atelier Workspace Recovery: 2-Column Multi-Panel Grid + Canvas Selector Harmonization (SUPERSEDES 11h 3-row cream wrap)
- **Purpose:** Reverts from the 11h "single cream wrap with text on top + canvas behind" to the original formal 2-column multi-panel grid layout. The 11h layout's loader veil became frozen (infinite loading loop) because changing the canvas wrapper broke the original DOM structural identifiers and severed the Alpine.js state hooks (`virtualAtelier`, `dressingRoom`). The new 2-column architecture restores:
  - **LEFT panel (380px on desktop, full-width on mobile):** White background, contains brand eyebrow + "Virtual Atelier" heading, Model/Garments tab buttons, "Select Base Profile" label with Male/Female GLB picker buttons, and a "Secure WebGL Pipeline Framework v2.0" footer
  - **RIGHT panel (flex-1):** Cream background, contains the 3D canvas viewport with cursor-tracking gold softbox (500×500px, 8% opacity, `blur-3xl`), loader, and zoom dock
- **Why the 11h layout broke the loading loop:** The 11h single-wrap layout had only ONE primary visual surface (the cream wrap), but the Alpine.js state hooks (`currentMode`, `dressingRoom`, `showroomView`) were still defined and looked for child DOM nodes that no longer existed (the showroom products panel, the dressing room layer panel). When the Three.js engine tried to find these nodes (e.g., for `requestAR` product buttons), it failed silently, left the loading veil frozen, and the user was stuck
- **Engine canvas ID binding harmonization (TASK 2 in `atelier-3d.js`):**
  - The directive introduces a FALLBACK CHAIN for the canvas ID lookup: `document.getElementById('atelier-33d-canvas') || document.getElementById('atelier-3d-canvas')`
  - First tries `atelier-33d-canvas` (the 11h directive ID), falls back to `atelier-3d-canvas` (the current layout ID)
  - The fallback chain allows the engine to work with BOTH the 11h canvas IDs and the new directive's canvas ID without further code changes
  - Defensive `else` branch (creating a new canvas + `appendChild`) is preserved for the case where NEITHER ID is found (logs `console.warn('[atelier-3d] canvas#atelier-3d-canvas not found, creating fallback canvas')`)
- **Failsafe timeout shortened (1500ms → 1200ms):** The new failsafe triggers 1.2 seconds after `DOMContentLoaded` (was 1.5s in 11h). The 300ms shorter window reflects the simpler 2-column architecture — less DOM to render, so the engine should be ready faster, and a stuck loader is less likely to indicate a real issue (vs. a complex 3-column layout that legitimately needs more time)
- **Failsafe warning message updated:** The new message is `"Failsafe unhook triggered to release canvas layout lock."` (was `"Failsafe unhook sequence triggered to clear canvas loader veil."` in 11h). The new message is more specific about the symptom ("canvas layout lock" vs "loader veil") and more concise (single sentence vs. with trailing period)
- **New canvas ID `atelier-3d-canvas` (single 3, replaces 11h's `atelier-33d-canvas`):** The directive uses the single-3 `atelier-3d-canvas` ID (matching the original 11a/11b architecture before the 11h double-3 was introduced). The engine's fallback chain handles both IDs seamlessly. Going back to single-3 is consistent with the broader "restore the original layout" theme of this directive

151. **2-column multi-panel grid layout (was 3-column in 11h, was 2-column in 11a-11c):** The new layout is a `flex flex-col lg:flex-row` with TWO children: a fixed-width left panel (`lg:w-[380px]`) and a flex-1 right panel. This is the "original" 11a-11c multi-panel architecture (before the 11g/11h dark theme and 3-column grid were introduced). The simpler 2-column structure:
   - Has only ONE primary surface in the right panel (no parallel showroom products grid to confuse the engine)
   - All the controls (avatar selection, zoom dock) are visible in the right panel or the left panel
   - The Alpine.js state hooks (`virtualAtelier`, `dressingRoom`) can be safely removed or refactored without breaking the engine

152. **Removed showroom products grid (Column C from 11h) and dressing room tab:** The 11h layout had a 3-column grid where Column C was the showroom products panel + dressing room tab. The new 2-column layout REMOVES these. The showroom products and dressing room panels were complex Alpine.js-driven UI (product cards with hover-scale, layer-based garment selection, measurement inputs). By removing them, the directive simplifies the layout to focus on the core 3D experience (avatar + canvas). The Alpine.js data factories (`virtualAtelier`, `dressingRoom`, `showroomView`, `viewportControls`) remain defined in the `<script>` block at L256-358 but are no longer referenced by the new layout — they become dead code that can be safely removed in a future cleanup

153. **`rounded-none` (sharp corners) on the new outer container (vs 11h's `rounded-sm`):** The new wrap has `rounded-none` (0px corners, sharp edges) compared to 11h's `rounded-sm` (2px). The new directive wants a "formal" multi-panel dashboard look — sharp corners signal a serious, editorial design (think Bloomberg terminal, FT.com, NYT). The 11h's `rounded-sm` was a softer, more consumer-friendly choice. The sharp corners also help distinguish the left panel (which has a `border-r` separator) from the canvas area

154. **`border-[#0D2A22]/10` (10% opacity) on the new outer container (was 20% in 11h):** The new wrap has a 10% opacity emerald border (vs 20% in 11h). On the new layout, the border is just a hint of definition — the actual separation between the left and right panels comes from the left panel's `border-r` and the left panel's white background. A heavier border (20%) would be redundant with the panel separator

155. **Left panel white background (was cream `bg-[#FBF9F6]` in 11h):** The new left panel has `bg-white` (pure white) instead of 11h's cream `bg-[#FBF9F6]`. The contrast between the white left panel and the cream right panel visually emphasizes the two-panel structure — the left panel "pops" as a control surface, while the right panel recedes as the immersive canvas. The 11h single-wrap design used cream throughout, which made the canvas area blend into the rest of the page; the 11i white-on-cream contrast gives the canvas a clear "stage" feel

156. **Left panel `lg:w-[380px]` (380px fixed on desktop, full-width on mobile):** The new left panel has a fixed 380px width on desktop (`lg:w-[380px]`) and full width on mobile (`w-full` + `border-b` for vertical separator). The 380px is wide enough for the avatar selection buttons (Male/Female, with GLB filename subtitles) and the tab buttons, but narrow enough to leave plenty of room for the canvas. On mobile, the panel stacks vertically and the canvas goes below (the `flex-col lg:flex-row` makes the panels stack on small screens and side-by-side on large screens)

157. **`border-r` separator on left panel (vs 11h's single-wrap border):** The new left panel has `lg:border-r border-[#0D2A22]/10` — a 10% opacity emerald right border that separates it from the right panel. On mobile, the right border is replaced with a `border-b` (bottom border) because the panels stack vertically. The separator is what makes the 2-panel structure visually clear

158. **Model/Garments tab buttons in the left panel (editorial UX):** The new left panel has two tab buttons (`Model` and `Garments`) styled as inline tabs with an underline indicator (the active `Model` button has `border-b border-[#0D2A22] font-semibold`, the inactive `Garments` has `text-[#0D2A22]/40`). The tab pattern is familiar from every major e-commerce site (Amazon, ASOS, Net-a-Porter) and signals that more content is coming (e.g., the Garments tab will eventually have its own content). For now, only the Model tab is active and shows the avatar selection buttons

159. **"Select Base Profile" label + Male/Female avatar picker buttons (key new feature):** The new left panel has a "Select Base Profile" label and two buttons (Male, Female) that call `window.__atelierEngine.loadBaseAvatar('/static/models/avatar_male.glb')` and `loadBaseAvatar('/static/models/avatar_female.glb')` respectively. The Male button is currently the default selected state (it has `border border-[#0D2A22]` instead of `border-[#0D2A22]/20` for Female). Each button shows the GLB filename as a subtitle (`avatar_male.glb`, `avatar_female.glb`) — this is a developer-friendly "what file is this?" label that helps debugging. The buttons use the same `if(window.__atelierEngine)` defensive guard as the zoom dock buttons (prevents `TypeError` if engine isn't ready yet)

160. **`loadBaseAvatar(glbUrl)` as the primary avatar API (was `loadHumanAvatar` in 11a-11c):** The new directive uses `loadBaseAvatar(url)` to load a specific GLB file. The 11a-11c version had `loadHumanAvatar` (which called `loadBaseAvatar` internally) plus the Female/Male UI buttons. The new architecture simplifies to just `loadBaseAvatar(url)` — the URL parameter makes the API more flexible (any GLB file path, not just the hardcoded `avatar_female.glb` or `avatar_male.glb`). The defensive `loadBaseAvatar` v2 (from 11g) already accepts a URL parameter and handles errors gracefully (try/catch/finally with loader dismissal in the finally block)

161. **500×500px cursor-following gold softbox (down from 600×600 in 11h):** The new spotlight is 500×500px (was 600×600 in 11h). The smaller size matches the smaller right panel (which is now constrained to `min-h-[500px]` vs the 11h wrap's 650px). The 500×500 spotlight covers most of the right panel without being too aggressive. Position offset is `${mouseX - 250}px` / `${mouseY - 250}px` to center the 500px radial at the cursor (vs 11h's `mouseX - 300` for the 600px size)

162. **8% gold opacity on the spotlight (down from 12% in 11h):** The new gradient `bg-[radial-gradient(circle_at_center,rgba(214,175,55,0.08)_0%,transparent_70%)]` uses 8% opacity at the center, lower than 11h's 12%. On the new right panel's cream background, an 8% gold tint is more subtle and "ambient" than 11h's 12% — appropriate for a workspace-style layout (where the canvas is the focus, not the spotlight). A 12% tint would feel too "luxe product" for a dashboard

163. **Spotlight gradient `transparent_70%` (vs 11h's `,transparent_75%`):** The new gradient ends at 70% radius (vs 11h's 75%). A tighter falloff means the spotlight is more focused (concentrated at the cursor, fading to transparent more quickly). On a smaller 500×500 spotlight, the 70% falloff keeps the visual "weight" similar to a larger spotlight with a 75% falloff

164. **Loader z-index 40 (was 50 in 11h):** The new `#canvas-loader` has `z-40` instead of 11h's `z-50`. The lower z-index keeps the loader above the canvas (`z-0`) and the spotlight (`z-10`) but below the zoom dock (which is now `z-50`). This means if the loader is visible while the zoom dock is also visible, the zoom dock stays clickable (the user can dismiss the loader by clicking elsewhere or hitting the failsafe). In 11h, the loader at z-50 was above the zoom dock (also z-40), making the zoom dock unclickable while the loader was visible

165. **Zoom dock z-index 50 (was 40 in 11h):** The new zoom dock has `z-50` (up from 11h's `z-40`). Combined with the loader now at `z-40`, the zoom dock is now ABOVE the loader. The user can always interact with the zoom buttons, even if the loader is technically still visible. This is a UX improvement over 11h where the loader (z-50) blocked the zoom dock (z-40)

166. **Canvas is `absolute inset-0 z-0` inside the right panel (was wrapped in `.atelier-canvas-wrap` in 11h):** The new canvas has `class="w-full h-full block focus:outline-none z-0 absolute inset-0"` — it's absolutely positioned to fill the right panel, with `z-0` so it sits below the loader (z-40) and zoom dock (z-50). In 11h, the canvas was wrapped in a separate `<div class="absolute inset-0 w-full h-full z-0 atelier-canvas-wrap pointer-events-auto">` that contained both the loader and the canvas. The new architecture puts the loader and canvas as SIBLINGS inside the right panel (no wrapping div), and the `.atelier-canvas-wrap` class is now on the right panel itself. This is a simpler DOM structure (fewer nested divs) and matches the directive's HTML exactly

167. **The right panel IS the `.atelier-canvas-wrap` (vs 11h's nested structure):** The new right panel has `class="flex-1 relative bg-[#FBF9F6] min-h-[500px] lg:min-h-0 atelier-canvas-wrap overflow-hidden"`. The `.atelier-canvas-wrap` class is now on the right panel itself, not on a nested div. The CSS rules (`.atelier-canvas-wrap { position: absolute; inset: 0; }` and `.atelier-canvas-wrap > canvas { pointer-events: auto; }`) need to be reviewed for compatibility — the new architecture has the canvas as a direct child of the wrap, so the `pointer-events: auto` rule should still work. The `position: absolute; inset: 0;` rule on the wrap is now `position: relative` (from `relative bg-[#FBF9F6]`), which is fine because the canvas inside has its own `absolute inset-0` positioning

168. **`min-h-[500px] lg:min-h-0` on the right panel (no fixed height):** The right panel uses `min-h-[500px]` (minimum 500px) on mobile and `lg:min-h-0` (no minimum, takes available height) on desktop. The 500px mobile minimum ensures the canvas is tall enough on small screens. On desktop, the right panel fills the available height of the flex container (which is `min-h-[650px]` from the outer container). The 11h version had a fixed 650px on the wrap, which could clip on tall viewports; the new `min-h-[500px] lg:min-h-0` is more flexible

169. **Outer container `min-h-[650px]` (no `h-full`):** The new outer container has `class="w-full min-h-[650px] bg-[#FBF9F6] border border-[#0D2A22]/10 rounded-none overflow-hidden flex flex-col lg:flex-row shadow-sm"`. There's no `h-full` (which 11h had) — the container is sized by its own `min-h-[650px]` plus the content. The 11h's `h-full` filled the `<main>` parent's height (which was `fixed inset-0`), but the new architecture lets the container size itself based on content. This is more robust across viewports

170. **No `max-w-7xl` on the new outer container (was 11h's `max-w-7xl`):** The new container has no max-width constraint, so it can stretch to the full width of the `<main>` element. The 11h version had `max-w-7xl mx-auto` (80rem max width, centered) which constrained the canvas to a reasonable width on very wide viewports. The new directive drops the constraint — the canvas can be as wide as the viewport, which is appropriate for a "workspace" feel (more screen real estate for the 3D model)

171. **Inline `transition-colors` on zoom dock buttons (vs 11h's `transition-colors duration-200`):** The new zoom buttons use the shorthand `transition-colors` instead of 11h's `transition-colors duration-200`. The shorthand uses Tailwind's default duration (150ms) which is snappier than 200ms. The shorter transition feels more responsive for a "workspace" feel where quick interactions are expected. The `hover:bg-[#D4AF37]` and `hover:text-[#0D2A22]` produce a quick gold flash on hover

172. **No `transition-all duration-300` on the outer container (was 11h's):** The new container has no `transition-all duration-300` class. The 11h version animated ALL property changes on the container, which was unnecessary and could cause jank (e.g., when the loader was dismissed and the container briefly resized). The new directive removes this — the container is a stable, non-animated surface. Only the spotlight (via `:class` and `:style` bindings) and the buttons (via `transition-colors`) animate

173. **Failsafe "canvas layout lock" terminology:** The new failsafe warning message uses the term "canvas layout lock" instead of 11h's "canvas loader veil". The new terminology is more specific to the symptom — the canvas being "locked" (frozen, unresponsive) is the user's perceived problem, while "loader veil" describes the visual element. The shift from visual-element language to user-symptom language reflects the directive's focus on the user-facing infinite loading loop problem

174. **Why showroom products and dressing room panels were removed (not just hidden):** The 11i directive explicitly removes the showroom products grid (Column C) and the dressing room tab content. The reasoning is two-fold:
    1. **Simplicity:** The 2-column layout is the "original" 11a-11c architecture. The 3-column grid in 11h was an experiment that added complexity without clear benefit. The directive says "Revert the layout to your original multi-panel grid layout" — meaning return to the simpler 2-column structure
    2. **Unblocking the engine:** The complex showroom products and dressing room UI had Alpine.js state hooks that depended on specific DOM nodes. When the 11h single-wrap layout was introduced, those nodes were removed but the state hooks remained — causing the Three.js engine to fail silently when it tried to interact with non-existent nodes. By removing the complex UI, the directive also removes the source of the silent failures
   The dead Alpine.js data factories (`dressingRoom`, `showroomView`, `viewportControls`) at L272-359 can be safely removed in a future cleanup pass — they're not breaking anything, just unused. (`virtualAtelier` is the root `x-data` on `<body>` and is preserved; `wardrobeItems` is used by `virtualAtelier.wardrobeItems` and is also preserved)

175. **`loadBaseAvatar` v2 is the canonical avatar API (preserved from 11g/11h):** The new Male/Female buttons in the left panel call `window.__atelierEngine.loadBaseAvatar('/static/models/avatar_male.glb')` and `loadBaseAvatar('/static/models/avatar_female.glb')`. The `loadBaseAvatar` v2 method (from 11g, preserved in 11h and 11i) is the canonical avatar loading API. It:
    1. Looks up `canvas-loader` for visibility tracking
    2. Forces loader visible (`display: 'flex'`)
    3. Loads the GLB via GLTFLoader
    4. Calls `safelyPurgeThreeAsset` for cleanup
    5. Adjusts model to viewport via `adjustModelToFitViewport(rawModel, true)`
    6. Sets up avatarWrapperGroup and camera/controls refresh
    7. In `finally` block: 300ms setTimeout fade to dismiss the loader
   The URL parameter makes the API more flexible than the 11a-11c `loadHumanAvatar` (which was hardcoded to `avatar_female.glb` or `avatar_male.glb`)

176. **Why the canvas ID fallback chain (`atelier-33d-canvas` || `atelier-3d-canvas`) handles the transition:** The 11h directive introduced `atelier-33d-canvas` (double 3) as the new canvas ID. The 11i directive reverts to `atelier-3d-canvas` (single 3). The fallback chain `getElementById('atelier-33d-canvas') || getElementById('atelier-3d-canvas')` allows the engine to work with EITHER ID — first it tries the 11h ID, then falls back to the 11i ID. This means:
    - Existing browser tabs with the 11h layout cached: the engine finds `atelier-33d-canvas` and works
    - New tabs with the 11i layout: the engine falls through to `atelier-3d-canvas` and works
    - Future code that uses either ID: works without code changes
   The chain is forward-compatible AND backward-compatible — no need to coordinate a "flag day" where everyone updates the ID simultaneously

177. **The `if(window.__atelierEngine)` guards are now used in 4 places:** The Male and Female avatar buttons in the new left panel use the same `if(window.__atelierEngine){ window.__atelierEngine.method(); }` defensive pattern as the zoom dock buttons. Total count of `if(window.__atelierEngine)` guards in the file: 4 (Male button, Female button, Zoom In, Zoom Out). The pattern is now the standard for any inline `onclick` handler that invokes an engine method — it prevents `TypeError: Cannot read properties of undefined` if the engine isn't ready yet, especially relevant for the avatar buttons which the user might click while the loader is still visible

### 11i-cleanup. Dead Alpine.js State Factory Removal (90 lines) — SUPERSEDED by 11k (dressing room placeholder restored as static UI)
- **Purpose:** Removes the 3 dead Alpine.js data factories that were unreferenced after the 11i layout simplification. The factories were originally bound to the removed showroom products grid and dressing room tab UI from 11g/11h, but their data definitions were never removed. They registered harmless event listeners that no UI consumed.
- **Removed:**
  - `viewportControls` (L272-284, 13 lines): Alpine.data factory that listened for `layer-state-updated` events from the engine and updated an `activeLayers` array
  - `showroomView` (L287-302, 16 lines): Alpine.data factory that listened for `layer-capsule-mesh` events and dispatched `swap-clothing` events to the engine
  - `dressingRoom` (L305-359, 55 lines): Alpine.data factory that managed `activeGarments`, `garmentLoading`, `layerSequence`, `measurements`, `toggleGarment`, `clearAll`, `applyMeasurements`
- **Preserved:**
  - `wardrobeItems` constant (L258-263, 6 lines): still used by `virtualAtelier.wardrobeItems` (line 268)
  - `virtualAtelier` (L265-269, 5 lines): the root `x-data` factory on `<body>` (line 92) — still required for Alpine.js to initialize
- **Why safe to remove:**
  - All 3 factories had no UI consumers after 11i removed the showroom/dressing room panels
  - The engine event listeners (`layer-state-updated` at L773, `swap-clothing` at L1212) are still defined internally in the engine and would still work IF a future UI dispatched/consumed them
  - The engine's public methods (`setGarmentLayer`, `clearAllLayers`, `applyMeasurements`) are still defined and callable from any future UI
  - The `{% if saved_measurements %}` block in the THREE.JS engine init script (L290-296) is preserved — it's a SEPARATE template block that applies saved measurements to the engine on load
- **Result:** `virtual_experience.html` reduced from 417 to 327 lines (90 lines saved). The Alpine.js init callback now contains only the `wardrobeItems` constant and the `virtualAtelier` data factory. Cleaner DOM, no behavioral change.
- **Verification:** grep confirms zero remaining references to `viewportControls`, `showroomView`, or `dressingRoom` in production code. All remaining mentions are in `knowledge.md` historical documentation.

178. **Dead code removal verification (grep + behavioral equivalence):** Before marking the cleanup complete, verified three things:
    1. **No `x-data="viewportControls"`, `x-data="showroomView"`, or `x-data="dressingRoom"` references in the body markup** — confirmed by grep showing 0 matches outside of the now-deleted data factories themselves
    2. **Engine event listeners intact** — `document.addEventListener('swap-clothing', ...)` (L1212) and `new CustomEvent('layer-state-updated', ...)` (L773) still exist in the engine; the event bridge is preserved even though the UI side is gone
    3. **Engine public methods intact** — `setGarmentLayer` (L494), `clearAllLayers` (L539), `applyMeasurements` (L421) are all still defined; future UI can call them via `window.__atelierEngine.setGarmentLayer(...)` without any code change to the engine
    The cleanup is purely subtractive (removes 90 lines of dead code) with zero behavioral change to the engine or visible UI. The page is now leaner: smaller HTML payload, fewer event listener registrations on page load, no risk of stale references if a future directive references `dressingRoom` expecting it to work.

### 11k. Three-Column Multi-Panel Grid Recovery (Atelier Workspace)
- **Purpose:** Restore the formal 3-column multi-panel workspace (Showroom + Dressing Room tabs + 3D viewport) with proper Alpine.js state tree, auto-load default female avatar, and integrate cursor-tracking spotlight as a transparent layer over the 3D canvas. Fixes the "infinite loading loop" root cause: the previous 11i layout had stripped out the essential multi-panel UI and altered the Alpine state tree.
- **Layout architecture (12-column Tailwind grid):**
  - Outer `<main>`: `w-full min-h-screen bg-[#FBF9F6] pt-24 pb-12 px-4 md:px-8 font-sans` (full viewport, cream background, padding top for header)
  - Inner: `max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8` (max-width 80rem, centered, 12-col grid on desktop, single-col on mobile, 2rem gap)
  - Left panel: `lg:col-span-4 space-y-6 flex flex-col justify-between` (4/12 = 33% width)
  - Right panel: `lg:col-span-8 relative bg-[#FBF9F6] border border-[#0D2A22]/10 min-h-[600px] shadow-sm overflow-hidden atelier-canvas-wrap` (8/12 = 67% width, min 600px height)
- **Left panel content (white card):**
  - Brand eyebrow: `text-[10px] font-mono uppercase tracking-[0.2em] text-[#D4AF37] block mb-1` "ÀSÌKÒ Studio Suite"
  - Heading: `text-2xl font-serif text-[#0D2A22] tracking-tight` "Virtual Atelier"
  - Tab buttons: Showroom (drives `activeMode = 'showroom'`) + Dressing Room (drives `activeMode = 'dressing_room'`); active state: `border-b-2 border-[#0D2A22] font-semibold text-[#0D2A22]`; inactive: `text-[#0D2A22]/40`
  - Showroom panel (`x-show="activeMode === 'showroom'"`): "Gender Axis Profile" label + 2-col grid with Male Axis / Female Axis buttons that call `switchGender('male')` / `switchGender('female')`
  - Dressing Room panel (`x-show="activeMode === 'dressing_room'"`): "Active Wardrobe Configuration" label + dashed-border placeholder with "Layering Engine Active" + "Select catalog apparel rows below to load textures." (static placeholder, not functional UI)
- **Right panel content (atelier-canvas-wrap):**
  - Local Alpine state: `x-data="{ mouseX: 0, mouseY: 0, isHovered: false }"` (component-local, independent of `virtualAtelier`)
  - Cursor tracking: `@mousemove="let rect = $el.getBoundingClientRect(); mouseX = $event.clientX - rect.left; mouseY = $event.clientY - rect.top;"` + `@mouseenter="isHovered = true"` + `@mouseleave="isHovered = false"`
  - Spotlight: 500×500px 8% opacity gold radial gradient (`bg-[radial-gradient(circle_at_center,rgba(214,175,55,0.08)_0%,transparent_70%)]`) with `blur-3xl transition-opacity duration-300` + `pointer-events-none` + `select-none` + z-10; opacity toggles via `:class="isHovered ? 'opacity-100' : 'opacity-0'"`
  - Loader: `id="canvas-loader"` z-40, "Assembling Spatial Viewport..." label, 5×5 spinner
  - Canvas: `id="atelier-33d-canvas"` z-0, `class="w-full h-full block focus:outline-none absolute inset-0 z-0"`
  - Zoom dock: z-50, `pointer-events-auto`, ＋/－ buttons (9×9, `bg-[#0D2A22] text-[#FBF9F6] hover:bg-[#D4AF37] hover:text-[#0D2A22]`)
- **Alpine.js state tree (`virtualAtelier` factory at L276-292):**
  - `activeMode: 'showroom'` (default tab; was `currentMode` in 11i)
  - `currentGender: 'female'` (default gender for Showroom panel)
  - `selectedVariant: null` (preserved from earlier; no current UI consumer)
  - `wardrobeItems: wardrobeItems` (preserved constant; future dressing room would re-use)
  - `switchGender(g)` method: sets `this.currentGender = g` AND calls `window.__atelierEngine.loadBaseAvatar('/static/models/avatar_${g}.glb')` (defensive `if(window.__atelierEngine)` guard)
- **Bootstrap script (L297-313, replaces 11i init):**
  - Uses `querySelector('.atelier-canvas-wrap')` (class lookup, replaces 11h's `getElementById('canvas-3d-target')`)
  - Calls `initAtelierEngine(parentContainer)` then `loadBaseAvatar('/static/models/avatar_female.glb')` (auto-load default)
  - Preserves `{% if saved_measurements %}` block (calls `applyMeasurements({ chest, waist, hips }, true)`)
  - No explicit loader dismissal (loadBaseAvatar v2's `finally` block + 1200ms failsafe handle it)
- **Engine canvas lookup (atelier-3d.js L120-145):** Updated `else` branch with `console.error("Initialization Failed: WebGL context canvas target target could not be successfully bound.")` (per directive literal, with duplicated "target" preserved). Fallback `appendChild` canvas creation preserved below the error log for robustness.
- **Header tabs (L125-132) updated to use `activeMode`:** Previously used `currentMode`; renamed to `activeMode` so the header nav and the grid's tabs share the same state via the body's `x-data="virtualAtelier"` scope.
- **Single `x-data="virtualAtelier"` (body L92):** The grid div does NOT have its own `x-data` — it inherits from the body. This is a deviation from the directive's literal HTML (which had `x-data` on the grid div) but is necessary for the header tabs to share state with the grid tabs. Alpine.js inherits scope from parent elements, so the grid's children (tabs, showroom, dressing room) all have access to `activeMode`, `currentGender`, `switchGender()`.

179. **12-col Tailwind grid (`grid-cols-1 lg:grid-cols-12`) supersedes 11i's `flex-col lg:flex-row`:** The new layout uses a 12-col grid with `col-span-4` (33%) + `col-span-8` (67%) inside `max-w-7xl mx-auto`. This provides explicit width ratios vs 11i's `flex-1` (which had no defined max-width on the canvas). The 12-col grid is also more flexible for future additions (e.g., 3-3-6 for a third column, or 6-6 for a half-half layout).

180. **`atelier-33d-canvas` (double-3) is canonical in 11k (was reverted in 11i):** The directive's HTML has `<canvas id="atelier-33d-canvas">` (double-3). The engine's fallback chain `getElementById('atelier-33d-canvas') || getElementById('atelier-3d-canvas')` puts the double-3 ID FIRST, so the engine finds the canvas regardless of which ID is in the layout. This is the reverse of 11i (which used single-3) and matches the original 11h directive. The double-3 is a visual hint ("3D canvas" with extra 3 for emphasis) vs the single-3 which is just "3D canvas".

181. **Body's `x-data="virtualAtelier"` is the single source of truth (NOT the grid div):** Per Alpine.js scope inheritance, the body's x-data defines `activeMode`/`currentGender`/`switchGender` for the entire page, and child elements (header tabs, grid tabs, showroom panel, dressing room panel) all read/write the same state via inheritance. The directive's literal HTML had `x-data="virtualAtelier"` on the grid div, but this would have created a SECOND `virtualAtelier` instance with independent state — the header's tab clicks would update the body's `activeMode` but NOT the grid's `activeMode` (and vice versa). The fix: remove the grid div's `x-data` and let it inherit from body. This is a one-line deviation from the literal HTML but is required for state coherence.

182. **`switchGender` does double duty (state + engine call):** The method sets `this.currentGender = g` (Alpine reactive state, drives the `:class` button highlight) AND calls `window.__atelierEngine.loadBaseAvatar('/static/models/avatar_${g}.glb')` (loads the corresponding GLB). The defensive `if(window.__atelierEngine)` guard prevents `TypeError` if the engine isn't ready yet. This makes the gender buttons functional, not just cosmetic — clicking "Male Axis" actually swaps the avatar from female to male.

183. **11k bootstrap auto-loads female avatar (per TASK 3):** `window.__atelierEngine.loadBaseAvatar('/static/models/avatar_female.glb')` is called immediately after engine init. The loader stays visible during the async GLB load and is dismissed by `loadBaseAvatar` v2's `finally` block (300ms opacity fade). The 1200ms failsafe handles engine init failures. This is a UX improvement over 11i/11h where the user had to manually click a gender button to load any avatar.

184. **11k bootstrap removes explicit loader dismissal (per TASK 3):** The 11i bootstrap had a 300ms loader-dismissal setTimeout that fired BEFORE the avatar was loaded (creating a brief empty-canvas flash). The 11k bootstrap delegates loader dismissal to `loadBaseAvatar` v2's finally block, which only fires after the GLB is loaded. The 1200ms failsafe provides the safety net for engine init failures.

185. **11k preserves the `wardrobeItems` constant in `virtualAtelier` factory:** Although no current UI uses `wardrobeItems`, the diagnosis says "preserve all active state bindings". Future dressing room panels would re-use the wardrobe data; removing it would be a regression. The constant at L259-274 is the source of truth for the 6-item wardrobe (mesh_dress_lux, mesh_top_structural, mesh_trouser_tapered, mesh_jacket_cyber, etc.).

186. **11k preserves the `{% if saved_measurements %}` block in the bootstrap:** The directive's literal TASK 3 code doesn't include the `applyMeasurements` block, but the diagnosis says "preserve all server-side Jinja2 loops/variables". The block at L305-311 is kept, calling `window.__atelierEngine.applyMeasurements({ chest, waist, hips }, true)` after the avatar loads. This applies any saved user measurements from the session, giving a personalized avatar on page load.

187. **Dressing room panel restored as placeholder (11k partially reverses 11i-cleanup):** The new HTML has a real `<div x-show="activeMode === 'dressing_room'">` with "Active Wardrobe Configuration" label + dashed-border "Layering Engine Active" / "Select catalog apparel rows below to load textures." box. The UI exists, but the dead `dressingRoom` data factory (with `activeGarments`, `garmentLoading`, `measurements`, `toggleGarment`, `clearAll`, `applyMeasurements` methods) is NOT restored. Future dressing room functionality would need to re-introduce those factories (or implement them in a simpler form).

188. **Spotlight `:class` opacity toggle (replaces 11i's static `opacity-8`):** The new spotlight uses Alpine's reactive `:class` binding to toggle opacity based on `isHovered` mouse state. When the user enters the right panel, the spotlight fades in (300ms via `transition-opacity duration-300`); when they leave, it fades out. This is more dynamic than 11i's static 8% opacity — the spotlight is a "follow the mouse" highlight that only appears when the user is actively looking at the canvas. The opacity 100%/0% toggle (not e.g. 0%/50%) is binary for clean fade behavior.

189. **Right panel's nested `x-data="{ mouseX, mouseY, isHovered }"` is intentional component-local state:** The right panel declares its own Alpine state for cursor tracking, independent of the `virtualAtelier` factory. The local state is `mouseX`, `mouseY` (cursor position relative to panel), `isHovered` (whether the cursor is inside the panel). The local x-data is nested inside the body's `x-data="virtualAtelier"` scope — Alpine.js supports nesting scopes, with the inner scope's local state (mouseX, etc.) being independent of the outer scope's state (activeMode, etc.).

190. **Loader label "Assembling Spatial Viewport..." (was "Synchronizing 3D Canvas..." in 11i):** New label per directive; uses "Assembling Spatial" terminology consistent with the brand's editorial language. The 10px font + 0.2em letter-spacing + uppercase + `[#0D2A22]/60` color gives a refined, editorial feel vs a utilitarian "loading..." message.

191. **Loader spinner `w-5 h-5` (was `w-6 h-6` in 11i):** Slightly smaller per directive. The 5×5 size fits the more compact 11k aesthetic and pairs well with the 10px label font. The 1px border + `border-t-transparent` creates a clean spinning indicator.

192. **Engine error message updated to directive's literal text (with duplicated "target" preserved):** `console.error("Initialization Failed: WebGL context canvas target target could not be successfully bound.")` (with the duplicated word "target" preserved literally per directive spec). The duplication is likely a typo in the directive but preserved per literal text. The `console.error` (was `console.warn` in 11i) raises the severity — engine init failures are critical and should be visible in the console.

193. **Engine preserves fallback `appendChild` canvas creation in `else` block (deviates from directive's literal):** The directive's TASK 2 else block is `console.error(...)` with no fallback. The engine keeps the existing `appendChild` fallback canvas creation BELOW the error log for robustness — if both `atelier-33d-canvas` and `atelier-3d-canvas` IDs are missing, the engine still creates a renderer and the 3D experience still works. The error log surfaces the configuration issue in the console.

194. **Header tabs use `activeMode` to share state with grid (in 11i they used `currentMode`):** Updated from `currentMode` to `activeMode` so both the header nav and the grid panel control the same `activeMode` state. The factory was renamed accordingly (removed `currentMode`, added `activeMode`). The header tabs are at L125-132, the grid tabs are at L165-175 — both write to the body's `activeMode`.

195. **`min-h-[600px]` on the right panel (vs 11i's `min-h-[500px] lg:min-h-0`):** The 11k right panel has a fixed `min-h-[600px]` (no responsive variant). The 600px minimum is taller than 11i's 500px — gives the 3D canvas more vertical space for the model + UI controls. The single breakpoint (no `lg:min-h-0`) means the panel maintains a consistent minimum height across viewports, which is more predictable for layout calculations.

196. **Right panel's `x-data` is positioned AFTER the class attribute (consistent with Alpine 3 best practice):** The right panel has `x-data="{ mouseX: 0, mouseY: 0, isHovered: false }"` as a SEPARATE attribute on the same element (L208-212), positioned after the long class string. This is the standard Alpine 3 pattern for nesting x-data on an element that already has many class names. The `@mousemove`, `@mouseenter`, `@mouseleave` event handlers are also positioned below the x-data for readability.

197. **Outer `<main>` has `pb-12` (no `pb-8` like 11i):** The 11k main has `pt-24 pb-12 px-4 md:px-8 font-sans` — 96px top padding (for the fixed header), 48px bottom padding, 16px horizontal padding on mobile / 32px on desktop, sans-serif font. The larger bottom padding (vs 11i's 32px) gives more breathing room at the bottom of the page, especially important since the canvas is 600px+ tall.

198. **The 11k directive's diagnosis "preserve all active state bindings" is the key constraint:** The 11i directive removed the showroom products grid and dressing room panel UI, and the 11i-cleanup removed the dead Alpine data factories (`dressingRoom`, `showroomView`, `viewportControls`). The 11k directive re-introduces the multi-panel UI (showroom tabs, dressing room placeholder) but the diagnosis says to preserve the dead factories removal (they're still removed in 11k). The result: the dressing room panel is a static placeholder, not a functional UI with state. Future directives could either re-introduce the `dressingRoom` factory for full functionality, or keep the placeholder approach.
