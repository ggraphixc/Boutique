-- supabase/migrations/09_admin_redesign_tables.sql
--
-- Adds the tables required by the redesigned admin control center:
--   - categories           (collection organization)
--   - product_reviews      (customer feedback)
--   - ads                  (campaigns / banners)
--   - store_settings       (singleton config)
--   - about_me             (singleton owner profile)
--
-- All tables use UUID PKs and soft delete via deleted_at where appropriate.
-- Idempotent: safe to re-run.

-- ============================================================================
-- 1. CATEGORIES
-- ============================================================================
CREATE TABLE IF NOT EXISTS categories (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(120) NOT NULL,
    slug          VARCHAR(140) NOT NULL UNIQUE,
    description   TEXT,
    color         VARCHAR(7) DEFAULT '#D4AF37',    -- hex for chip
    display_order INT NOT NULL DEFAULT 0,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_categories_active_order
    ON categories(is_active, display_order);

-- Add FK from products.category_id to categories.
-- Add the column if it does not exist, then attach the FK.
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS category_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'products_category_id_fkey'
    ) THEN
        BEGIN
            ALTER TABLE products
            ADD CONSTRAINT products_category_id_fkey
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL;
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'skipping category FK: %', SQLERRM;
        END;
    END IF;
END $$;

-- ============================================================================
-- 2. PRODUCT REVIEWS
-- ============================================================================
CREATE TABLE IF NOT EXISTS product_reviews (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id    UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    customer_name VARCHAR(160) NOT NULL,
    customer_email VARCHAR(255),
    rating        SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title         VARCHAR(255),
    body          TEXT,
    verified      BOOLEAN NOT NULL DEFAULT false,
    replied       BOOLEAN NOT NULL DEFAULT false,
    reply_body    TEXT,
    replied_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_reviews_product
    ON product_reviews(product_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_reviews_rating
    ON product_reviews(rating)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_reviews_needs_reply
    ON product_reviews(created_at DESC)
    WHERE deleted_at IS NULL AND replied = false;

-- ============================================================================
-- 3. ADS / CAMPAIGNS
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ad_status_type') THEN
        CREATE TYPE ad_status_type AS ENUM ('draft', 'scheduled', 'active', 'paused', 'ended');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS ads (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name           VARCHAR(160) NOT NULL,
    placement      VARCHAR(80) NOT NULL DEFAULT 'homepage_hero',
    image          TEXT,
    color_from     VARCHAR(7) DEFAULT '#D4AF37',
    color_to       VARCHAR(7) DEFAULT '#0D2A22',
    link_url       TEXT,
    copy_headline  VARCHAR(255),
    copy_body      TEXT,
    status         ad_status_type NOT NULL DEFAULT 'draft',
    starts_at      TIMESTAMPTZ,
    ends_at        TIMESTAMPTZ,
    impressions    BIGINT NOT NULL DEFAULT 0,
    clicks         BIGINT NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ads_status ON ads(status, starts_at DESC);

-- ============================================================================
-- 4. STORE SETTINGS (singleton)
-- ============================================================================
CREATE TABLE IF NOT EXISTS store_settings (
    id                       INT PRIMARY KEY DEFAULT 1,
    currency                 VARCHAR(8) NOT NULL DEFAULT 'USD',
    timezone                 VARCHAR(64) NOT NULL DEFAULT 'UTC',
    locale                   VARCHAR(8) NOT NULL DEFAULT 'en',
    shipping_domestic        NUMERIC(10,2) NOT NULL DEFAULT 0,
    shipping_international   NUMERIC(10,2) NOT NULL DEFAULT 0,
    free_shipping_threshold  NUMERIC(10,2) NOT NULL DEFAULT 0,
    mesh_provider            VARCHAR(40) NOT NULL DEFAULT 'instantmesh',
    auto_mesh                BOOLEAN NOT NULL DEFAULT true,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT store_settings_singleton CHECK (id = 1)
);

-- Seed singleton row
INSERT INTO store_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 5. ABOUT ME / OWNER PROFILE (singleton)
-- ============================================================================
CREATE TABLE IF NOT EXISTS about_me (
    id            INT PRIMARY KEY DEFAULT 1,
    name          VARCHAR(160) NOT NULL DEFAULT '',
    role          VARCHAR(160) NOT NULL DEFAULT '',
    email         VARCHAR(255) NOT NULL DEFAULT '',
    location      VARCHAR(160) NOT NULL DEFAULT '',
    instagram     VARCHAR(80) NOT NULL DEFAULT '',
    founded_year  INT,
    tagline       VARCHAR(255) NOT NULL DEFAULT '',
    story         TEXT NOT NULL DEFAULT '',
    avatar_url    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT about_me_singleton CHECK (id = 1)
);

INSERT INTO about_me (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- TRIGGERS: keep updated_at fresh
-- ============================================================================
CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'categories_touch') THEN
        CREATE TRIGGER categories_touch BEFORE UPDATE ON categories
        FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'reviews_touch') THEN
        CREATE TRIGGER reviews_touch BEFORE UPDATE ON product_reviews
        FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'ads_touch') THEN
        CREATE TRIGGER ads_touch BEFORE UPDATE ON ads
        FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'store_settings_touch') THEN
        CREATE TRIGGER store_settings_touch BEFORE UPDATE ON store_settings
        FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'about_me_touch') THEN
        CREATE TRIGGER about_me_touch BEFORE UPDATE ON about_me
        FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
    END IF;
END $$;

-- ============================================================================
-- SEED: starter categories
-- ============================================================================
INSERT INTO categories (name, slug, color, display_order, is_active) VALUES
    ('Outerwear',  'outerwear',  '#0D2A22', 1, true),
    ('Tailoring',  'tailoring',  '#1E3A5F', 2, true),
    ('Knitwear',   'knitwear',   '#6B4226', 3, true),
    ('Dresses',    'dresses',    '#A03366', 4, true),
    ('Accessories','accessories','#D4AF37', 5, true),
    ('Footwear',   'footwear',   '#2D2D2D', 6, true)
ON CONFLICT (slug) DO NOTHING;
