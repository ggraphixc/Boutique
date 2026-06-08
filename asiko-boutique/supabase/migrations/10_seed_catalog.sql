-- Migration 10: Seed product catalog with real data
-- Updates existing products and adds 8 new ones across Nigerian fashion categories.

BEGIN;

-- Update existing products with proper prices and descriptions
UPDATE products SET
    name = 'Green G-Gown',
    description = 'A flowing agbada-inspired gown in rich emerald green. Hand-finished with gold thread accents at the neckline. Perfect for traditional ceremonies and special occasions.',
    price = 85000,
    slug = 'green-g-gown'
WHERE name = 'Green G-gown';

UPDATE products SET
    name = 'Lagos Silk Blazer',
    description = 'Structured silk blazer cut in the Lagos power style. Notch lapel, single-button closure, fully lined. A modern take on West African tailoring.',
    price = 65000,
    slug = 'lagos-silk-blazer'
WHERE name = 'Lagos Silk Blazer';

-- Seed 8 new products
INSERT INTO products (store_id, name, description, price, stock_quantity, category_id, slug, base_image, pipeline_status)
SELECT
    (SELECT id FROM stores LIMIT 1),
    p.name,
    p.description,
    p.price,
    p.stock,
    (SELECT id FROM categories WHERE name = p.category LIMIT 1),
    p.slug,
    NULL,
    'idle'
FROM (VALUES
    ('Ivory Agbada Set', 'Three-piece agbada ensemble in premium ivory cotton. Embroidered chest panel with matching fila cap. Ideal for weddings and cultural celebrations.', 120000, 8, 'Tailoring', 'ivory-agbada-set'),
    ('Adire Bubu Dress', 'Hand-dyed adire bubu dress in indigo and white. Relaxed fit with wide sleeves. Each piece is uniquely dyed using traditional Yoruba techniques.', 45000, 12, 'Dresses', 'adire-bubu-dress'),
    ('Kano Leather Loafers', 'Handcrafted leather loafers from Kano artisans. Full grain leather upper, cushioned insole. Available in tan and dark brown.', 35000, 15, 'Footwear', 'kano-leather-loafers'),
    ('Aso-Oke Dinner Jacket', 'Contemporary dinner jacket woven in aso-oke fabric. Slim fit, peak lapel, satin trim. A statement piece for evening events.', 95000, 5, 'Tailoring', 'aso-oke-dinner-jacket'),
    ('Benin Bronze Cuff', 'Solid brass cuff bracelet cast using lost-wax technique. Geometric patterns inspired by Benin bronzes. Adjustable fit.', 18000, 20, 'Accessories', 'benin-bronze-cuff'),
    ('Calabar Mermaid Skirt', 'High-waisted mermaid skirt in george fabric. Flared hem with gold border detail. Pairs beautifully with any fitted top.', 38000, 10, 'Dresses', 'calabar-mermaid-skirt'),
    ('Hausa Embroidered Cap', 'Hand-embroidered hula cap from Hausa craftsmen. Intricate geometric stitching in gold thread on deep green fabric.', 8000, 25, 'Accessories', 'hausa-embroidered-cap'),
    ('Sahel Kimono Jacket', 'Lightweight kimono-style jacket in Sahel cotton print. Open front, wide sleeves, belt tie. Versatile layering piece.', 28000, 18, 'Outerwear', 'sahel-kimono-jacket')
) AS p(name, description, price, stock, category, slug);

-- Add variants for new products
INSERT INTO product_variants (product_id, size, color, stock_qty)
SELECT p.id, v.size, v.color, v.stock
FROM products p
CROSS JOIN (VALUES
    ('S', 'Default', 3),
    ('M', 'Default', 5),
    ('L', 'Default', 4),
    ('XL', 'Default', 3)
) AS v(size, color, stock)
WHERE p.slug IN ('ivory-agbada-set', 'adire-bubu-dress', 'aso-oke-dinner-jacket', 'calabar-mermaid-skirt', 'sahel-kimono-jacket')
AND v.size IN ('S', 'M', 'L', 'XL');

-- Footwear variants (EU sizes)
INSERT INTO product_variants (product_id, size, color, stock_qty)
SELECT p.id, v.size, v.color, v.stock
FROM products p
CROSS JOIN (VALUES
    ('EU 40', 'Tan', 4),
    ('EU 41', 'Tan', 5),
    ('EU 42', 'Tan', 4),
    ('EU 43', 'Tan', 3),
    ('EU 40', 'Brown', 3),
    ('EU 41', 'Brown', 4),
    ('EU 42', 'Brown', 3),
    ('EU 43', 'Brown', 2)
) AS v(size, color, stock)
WHERE p.slug = 'kano-leather-loafers';

-- Accessories (one size)
INSERT INTO product_variants (product_id, size, color, stock_qty)
SELECT p.id, 'One Size', v.color, v.stock
FROM products p
CROSS JOIN (VALUES
    ('Gold', 10),
    ('Bronze', 10)
) AS v(color, stock)
WHERE p.slug = 'benin-bronze-cuff';

INSERT INTO product_variants (product_id, size, color, stock_qty)
SELECT p.id, 'One Size', 'Green', 25
FROM products p
WHERE p.slug = 'hausa-embroidered-cap';

COMMIT;
