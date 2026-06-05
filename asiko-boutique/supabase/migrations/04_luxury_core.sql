-- ASIKO Boutique Migration 04: Luxury Core Extensions
-- Digital Atelier, Concierge Telemetry, Capsule Matrix, Tiered Allocation

-- 1. Digital Atelier Measurement Vault
CREATE TABLE IF NOT EXISTS asiko_measurement_vault (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INT NULL,
    session_key VARCHAR(40) UNIQUE NULL,
    display_unit VARCHAR(2) DEFAULT 'cm' CHECK (display_unit IN ('cm', 'in')),
    chest DECIMAL(5,2) NOT NULL CHECK (chest BETWEEN 50.0 AND 200.0),
    waist DECIMAL(5,2) NOT NULL CHECK (waist BETWEEN 40.0 AND 180.0),
    hips DECIMAL(5,2) NOT NULL CHECK (hips BETWEEN 60.0 AND 220.0),
    height DECIMAL(5,2) NULL CHECK (height BETWEEN 100.0 AND 250.0),
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Concierge Telemetry Logging
CREATE TABLE IF NOT EXISTS telemetry_concierge_clicks (
    id BIGSERIAL PRIMARY KEY,
    cart_id VARCHAR(255) NOT NULL,
    clicked_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Capsule Looks & Bundle Matrix
CREATE TABLE IF NOT EXISTS asiko_capsule_looks (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS asiko_capsule_assignments (
    id BIGSERIAL PRIMARY KEY,
    capsule_id BIGINT REFERENCES asiko_capsule_looks(id) ON DELETE CASCADE,
    product_id UUID NOT NULL,
    priority_order INT DEFAULT 0,
    is_required_for_look BOOLEAN DEFAULT FALSE
);

-- 4. Tiered Allocation & Pre-Order Matrix
CREATE TABLE IF NOT EXISTS asiko_allocation_windows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_product_id UUID UNIQUE NOT NULL,
    tier_level_required INT DEFAULT 1,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    max_allocation_units INT NOT NULL,
    allocated_units INT DEFAULT 0
);
