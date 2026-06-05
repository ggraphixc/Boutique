# ASIKO Boutique — Design System & Technical Specification

Absolute visual, structural, and behavioral source of truth for the ÀSÌKÒ Boutique single-brand luxury platform. All layouts, typography weights, color styling definitions, and interactive 3D WebGL scenes must strictly comply with these parameters.

---

## 1. Stack Overview

| Layer | Technology | Role |
|-------|-----------|------|
| Backend Runtime | Python 3.14 / Starlette 1.0 | Async HTTP, Jinja2 template engine, session management |
| Data Ledger | Django 6.0 | ORM models, cryptographic signing (Signer salt: `asiko.concierge.vector`) |
| Interactivity | HTMX + Alpine.js | Server-driven async fragment updates + client-side state tracking |
| 3D Graphics | Three.js via CDN | WebGL rendering, OrbitControls, GLTFLoader |
| Styling | Tailwind CSS via CDN | Utility-first CSS, responsive design |
| Database | asyncpg / Neon PostgreSQL | Connection pool (min=2, max=10, command_timeout=30.0) |
| Email | Brevo API | Transactional notifications with graceful fallback |

---

## 2. Visual Design Tokens & Color Ambiance

### 2.1 Color Palette Matrix

| Token Name | Hex / Gradient | Tailwind Utility | Architectural Intent |
|------------|---------------|------------------|---------------------|
| **Background Canvas** | `#FBF9F6` | `bg-[#FBF9F6]` | Primary editorial space, minimalist padding |
| **Primary Luxury Base** | `#0D2A22` | `bg-[#0D2A22]` / `text-[#0D2A22]` | Deep forest velvet; structural nav, dark sections |
| **Champagne Gold Accent** | `#D4AF37` | `text-[#D4AF37]` / `border-[#D4AF37]` | Active borders, focus rings, glowing elements |
| **Rich Charcoal Text** | `#1A1A1A` | `text-[#1A1A1A]` | High-contrast body copy, editorial typography |
| **Success State** | `#10B981` | `text-[#10B981]` | Live inventory, verified transactional alerts |
| **Alert / Failure** | `#EF4444` | `text-[#EF4444]` | Oversell safeguards, validation failures |
| **Iridescent Glow A** | `from-fuchsia-300/30 to-cyan-200/20` | `blur-[120px]` | Ambient backlighting orb mesh |
| **Iridescent Glow B** | `from-amber-200/20 to-emerald-200/30` | `blur-[100px]` | Core workspace ambient mesh |
| **Glassmorphism Panel** | `backdrop-blur-2xl bg-white/40` | — | Floating HUD decks, overlay panels |

### 2.2 Typography Scales

| Role | Font Family | Weight | Tracking | Usage |
|------|------------|--------|----------|-------|
| Editorial Display (h1-h3) | Playfair Display (Serif) | `font-light` / `font-medium` | `tracking-[0.3em]` | Headlines, collection titles, brand statements |
| Utility & Interface UI | Inter (Sans-Serif) | `font-normal` / `font-medium` | `tracking-normal` | Descriptions, data lists, forms, inputs |
| Technical Metrics | Monospace | `font-mono` | `tracking-wider` | Pricing (₦), stock counts, timers, admin logs |

---

## 3. Component Archetypes

### 3.1 The Luxury Product Card
- **Structure:** Minimal layout — item title, collection label, transparent pricing (no "DM for price")
- **Micro-interactions:** `hover:scale-[1.02]` with fade-up "View Passport" overlay
- **Aspect ratio:** 3:4 (`aspect-[3/4]`) for product images
- **Template:** `storefront/product_grid.html`, `storefront/product_detail.html`

### 3.2 The Digital Product Passport (DPP)
- **Intent:** Overlapping micro-card mapped to catalog profiles
- **Content:** Fabric lineage (Aba handloomed cotton), organic vegetable dye tracking, verified living wage indicators
- **Trigger:** Alpine.js accordion on PDP (`x-collapse`)
- **Template:** `storefront/product_detail.html` (Digital Atelier section)

### 3.3 The 3D Virtual Showroom Panel
- **Layout:** Left WebGL viewport + right glassmorphic control deck
- **Control Deck:** Async HTMX list via `GET /api/virtual/showroom-items`
- **Behavior:** Card click dispatches `load-showroom-model` event → camera transition + model swap
- **Template:** `virtual_experience.html`
- **Routes:** `app/routes/virtual_experience.py`

