-- ÀSÌKÒ Boutique Seed Data
-- Seed: 4 products with size variants (S, M, L, XL)

-- Product 1: Aspirational Segment
INSERT INTO products (id, name, description, segment, price, base_image) VALUES
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Lagos Silk Blazer', 'Hand-tailored silk blazer from Aba textile district. Features premium African-inspired lining and mother-of-pearl buttons.', 'aspirational', 85000.00, '/images/lagos-silk-blazer.jpg');

INSERT INTO product_variants (product_id, size, color, stock_qty) VALUES
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'S', 'Midnight Navy', 12),
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'M', 'Midnight Navy', 18),
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'L', 'Midnight Navy', 15),
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'XL', 'Midnight Navy', 8),
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'S', 'Ivory Cream', 10),
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'M', 'Ivory Cream', 14),
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'L', 'Ivory Cream', 11),
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'XL', 'Ivory Cream', 6);

-- Product 2: Value Segment
INSERT INTO products (id, name, description, segment, price, base_image) VALUES
('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'Ankara Casual Shirt', 'Breathable cotton Ankara print shirt. Perfect for casual outings and cultural events. Machine washable.', 'value', 15000.00, '/images/ankara-casual-shirt.jpg');

INSERT INTO product_variants (product_id, size, color, stock_qty) VALUES
('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'S', 'Sunset Orange', 25),
('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'M', 'Sunset Orange', 30),
('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'L', 'Sunset Orange', 22),
('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'XL', 'Sunset Orange', 15),
('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'S', 'Forest Green', 20),
('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'M', 'Forest Green', 28),
('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'L', 'Forest Green', 19),
('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'XL', 'Forest Green', 12);

-- Product 3: Aspirational Segment
INSERT INTO products (id, name, description, segment, price, base_image) VALUES
('c3d4e5f6-a7b8-9012-cdef-123456789012', 'Aba Handloomed Trousers', 'Premium handloomed cotton trousers from Aba textile cluster. Features reinforced seams and classic tailoring.', 'aspirational', 45000.00, '/images/aba-handloomed-trousers.jpg');

INSERT INTO product_variants (product_id, size, color, stock_qty) VALUES
('c3d4e5f6-a7b8-9012-cdef-123456789012', 'S', 'Charcoal Grey', 14),
('c3d4e5f6-a7b8-9012-cdef-123456789012', 'M', 'Charcoal Grey', 20),
('c3d4e5f6-a7b8-9012-cdef-123456789012', 'L', 'Charcoal Grey', 16),
('c3d4e5f6-a7b8-9012-cdef-123456789012', 'XL', 'Charcoal Grey', 9),
('c3d4e5f6-a7b8-9012-cdef-123456789012', 'S', 'Khaki Sand', 12),
('c3d4e5f6-a7b8-9012-cdef-123456789012', 'M', 'Khaki Sand', 17),
('c3d4e5f6-a7b8-9012-cdef-123456789012', 'L', 'Khaki Sand', 13),
('c3d4e5f6-a7b8-9012-cdef-123456789012', 'XL', 'Khaki Sand', 7);

-- Product 4: Value Segment
INSERT INTO products (id, name, description, segment, price, base_image) VALUES
('d4e5f6a7-b8c9-0123-defa-234567890123', 'Adire Tie-Dye Dress', 'Traditional Adire tie-dye cotton dress. Each piece is unique with hand-crafted patterns.', 'value', 22000.00, '/images/adire-tie-dye-dress.jpg');

INSERT INTO product_variants (product_id, size, color, stock_qty) VALUES
('d4e5f6a7-b8c9-0123-defa-234567890123', 'S', 'Indigo Blue', 22),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'M', 'Indigo Blue', 28),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'L', 'Indigo Blue', 20),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'XL', 'Indigo Blue', 14),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'S', 'Earth Brown', 18),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'M', 'Earth Brown', 25),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'L', 'Earth Brown', 17),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'XL', 'Earth Brown', 10);
