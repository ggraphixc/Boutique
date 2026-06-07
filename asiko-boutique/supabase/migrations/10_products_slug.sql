-- ASIKO Boutique - Migration 10: products.slug
-- Add a slug column to products for SEO-friendly URLs.
-- Idempotent: uses IF NOT EXISTS.

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS slug VARCHAR(255);

-- Unique slug per (store_id, slug) — only enforce uniqueness when slug is not null.
-- Partial unique index lets multiple products exist with a NULL slug (legacy rows)
-- while preventing duplicates among products that have a slug.
CREATE UNIQUE INDEX IF NOT EXISTS uq_products_store_slug
    ON products (store_id, slug)
    WHERE slug IS NOT NULL;

-- Backfill helper: derive slug from name for any existing rows that lack one.
-- Slugify rule: lowercase, replace non-alphanumeric with '-', collapse, trim.
UPDATE products
SET slug = LOWER(REGEXP_REPLACE(REGEXP_REPLACE(name, '[^a-zA-Z0-9]+', '-', 'g'), '-+', '-', 'g'))
WHERE slug IS NULL AND name IS NOT NULL;

-- Trigger to auto-populate slug from name on INSERT when not provided.
CREATE OR REPLACE FUNCTION set_products_slug()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.slug IS NULL OR TRIM(NEW.slug) = '' THEN
        NEW.slug := LOWER(REGEXP_REPLACE(REGEXP_REPLACE(NEW.name, '[^a-zA-Z0-9]+', '-', 'g'), '-+', '-', 'g'));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_products_slug ON products;
CREATE TRIGGER trg_products_slug
    BEFORE INSERT OR UPDATE OF name ON products
    FOR EACH ROW
    EXECUTE FUNCTION set_products_slug();
