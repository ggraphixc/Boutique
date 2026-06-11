# ASIKO Boutique - Project Knowledge Base

## Overview

ASIKO Boutique is a single-brand luxury e-commerce platform for Nigerian fashion retail. Built with Python/Starlette (async HTTP), it eliminates physical commercial lease costs, generator fuel expenses, and manual social-commerce transfer fraud. Features include a 3D try-on experience, Paystack payments, customer accounts, and an admin dashboard.

---

## Architecture

### Tech Stack
- **Web Framework:** Python 3.14 with Starlette 1.0 (async HTTP, Jinja2, HTMX, Alpine.js)
- **Database:** PostgreSQL via asyncpg (Neon cluster)
- **Templates:** Jinja2 with HTMX for server-driven interactivity, Alpine.js for client state
- **Styling:** Tailwind CSS via CDN (light theme, dark mode via `darkMode: 'class'`)
- **Sessions:** Server-side with Starlette SessionMiddleware
- **Email:** Brevo SMTP API for transactional notifications
- **Payments:** Paystack (reference format: `asiko_{order_id}`, amount in kobo)
- **3D Viewer:** Google `<model-viewer>` web component (replaces custom Three.js TryOnEngine)
- **3D Pipeline:** Hunyuan3D-2 via HF Space `/shape_generation` (texture gen not yet available)

### Directory Structure
```
asiko-boutique/
├ .env                              # DATABASE_URL, BREVO_API_KEY, PAYSTACK_SECRET_KEY, AUTH_SALT
├ knowledge.md
├ design.md
├ requirements.txt
├ supabase/
│   └── migrations/
│       ├── 01_init_schema.sql      # stores, products, orders, order_items, nigerian_states
│       ├── 02_reservations.sql     # product_variants, product_reservations
│       ├── 03_waitlist.sql         # product_waitlists
│       ├── 04_luxury_core.sql      # measurement_vault, concierge, capsule, allocation
│       ├── 04_dpp_ledger.sql       # Digital Product Passport provenance
│       ├── 05_single_brand.sql     # Consolidated to single ASIKO store
│       ├── 06_schema_alignment.sql # payload_metadata, session_identifier, mock tables
│       ├── 07_gltf_columns.sql     # model_3d_url, mesh_node_identifier, custom_shader_color
│       ├── 08_admin_redesign.sql   # categories, product_reviews, store_settings
│       ├── 09_admin_redesign.sql   # categories, product_reviews, store_settings (alt)
│       ├── 10_seed_catalog.sql     # 10 products, 39 variants
│       ├── 11_customers_auth.sql   # customers table, order FK
│       └── 12_product_images_pipeline.sql  # base_image, source_2d_image_url for 10 products, queue pipeline
├ static/
│   └── uploads/optimized/         # Generated .glb files from pipeline (4 files)
├ app/
│   ├── core.py                    # Templates, naira filter, session helpers
│   ├── main.py                    # App factory, route registration, WebSocket, lifespan
│   ├── database.py                # asyncpg pool lifecycle (min=2, max=10)
│   ├── realtime.py                # ConnectionManager, Postgres LISTEN/NOTIFY
│   ├── services/
│   │   ├── brevo.py               # Brevo API (send_transactional_email)
│   │   ├── settlement.py          # Paystack init, HMAC verification, 36-state matrix
│   │   └── dpp_crypto.py          # Digital Product Passport signing
│   ├── routes/
│   │   ├── storefront.py          # Homepage, PDP, try-on page, reviews, lookbook, DPP, About
│   │   ├── virtual.py             # /virtual-experience, showroom items (deprecated)
│   │   ├── cart.py                # HTMX cart add/update/drawer
│   │   ├── checkout.py            # Paystack checkout
│   │   ├── webhooks.py            # Paystack webhook, Brevo dispatch
│   │   ├── admin.py               # Admin product CRUD
│   │   ├── admin_sections.py      # 15+ section handlers, order status, RT fragments
│   │   ├── admin_dashboard.py     # Pipeline link-2d, pipeline status
│   │   ├── customer.py            # Register, login, logout, account dashboard
│   │   ├── waitlist.py            # Out-of-stock enrollment
│   │   └── dpp_verification.py    # Avatar profile binding
│   ├── workers/
│   │   └── pipeline_daemon.py     # Hunyuan3D-2 pipeline (/shape_generation)
│   ├── templates/
│   │   ├── base.html              # Public shell, dark mode, About nav link
│   │   ├── virtual_experience.html # Try-on page, model-viewer, Alpine.js in-place swap
│   │   ├── admin/
│   │   │   ├── base.html          # v2 shell, 10 nav buttons, dark mode
│   │   │   └── sections/          # dashboard, products, orders, sales, etc.
│   │   ├── storefront/
│   │   │   ├── index.html         # Homepage with Alpine.js search/category filter
│   │   │   ├── product_detail.html # Editorial PDP, 3D badge, reviews
│   │   │   └── about.html         # Public About page
│   │   ├── customer/
│   │   │   ├── dashboard.html     # Order history
│   │   │   ├── order_detail.html  # Order detail
│   │   │   ├── register.html      # Create account
│   │   │   └── login.html         # Sign in
│   │   └── components/
│   └── tests/
│       ├── test_admin_sections.py        # 72 tests
│       ├── test_admin_create_product.py  # 30 tests
│       ├── test_storefront_pages.py      # 43 tests
│       ├── test_realtime.py             # 35 tests (incl. _extract_glb_path)
│       └── test_pipeline_worker.py      # 7 tests
```

