# ASIKO BOUTIQUE — Complete Project Documentation
# Nigerian Fashion Marketplace

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [What the Project Solves](#2-what-the-project-solves)
3. [Tech Stack](#3-tech-stack)
4. [Architecture Overview](#4-architecture-overview)
5. [Directory Structure](#5-directory-structure)
6. [Phase-by-Phase Development](#6-phase-by-phase-development)
7. [Core Systems Deep Dive](#7-core-systems-deep-dive)
8. [Database Schema](#8-database-schema)
9. [API Endpoints](#9-api-endpoints)
10. [Design System](#10-design-system)
11. [AI Fashion Stylist](#11-ai-fashion-stylist)
12. [Email System (Brevo)](#12-email-system-brevo)
13. [Payment Integration (OPay)](#13-payment-integration-opay)
14. [Real-Time System](#14-real-time-system)
15. [Admin Dashboard](#15-admin-dashboard)
16. [Customer Experience](#16-customer-experience)
17. [Performance Optimization](#17-performance-optimization)
18. [Security](#18-security)
19. [Testing](#19-testing)
20. [Environment Variables](#20-environment-variables)
21. [Running the Application](#21-running-the-application)
22. [Known Limitations](#22-known-limitations)
23. [Future Work](#23-future-work)
24. [QA Checklist](QA_CHECKLIST.md)

---

## 1. Executive Summary

ASIKO Boutique is a **single-brand Nigerian fashion e-commerce platform** built with Python/Starlette. It eliminates physical commercial lease costs, generator fuel expenses, and manual social-commerce transfer fraud. The platform features AI-powered fashion assistance, OPay payment integration, Brevo transactional email, a full admin dashboard with per-section settings, and a modern storefront with dynamic pages — all operated by a single boutique owner.

### Key Capabilities
- **8 garment categories**: Dress, Shirt, Trouser, Skirt, Jacket, Hoodie, Shoe, Bag
- **50+ products** with size/color variants and inventory tracking
- **AI Fashion Stylist** powered by OpenRouter (free models) with brand-aware responses
- **OPay payments** — card + bank transfer with HMAC-SHA512 webhook verification
- **Brevo email** — welcome, password reset, newsletter, order confirmation
- **Dynamic pages** — owner creates blog posts and custom pages, toggles live, chooses navbar/footer placement
- **Per-section admin settings** with save feedback for non-technical users
- **Separate dark modes** — admin and storefront use independent dark mode toggles
- **155+ automated tests** covering storefront, admin, realtime, and integrations

---

## 2. What the Project Solves

| Problem | Solution |
|---------|----------|
| Physical boutique rent in Lagos is ₦5M+/year | Online storefront costs near-zero hosting |
| Generator fuel ₦200K+/month | Cloud-hosted server (Neon Postgres, no server to run) |
| Social commerce fraud (no order tracking) | Full order lifecycle with OPay verification |
| Manual inventory (Excel/spreadsheet) | Real-time stock management with variant tracking |
| No customer data ownership | Customer accounts with order history and preferences |
| 3D try-on not feasible (no GPU, no Blender) | Brand-focused 3D PNG imagery site-wide |
| Generic AI chatbots | Brand-aware AI Stylist trained on ASIKO products and Nigerian fashion |
| Non-technical owner can't update site | Admin settings for every section (homepage, shop, about, etc.) |
| Transactional email required | Brevo API integration for all email types |

---

## 3. Tech Stack

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.14 |
| **Web Framework** | Starlette 1.0 (async ASGI) |
| **Database** | PostgreSQL via asyncpg (Neon serverless) |
| **Templates** | Jinja2 |
| **Interactivity** | HTMX 1.9.12 + Alpine.js 3.14 |
| **Styling** | Tailwind CSS (CDN) |
| **Sessions** | Starlette SessionMiddleware (signed cookie) |
| **Email** | Brevo SMTP API (REST) |
| **Payments** | OPay (card + bank transfer, HMAC-SHA512) |
| **AI** | OpenRouter (free models: Gemini, Llama, Mistral, Qwen) |
| **Payments Framework** | OPay (not Paystack — user chose OPay for Nigerian market familiarity) |
| **Real-Time** | WebSocket + Postgres LISTEN/NOTIFY (4 channels) |
| **3D Branding** | Free 3D-rendered PNG images (no WebGL, no Three.js) |
| **Testing** | pytest + pytest-asyncio |

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  HTMX (server-driven) + Alpine.js (client state) + Tailwind     │
│  Admin: 14-section sidebar | Store: Navbar + Footer              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                     ASGI APPLICATION                              │
│  Starlette app factory (app/main.py)                             │
│  ├── SessionMiddleware (signed cookie, 7-day expiry)             │
│  ├── CustomPagesMiddleware (30s TTL cache, single DB query)      │
│  ├── NoCacheStaticFiles (debug-only no-cache)                    │
│  └── Route modules (19 route files)                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ asyncpg pool (min=2, max=10)
┌──────────────────────────▼──────────────────────────────────────┐
│                    SERVICE LAYER                                  │
│  ├── settings_service.py (TTL cache, defaults dict)              │
│  ├── fashion_ai.py (OpenRouter/OpenAI/Anthropic/rule-based)     │
│  ├── brevo.py (transactional email + contact sync)               │
│  ├── opay_service.py (payment init, verify, webhooks)           │
│  ├── settlement.py (settlement service)                          │
│  ├── dpp_crypto.py (Digital Product Passport signing)            │
│  └── mesh_generator.py (3D mesh generation)                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  DATA LAYER                                       │
│  Neon Postgres (serverless)                                       │
│  ├── 60+ tables across 24 migrations                             │
│  ├── 4 LISTEN/NOTIFY channels (pipeline, reviews, orders, stock) │
│  ├── store_settings singleton (id=1, 50+ columns)                │
│  └── Connection retry logic (4 attempts, exponential backoff)     │
└─────────────────────────────────────────────────────────────────┘
```

### Request Lifecycle
1. **Client request** → Starlette ASGI app
2. **SessionMiddleware** validates/creates signed session cookie
3. **CustomPagesMiddleware** checks in-memory cache (30s TTL), fetches nav/footer pages if stale
4. **Route handler** processes request (may call settings_service, fashion_ai, brevo, opay)
5. **Jinja2 template** rendered with context (settings, cart, customer, nav_pages)
6. **HTMX response** (fragment) or full HTML page returned
7. **WebSocket/SSE** for real-time updates (admin dashboard, store stock, pipeline status)

---

## 5. Directory Structure

```
asiko-boutique/
├ .env                              # DATABASE_URL, BREVO_API_KEY, OPAY_* keys, AUTH_SALT
├ .env.example                      # Template for environment variables
├ knowledge.md                      # Project knowledge base
├ design.md                         # Design specifications
├ requirements.txt                  # Python dependencies
├ package.json                      # Tailwind build (if needed)
├ run.bat / run.ps1                 # Dev server launch scripts
│
├ app/
│   ├── __init__.py
│   ├── main.py                     # App factory, route registration, lifespan, middleware
│   ├── database.py                 # asyncpg pool lifecycle with retry logic
│   ├── core.py                     # Jinja2 templates, naira filter, session helpers
│   ├── realtime.py                 # ConnectionManager, Postgres LISTEN/NOTIFY
│   ├── settings_service.py         # Centralized settings with TTL cache
│   ├── fashion_ai.py               # Multi-provider LLM, intent detection, recommendations
│   ├── color_analysis.py           # Color analysis module
│   │
│   ├── services/
│   │   ├── brevo.py                # Brevo email service (send + templates)
│   │   ├── opay_service.py         # OPay payment (init, verify, webhooks)
│   │   ├── settlement.py           # Settlement service
│   │   ├── mesh_generator.py       # 3D mesh generation
│   │   └── dpp_crypto.py           # Digital Product Passport cryptography
│   │
│   ├── routes/
│   │   ├── storefront.py           # Homepage, PDP, lookbook, DPP, About
│   │   ├── cart.py                 # HTMX cart add/update/drawer
│   │   ├── checkout.py             # OPay checkout flow
│   │   ├── webhooks.py             # OPay webhook, inline Brevo dispatch
│   │   ├── admin.py                # Admin product CRUD
│   │   ├── admin_sections.py       # 15+ section handlers, order status, RT fragments
│   │   ├── admin_dashboard.py      # Pipeline link-2d, pipeline status
│   │   ├── admin_inventory.py      # Inventory management routes
│   │   ├── customer.py             # Register, login, forgot-password, newsletter
│   │   ├── waitlist.py             # Out-of-stock enrollment
│   │   ├── dpp_verification.py     # Avatar profile binding
│   │   ├── fashion_chat.py         # AI Stylist chat API
│   │   ├── wardrobe.py             # Wardrobe management API
│   │   ├── ws_admin.py             # Admin WebSocket
│   │   ├── ws_store.py             # Store WebSocket
│   │   ├── sse_streams.py          # Server-Sent Events
│   │   └── luxury_extensions.py    # Luxury feature routes
│   │
│   ├── catalog/
│   │   └── routes.py               # Catalog routes
│   │
│   ├── workers/
│   │   └── pipeline_daemon.py      # Hunyuan3D-2 pipeline (deprecated)
│   │
│   ├── templates/
│   │   ├── base.html               # Public shell, dark mode, toast, confirm dialog
│   │   ├── fashion_assistant.html  # AI Stylist chatroom page
│   │   ├── admin/
│   │   │   ├── base.html           # Admin shell, 14 nav items, dark mode, toasts
│   │   │   └── sections/           # 24 section templates
│   │   │       ├── dashboard.html
│   │   │       ├── products.html
│   │   │       ├── orders.html
│   │   │       ├── sales.html
│   │   │       ├── analytics.html
│   │   │       ├── members.html
│   │   │       ├── operations.html
│   │   │       ├── settings.html   # 11+ config sections
│   │   │       ├── about.html
│   │   │       ├── logistics.html
│   │   │       ├── social.html
│   │   │       ├── loyalty.html
│   │   │       ├── tags.html
│   │   │       ├── pages.html      # Dynamic pages management
│   │   │       └── blog.html       # Blog management
│   │   ├── storefront/
│   │   │   ├── index.html          # Homepage
│   │   │   ├── product_detail.html # PDP
│   │   │   ├── product_grid.html   # Shop grid
│   │   │   ├── about.html          # About page
│   │   │   ├── lookbook.html       # Lookbook
│   │   │   ├── dpp_verification.html # DPP verification
│   │   │   ├── page.html           # Dynamic custom page
│   │   │   ├── blog_listing.html   # Blog listing
│   │   │   └── blog_post.html      # Individual blog post
│   │   ├── customer/
│   │   │   ├── dashboard.html      # Customer dashboard
│   │   │   ├── order_detail.html   # Order detail
│   │   │   ├── register.html       # Registration
│   │   │   ├── login.html          # Login
│   │   │   ├── forgot_password.html # Forgot password
│   │   │   └── reset_password.html # Reset password
│   │   ├── cart/
│   │   │   ├── cart_badge.html     # Cart count badge
│   │   │   └── cart_content.html   # Cart drawer content
│   │   ├── checkout/
│   │   │   ├── index.html          # Checkout page
│   │   │   ├── confirmation.html   # Order confirmation
│   │   │   └── shipping_summary.html
│   │   └── components/             # Reusable components
│   │
│   └── tests/                      # 14 test files, 155+ tests
│       ├── test_admin_sections.py
│       ├── test_admin_create_product.py
│       ├── test_storefront_pages.py
│       ├── test_realtime.py
│       ├── test_pipeline_worker.py
│       ├── test_catalog.py
│       ├── test_dpp.py
│       ├── test_dual_ingestion.py
│       ├── test_flow.py
│       ├── test_schema_guard.py
│       ├── test_sse_streams.py
│       ├── test_webhooks.py
│       └── test_image_to_3d_ledger.py
│
├ database/
│   └── migrations/                 # 13 migration files (05-23)
│       ├── 05_single_brand.sql
│       ├── 06_schema_alignment.sql
│       ├── 07_gltf_columns.sql
│       ├── 08_admin_redesign.sql
│       ├── 09_admin_redesign.sql
│       ├── 10_seed_catalog.sql
│       ├── 11_customers_auth.sql
│       ├── 12_product_images_pipeline.sql
│       ├── 13_virtual_avatar.sql
│       ├── 14_admin_audit.sql
│       ├── 15_measurements_body_types.sql
│       ├── 16_ai_fashion.sql
│       ├── 17_logistics_providers.sql
│       ├── 18_social_commerce.sql
│       ├── 19_loyalty_referrals.sql
│       ├── 20_settings_expansion.sql
│       ├── 21_ai_training_data.sql
│       ├── 22_custom_pages.sql
│       └── 23_password_reset_tokens.sql
│
├ static/
│   ├── css/
│   ├── js/
│   ├── images/
│   │   ├── branding/               # Brand logos and assets
│   │   ├── icon-image/             # 16 3D PNG images (hero, login, etc.)
│   │   ├── products/               # Product images
│   │   └── lookbook/               # Lookbook images
│   ├── assets/
│   └── uploads/                    # User-uploaded files
│
└ docs/
    ├── ASIKO_BOUTIQUE.md           # This document
    └── PHASE_4_ARCHITECTURE.md     # Historical (to be deleted)
```

---

## 6. Phase-by-Phase Development

### Phase 1: Core E-Commerce (Complete)
**Goal:** Basic storefront with product catalog and cart.

- Product catalog with 8 categories (Dress, Shirt, Trouser, Skirt, Jacket, Hoodie, Shoe, Bag)
- Product detail pages with size/color variants
- Shopping cart with HTMX-powered add/update/drawer
- Checkout flow with order creation
- Customer registration and login (SHA-256 + salt)
- Session-based cart persistence
- Admin product CRUD (create, read, update, delete)
- Seed catalog: 10 products with 39 variants (₦8K – ₦120K range)

### Phase 2: Payments & Delivery (Complete)
**Goal:** Nigerian payment integration and delivery system.

- OPay integration (card + bank transfer)
- Webhook verification (HMAC-SHA512)
- 36-state Nigerian shipping matrix (₦1,500 Lagos to ₦4,000 Borno)
- Order lifecycle: pending → paid → processing → shipped → delivered
- Admin order management with status updates
- Brevo transactional email (order confirmation, status updates)

### Phase 3: AI Fashion Assistant (Complete)
**Goal:** Brand-aware AI stylist powered by free LLM models.

- OpenRouter integration (Gemini 2.0 Flash, Llama 3.3, Mistral, Qwen3)
- Intent detection (13 patterns: wedding, church, office, party, casual, traditional, date, color, trend, wardrobe, budget, season)
- Product recommendation engine with scoring (0-100) based on preferences, occasion, color harmony, season, stock
- Color harmony rules (complementary colors, seasonal palettes)
- Category compatibility matrix (dress↔shoe↔bag, shirt↔trouser↔jacket, etc.)
- Brand-aware system prompt built from DB: training data + current product catalog
- Wardrobe manager: analyze owned pieces, suggest missing items, generate outfit combinations
- Event styling: occasion-specific recommendations from style_events table
- Rule-based fallback when no LLM configured
- Chat history persistence in fashion_chat_history table

### Phase 4: Admin Dashboard (Complete)
**Goal:** Full admin control for non-technical boutique owner.

- 14-section admin sidebar with light-blue active states
- Dashboard with real-time KPIs (total sales, orders, products, customers)
- Product management (CRUD with variant support)
- Order management with status dropdowns
- Analytics section with charts
- Members/customer management
- Operations: inventory tracking, order processing, waitlist management
- AI Stylist admin: training data CRUD (add Q&A pairs for brand knowledge)
- Settings: per-section save with 11+ configuration areas
- Notifications: bell icon with real-time unread count
- Custom confirm dialog (replaces browser `window.confirm`)
- Toast notifications (`asikoToast()`) for success/failure feedback
- Dark mode toggle (admin-specific key: `asiko:admin:darkMode`)

### Phase 5: Storefront Redesign (Complete)
**Goal:** Fashion-first design with modern UI patterns.

- Hero section with floating 3D PNG images (real 3D-rendered PNGs, not CSS silhouettes)
- Trust badges (Free Shipping, Secure Payment, Authentic Quality, Easy Returns)
- Product cards with stopPropagation (cart form doesn't trigger card link)
- Simplified checkout (step-by-step visual, two-column layout, sticky summary)
- Customer dashboard extending base.html (consistent dark mode)
- Product detail page with rounded-xl cards, form separated from nav
- Dynamic pages system (owner creates pages, toggles live, chooses navbar/footer)
- Blog system (owner writes posts, published to /blog)
- Footer redesigned: dark emerald with newsletter, 4-column grid
- Mobile responsive across all breakpoints (login, register, dashboard, admin)

### Phase 6: Email & Settings (Complete)
**Goal:** Complete email system and centralized settings.

- Brevo email service (`app/services/brevo.py`) — centralized for all email types
- Welcome greeting email on customer registration (async, non-blocking)
- Password reset flow: `/forgot-password` → email with 1hr token → `/reset-password`
- Newsletter subscribe with Brevo contact sync
- 50+ store_settings columns across all sections
- Settings TTL cache (30s in-memory, invalidated on save)
- Per-section save buttons in admin settings
- `_pg_literal()` for safe SQL embedding with asyncpg
- Performance: NoCacheStaticFiles debug-only, CustomPagesMiddleware 30s cache

### Phase 7: Polish & Documentation (Current)
**Goal:** Documentation, testing, and production readiness.

- Comprehensive project documentation (this document)
- 155+ automated tests
- DB connection retry logic (4 attempts, exponential backoff)
- Separate dark mode keys (admin vs storefront)
- Toast/alert system unified across all sections
- Custom confirm dialog (vanilla JS, Promise-based)
- Password visibility toggles on login/register
- Register page: confirm password + terms checkbox
- Remember me toggle on login
- Logout button in customer dashboard

---

## 7. Core Systems Deep Dive

### 7.1 Settings Service (`app/settings_service.py`)

**Pattern:** Singleton row in `store_settings` (id=1), in-memory TTL cache (30s), defaults dict.

```python
# Default settings — used when DB row is missing
DEFAULTS = {
    "store_name": "ASIKO Boutique",
    "ai_provider": "openrouter",
    "ai_model": "google/gemini-2.0-flash-001",
    "hero_title": "Authentic",
    "hero_title_accent": "Nigerian Fashion",
    "chatbot_enabled": True,
    "blog_enabled": True,
    "email_welcome_enabled": True,
    # ... 50+ keys
}

async def get_settings(db_pool) -> dict:
    # Returns cached settings or fetches from DB
    # Cache TTL: 30 seconds

async def save_settings(db_pool, payload, partial=False) -> bool:
    # Uses _pg_literal() for SQL embedding (not $N parameters)
    # Invalidates cache after save
```

**Why raw SQL embedding?** asyncpg's prepared statement cache breaks with dynamic column INSERT/UPDATE. Column names are code-controlled (safe), string values are single-quote-escaped.

### 7.2 Custom Pages Middleware

**Problem:** Every page request needs nav/footer pages from DB → 2 queries per request.

**Solution:** In-memory TTL cache with single query every 30s.

```python
class CustomPagesMiddleware:
    _nav_pages: list = []
    _footer_pages: list = []
    _cache_ts: float = 0.0
    CACHE_TTL: int = 30

    async def __call__(self, scope, receive, send):
        # Check cache, fetch if stale (1 query), set request.state.nav_pages
```

### 7.3 AI Fashion Stylist (`app/fashion_ai.py`)

**Multi-Provider LLM:**
- OpenRouter (default): Free models — Gemini 2.0 Flash, Llama 3.3 70B, Mistral Small, Qwen3 235B
- OpenAI: GPT-4o-mini (if OPENAI_API_KEY set)
- Anthropic: Claude 3.5 Haiku (if ANTHROPIC_API_KEY set)
- Rule-based fallback: When no LLM configured

**Brand-Aware Prompt (`_build_brand_aware_prompt()`):**
1. Base system prompt (Nigerian fashion stylist persona)
2. Brand info from settings (store name, description)
3. Training data from `ai_training_data` table (6 categories: brand, faq, product, style, voice, custom)
4. Current product catalog (top 30 in-stock items with prices)
5. Admin override instructions (highest priority)

**Intent Detection (`detect_intent()`):**
13 regex patterns detect user intent:
- `recommend` → "show me something for..."
- `wedding` → wedding-guest event slug
- `church` → church event slug
- `office` → office/business event slug
- `party` → party event slug
- `casual` → casual event slug
- `traditional` → traditional event slug
- `date` → date-night event slug
- `color` → color question
- `trend` → trend question
- `wardrobe` → wardrobe question
- `budget` → budget question
- `season` → seasonal recommendation

**Product Scoring (`score_product_for_user()`):**
Scores 0-100 based on:
- Budget fit (+/-15)
- Category relevance for occasion (+/-20)
- Color harmony (+/-15)
- Season match (+/-10)
- Stock availability (-30 if out of stock)
- Purchase history diversity (-10 if same category recently bought)
- Description quality (+3)

**Category Compatibility Matrix:**
```python
CATEGORY_PAIRS = {
    "dress": ["shoe", "bag", "accessory"],
    "shirt": ["trouser", "skirt", "shoe", "bag", "jacket"],
    "trouser": ["shirt", "hoodie", "jacket", "shoe", "bag"],
    "skirt": ["shirt", "blouse", "jacket", "shoe", "bag"],
    "jacket": ["shirt", "trouser", "skirt", "dress"],
    "hoodie": ["trouser", "skirt", "shoe"],
    "shoe": ["dress", "shirt", "trouser", "skirt", "bag"],
    "bag": ["dress", "shirt", "trouser", "skirt"],
}
```

### 7.4 Cart System

**Storage:** Server-side session (signed cookie, 7-day expiry).

**Data Shape:** `{"lines": [...], "total": float, "item_count": int}`
- Uses `lines` key (not `items`) to avoid Python `dict.items()` collision.

**Stock Validation:** SELECT FOR UPDATE row locking prevents oversell.

**Cart Badge Fix:** Uses `id="cart-badge"` on `<span>` wrapper. HTMX `hx-swap="outerHTML"` replaces entire element.

### 7.5 Toast & Confirm System

**Toast (`asikoToast(type, title, msg)`):**
- Types: `success`, `error`, `info`, `warning`
- Query param auto-display: `?toast_success=Order+placed`
- HTMX POST auto-toast via `HX-Trigger` header
- 4-second auto-dismiss with progress bar

**Confirm (`asikoConfirm(title, message, opts)`):**
- Vanilla JS, returns Promise (async/await compatible)
- Custom modal (not browser `window.confirm()`)
- Options: `confirmText`, `cancelText`, `danger` (red button)
- Zero `hx-confirm` remaining in codebase

---

## 8. Database Schema

### Core Tables
| Table | Purpose |
|-------|---------|
| `stores` | Single ASIKO store (slug: `asiko`) |
| `products` | Product catalog with 8 categories |
| `product_variants` | Size/color variants (48+ seeded) |
| `orders` | Customer orders with JSONB metadata |
| `order_items` | Line items with product FK |
| `nigerian_states` | 37 rows (36 states + FCT) with shipping costs |
| `customers` | Customer accounts (SHA-256 + salt auth) |
| `categories` | Product categories (Tailoring, Dresses, Outerwear, Accessories, Footwear) |
| `product_reviews` | Customer reviews with rating, verified badge, admin reply |

### Settings & Configuration
| Table | Purpose |
|-------|---------|
| `store_settings` | Singleton row (id=1), 50+ columns for all settings |
| `ai_training_data` | Brand knowledge Q&A for AI Stylist (migration 21) |
| `custom_pages` | Dynamic pages with is_live, show_in_nav, show_in_footer (migration 22) |
| `blog_posts` | Blog posts linked to custom_pages (migration 22) |

### Authentication & Security
| Table | Purpose |
|-------|---------|
| `customers` | Customer accounts with password_hash |
| `password_reset_tokens` | Password reset tokens (1hr expiry, single-use) (migration 23) |
| `admin_audit_log` | Admin action audit trail |

### AI & Recommendations
| Table | Purpose |
|-------|---------|
| `user_preferences` | Customer style preferences (colors, occasions, budget, fit) |
| `fashion_chat_history` | Chat history (customer_id or session_id) |
| `wardrobe_items` | Customer wardrobe inventory |
| `style_events` | Occasion-specific styling rules (wedding, church, office, etc.) |

### Commerce & Logistics
| Table | Purpose |
|-------|---------|
| `product_waitlists` | Out-of-stock enrollment |
| `delivery_providers` | Nigerian delivery providers (Kwik, GIG, DHL, FedEx) |
| `social_commerce` | Social sharing tracking |
| `loyalty_programs` | Customer loyalty/referral system |

### Digital Product Passport
| Table | Purpose |
|-------|---------|
| `dpp_passports` | Digital Product Passport provenance |
| `avatar_profiles` | Avatar profile binding for verification |

### Migrations
24 migrations covering:
- 05: Single-brand consolidation
- 06: Schema alignment (payload_metadata, session_identifier)
- 07: 3D GLTF columns (model_3d_url, mesh_node_identifier)
- 08-09: Admin redesign (categories, product_reviews, store_settings)
- 10: Seed catalog (10 products, 39 variants)
- 11: Customer auth (customers table, order FK)
- 12: Product images pipeline
- 13: Virtual avatar system
- 14: Admin audit log
- 15: Measurements & body types
- 16: AI fashion assistant tables
- 17: Logistics providers (Nigerian delivery)
- 18: Social commerce
- 19: Loyalty & referrals
- 20: Settings expansion (28 new columns)
- 21: AI training data
- 22: Custom pages & blog
- 23: Password reset tokens

---

## 9. API Endpoints

### Storefront
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Homepage with product grid, search/filter |
| GET | `/product/{product_id}` | Editorial PDP with reviews |
| GET | `/lookbook` | Curated ensembles and styling inspiration |
| GET | `/about` | Public About page |
| GET | `/page/{slug}` | Dynamic custom page |
| GET | `/blog` | Blog listing |
| GET | `/blog/{slug}` | Individual blog post |

### Cart & Checkout
| Method | Path | Description |
|--------|------|-------------|
| POST | `/cart/add` | Add item to cart (accepts product_id or variant_id) |
| POST | `/cart/update` | Modify cart quantity |
| GET | `/cart/drawer` | Cart drawer HTMX fragment |
| GET | `/cart/badge` | Cart count badge |
| GET | `/checkout` | Checkout with OPay |
| POST | `/checkout/submit` | Process order |

### Customer
| Method | Path | Description |
|--------|------|-------------|
| GET | `/register` | Registration page |
| POST | `/register` | Create account (sends welcome email async) |
| GET | `/login` | Login page |
| POST | `/login` | Authenticate |
| GET | `/logout` | Sign out |
| GET | `/account` | Customer dashboard (order history) |
| GET | `/account/order/{order_id}` | Order detail |
| GET | `/forgot-password` | Forgot password page |
| POST | `/forgot-password` | Submit password reset |
| GET | `/reset-password?token=...` | Reset password page |
| POST | `/reset-password` | Submit new password |
| POST | `/newsletter/subscribe` | Newsletter subscribe |

### AI Stylist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/stylist` | AI Stylist chatroom page |
| POST | `/api/fashion/chat` | Send message to AI Stylist |
| GET | `/api/fashion/recommendations` | Get product recommendations |
| GET | `/api/fashion/events` | List style events |
| GET | `/api/fashion/event/{slug}` | Get event styling advice |
| POST | `/api/wardrobe/add` | Add item to wardrobe |
| GET | `/api/wardrobe/list` | List wardrobe items |
| POST | `/api/wardrobe/analyze` | Analyze wardrobe |

### Admin
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/dashboard` | Admin dashboard |
| GET | `/admin/sections/{section}` | Admin sections (15+) |
| GET | `/admin/products` | Admin products (HTMX) |
| POST | `/admin/products` | Create product |
| PUT | `/admin/products/{id}` | Edit product |
| DELETE | `/admin/products/{id}` | Delete product |
| POST | `/admin/orders/{order_id}/status` | Update order status |
| POST | `/admin/sections/settings` | Save settings (per-section) |
| GET | `/admin/pages` | Dynamic pages management |
| POST | `/admin/pages` | Create/update page |
| POST | `/admin/pages/{id}/toggle` | Toggle page live status |
| GET | `/admin/blog` | Blog management |
| POST | `/admin/blog` | Create/update blog post |

### Real-Time
| Method | Path | Description |
|--------|------|-------------|
| WS | `/ws/admin` | Admin WebSocket (real-time updates) |
| WS | `/ws/store` | Store WebSocket (stock updates) |
| GET | `/api/realtime/pipeline/{product_id}` | Pipeline status (RT) |
| GET | `/api/realtime/activity` | Activity feed (RT) |
| GET | `/api/realtime/reviews` | Review notifications (RT) |
| GET | `/api/realtime/dashboard` | Dashboard KPIs (RT) |
| GET | `/api/stream/pipeline/{product_id}` | Pipeline SSE stream |

### Payments & Webhooks
| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhooks/opay` | OPay webhook (HMAC-SHA512) |
| GET | `/payment/process/return` | OPay return URL |
| POST | `/payment/process/callback` | OPay callback |

---

## 10. Design System

### Design Tokens
| Token | Value | Usage |
|-------|-------|-------|
| Background | `#FBF9F6` | Page bg, cream |
| Primary | `#0D2A22` | Deep emerald, buttons, headings |
| Accent | `#D4AF37` | Gold, badges, CTAs |
| Text | `#1A1A1A` | Body text |
| Success | `#10B981` | Positive states |
| Error | `#EF4444` | Negative states |

### Typography
- **Playfair Display**: Editorial headings, hero text
- **Inter**: UI elements, body text
- **Monospace**: Prices, statuses, codes

### Dark Mode
- Admin: `localStorage["asiko:admin:darkMode"]`
- Storefront: `localStorage["asiko:store:darkMode"]`
- Independent toggles — admin dark mode doesn't affect storefront
- Tailwind `darkMode: 'class'` with `dark:` prefix classes

### 3D Brand Imagery
16 free 3D-rendered PNG images in `static/images/icon-image/`:
- Hero: Floating fashion items
- Login/Register: Background imagery
- Lookbook: Category illustrations
- Footer: Decorative elements
- Dashboard: Welcome imagery
- Admin sidebar: Brand identity

### Mobile Responsiveness
All pages fully responsive:
- Admin: Hamburger menu, collapsible sidebar
- Store: Stacked layouts, touch-friendly
- Login/Register: Centered cards, full-width on mobile
- Cart: Drawer overlay, responsive grid
- Checkout: Single-column on mobile, two-column on desktop

---

## 11. AI Fashion Stylist

### Provider Configuration
Configurable from admin settings (`ai_provider`, `ai_api_key`, `ai_model`):

| Provider | Models | Cost |
|----------|--------|------|
| OpenRouter (default) | Gemini 2.0 Flash, Llama 3.3 70B, Mistral Small, Qwen3 235B | Free tier available |
| OpenAI | GPT-4o-mini | Pay-per-token |
| Anthropic | Claude 3.5 Haiku | Pay-per-token |
| None | Rule-based responses | Free |

### Training Data
Admin can add Q&A pairs in 6 categories via `/admin/sections/ai-stylist`:
- **brand**: Brand story, values, mission
- **faq**: Common customer questions
- **product**: Product-specific knowledge
- **style**: Nigerian fashion expertise
- **voice**: Brand voice guidelines
- **custom**: Additional context

### Chatroom Features
- Immersive full-screen chat (no footer in chatroom)
- Product recommendations inline with chat
- Quick suggestion chips (configurable from settings)
- Welcome message (configurable from settings)
- Chat history persistence
- Session-based for anonymous users, customer_id for logged-in users

### System Prompt Structure
```
1. Base personality (Nigerian fashion stylist)
2. Brand info from settings
3. Training data from ai_training_data table
4. Current product catalog (30 items)
5. Admin override instructions
```

---

## 12. Email System (Brevo)

### Centralized Service (`app/services/brevo.py`)
All email goes through `send_transactional_email()` — single point of configuration.

### Email Types
| Type | Trigger | Template |
|------|---------|----------|
| Welcome | Customer registration | Branded greeting with "Start Shopping" CTA |
| Password Reset | `/forgot-password` submit | Reset link with 1hr expiry |
| Newsletter Confirm | `/newsletter/subscribe` | Subscription confirmation |
| Order Confirmation | Order paid | Order details + tracking |
| Status Update | Admin changes status | Shipping/delivery notification |

### Brand Templates
All emails wrapped in:
- `_BRAND_HEADER`: Deep emerald (#0D2A22) header with "ASIKO BOUTIQUE" + "Contemporary Nigerian Fashion"
- `_BRAND_FOOTER`: Gold (#D4AF37) footer with copyright

### Configuration (Admin Settings)
- `brevo_api_key`: Brevo API key (from .env)
- `sender_email`: Sender email address
- `sender_name`: "ASIKO Boutique"
- `admin_email`: "hello@asikoboutique.com"
- 5 boolean toggles: welcome, order, shipping, newsletter, password_reset

### Graceful Degradation
When API key is placeholder (`your_*`), emails skip silently — no errors, no crashes.

---

## 13. Payment Integration (OPay)

### Flow
```
1. Customer fills checkout form
2. POST /checkout/submit → creates order (status: pending)
3. initialize_opay_payment() → OPay API
4. Redirect to OPay payment page
5. Customer pays (card or bank transfer)
6. OPay webhook → POST /webhooks/opay
7. verify_opay_webhook_signature() → HMAC-SHA512
8. Update order status → paid
9. Redirect to /checkout/confirmation
```

### OPay API Endpoints Used
- `POST /api/v1/gateway/webanchor/initialize` — Initialize payment
- `GET /api/v1/gateway/query/reference` — Verify payment
- `POST /api/v1/bank-transfer/create` — Virtual bank account

### Mock Mode
When `OPAY_SECRET_KEY` starts with `your_`:
- `initialize_opay_payment()` returns mock URL
- `verify_opay_payment()` returns mock success
- `verify_opay_webhook_signature()` returns True
- `get_opay_bank_account()` returns mock details

### Reference Format
`asiko_{order_id}` — consistent with previous Paystack integration.

---

## 14. Real-Time System

### Architecture
- **WebSocket**: Bidirectional for admin dashboard and store stock updates
- **SSE (Server-Sent Events)**: One-way for pipeline status, activity feed
- **Postgres LISTEN/NOTIFY**: 4 channels for database-level events

### Channels
| Channel | Purpose |
|---------|---------|
| `ch_pipeline` | 3D pipeline status updates |
| `ch_new_review` | New product review notifications |
| `ch_new_order` | New order alerts |
| `ch_stock` | Stock level changes |

### ConnectionManager (`app/realtime.py`)
- Maintains active WebSocket connections per channel
- `broadcast(channel, data)` — sends to all connected clients
- `start_listeners(pool)` — starts Postgres LISTEN/NOTIFY
- `stop_listeners()` — graceful shutdown

---

## 15. Admin Dashboard

### Sidebar Navigation (14 items)
**Core Group:**
- Dashboard (KPIs)
- Sales (orders, revenue)
- View Store (opens storefront)

**Product Group:**
- Products (CRUD)
- Tags (product tagging)
- Analytics (charts)
- Members (customers)
- Operations (inventory, orders, waitlist)

**Growth Group:**
- Logistics (delivery providers)
- Social (social commerce)
- Loyalty (referral program)
- AI Stylist (training data)
- Pages (dynamic pages)
- Blog (blog management)

**Account Group:**
- Settings (11+ sections)
- About Me (store profile)

### Settings Sections (11+)
1. Store Profile
2. AI Provider
3. Homepage
4. Lookbook
5. Shop
6. About
7. AI Stylist
8. Pages & Blog
9. Security
10. Notifications
11. Email (Brevo)
12. Email Notifications

Each section has its own save button. Save triggers `asikoToast()` feedback.

### Admin Dark Mode
- Toggle button in header
- Persisted to `localStorage["asiko:admin:darkMode"]`
- Applies `dark` class to `<html>` element
- All admin templates support `dark:` Tailwind classes

---

## 16. Customer Experience

### Registration
- Full name, email, password, confirm password
- Password visibility toggle (eye icon)
- Agree to Terms checkbox (required)
- Welcome email sent async via Brevo

### Login
- Email + password
- Password visibility toggle
- Remember me toggle (7-day session)
- Forgot password link

### Password Reset
- `/forgot-password` → enter email
- Token generated (64-char, 1hr expiry, single-use)
- Email sent with reset link
- `/reset-password?token=...` → enter new password
- Token marked as used

### Customer Dashboard
- Order history with status badges
- Quick actions: Continue Shopping, Wishlist, Track Order, Profile, Logout
- Order detail page with full item breakdown
- Extends base.html (consistent dark mode)

### Newsletter
- Subscribe form in footer
- POST `/newsletter/subscribe`
- Syncs to Brevo contact list
- Confirmation email sent

---

## 17. Performance Optimization

### Settings TTL Cache
- In-memory cache with 30-second TTL
- `get_settings()` returns cached if fresh
- `save_settings()` calls `invalidate_settings_cache()`
- Avoids DB query on every page load

### CustomPagesMiddleware Cache
- Single DB query every 30 seconds (not per-request)
- Caches nav pages and footer pages
- Attached to `request.state` for template access

### NoCacheStaticFiles
- Debug mode: Forces fresh fetch (no 304)
- Production: Normal browser caching (`ASIKO_DEBUG=false`)
- Anti-304 bypass for local dev hot-reload

### Database Connection
- Connection pool: min=2, max=10
- Command timeout: 60 seconds
- Max inactive connection lifetime: 300 seconds
- Retry logic: 4 attempts with exponential backoff (2s, 4s, 8s, 16s)

### Combined DB Queries
- Analytics KPIs in single subquery
- Product funnel in single GROUP BY
-减少了数据库查询次数

---

## 18. Security

### Authentication
- Customer: SHA-256 + salt (not bcrypt, for simplicity)
- Salt from `AUTH_SALT` env var
- Session cookie: `asiko_session`, 7-day expiry

### Payment Security
- OPay HMAC-SHA512 webhook verification
- Reference format: `asiko_{order_id}`
- Mock mode for development

### Password Reset
- 64-character random token
- 1-hour expiry
- Single-use (marked as used after reset)
- Stored in `password_reset_tokens` table

### Session Security
- Signed cookie (SECRET_KEY)
- 7-day max age
- Server-side session data

### SQL Injection Prevention
- asyncpg parameterized queries ($1, $2, etc.)
- `_pg_literal()` for settings save (code-controlled columns only)
- No user input in column names

### CSRF Protection
- Starlette SessionMiddleware provides CSRF tokens
- Forms include CSRF token

---

## 19. Testing

### Test Files (14)
| File | Tests | Coverage |
|------|-------|----------|
| `test_admin_sections.py` | 72 | Admin section handlers |
| `test_admin_create_product.py` | 30 | Product CRUD |
| `test_storefront_pages.py` | 43 | Storefront routes |
| `test_realtime.py` | 35 | WebSocket, LISTEN/NOTIFY |
| `test_pipeline_worker.py` | 7 | Pipeline daemon |
| `test_catalog.py` | ~15 | Catalog routes |
| `test_dpp.py` | ~10 | Digital Product Passport |
| `test_dual_ingestion.py` | ~10 | Dual ingestion |
| `test_flow.py` | ~15 | End-to-end flows |
| `test_schema_guard.py` | ~10 | Schema validation |
| `test_sse_streams.py` | ~10 | Server-Sent Events |
| `test_webhooks.py` | ~10 | OPay webhooks |

### Running Tests
```bash
# All tests
python -m pytest app/tests/ -v

# Specific test file
python -m pytest app/tests/test_admin_sections.py -v

# With coverage
python -m pytest app/tests/ -v --tb=short
```

---

## 20. Environment Variables

```bash
# === DATABASE (Required) ===
DATABASE_URL="postgresql://Asiko:npg_xxx@ep-xxx.pooler.region.aws.neon.tech/boutique?sslmode=require"

# === BREVO EMAIL (Required for transactional emails) ===
BREVO_API_KEY="xkeysib-..."
SENDER_EMAIL="orders@asikoboutique.com"

# === OPAY PAYMENTS (Required for checkout) ===
OPAY_MERCHANT_ID="your_merchant_id"
OPAY_SECRET_KEY="your_secret_key"
OPAY_PUBLIC_KEY="your_public_key"
OPAY_CALLBACK_URL="https://asikoboutique.com/webhooks/opay"
OPAY_RETURN_URL="https://asikoboutique.com/checkout/confirmation"

# === AUTH (Required for customer registration/login) ===
AUTH_SALT="your-auth-salt-here"

# === SESSION SECURITY (Optional) ===
SECRET_KEY="your-production-secret-key"

# === AI (Optional — falls back to rule-based) ===
OPENAI_API_KEY="your_openai_key"
ANTHROPIC_API_KEY="your_anthropic_key"

# === ENVIRONMENT ===
ENVIRONMENT="development"
ASIKO_DEBUG="true"
```

---

## 21. Running the Application

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start dev server
python -m uvicorn app.main:app --reload --port 8000

# Or use run scripts
./run.bat          # Windows
./run.ps1          # PowerShell
```

### Production
```bash
# Set ASIKO_DEBUG=false for production caching
ASIKO_DEBUG=false python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Database Setup
```bash
# Run migrations in order (05-23)
psql $DATABASE_URL -f database/migrations/05_single_brand.sql
# ... repeat for each migration
```

---

## 22. Known Limitations

1. **No GPU / No Docker**: Cannot self-host Hunyuan3D-2 for 3D model generation. 3D PNG images used as branding instead.

2. **OPay Mock Mode**: All OPay keys are placeholder. Checkout works in mock mode only.

3. **No Admin Auth**: Admin dashboard has no authentication. Anyone with URL access can manage.

4. **Simple Auth**: Customer auth uses SHA-256 + salt, not bcrypt. Acceptable for current scale.

5. **3D Showroom Removed**: Virtual try-on removed from platform. 3D branding via PNG images only.

6. **Single-Boutique**: Not a multi-vendor marketplace. Single ASIKO brand store.

---

## 23. Future Work

1. **OPay Live Keys**: Replace placeholder keys for real payment processing.

2. **Admin Authentication**: Add login required for admin dashboard.

3. **Product Image Upload**: Allow admin to upload product images (currently using external URLs).

4. **Advanced Analytics**: More detailed sales, customer, and product analytics.

5. **Email Templates**: More email templates (abandoned cart, restock notification).

6. **SEO Optimization**: Meta tags, structured data, sitemap generation.

7. **Performance Monitoring**: APM integration, error tracking.

8. **Backup System**: Automated database backups.

---

*Document generated for ASIKO Boutique — Nigerian Fashion Marketplace*
*Last updated: June 2026*
