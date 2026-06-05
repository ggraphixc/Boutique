-- ASIKO Boutique - Multi-Vendor Database Schema
-- Migration: 01_init_schema.sql

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Stores / Vendors table
CREATE TABLE stores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    owner_email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Products table (linked to stores)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL CHECK (price > 0),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    base_image TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Orders table
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_email TEXT NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL CHECK (total_amount > 0),
    shipping_state VARCHAR(100),
    shipping_cost NUMERIC(10, 2) DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'processing', 'shipped', 'delivered', 'cancelled')),
    payment_reference TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Order Items table
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price NUMERIC(10, 2) NOT NULL CHECK (price > 0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_products_store_id ON products(store_id);
CREATE INDEX idx_products_stock_quantity ON products(stock_quantity);
CREATE INDEX idx_orders_customer_email ON orders(customer_email);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);

-- Nigerian States Shipping Matrix
CREATE TABLE nigerian_states (
    code VARCHAR(2) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    shipping_cost NUMERIC(10, 2) NOT NULL DEFAULT 2000.00,
    weight_factor NUMERIC(3, 2) DEFAULT 1.00
);

-- Seed Nigerian States with shipping costs
INSERT INTO nigerian_states (code, name, shipping_cost, weight_factor) VALUES
('AB', 'Abia', 2500.00, 1.00),
('AD', 'Adamawa', 3000.00, 1.10),
('AK', 'Akwa Ibom', 2500.00, 1.00),
('AN', 'Anambra', 2500.00, 1.00),
('BA', 'Bauchi', 3500.00, 1.20),
('BY', 'Bayelsa', 3000.00, 1.10),
('BE', 'Benue', 3000.00, 1.10),
('BO', 'Borno', 4000.00, 1.30),
('CR', 'Cross River', 2500.00, 1.00),
('DE', 'Delta', 2500.00, 1.00),
('EB', 'Ebonyi', 2500.00, 1.00),
('ED', 'Edo', 2500.00, 1.00),
('EK', 'Ekiti', 2500.00, 1.00),
('EN', 'Enugu', 2500.00, 1.00),
('FC', 'FCT', 2000.00, 1.00),
('GO', 'Gombe', 3500.00, 1.20),
('IM', 'Imo', 2500.00, 1.00),
('JI', 'Jigawa', 3500.00, 1.20),
('KD', 'Kaduna', 3000.00, 1.10),
('KN', 'Kano', 3000.00, 1.10),
('KT', 'Katsina', 3500.00, 1.20),
('KE', 'Kebbi', 3500.00, 1.20),
('KO', 'Kogi', 3000.00, 1.10),
('KW', 'Kwara', 2500.00, 1.00),
('LA', 'Lagos', 1500.00, 1.00),
('NA', 'Nasarawa', 2500.00, 1.00),
('NI', 'Niger', 3000.00, 1.10),
('OG', 'Ogun', 2000.00, 1.00),
('ON', 'Ondo', 2500.00, 1.00),
('OS', 'Osun', 2500.00, 1.00),
('OY', 'Oyo', 2500.00, 1.00),
('PL', 'Plateau', 3000.00, 1.10),
('RI', 'Rivers', 2500.00, 1.00),
('SO', 'Sokoto', 3500.00, 1.20),
('TA', 'Taraba', 3500.00, 1.20),
('YO', 'Yobe', 4000.00, 1.30),
('ZA', 'Zamfara', 3500.00, 1.20);

-- Seed Stores
INSERT INTO stores (id, name, slug, owner_email) VALUES
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'ASIKO Main Store', 'asiko-main', 'vendor@asikoboutique.com'),
('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'Lagos Textile Co', 'lagos-textile', 'lagos@textileco.com'),
('c3d4e5f6-a7b8-9012-cdef-123456789012', 'Aba Fashion House', 'aba-fashion', 'aba@fashionhouse.com');

-- Seed Products
INSERT INTO products (id, store_id, name, description, price, stock_quantity, base_image) VALUES
('d4e5f6a7-b8c9-0123-defa-234567890123', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Lagos Silk Blazer', 'Hand-tailored silk blazer with premium African-inspired lining', 85000.00, 50, '/images/lagos-silk-blazer.jpg'),
('e5f6a7b8-c9d0-1234-efab-345678901234', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Ankara Casual Shirt', 'Breathable cotton Ankara print shirt', 15000.00, 100, '/images/ankara-shirt.jpg'),
('f6a7b8c9-d0e1-2345-fabc-456789012345', 'b2c3d4e5-f6a7-8901-bcde-f12345678901', 'Aba Handloomed Trousers', 'Premium handloomed cotton trousers', 45000.00, 30, '/images/aba-trousers.jpg'),
('a7b8c9d0-e1f2-3456-abcd-567890123456', 'b2c3d4e5-f6a7-8901-bcde-f12345678901', 'Adire Tie-Dye Dress', 'Traditional Adire tie-dye cotton dress', 22000.00, 45, '/images/adire-dress.jpg'),
('b8c9d0e1-f2a3-4567-bcde-678901234567', 'c3d4e5f6-a7b8-9012-cdef-123456789012', 'Kano Leather Sandals', 'Handcrafted leather sandals from Kano', 8500.00, 75, '/images/kano-sandals.jpg'),
('c9d0e1f2-a3b4-5678-cdef-789012345678', 'c3d4e5f6-a7b8-9012-cdef-123456789012', 'Benin Bronze Earrings', 'Cast bronze earrings inspired by Benin art', 12000.00, 60, '/images/benin-earrings.jpg');