---

## Core Systems

### 1. Cart Session Management
- **Storage:** Server-side session (signed cookie)
- **Data Shape:** `{"lines": [...], "total": float, "item_count": int}` — uses `lines` key (not `items`) to avoid `dict.items()` collision
- **Handlers:** `cart_add` (validates stock), `cart_update` (increment/decrement/remove), `cart_drawer` (HTMX fragment)
- **Stock Validation:** Queries `product_variants.stock_qty` before add/increment

### 2. Customer Authentication
- **Method:** SHA-256 + salt (not bcrypt), salt via `AUTH_SALT` env var
- **Table:** `customers` (id, email, password_hash, full_name, phone, created_at)
- **Routes:** `/register`, `/login`, `/logout`, `/account` (order history), `/account/order/{id}`
- **Orders linked via:** `customer_id` FK (optional, so existing orders remain valid)

### 3. Checkout & Payments
- **Paystack reference:** `asiko_{order_id}`, amount in kobo (Naira × 100)
- **Flow:** Create order (pending) → Initialize Paystack → Redirect → Webhook marks paid
- **Email:** Confirmation via Brevo `send_transactional_email()` with graceful fallback
- **36-State Shipping:** ₦1,500 (Lagos) to ₦4,000 (Borno, Yobe)

### 4. 3D Try-On Viewer
- **Viewer:** Google `<model-viewer>` web component (CDN: `model-viewer.min.js` 3.5.0)
- **Rendering:** GLB files loaded directly, auto-rotate, camera controls, environment lighting, AR support
- **In-place swapping:** Alpine.js `tryOnApp()` — clicking a product in browse panel swaps `model-viewer src` + product info with no page navigation
- **Mobile:** Stacked layout (`lg:grid-cols-3` → single column), toggle button for product details
- **Poster fallback:** If no GLB, shows `base_image` as poster; if no image, shows placeholder "A"
- **Covered products:** Benin Bronze Cuff currently has a completed GLB (assigned from stale pipeline file)
- **Pipeline:** Hunyuan3D-2 via `/shape_generation` endpoint (NOT `/generation_all` — broken on HF Space)
- **Pipeline status:** `idle → queued → generating_mesh → completed | failed`
- **DB columns:** `model_3d_url`, `source_2d_image_url`, `pipeline_status`, `asset_category`