### 3.4 The 3D Virtual Dressing Room Fitting Deck
- **Canvas:** Centered 3D human mesh + iridescent gradient ambient rings
- **Controls:** Floating dock — Atelier Drape Dress, Cyber Blazer, Tapered Trouser, Structural Shell Top
- **State:** `$dispatch('swap-clothing', { asset: '...' })` → sub-mesh swap with progress skeleton
- **Template:** `virtual_experience.html` (extended)

### 3.5 The Transfer Escrow Block
- **Boundary:** `border-[#D4AF37]/40` container
- **Timer:** Alpine.js 30-minute countdown loop for checkout settlement
- **Template:** `checkout/index.html`

### 3.6 The Cart Drawer
- **Layout:** Slide-in from right, glassmorphic backdrop
- **Content:** Variant-based lines (size/color), HTMX fragment updates
- **OOB targets:** `#cart-counter`, `#cart-total`
- **Template:** `cart/cart_content.html`

---

## 4. Three.js Technical Specifications

### 4.1 Rendering Configuration

```javascript
const renderer = new THREE.WebGLRenderer({
    alpha: true,                    // Transparent canvas — CSS gradients show through
    antialias: true,
    powerPreference: 'high-performance'
});
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.2;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
```

### 4.2 PBR Material Profiles (Garment Simulation)

| Property | Value | Purpose |
|----------|-------|---------|
| `clearcoat` | `0.2` | Subtle sheen on procedural garment meshes |
| `roughness` | `0.3` | Ambient neon specular hits |
| `metalness` | `0.1` | Block structural hue distortion |

### 4.3 Lighting Rig

```javascript
// Key light — warm editorial
const keyLight = new THREE.DirectionalLight(0xFFF8E7, 1.2);
keyLight.position.set(5, 8, 5);

// Fill light — cool ambient
const fillLight = new THREE.AmbientLight(0xE8F0FE, 0.4);

// Rim light — gold accent
const rimLight = new THREE.PointLight(0xD4AF37, 0.6, 20);
rimLight.position.set(-3, 4, -2);
```

### 4.4 Asset Export Guardrails

| Constraint | Limit | Notes |
|------------|-------|-------|
| Triangle budget | 50,000 max | Per mesh file |
| File size | 2 MB max | `.glb` compressed |
| Authoring pipeline | CLO 3D / Marvelous Designer → Blender | Flat-shaded normals, PBR clearcoat |

### 4.5 Resource Disposal Routine

```javascript
function safelyPurgeThreeAsset(node) {
    node.traverse((child) => {
        if (child.isMesh) {
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach(mat => mat.dispose());
                } else {
                    child.material.dispose();
                }
            }
        }
    });
}
```

Execute on every mesh swap to prevent GPU memory leaks on mobile devices.

---

## 5. Behavior & Integration Patterns

### 5.1 HTMX Data Flows

**Showroom Item Retrieval:**
- Endpoint: `GET /api/virtual/showroom-items`
- Returns: Server-rendered HTML fragment cards (not JSON)
- Cards include inline Alpine `@click` handlers for `$dispatch`

**Cart Operations:**
- `POST /cart/add` → Returns `cart/cart_badge.html` (OOB swap to `#cart-counter`)
- `POST /cart/update` → Returns `cart/cart_content.html` (drawer refresh)
- `GET /cart/drawer` → Full drawer render

**Checkout Flow:**
- `GET /checkout` → Shipping form with 37-state dropdown
- `GET /checkout/shipping-summary?state=XX` → HTMX cost fragment
- `POST /checkout/submit` → Atomic transaction + Brevo email + redirect

### 5.2 Out-of-Band (OOB) Communication

| Trigger | OOB Target | Effect |
|---------|-----------|--------|
| Cart add/update | `#cart-counter` | Badge count refresh |
| Cart update | `#cart-total` | Total price refresh |
| Oversell attempt | `#cart-error` | Error div injection |
| Admin stock update | `#status-variant-{id}` | Inline saved indicator |
| Capsule bundle buy | `#cart-counter`, `#cart-total` | Multi-target OOB |

### 5.3 Event Dispatch Map

| Event Name | Source | Payload | Consumer |
|------------|--------|---------|----------|
| `load-showroom-model` | Showroom card `@click` | `{ modelUrl, color, mesh }` | Three.js viewport |
| `swap-clothing` | Dressing room dock | `{ asset }` | Dressing room renderer |
| `inspect-showroom-product` | Virtual atelier button | `{ modelUrl, color }` | Inspector panel |

---

## 6. Route Registry

