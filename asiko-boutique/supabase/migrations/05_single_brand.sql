-- Migration 05: Single-Brand ASIKO Refactor
-- Removes multi-vendor architecture, consolidates all products under ASIKO brand

BEGIN;

-- Reassign all products to ASIKO Main Store
UPDATE products SET store_id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
WHERE store_id != 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';

-- Delete non-ASIKO vendors
DELETE FROM stores WHERE slug != 'asiko-main';

-- Rename ASIKO Main Store to ASIKO
UPDATE stores
SET name = 'ASIKO',
    slug = 'asiko',
    owner_email = 'hello@asikoboutique.com'
WHERE id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';

COMMIT;
