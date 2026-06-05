-- ============================================================================
-- ÀSÌKÒ BOUTIQUE — MASTER DATABASE SCHEMA
-- Engine: PostgreSQL 15+ / Neon Serverless
-- Generated: 2026-06-02
-- Source of truth: 6 incremental migrations + 49 SQL queries across 9 route files
-- ============================================================================

-- Idempotency guards: clean cascading drops in dependency order
DROP TABLE IF EXISTS mock_product_reservations CASCADE;
DROP TABLE IF EXISTS mock_allocation_windows CASCADE;
DROP TABLE IF EXISTS mock_products CASCADE;
DROP TABLE IF EXISTS asiko_capsule_assignments CASCADE;
DROP TABLE IF EXISTS asiko_capsule_looks CASCADE;
DROP TABLE IF EXISTS asiko_allocation_windows CASCADE;
DROP TABLE IF EXISTS asiko_measurement_vault CASCADE;
DROP TABLE IF EXISTS telemetry_concierge_clicks CASCADE;
DROP TABLE IF EXISTS product_waitlists CASCADE;
DROP TABLE IF EXISTS product_reservations CASCADE;
DROP TABLE IF EXISTS product_variants CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS nigerian_states CASCADE;
DROP TABLE IF EXISTS stores CASCADE;

-- Required for uuid_generate_v4() in migration 01 tables
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. STORES (Single-brand: only row is ASIKO)
-- ============================================================================

CREATE TABLE stores (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    owner_email TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 2. PRODUCTS — Core catalog entity
--    Code references: storefront.py, cart.py, admin_dashboard.py, database.py,
--    luxury_extensions.py (p.slug), waitlist.py
-- ============================================================================

CREATE TABLE products (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id        UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT,
    slug            TEXT UNIQUE,
    price           NUMERIC(12, 2) NOT NULL CHECK (price > 0),
    stock_quantity  INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    base_image      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_products_store_id     ON products(store_id);
CREATE INDEX idx_products_stock_qty    ON products(stock_quantity);
CREATE INDEX idx_products_slug         ON products(slug) WHERE slug IS NOT NULL;

-- ============================================================================
-- 3. PRODUCT VARIANTS — Size/color matrix per product
--    Code references: cart.py, checkout.py, admin_dashboard.py, admin_inventory.py,
--    storefront.py, waitlist.py
--    Column: stock_qty (NOT stock_quantity)
-- ============================================================================

CREATE TABLE product_variants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id  UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    size        VARCHAR(50) NOT NULL,
    color       VARCHAR(50) NOT NULL,
    stock_qty   INTEGER NOT NULL CHECK (stock_qty >= 0),
    UNIQUE(product_id, size, color)
);

CREATE INDEX idx_variants_product_id ON product_variants(product_id);
CREATE INDEX idx_variants_stock      ON product_variants(stock_qty);

-- ============================================================================
-- 4. ORDERS — Transactional gateway
--    Code references: checkout.py, admin_dashboard.py, database.py, webhooks.py
--    Status values used: 'pending', 'paid', 'processing', 'shipped', 'delivered', 'cancelled'
-- ============================================================================

CREATE TABLE orders (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_email    TEXT NOT NULL,
    total_amount      NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
    shipping_state    VARCHAR(100),
    shipping_cost     NUMERIC(12, 2) DEFAULT 0,
    status            TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'paid', 'processing', 'shipped', 'delivered', 'cancelled')),
    payment_reference TEXT,
    metadata          JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_orders_customer_email ON orders(customer_email);
CREATE INDEX idx_orders_status         ON orders(status);
CREATE INDEX idx_orders_created_at     ON orders(created_at DESC);

-- ============================================================================
-- 5. ORDER ITEMS — Line items per order
--    Code references: checkout.py, database.py
-- ============================================================================

CREATE TABLE order_items (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id    UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    price       NUMERIC(12, 2) NOT NULL CHECK (price > 0),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_order_items_order_id   ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);

