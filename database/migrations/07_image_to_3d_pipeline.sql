-- database/migrations/07_image_to_3d_pipeline.sql

-- Establish the explicit tracking states for the automated background process
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

-- Expand the core products table to support 2D image inputs and AI processing states
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS source_2d_image_url TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS pipeline_status generation_status_type DEFAULT 'idle',
ADD COLUMN IF NOT EXISTS external_ai_job_id VARCHAR(255) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS pipeline_error_log TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS automated_mesh_retry_count INT DEFAULT 0;

-- Optimize query performance for background processing loops
CREATE INDEX IF NOT EXISTS idx_products_pipeline_processing 
ON products(pipeline_status) 
WHERE pipeline_status IN ('queued', 'generating_mesh', 'optimizing_gltf');