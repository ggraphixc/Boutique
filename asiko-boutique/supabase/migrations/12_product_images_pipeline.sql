-- Migration 12: Assign product images and queue 3D pipeline
-- Sets base_image and source_2d_image_url for all products, then queues them for 3D generation.

BEGIN;

-- 1. Set images for the 8 seed products
UPDATE products SET
    base_image = '/static/uploads/prod_agbada.jpg',
    source_2d_image_url = '/static/uploads/prod_agbada.jpg',
    pipeline_status = 'queued'
WHERE slug = 'ivory-agbada-set';

UPDATE products SET
    base_image = '/static/uploads/prod_bubu_dress.jpg',
    source_2d_image_url = '/static/uploads/prod_bubu_dress.jpg',
    pipeline_status = 'queued'
WHERE slug = 'adire-bubu-dress';

UPDATE products SET
    base_image = '/static/uploads/prod_loafers.jpg',
    source_2d_image_url = '/static/uploads/prod_loafers.jpg',
    pipeline_status = 'queued'
WHERE slug = 'kano-leather-loafers';

UPDATE products SET
    base_image = '/static/uploads/prod_aso_oke_jacket.jpg',
    source_2d_image_url = '/static/uploads/prod_aso_oke_jacket.jpg',
    pipeline_status = 'queued'
WHERE slug = 'aso-oke-dinner-jacket';

UPDATE products SET
    base_image = '/static/uploads/prod_bronze_cuff.jpg',
    source_2d_image_url = '/static/uploads/prod_bronze_cuff.jpg',
    pipeline_status = 'queued'
WHERE slug = 'benin-bronze-cuff';

UPDATE products SET
    base_image = '/static/uploads/prod_mermaid_skirt.jpg',
    source_2d_image_url = '/static/uploads/prod_mermaid_skirt.jpg',
    pipeline_status = 'queued'
WHERE slug = 'calabar-mermaid-skirt';

UPDATE products SET
    base_image = '/static/uploads/prod_embroidered_cap.jpg',
    source_2d_image_url = '/static/uploads/prod_embroidered_cap.jpg',
    pipeline_status = 'queued'
WHERE slug = 'hausa-embroidered-cap';

UPDATE products SET
    base_image = '/static/uploads/prod_kimono_jacket.jpg',
    source_2d_image_url = '/static/uploads/prod_kimono_jacket.jpg',
    pipeline_status = 'queued'
WHERE slug = 'sahel-kimono-jacket';

-- 2. Fix Lagos Silk Blazer: update source_2d_image_url (bad path), set base_image, re-queue
--    Previous: source_2d_image_url = '/static/images/test_gown.jpg' (does not exist)
--    Using same hash-named image already in static/uploads/
UPDATE products SET
    base_image = '/static/uploads/prod_e0530280c73032b8.jpg',
    source_2d_image_url = '/static/uploads/prod_e0530280c73032b8.jpg',
    pipeline_status = 'queued',
    pipeline_error_log = NULL
WHERE slug = 'lagos-silk-blazer';

-- 3. Ensure Men's Stylish Jacket is queued with its correct image
--    Already has base_image set, but ensure pipeline is queued
UPDATE products SET
    pipeline_status = 'queued',
    source_2d_image_url = base_image
WHERE slug = 'green-g-gown';

COMMIT;