-- ============================================================================
-- 6. NIGERIAN STATES — 36 states + FCT shipping matrix
--    Code references: checkout.py, database.py, settlement.py
--    Columns: code (PK), name, shipping_cost, weight_factor
-- ============================================================================

CREATE TABLE nigerian_states (
    code            VARCHAR(2) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    shipping_cost   NUMERIC(12, 2) NOT NULL DEFAULT 2000.00,
    weight_factor   NUMERIC(3, 2) DEFAULT 1.00
);

-- ============================================================================
-- 7. PRODUCT RESERVATIONS — Omnichannel stock holds
--    Code references: admin_inventory.py, settlement.py, luxury_extensions.py,
--    admin_dashboard.py
--    Status values used: 'staged', 'expired', 'paid', 'pending'
--    NOTE: Original CHECK only allowed 'pending','settled','expired'
--          which missed 'staged' and 'paid'. Fixed below.
-- ============================================================================

CREATE TABLE product_reservations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_id          UUID NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    session_identifier  VARCHAR(255),
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    status              VARCHAR(50) DEFAULT 'staged'
                        CHECK (status IN ('staged', 'pending', 'paid', 'settled', 'expired')),
    created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reservations_status  ON product_reservations(status);
CREATE INDEX idx_reservations_variant ON product_reservations(variant_id);

-- ============================================================================
-- 8. PRODUCT WAITLISTS — Out-of-stock demand queue
--    Code references: waitlist.py, admin_dashboard.py
--    Enforces: UNIQUE(email, variant_id), idempotent ON CONFLICT DO NOTHING
-- ============================================================================

CREATE TABLE product_waitlists (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) NOT NULL,
    variant_id  UUID NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    notified    BOOLEAN DEFAULT FALSE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_email_variant UNIQUE (email, variant_id)
);

-- Partial index: fast pipeline for batch Brevo dispatches (WHERE notified = FALSE)
CREATE INDEX idx_waitlist_variant_notified
    ON product_waitlists(variant_id)
    WHERE notified = FALSE;

-- ============================================================================
-- 9. DIGITAL ATELIER — Measurement Vault
--    Code references: luxury_extensions.py
--    Upsert via ON CONFLICT (session_key) DO UPDATE
-- ============================================================================