### 5. Product Reviews
- **Submit:** `POST /product/{product_id}/review` (customer_name, email, rating, title, body)
- **List:** `GET /product/{product_id}/reviews` (HTMX fragment, loads on page)
- **Table:** `product_reviews` (id, product_id, customer_name, customer_email, rating, title, body, verified, replied, reply_body, replied_at, created_at, updated_at, deleted_at)

### 6. Admin Order Management
- **Status update:** `POST /admin/orders/{order_id}/status` with HTMX dropdown
- **Valid statuses:** pending → paid → processing → shipped → delivered (or cancelled)
- **Sales section:** Order table with per-row status dropdowns

### 7. Homepage Search/Filter
- **Client-side Alpine.js** with search input + category pills
- **Categories:** All, Tailoring, Dresses, Outerwear, Accessories, Footwear
- **Query:** `LEFT JOIN categories` for `category_name`

### 8. Brevo Email Integration
- **Config:** `BREVO_API_KEY` and `SENDER_EMAIL` in .env
- **Types:** Order confirmation, admin notification, status change, waitlist
- **Graceful degradation:** Skipped when API key is placeholder

---

## Database Schema

### Migration 01: Core Tables
- **stores** — Single ASIKO store (slug: `asiko`)
- **products** — id, store_id, name, description, price, stock_quantity, base_image
- **orders** — Customer orders with JSONB metadata
- **order_items** — Line items with product FK
- **nigerian_states** — 37 rows (36 states + FCT) with shipping costs

### Migration 02-06: Reservations, Waitlist, Luxury, Schema
- **product_variants** — Size/color variants (48 seeded)
- **product_reservations** — Active stock holds
- **product_waitlists** — Email + variant enrollment
- **asiko_measurement_vault** — Body measurements
- **asiko_capsule_looks / assignments** — Curated looks
- **asiko_allocation_windows** — Tiered pre-order gates
- **Mock tables** — For test suite isolation

### Migration 07: 3D GLTF Columns
- **products:** `model_3d_url`, `model_usdz_url`, `apparel_layer_depth`
- **product_variants:** `mesh_node_identifier`, `custom_shader_color`, `morph_target_index`

### Migration 08-09: Admin Redesign
- **categories** — Product categories (Tailoring, Dresses, Outerwear, Accessories, Footwear)
- **product_reviews** — Customer reviews with rating, verified badge, admin reply
- **store_settings** — Key-value settings

### Migration 10: Seed Catalog
- **10 products** with 39 variants (₦8k – ₦120k range)
- Items: Green G-Gown, Lagos Silk Blazer, Ivory Agbada Set, Adire Bubu Dress, Kano Leather Loafers, Aso-Oke Dinner Jacket, Benin Bronze Cuff, Calabar Mermaid Skirt, Hausa Embroidered Cap, Sahel Kimono Jacket

### Migration 11: Customer Auth
- **customers** table (id, email, password_hash, full_name, phone, created_at)
- **orders.customer_id** FK added

---

## 3D Pipeline

### Hunyuan3D-2 Pipeline
- **Space:** `tencent/Hunyuan3D-2` on Hugging Face
- **Endpoint:** `/shape_generation` (NOT `/generation_all` — broken on public Space, `texgen_worker` fails to load)
- **Pipeline daemon:** `app/workers/pipeline_daemon.py` — polls for queued products every 5 seconds
- **GLB extraction:** `_extract_glb_path` handles multiple Gradio result shapes including `value` key
- **Output:** Saves to `static/uploads/optimized/mesh_prod_{uuid}.glb`
- **URL normalization:** Windows backslashes replaced with forward slashes in `model_3d_url`

### Render Fallback (Poster)
- `<model-viewer>` uses `poster` attribute to show `base_image` while GLB loads
- If no `model_3d_url` exists, the poster stays visible (no 3D model)
- Old texture fallback system (`_applySourceImageTexture` in `atelier-3d.js`) is deprecated — replaced by model-viewer

---

## Design Tokens

