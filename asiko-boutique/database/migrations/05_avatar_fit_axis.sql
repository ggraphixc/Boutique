-- ASIKO Boutique Migration 05: Apparel Skeleton Fit Axis
-- Adds target_skeleton_fit column to products for gender-based avatar compatibility

-- Append target layout configuration parameters to the primary catalogs table
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS target_skeleton_fit VARCHAR(24) DEFAULT 'female';

-- Add a validation constraint loop to block garbage inputs from entering production matrices
ALTER TABLE products 
DROP CONSTRAINT IF EXISTS chk_target_skeleton_fit;

ALTER TABLE products 
ADD CONSTRAINT chk_target_skeleton_fit 
CHECK (target_skeleton_fit IN ('male', 'female', 'unisex'));

-- Generate high-performance scan coverage indexes across foreign assignment arrays
CREATE INDEX IF NOT EXISTS idx_products_skeleton_fit ON products(target_skeleton_fit);