-- Migration 14: Phase 2 body types, photos, fabric, outfits, saved looks
-- Adds body type presets, photo uploads, fabric properties, outfit combinations, saved looks

-- Body type enum
DO $$ BEGIN
    CREATE TYPE body_type AS ENUM ('slim', 'athletic', 'curvy', 'plus', 'petite', 'tall', 'custom');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Fit type enum
DO $$ BEGIN
    CREATE TYPE fit_type AS ENUM ('tight', 'regular', 'loose', 'oversized');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Fabric type enum
DO $$ BEGIN
    CREATE TYPE fabric_type AS ENUM ('cotton', 'silk', 'lace', 'denim', 'wool', 'leather', 'auto');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Extend avatar_measurements with body type, weight, photos
ALTER TABLE avatar_measurements
    ADD COLUMN IF NOT EXISTS body_type body_type DEFAULT 'custom',
    ADD COLUMN IF NOT EXISTS weight_kg NUMERIC(5,1),
    ADD COLUMN IF NOT EXISTS front_photo_url TEXT,
    ADD COLUMN IF NOT EXISTS side_photo_url TEXT,
    ADD COLUMN IF NOT EXISTS fit_preference fit_type DEFAULT 'regular',
    ADD COLUMN IF NOT EXISTS fabric_preference fabric_type DEFAULT 'auto';

-- Saved looks table
CREATE TABLE IF NOT EXISTS saved_looks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(128) NOT NULL,
    name VARCHAR(255) NOT NULL DEFAULT 'My Look',
    garment_ids TEXT[] NOT NULL DEFAULT '{}',
    measurements JSONB,
    body_type body_type DEFAULT 'custom',
    fit_preference fit_type DEFAULT 'regular',
    fabric_preference fabric_type DEFAULT 'auto',
    thumbnail_url TEXT,
    share_token VARCHAR(64) UNIQUE,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_saved_looks_session ON saved_looks(session_id);
CREATE INDEX IF NOT EXISTS idx_saved_looks_share ON saved_looks(share_token) WHERE share_token IS NOT NULL;

-- Outfit items table (for multi-garment combinations)
CREATE TABLE IF NOT EXISTS outfit_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    look_id UUID NOT NULL REFERENCES saved_looks(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    slot VARCHAR(32) NOT NULL DEFAULT 'main',
    layer_order INT DEFAULT 0,
    fabric fabric_type DEFAULT 'auto',
    fit fit_type DEFAULT 'regular',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outfit_items_look ON outfit_items(look_id);