| Token | Value | Usage |
|-------|-------|-------|
| Background | `#FBF9F6` | Page bg, cream |
| Primary | `#0D2A22` | Deep emerald, buttons, headings |
| Accent | `#D4AF37` | Gold, badges, CTAs |
| Text | `#1A1A1A` | Body text |
| Success | `#10B981` | Positive states |
| Error | `#EF4444` | Negative states |

- **Typography:** Playfair Display (editorial), Inter (UI), Monospace (prices/statuses)
- **Dark mode:** Tailwind `darkMode: 'class'`, persisted in `localStorage["asiko:darkMode"]`

---

## Key Design Decisions

1. **No JS frameworks** — HTMX for server communication, Alpine.js for client state only
2. **`lines` not `items`** — Cart data uses `lines` key to avoid `dict.items()` collision
3. **Starlette 1.0 TemplateResponse** — `TemplateResponse(request, "name", {context})`
4. **Graceful email** — Brevo emails skip silently when API key is placeholder
5. **Atomic stock** — SELECT FOR UPDATE row locking prevents oversell
6. **Model-viewer 3D** — Google `<model-viewer>` web component (not custom Three.js). Built-in AR, camera controls, auto-rotation, environment lighting
7. **Pipeline daemon** — Lazy HF Space connection, retries on failure
8. **Poster fallback** — `base_image` shown as model-viewer poster when GLB unavailable
9. **Client-side search** — Alpine.js filtering (no server round-trip needed)
10. **Paystack reference** — `asiko_{order_id}` format, kobo amounts
11. **Customer auth** — SHA-256 + salt (not bcrypt) for simplicity
12. **Route export convention** — All modules export as `routes`
13. **Lifespan pool binding** — `app.state.db_pool` for direct pool access
14. **dotenv at entry** — `load_dotenv()` at top of `main.py`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Homepage with product grid, search/filter |
| GET | `/product/{product_id}` | Editorial PDP, 3D badge, reviews |
| GET | `/try/{product_id}` | 3D try-on page with model-viewer, Alpine.js in-place swap |
| POST | `/product/{product_id}/review` | Submit review |
| GET | `/product/{product_id}/reviews` | Reviews list (HTMX fragment) |
| GET | `/virtual-experience` | Showroom / 3D experience |
| POST | `/cart/add` | Add item to cart |
| POST | `/cart/update` | Modify cart quantity |
| GET | `/cart/drawer` | Cart drawer HTMX fragment |
| GET | `/checkout` | Checkout with Paystack |
| POST | `/checkout/submit` | Process order |
| GET | `/checkout/confirmation` | Order confirmation |
| POST | `/payments/webhook` | Paystack webhook (HMAC-SHA512) |
| GET | `/register` | Customer registration |
| POST | `/register` | Create account |
| GET | `/login` | Sign in page |
| POST | `/login` | Authenticate |
| GET | `/logout` | Sign out |
| GET | `/account` | Customer dashboard (order history) |
| GET | `/account/order/{order_id}` | Order detail |
| GET | `/about` | Public About page |
| GET | `/admin/dashboard` | Admin dashboard |
| GET | `/admin/sections/{section}` | Admin sections (15+) |
| GET | `/admin/products` | Admin products (HTMX) |
| POST | `/admin/products` | Create product |
| PUT | `/admin/products/{id}` | Edit product |
| DELETE | `/admin/products/{id}` | Delete product |
| POST | `/admin/orders/{order_id}/status` | Update order status |
| GET | `/admin/orders/{order_id}/items` | Order items fragment |
| POST | `/admin/waitlist/notify` | Batch restock emails |
| GET | `/api/realtime/pipeline/{product_id}` | Pipeline status (RT) |
| GET | `/api/realtime/activity` | Activity feed (RT) |
| GET | `/api/realtime/reviews` | Review notifications (RT) |
| GET | `/api/realtime/dashboard` | Dashboard KPIs (RT) |
| GET | `/api/realtime/pdp/{product_id}` | PDP stock/reviews (RT) |
| GET | `/api/stream/pipeline/{product_id}` | Pipeline SSE stream |
| GET | `/api/waitlist/stream/{variant_id}` | Waitlist SSE stream |
| POST | `/admin/reserve` | Reserve stock |
| POST | `/admin/settle` | Release expired holds |
| GET | `/admin/reservations` | List reservations |
| POST | `/webhooks/test-email` | Debug Brevo config |
| WS | `/ws/admin` | Admin WebSocket |
| WS | `/ws/store` | Store WebSocket |