| Route | Method | Handler | Template |
|-------|--------|---------|----------|
| `/` | GET | `storefront.homepage` | `storefront/index.html` |
| `/htmx/products` | GET | `storefront.product_grid_fragment` | `storefront/product_grid.html` |
| `/product/{id}` | GET | `storefront.product_detail` | `storefront/product_detail.html` |
| `/cart/add` | POST | `cart.cart_add` | `cart/cart_badge.html` |
| `/cart/update` | POST | `cart.cart_update` | `cart/cart_content.html` |
| `/cart/drawer` | GET | `cart.cart_drawer` | `cart/cart_content.html` |
| `/checkout` | GET | `checkout.checkout_page` | `checkout/index.html` |
| `/checkout/shipping-summary` | GET | `checkout.shipping_summary` | `checkout/shipping_summary.html` |
| `/checkout/submit` | POST | `checkout.checkout_submit` | Redirect |
| `/checkout/confirmation` | GET | `checkout.checkout_confirmation` | `checkout/confirmation.html` |
| `/virtual-experience` | GET | `virtual.virtual_experience` | `virtual_experience.html` |
| `/api/virtual/showroom-items` | GET | `virtual.showroom_items_fragment` | HTML fragment |
| `/api/virtual/capsule-layers` | GET | `virtual.capsule_layers_fragment` | HTML fragment |
| `/api/virtual/profile/set` | POST | `dpp_verification.set_avatar_profile` | JSON response |
| `/api/virtual/avatar-profile` | POST | `virtual_experience.update_session_avatar_profile` | JSON response |
| `/admin/products` | GET | `admin.get_admin_products_fragment` | HTML fragment |
| `/admin/products/{id}/detail` | GET | `admin.get_product_detail_fragment` | HTML fragment |
| `/admin/products/{id}` | DELETE | `admin.handle_delete_product` | Empty response |
| `/admin/settings` | GET | `admin.get_general_settings_fragment` | HTML fragment |
| `/admin/dashboard` | GET | `admin_dashboard.admin_dashboard_home` | `admin/dashboard.html` |
| `/admin/dashboard/update-stock` | POST | `admin_dashboard.inline_update_stock` | HTML fragment |
| `/admin/dashboard/notify-waitlist` | POST | `admin_dashboard.inline_trigger_restock_alert` | HTML fragment |
| `/admin/reservations` | GET | `admin_inventory.list_reservations` | HTML fragment |
| `/admin/reserve` | POST | `admin_inventory.reserve_stock` | HTML fragment |
| `/admin/settle` | POST | `admin_inventory.settle_reservations` | HTML fragment |
| `/waitlist/join` | POST | `waitlist.join_waitlist` | HTML fragment |
| `/test-pdp` | GET | `main.debug_root` | `storefront/product_detail.html` |

---

## 7. Database Schema Reference

### Core Tables

| Table | Primary Key | Purpose |
|-------|------------|---------|
| `stores` | UUID | Single-brand store (ASIKO only) |
| `products` | UUID | Catalog entities with `model_3d_url` |
| `product_variants` | UUID | Size/color matrix with `mesh_node_identifier`, `custom_shader_color` |
| `orders` | UUID | Transactional records with JSONB metadata |
| `order_items` | UUID | Line items per order |
| `nigerian_states` | VARCHAR(2) | 37-row shipping matrix |
| `product_reservations` | UUID | Stock holds (`staged` → `paid` / `expired`) |
| `product_waitlists` | UUID | Demand queue with partial index `WHERE notified = FALSE` |

### Digital Product Passport Tables

| Table | Primary Key | Purpose |
|-------|------------|---------|
| `product_serialized_passports` | VARCHAR(64) | Unique garment serial tracking with artisan attribution |

### DPP Product Columns

| Table | Column | Type | Purpose |
|-------|--------|------|---------|
| `products` | `fabric_lineage` | TEXT | Fabric provenance tracking (default: Premium Handloomed Cotton) |
| `products` | `processing_dye_vector` | TEXT | Dye process tracking (default: Organic Plant-Based Vegetable Dye) |
| `products` | `living_wage_index` | NUMERIC(5,2) | Living wage certification index (default: 100.00) |

### Luxury Extension Tables

| Table | Primary Key | Purpose |
|-------|------------|---------|
| `asiko_measurement_vault` | UUID | Digital Atelier body measurements |
| `telemetry_concierge_clicks` | BIGSERIAL | WhatsApp click tracking |
| `asiko_capsule_looks` | BIGSERIAL | Curated product bundles |
| `asiko_capsule_assignments` | BIGSERIAL | Product-to-capsule links |
| `asiko_allocation_windows` | UUID | Tiered pre-order access |

