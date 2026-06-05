-- ASIKO Boutique - Omnichannel Stock Sentinel
-- Migration: 02_reservations.sql
-- Adds product variants + reservation hold system for manual sales channels

-- Product Variants (size/color matrix per product)
CREATE TABLE IF NOT EXISTS product_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    size VARCHAR(50) NOT NULL,
    color VARCHAR(50) NOT NULL,
    stock_qty INT NOT NULL CHECK (stock_qty >= 0),
    UNIQUE(product_id, size, color)
);

CREATE INDEX IF NOT EXISTS idx_variants_product_id ON product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_variants_stock ON product_variants(stock_qty);

-- Product Reservations (temporary stock holds for manual sales)
CREATE TABLE IF NOT EXISTS product_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_id UUID NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity INT NOT NULL CHECK (quantity > 0),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'settled', 'expired')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reservations_status ON product_reservations(status);
CREATE INDEX IF NOT EXISTS idx_reservations_variant ON product_reservations(variant_id);

-- Seed variants for existing products (4 sizes x 2 colors each)
-- Product: Lagos Silk Blazer (d4e5f6a7-b8c9-0123-defa-234567890123)
INSERT INTO product_variants (product_id, size, color, stock_qty) VALUES
('d4e5f6a7-b8c9-0123-defa-234567890123', 'S', 'Midnight Black', 12),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'M', 'Midnight Black', 15),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'L', 'Midnight Black', 13),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'XL', 'Midnight Black', 10),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'S', 'Ivory Gold', 8),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'M', 'Ivory Gold', 10),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'L', 'Ivory Gold', 9),
('d4e5f6a7-b8c9-0123-defa-234567890123', 'XL', 'Ivory Gold', 7),

-- Product: Ankara Casual Shirt (e5f6a7b8-c9d0-1234-efab-345678901234)
('e5f6a7b8-c9d0-1234-efab-345678901234', 'S', 'Blue Indigo', 20),
('e5f6a7b8-c9d0-1234-efab-345678901234', 'M', 'Blue Indigo', 25),
('e5f6a7b8-c9d0-1234-efab-345678901234', 'L', 'Blue Indigo', 22),
('e5f6a7b8-c9d0-1234-efab-345678901234', 'XL', 'Blue Indigo', 18),
('e5f6a7b8-c9d0-1234-efab-345678901234', 'S', 'Sunset Orange', 15),
('e5f6a7b8-c9d0-1234-efab-345678901234', 'M', 'Sunset Orange', 20),
('e5f6a7b8-c9d0-1234-efab-345678901234', 'L', 'Sunset Orange', 18),
('e5f6a7b8-c9d0-1234-efab-345678901234', 'XL', 'Sunset Orange', 15),

-- Product: Aba Handloomed Trousers (f6a7b8c9-d0e1-2345-fabc-456789012345)
('f6a7b8c9-d0e1-2345-fabc-456789012345', 'S', 'Natural Cotton', 8),
('f6a7b8c9-d0e1-2345-fabc-456789012345', 'M', 'Natural Cotton', 10),
('f6a7b8c9-d0e1-2345-fabc-456789012345', 'L', 'Natural Cotton', 7),
('f6a7b8c9-d0e1-2345-fabc-456789012345', 'XL', 'Natural Cotton', 5),
('f6a7b8c9-d0e1-2345-fabc-456789012345', 'S', 'Washed Grey', 6),
('f6a7b8c9-d0e1-2345-fabc-456789012345', 'M', 'Washed Grey', 8),
('f6a7b8c9-d0e1-2345-fabc-456789012345', 'L', 'Washed Grey', 5),
('f6a7b8c9-d0e1-2345-fabc-456789012345', 'XL', 'Washed Grey', 4),

-- Product: Adire Tie-Dye Dress (a7b8c9d0-e1f2-3456-abcd-567890123456)
('a7b8c9d0-e1f2-3456-abcd-567890123456', 'S', 'Classic Indigo', 10),
('a7b8c9d0-e1f2-3456-abcd-567890123456', 'M', 'Classic Indigo', 12),
('a7b8c9d0-e1f2-3456-abcd-567890123456', 'L', 'Classic Indigo', 11),
('a7b8c9d0-e1f2-3456-abcd-567890123456', 'XL', 'Classic Indigo', 8),
('a7b8c9d0-e1f2-3456-abcd-567890123456', 'S', 'Earth Brown', 7),
('a7b8c9d0-e1f2-3456-abcd-567890123456', 'M', 'Earth Brown', 9),
('a7b8c9d0-e1f2-3456-abcd-567890123456', 'L', 'Earth Brown', 8),
('a7b8c9d0-e1f2-3456-abcd-567890123456', 'XL', 'Earth Brown', 6),

-- Product: Kano Leather Sandals (b8c9d0e1-f2a3-4567-bcde-678901234567)
('b8c9d0e1-f2a3-4567-bcde-678901234567', 'S', 'Brown Leather', 15),
('b8c9d0e1-f2a3-4567-bcde-678901234567', 'M', 'Brown Leather', 20),
('b8c9d0e1-f2a3-4567-bcde-678901234567', 'L', 'Brown Leather', 18),
('b8c9d0e1-f2a3-4567-bcde-678901234567', 'XL', 'Brown Leather', 12),
('b8c9d0e1-f2a3-4567-bcde-678901234567', 'S', 'Black Leather', 12),
('b8c9d0e1-f2a3-4567-bcde-678901234567', 'M', 'Black Leather', 18),
('b8c9d0e1-f2a3-4567-bcde-678901234567', 'L', 'Black Leather', 15),
('b8c9d0e1-f2a3-4567-bcde-678901234567', 'XL', 'Black Leather', 10),

-- Product: Benin Bronze Earrings (c9d0e1f2-a3b4-5678-cdef-789012345678)
('c9d0e1f2-a3b4-5678-cdef-789012345678', 'S', 'Bronze', 20),
('c9d0e1f2-a3b4-5678-cdef-789012345678', 'M', 'Bronze', 20),
('c9d0e1f2-a3b4-5678-cdef-789012345678', 'L', 'Bronze', 15),
('c9d0e1f2-a3b4-5678-cdef-789012345678', 'XL', 'Bronze', 5),
('c9d0e1f2-a3b4-5678-cdef-789012345678', 'S', 'Antique Gold', 18),
('c9d0e1f2-a3b4-5678-cdef-789012345678', 'M', 'Antique Gold', 18),
('c9d0e1f2-a3b4-5678-cdef-789012345678', 'L', 'Antique Gold', 12),
('c9d0e1f2-a3b4-5678-cdef-789012345678', 'XL', 'Antique Gold', 4);
