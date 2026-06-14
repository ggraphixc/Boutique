-- Migration 19: Loyalty System
-- Points, referrals, VIP tiers, rewards catalog

-- Loyalty points ledger
CREATE TABLE IF NOT EXISTS loyalty_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    points INT NOT NULL,
    source VARCHAR(30) NOT NULL
        CHECK (source IN (
            'purchase','referral','review','social_share',
            'try_on','birthday','vip_bonus','admin_adjust','redemption'
        )),
    reference_id UUID,
    description TEXT,
    balance_after INT NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lp_customer ON loyalty_points(customer_id);
CREATE INDEX IF NOT EXISTS idx_lp_source ON loyalty_points(source);

-- Customer loyalty summary
CREATE TABLE IF NOT EXISTS loyalty_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID UNIQUE NOT NULL REFERENCES customers(id),
    total_points_earned INT DEFAULT 0,
    total_points_redeemed INT DEFAULT 0,
    current_balance INT DEFAULT 0,
    lifetime_spend NUMERIC(12,2) DEFAULT 0,
    lifetime_orders INT DEFAULT 0,
    vip_tier VARCHAR(20) DEFAULT 'bronze'
        CHECK (vip_tier IN ('bronze','silver','gold','platinum','diamond')),
    vip_since TIMESTAMPTZ,
    referral_code VARCHAR(20) UNIQUE,
    referred_by UUID REFERENCES customers(id),
    total_referrals INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- VIP tier thresholds
CREATE TABLE IF NOT EXISTS vip_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier_name VARCHAR(20) UNIQUE NOT NULL,
    min_spend NUMERIC(12,2) NOT NULL,
    points_multiplier NUMERIC(3,2) DEFAULT 1.0,
    discount_percent NUMERIC(5,2) DEFAULT 0,
    free_shipping BOOLEAN DEFAULT FALSE,
    early_access BOOLEAN DEFAULT FALSE,
    badge_url TEXT,
    benefits JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Referrals
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL REFERENCES customers(id),
    referred_id UUID REFERENCES customers(id),
    referral_code VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending','registered','first_purchase','rewarded')),
    reward_points INT DEFAULT 0,
    first_purchase_amount NUMERIC(12,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    rewarded_at TIMESTAMPTZ
);

-- Points catalog (what you can redeem)
CREATE TABLE IF NOT EXISTS rewards_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    points_cost INT NOT NULL,
    reward_type VARCHAR(30) NOT NULL
        CHECK (reward_type IN ('discount','free_shipping','free_item','exclusive_access')),
    reward_value NUMERIC(12,2),
    image_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    stock INT DEFAULT -1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Point redemptions
CREATE TABLE IF NOT EXISTS point_redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    reward_id UUID NOT NULL REFERENCES rewards_catalog(id),
    points_spent INT NOT NULL,
    order_id UUID REFERENCES orders(id),
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending','fulfilled','expired','cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed VIP tiers
INSERT INTO vip_tiers (tier_name, min_spend, points_multiplier, discount_percent, free_shipping, early_access, benefits) VALUES
('bronze',   0,        1.0, 0,   FALSE, FALSE, '{"welcome_bonus": 100}'),
('silver',   50000,    1.5, 5,   TRUE,  FALSE, '{"free_shipping": true, "birthday_bonus": 200}'),
('gold',     200000,   2.0, 10,  TRUE,  TRUE,  '{"free_shipping": true, "early_access": true, "birthday_bonus": 500}'),
('platinum',  500000,  2.5, 15,  TRUE,  TRUE,  '{"free_shipping": true, "early_access": true, "exclusive_drops": true, "birthday_bonus": 1000}'),
('diamond',  1000000,  3.0, 20,  TRUE,  TRUE,  '{"free_shipping": true, "early_access": true, "exclusive_drops": true, "personal_stylist": true, "birthday_bonus": 2000}')
ON CONFLICT (tier_name) DO NOTHING;

-- Seed rewards catalog
INSERT INTO rewards_catalog (name, description, points_cost, reward_type, reward_value) VALUES
('₦500 Discount', 'Discount on your next order', 500, 'discount', 500),
('₦1000 Discount', 'Discount on your next order', 1000, 'discount', 1000),
('₦2000 Discount', 'Discount on your next order', 2000, 'discount', 2000),
('Free Shipping', 'Free delivery on your next order', 300, 'free_shipping', 0),
('VIP Early Access', '48-hour early access to new drops', 1500, 'exclusive_access', 0)
ON CONFLICT DO NOTHING;