### Avatar Fit Axis Column

| Table | Column | Type | Purpose |
|-------|--------|------|---------|
| `products` | `target_skeleton_fit` | VARCHAR(24) | Gender compatibility for 3D avatar (male/female/unisex) |

### Admin Audit Ledger

| Table | Primary Key | Purpose |
|-------|------------|---------|
| `administrative_audit_logs` | SERIAL | Immutable trail of administrative actions and metadata updates |

### 3D Virtual Showroom Columns

| Table | Column | Type | Purpose |
|-------|--------|------|---------|
| `products` | `model_3d_url` | VARCHAR(512) | Path to `.glb`/`.gltf` asset |
| `product_variants` | `mesh_node_identifier` | VARCHAR(100) | Sub-mesh name tag |
| `product_variants` | `custom_shader_color` | VARCHAR(7) | Hex color for material override |

---

## 8. File Structure

```
asiko-boutique/
├── app/
│   ├── main.py                    # App factory, lifespan, routing
│   ├── core.py                    # Templates, naira filter, session helpers
│   ├── database.py                # asyncpg pool lifecycle
│   ├── catalog/
│   │   └── routes.py              # Session-based PDP endpoints
│   ├── routes/
│   │   ├── storefront.py          # Homepage, PDP, HTMX grid
│   │   ├── cart.py                # Variant-based cart operations
│   │   ├── checkout.py            # Atomic checkout + Brevo
│   │   ├── admin_dashboard.py     # Executive dashboard
│   │   ├── admin_inventory.py     # Stock Sentinel
│   │   ├── waitlist.py            # Idempotent enrollment
│   │   ├── virtual_experience.py  # Avatar profile session endpoint
│   │   ├── admin.py               # Admin CRUD: products table, delete, detail view
│   │   ├── virtual.py             # 3D showroom & capsule layers endpoints
│   │   ├── luxury_extensions.py   # DB-backed luxury features
│   │   └── webhooks.py            # Order status webhooks
│   ├── services/
│   │   ├── brevo.py               # Brevo API wrapper
│   │   ├── settlement.py          # Paystack, shipping, workers
│   │   └── dpp_crypto.py          # Digital Product Passport signing service
│   │   ├── templates/
│   │   │   ├── base.html
│   │   │   ├── admin/
│   │   │   │   ├── base.html
│   │   │   │   └── products_table.html
│   │   │   ├── storefront/
│   │   │   │   ├── index.html
│   │   │   │   ├── product_grid.html
│   │   │   │   ├── product_detail.html
│   │   │   │   └── dpp_verification.html
│   │   │   ├── cart/
│   │   │   │   ├── cart_badge.html
│   │   │   │   └── cart_content.html
│   │   │   ├── checkout/
│   │   │   │   ├── index.html
│   │   │   │   ├── shipping_summary.html
│   │   │   │   └── confirmation.html
│   │   │   ├── virtual_experience.html
│   │   │   └── components/
│   │   │       └── shoppable_lookbook.html
│   └── tests/
│       ├── test_catalog.py        # 12 tests
│       ├── test_flow.py           # 15 tests
│       ├── test_dpp.py            # DPP cryptographic verification suite (13 tests)
│       ├── test_avatar_flows.py   # Avatar fit axis integration tests (12 tests)
│       └── test_admin_crud.py     # Admin panel security and lifecycle tests (9 tests)
├── database/
├── database/
│   └── migrations/
│       ├── 05_avatar_fit_axis.sql  # target_skeleton_fit column + constraint
│       └── 06_admin_audit.sql      # Administrative audit ledger
├── supabase/
│   ├── schema.sql                 # 16 tables, 15 indexes, seed data
│   └── migrations/
│       ├── 01_init_schema.sql
│       ├── 02_reservations.sql
│       ├── 03_waitlist.sql
│       ├── 04_luxury_core.sql
│       ├── 04_dpp_ledger.sql      # Digital Product Passport provenance columns
│       ├── 05_single_brand.sql
│       ├── 06_schema_alignment.sql
│       └── 07_gltf_columns.sql
├── static/
│   ├── css/
│   ├── images/
│   ├── models/                    # 3D .glb files (7 garment placeholders)
│   │   └── PIPELINE.md            # Production import documentation
├── knowledge.md
└── design.md                      # This file
```