CREATE TABLE asiko_measurement_vault (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         INTEGER,
    session_key     VARCHAR(40) UNIQUE,
    display_unit    VARCHAR(2) DEFAULT 'cm' CHECK (display_unit IN ('cm', 'in')),
    chest           DECIMAL(5, 2) NOT NULL CHECK (chest BETWEEN 50.0 AND 200.0),
    waist           DECIMAL(5, 2) NOT NULL CHECK (waist BETWEEN 40.0 AND 180.0),
    hips            DECIMAL(5, 2) NOT NULL CHECK (hips BETWEEN 60.0 AND 220.0),
    height          DECIMAL(5, 2) CHECK (height BETWEEN 100.0 AND 250.0),
    updated_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 10. CONCIERGE TELEMETRY — WhatsApp click tracking
--     Code references: luxury_extensions.py
--     NOTE: Original schema had cart_id VARCHAR(255) NOT NULL with no default.
--           Code inserts only (payload_metadata, clicked_at) without cart_id.
--           Made cart_id nullable to fix NOT NULL violation.
-- ============================================================================

CREATE TABLE telemetry_concierge_clicks (
    id                BIGSERIAL PRIMARY KEY,
    cart_id           VARCHAR(255),
    payload_metadata  TEXT,
    clicked_at        TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 11. CAPSULE LOOKS — Curated product bundles
--     Code references: luxury_extensions.py
-- ============================================================================

CREATE TABLE asiko_capsule_looks (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(255) UNIQUE NOT NULL,
    description     TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 12. CAPSULE ASSIGNMENTS — Links products to capsule looks
--     Code references: storefront.py (Query 30, 31), luxury_extensions.py
--     NOTE: product_id references products(id) but was originally missing FK.
--           Added FK constraint below for referential integrity.
-- ============================================================================

CREATE TABLE asiko_capsule_assignments (
    id                      BIGSERIAL PRIMARY KEY,
    capsule_id              BIGINT REFERENCES asiko_capsule_looks(id) ON DELETE CASCADE,
    product_id              UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    priority_order          INTEGER DEFAULT 0,
    is_required_for_look    BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_capsule_assign_capsule_id ON asiko_capsule_assignments(capsule_id);
CREATE INDEX idx_capsule_assign_product_id ON asiko_capsule_assignments(product_id);

-- ============================================================================
-- 13. ALLOCATION WINDOWS — Tiered pre-order access control
--     Code references: luxury_extensions.py (Query 47, 48, 49)
--     JOIN: products ON p.id = w.target_product_id WHERE p.slug = $1
--     NOTE: target_product_id had no FK. Added FK below.
-- ============================================================================

CREATE TABLE asiko_allocation_windows (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_product_id       UUID UNIQUE NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    tier_level_required     INTEGER DEFAULT 1,
    start_time              TIMESTAMPTZ NOT NULL,
    end_time                TIMESTAMPTZ NOT NULL,
    max_allocation_units    INTEGER NOT NULL,
    allocated_units         INTEGER DEFAULT 0
);

-- ============================================================================
-- 14. MOCK PRODUCTS — Test suite only (mock_test_data)
-- ============================================================================

CREATE TABLE mock_products (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR(255) NOT NULL,
    slug    VARCHAR(255) UNIQUE NOT NULL
);

-- ============================================================================
-- 15. MOCK ALLOCATION WINDOWS — Test suite only
-- ============================================================================

CREATE TABLE mock_allocation_windows (
    id                  SERIAL PRIMARY KEY,
    target_product_id   INTEGER REFERENCES mock_products(id) ON DELETE CASCADE,
    tier_level_required INTEGER NOT NULL DEFAULT 1,
    max_units           INTEGER NOT NULL,
    allocated_units     INTEGER NOT NULL DEFAULT 0,
    start_time          TIMESTAMPTZ NOT NULL,
    end_time            TIMESTAMPTZ NOT NULL
);

-- ============================================================================
-- 16. MOCK PRODUCT RESERVATIONS — Test suite only
-- ============================================================================

CREATE TABLE mock_product_reservations (
    id                  SERIAL PRIMARY KEY,
    variant_id          VARCHAR(100) NOT NULL,
    session_identifier  VARCHAR(255) NOT NULL,
    quantity            INTEGER NOT NULL DEFAULT 1,
    status              VARCHAR(50) NOT NULL DEFAULT 'staged',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SEED DATA: Nigerian States (36 States + FCT)
-- ============================================================================

INSERT INTO nigerian_states (code, name, shipping_cost, weight_factor) VALUES
('AB', 'Abia',            3500.00, 1.10),
('AD', 'Adamawa',         4000.00, 1.15),
('AK', 'Akwa Ibom',       3500.00, 1.10),
('AN', 'Anambra',         3000.00, 1.05),
('BA', 'Bauchi',          4500.00, 1.20),
('BY', 'Bayelsa',         4000.00, 1.15),
('BE', 'Benue',           4000.00, 1.15),
('BO', 'Borno',           5000.00, 1.25),
('CR', 'Cross River',     3500.00, 1.10),
('DE', 'Delta',           3000.00, 1.05),
('EB', 'Ebonyi',          3500.00, 1.10),
('ED', 'Edo',             3000.00, 1.05),
('EK', 'Ekiti',           3000.00, 1.05),
('EN', 'Enugu',           3000.00, 1.05),
('FC', 'FCT Abuja',       2000.00, 1.00),
('GO', 'Gombe',           4500.00, 1.20),
('IM', 'Imo',             3000.00, 1.05),
('JI', 'Jigawa',          4500.00, 1.20),
('KD', 'Kaduna',          3500.00, 1.10),
('KN', 'Kano',            4000.00, 1.15),
('KT', 'Katsina',         4500.00, 1.20),
('KE', 'Kebbi',           4500.00, 1.20),
('KO', 'Kogi',            3500.00, 1.10),
('KW', 'Kwara',           3000.00, 1.05),
('LA', 'Lagos',           2000.00, 1.00),
('NA', 'Nasarawa',        3500.00, 1.10),
('NI', 'Niger',           4000.00, 1.15),
('OG', 'Ogun',            2500.00, 1.02),
('ON', 'Ondo',            3000.00, 1.05),
('OS', 'Osun',            3000.00, 1.05),
('OY', 'Oyo',             2500.00, 1.02),
('PL', 'Plateau',         4000.00, 1.15),
('RI', 'Rivers',          3500.00, 1.10),
('SO', 'Sokoto',          5000.00, 1.25),
('TA', 'Taraba',          4500.00, 1.20),
('YO', 'Yobe',            5000.00, 1.25),
('ZA', 'Zamfara',         5000.00, 1.25)
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- SEED DATA: ASIKO Brand Store (single-brand architecture)
-- ============================================================================

INSERT INTO stores (id, name, slug, owner_email)
VALUES ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'ASIKO', 'asiko', 'hello@asikoboutique.com')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SEED DATA: Mock test tables (required by test_catalog.py and test_flow.py)
-- ============================================================================

INSERT INTO mock_products (name, slug)
VALUES ('The Architectural Blazer', 'architectural-blazer')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO mock_allocation_windows (target_product_id, tier_level_required, max_units, allocated_units, start_time, end_time)
SELECT mp.id, 1, 3, 0, NOW() - INTERVAL '1 day', NOW() + INTERVAL '7 days'
FROM mock_products mp
WHERE mp.slug = 'architectural-blazer'
AND NOT EXISTS (
    SELECT 1 FROM mock_allocation_windows maw
    WHERE maw.target_product_id = mp.id
);

-- ============================================================================
-- 17. 3D VIRTUAL SHOWROOM — Model asset paths & variant mesh metadata
--     Code references: virtual_experience.py
--     products.model_3d_url: Path to .glb/.gltf asset (nullable)
--     product_variants.mesh_node_identifier: Sub-mesh name tag for loader
--     product_variants.custom_shader_color: Hex color string for material override
-- ============================================================================

ALTER TABLE products ADD COLUMN IF NOT EXISTS model_3d_url VARCHAR(512) DEFAULT NULL;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS mesh_node_identifier VARCHAR(100) DEFAULT NULL;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS custom_shader_color VARCHAR(7) DEFAULT NULL;

-- Spatial pipeline extensions: morph targets, layer depth, Apple AR USDZ
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS morph_target_index INTEGER DEFAULT 0;
ALTER TABLE products ADD COLUMN IF NOT EXISTS apparel_layer_depth INTEGER DEFAULT 1;
ALTER TABLE products ADD COLUMN IF NOT EXISTS model_usdz_url VARCHAR(512) DEFAULT NULL;

-- Digital Product Passport (DPP) traceability columns
ALTER TABLE products ADD COLUMN IF NOT EXISTS fabric_lineage TEXT DEFAULT NULL;
ALTER TABLE products ADD COLUMN IF NOT EXISTS processing_dye_vector TEXT DEFAULT NULL;
ALTER TABLE products ADD COLUMN IF NOT EXISTS living_wage_index NUMERIC(5, 2) DEFAULT NULL;

-- Avatar skeleton fit column for gender-filtered capsule layers
ALTER TABLE products ADD COLUMN IF NOT EXISTS target_skeleton_fit VARCHAR(20) DEFAULT 'unisex';

-- ============================================================================
-- SEED DATA: 3D Virtual Showroom test asset
-- ============================================================================

-- ============================================================================
-- SEED DATA: 3D Virtual Showroom — Products with GLB model paths
-- Each product maps to a .glb file in static/models/ generated by
-- scripts/generate_glb_models.py
-- ============================================================================

-- Product: Atelier Drape Dress → draped-silhouette-gown.glb
INSERT INTO products (store_id, name, description, price, model_3d_url)
SELECT
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'Atelier Drape Dress',
    'Sleek luxury floor-length silk gown with tailored pleating.',
    450000.00,
    '/static/models/draped-silhouette-gown.glb'
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Atelier Drape Dress'
);

INSERT INTO product_variants (product_id, size, color, stock_qty, mesh_node_identifier, custom_shader_color)
SELECT p.id, 'S', 'Onyx Black', 14, 'Gown_Mesh', '#0D0D0D'
FROM products p
WHERE p.name = 'Atelier Drape Dress'
AND NOT EXISTS (
    SELECT 1 FROM product_variants v
    WHERE v.product_id = p.id AND v.size = 'S' AND v.color = 'Onyx Black'
);

INSERT INTO product_variants (product_id, size, color, stock_qty, mesh_node_identifier, custom_shader_color)
SELECT p.id, 'M', 'Onyx Black', 18, 'Gown_Mesh', '#0D0D0D'
FROM products p
WHERE p.name = 'Atelier Drape Dress'
AND NOT EXISTS (
    SELECT 1 FROM product_variants v
    WHERE v.product_id = p.id AND v.size = 'M' AND v.color = 'Onyx Black'
);

INSERT INTO product_variants (product_id, size, color, stock_qty, mesh_node_identifier, custom_shader_color)
SELECT p.id, 'L', 'Onyx Black', 10, 'Gown_Mesh', '#0D0D0D'
FROM products p
WHERE p.name = 'Atelier Drape Dress'
AND NOT EXISTS (
    SELECT 1 FROM product_variants v
    WHERE v.product_id = p.id AND v.size = 'L' AND v.color = 'Onyx Black'
);

-- Product: Lagos Silk Blazer → architectural-blazer.glb
UPDATE products SET model_3d_url = '/static/models/architectural-blazer.glb'
WHERE name LIKE '%Silk Blazer%' AND model_3d_url IS NULL;

-- Product: Aba Handloomed Trousers → tailored-column-trouser.glb
UPDATE products SET model_3d_url = '/static/models/tailored-column-trouser.glb'
WHERE name LIKE '%Trousers%' AND model_3d_url IS NULL;

-- Product: Adire Tie-Dye Dress → draped-silhouette-gown.glb
UPDATE products SET model_3d_url = '/static/models/draped-silhouette-gown.glb'
WHERE name LIKE '%Adire%' AND model_3d_url IS NULL;

-- ============================================================================
-- SCHEMA NOTES
-- ============================================================================
--
-- 1. PRODUCT DUAL-TRACK INVENTORY:
--    - products.stock_quantity: Legacy aggregate counter (used by storefront.py, database.py)
--    - product_variants.stock_qty: Per-SKU granular stock (used by cart, checkout, admin)
--    Both are maintained. The variants table is the source of truth for new operations.
--
-- 2. RESERVATION STATUS LIFECYCLE:
--    'staged' → 'paid' (successful settlement) or 'expired' (worker sweep)
--    'pending' → used by luxury_extensions.py capsule bundle allocation
--
-- 3. CAPSULE ASSIGNMENTS FK:
--    asiko_capsule_assignments.product_id now references products(id) ON DELETE CASCADE.
--    Original migration 04 had no FK. Code relies on this join (storefront.py Query 31).
--
-- 4. ALLOCATION WINDOWS FK:
--    asiko_allocation_windows.target_product_id now references products(id) ON DELETE CASCADE.
--    Original migration 04 had no FK. Code joins on p.id = w.target_product_id (luxury_extensions.py Query 47-48).
--
-- 5. TELEMETRY CART_ID NULLABLE:
--    telemetry_concierge_clicks.cart_id changed from NOT NULL to NULLABLE.
--    Code inserts only (payload_metadata, clicked_at) without cart_id (luxury_extensions.py Query 45).
--
-- 6. INDEX STRATEGY:
--    - Partial index on product_waitlists WHERE notified = FALSE for fast batch dispatch
--    - Composite unique constraints prevent duplicate waitlist entries and variant duplication
--    - B-tree indexes on all FK columns used in JOINs
--    - Status indexes for dashboard metrics aggregation queries
-- ============================================================================
