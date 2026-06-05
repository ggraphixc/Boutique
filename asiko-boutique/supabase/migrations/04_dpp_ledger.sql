-- ASIKO Boutique Migration 04: Digital Product Passport (DPP) Ledger
-- Anchors verifiable provenance parameters for luxury garment authentication

-- Track explicit provenance data metrics per product
ALTER TABLE products ADD COLUMN IF NOT EXISTS fabric_lineage TEXT DEFAULT 'Premium Handloomed Cotton';
ALTER TABLE products ADD COLUMN IF NOT EXISTS processing_dye_vector TEXT DEFAULT 'Organic Plant-Based Vegetable Dye';
ALTER TABLE products ADD COLUMN IF NOT EXISTS living_wage_index NUMERIC(5,2) DEFAULT 100.00;

-- Track item-specific serial entries for unique garment instances
CREATE TABLE IF NOT EXISTS product_serialized_passports (
    serial_number VARCHAR(64) PRIMARY KEY,
    product_id INT REFERENCES products(id) ON DELETE CASCADE,
    artisan_identifier VARCHAR(50) NOT NULL,
    manufactured_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_passport_product ON product_serialized_passports(product_id);
CREATE INDEX IF NOT EXISTS idx_passport_artisan ON product_serialized_passports(artisan_identifier);
CREATE INDEX IF NOT EXISTS idx_passport_manufactured ON product_serialized_passports(manufactured_at DESC);