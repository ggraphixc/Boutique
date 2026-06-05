-- Migration 06: Schema Alignment for Luxury Extensions
-- Adds missing columns required by luxury_extensions.py queries
-- Does NOT alter existing column types (UUID stays UUID)

BEGIN;

-- 1. Add payload_metadata to telemetry_concierge_clicks
--    (luxury_extensions.py concierge_redirect logs unsigned_payload here)
ALTER TABLE telemetry_concierge_clicks
    ADD COLUMN IF NOT EXISTS payload_metadata TEXT;

-- 2. Add session_identifier to product_reservations
--    (luxury_extensions.py add_capsule_bundle tracks session origin)
ALTER TABLE product_reservations
    ADD COLUMN IF NOT EXISTS session_identifier VARCHAR(255);

-- 3. Create a lightweight SERIAL products mock for allocation_windows FK tests
--    (The test suite needs a simple INT FK path; keep existing UUID products intact)
CREATE TABLE IF NOT EXISTS mock_products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL
);

-- Seed a test product for allocation tests
INSERT INTO mock_products (name, slug)
VALUES ('The Architectural Blazer', 'architectural-blazer')
ON CONFLICT (slug) DO NOTHING;

-- 4. Create a SERIAL-based allocation windows table for test suite
CREATE TABLE IF NOT EXISTS mock_allocation_windows (
    id SERIAL PRIMARY KEY,
    target_product_id INT REFERENCES mock_products(id) ON DELETE CASCADE,
    tier_level_required INT NOT NULL DEFAULT 1,
    max_units INT NOT NULL,
    allocated_units INT NOT NULL DEFAULT 0,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Seed an active allocation window for the test product
INSERT INTO mock_allocation_windows (target_product_id, tier_level_required, max_units, allocated_units, start_time, end_time)
SELECT mp.id, 1, 3, 0, NOW() - INTERVAL '1 day', NOW() + INTERVAL '7 days'
FROM mock_products mp
WHERE mp.slug = 'architectural-blazer'
AND NOT EXISTS (
    SELECT 1 FROM mock_allocation_windows maw
    WHERE maw.target_product_id = mp.id
);

-- 5. Create a VARCHAR-based product_reservations table for test suite
CREATE TABLE IF NOT EXISTS mock_product_reservations (
    id SERIAL PRIMARY KEY,
    variant_id VARCHAR(100) NOT NULL,
    session_identifier VARCHAR(255) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    status VARCHAR(50) NOT NULL DEFAULT 'staged',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMIT;
