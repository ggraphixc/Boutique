-- Migration 17: Logistics & Shipping System
-- Delivery providers, shipments, tracking, shipping rates

-- Delivery providers
CREATE TABLE IF NOT EXISTS delivery_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    api_base_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    supports_pickup BOOLEAN DEFAULT FALSE,
    supports_tracking BOOLEAN DEFAULT TRUE,
    base_rate NUMERIC(10,2) DEFAULT 0,
    per_km_rate NUMERIC(10,2) DEFAULT 0,
    states_served TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Shipments
CREATE TABLE IF NOT EXISTS shipments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    provider_id UUID REFERENCES delivery_providers(id),
    tracking_number VARCHAR(100),
    status VARCHAR(30) DEFAULT 'pending'
        CHECK (status IN (
            'pending','picked_up','in_transit','out_for_delivery',
            'delivered','failed','returned','cancelled'
        )),
    sender_name VARCHAR(150),
    sender_phone VARCHAR(20),
    sender_address TEXT,
    sender_state VARCHAR(50),
    receiver_name VARCHAR(150),
    receiver_phone VARCHAR(20),
    receiver_address TEXT,
    receiver_state VARCHAR(50),
    item_description TEXT,
    item_value NUMERIC(12,2),
    weight_kg NUMERIC(8,2),
    shipping_cost NUMERIC(10,2),
    estimated_delivery DATE,
    actual_delivery TIMESTAMPTZ,
    current_location TEXT,
    status_history JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ship_order ON shipments(order_id);
CREATE INDEX IF NOT EXISTS idx_ship_tracking ON shipments(tracking_number);
CREATE INDEX IF NOT EXISTS idx_ship_status ON shipments(status);

-- Shipping rates by state
CREATE TABLE IF NOT EXISTS shipping_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID REFERENCES delivery_providers(id),
    origin_state VARCHAR(50) NOT NULL,
    destination_state VARCHAR(50) NOT NULL,
    base_rate NUMERIC(10,2) NOT NULL,
    per_kg_rate NUMERIC(10,2) DEFAULT 0,
    estimated_days INT DEFAULT 3,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(provider_id, origin_state, destination_state)
);

-- Delivery tracking events
CREATE TABLE IF NOT EXISTS tracking_events (
    id BIGSERIAL PRIMARY KEY,
    shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL,
    location TEXT,
    description TEXT,
    event_time TIMESTAMPTZ DEFAULT NOW(),
    raw_data JSONB
);

CREATE INDEX IF NOT EXISTS idx_tev_shipment ON tracking_events(shipment_id);

-- Seed default Nigerian delivery providers
INSERT INTO delivery_providers (name, slug, supports_tracking, base_rate, states_served) VALUES
('KwikDelivery', 'kwik', TRUE, 1500, ARRAY['lagos','abuja','ogun']),
('GIG Logistics', 'gig', TRUE, 2000, ARRAY['lagos','abuja','ogun','rivers','kano','enugu']),
('DHL Nigeria', 'dhl', TRUE, 3500, ARRAY['lagos','abuja','rivers','kano','enugu','ibadan']),
('FedEx Nigeria', 'fedex', TRUE, 3000, ARRAY['lagos','abuja','rivers'])
ON CONFLICT (slug) DO NOTHING;
