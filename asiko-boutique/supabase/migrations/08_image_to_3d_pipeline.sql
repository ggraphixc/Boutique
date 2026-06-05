-- supabase/migrations/08_image_to_3d_pipeline.sql

-- 1. Create custom status enumeration type safely
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'generation_status_type') THEN
        CREATE TYPE generation_status_type AS ENUM (
            'idle', 
            'queued', 
            'generating_mesh', 
            'optimizing_gltf', 
            'completed', 
            'failed'
        );
    END IF;
END $$;

-- 2. Create asset category enumeration type for apparel/footwear differentiation
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'asset_category_type') THEN
        CREATE TYPE asset_category_type AS ENUM ('apparel', 'footwear');
    END IF;
END $$;

-- 3. Expand products table to hold 2D reference inputs and pipeline control dimensions
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS source_2d_image_url TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS pipeline_status generation_status_type DEFAULT 'idle',
ADD COLUMN IF NOT EXISTS external_ai_job_id VARCHAR(255) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS pipeline_error_log TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS automated_mesh_retry_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS asset_category asset_category_type DEFAULT 'apparel';

-- 4. High-performance lookup index for background processing sweeps
CREATE INDEX IF NOT EXISTS idx_products_pipeline_processing 
ON products(pipeline_status) 
WHERE pipeline_status IN ('queued', 'generating_mesh', 'optimizing_gltf');

-- 5. Index for asset category queries
CREATE INDEX IF NOT EXISTS idx_products_asset_category 
ON products(asset_category);