---

## Environment Variables

```bash
# Neon PostgreSQL (required)
DATABASE_URL="postgresql://Asiko:npg_xxx@ep-xxx.pooler.region.aws.neon.tech/boutique?sslmode=require"

# Brevo Email (required for transactional emails)
BREVO_API_KEY="xkeysib-..."
SENDER_EMAIL="notifications@asikoboutique.com"

# Paystack (required for checkout)
PAYSTACK_SECRET_KEY="your_paystack_secret_key_here"

# Auth (required for customer registration/login)
AUTH_SALT="your-auth-salt-here"

# Session Security (optional)
SECRET_KEY="your-production-secret-key"

# Environment
ENVIRONMENT="development"
```

---

## Running

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Integration Tests
```bash
python -m pytest app/tests/test_admin_sections.py -v      # 72 tests
python -m pytest app/tests/test_admin_create_product.py -v  # 30 tests
python -m pytest app/tests/test_storefront_pages.py -v      # 43 tests
python -m pytest app/tests/test_realtime.py -v             # 35 tests
python -m pytest app/tests/test_pipeline_worker.py -v      # 7 tests
python -m pytest app/tests/ -v                             # All tests (excluding test_image_to_3d_pipeline.py which times out on DB pool init)
```

---

## Current State (Live DB)

- **All 10 products at `generating_mesh`** — Pipeline daemon processing them, none completed yet
- **Benin Bronze Cuff** — Manually assigned `model_3d_url = /static/uploads/optimized/mesh_prod_f4bcceab.glb`, `pipeline_status = completed` (stale GLB from old product)
- **Lagos Silk Blazer** — Stale auto-generated path cleared, now at `generating_mesh`
- **Product images:** All 10 products have `base_image` set to `/static/uploads/prod_*.jpg` (8 from Pexels, 2 from legacy uploads)
- **GLBs on disk (4 stale):** `mesh_prod_2eb03a95.glb` (1.5MB), `mesh_prod_709e8d8f.glb` (11.7MB), `mesh_prod_f4bcceab.glb` (14.1MB), `mesh_prod_fe644559.glb` (1.5MB) — all generated for deleted/seeded-over products
- **HF Space:** `/generation_all` broken (NameError, `HAS_TEXTUREGEN = False`), `/shape_generation` works but slow (30-60s per generation on free tier)
- **No NVIDIA GPU / no Docker** on this machine — cannot self-host Hunyuan3D-2
- **PAYSTACK_SECRET_KEY:** Placeholder — checkout fails until real test key provided
- **187 tests pass** (admin sections 72, admin create 30, storefront 43, realtime 35, pipeline worker 7)
- **Test files moved away from atelier-3d.js** — model-viewer checks for `ar-button`, `camera-controls` instead of Three.js canvas

---

## Remaining Work

1. **Paystack test keys** — Replace placeholder in `.env` to enable checkout
2. **Pipeline completion** — Wait for all 10 products to finish `generating_mesh`; pipeline has cold-start delays on public HF Space
3. **Self-host Hunyuan3D-2** — Needs GPU VM (RunPod, Vast.ai, or GCP with T4 ~$0.35/hr); not feasible on current dev machine (no NVIDIA GPU, no Docker)
4. **Proper AI textures (future)** — Self-host with `--enable_tex` flag (~16GB VRAM), or use Meshy/Tripo3D for better quality
