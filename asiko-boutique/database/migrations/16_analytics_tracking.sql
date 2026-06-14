-- Migration 16: Analytics Tracking System
-- Real page views, funnel events, traffic sources, session tracking

-- Page view tracking (every page visit)
CREATE TABLE IF NOT EXISTS page_views (
    id BIGSERIAL PRIMARY KEY,
    path VARCHAR(500) NOT NULL,
    product_id UUID,
    store_id UUID,
    session_id VARCHAR(100),
    customer_id UUID,
    referrer TEXT,
    user_agent TEXT,
    ip_hash VARCHAR(64),
    device_type VARCHAR(10) CHECK (device_type IN ('desktop','mobile','tablet')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pv_path ON page_views(path);
CREATE INDEX IF NOT EXISTS idx_pv_product ON page_views(product_id);
CREATE INDEX IF NOT EXISTS idx_pv_store ON page_views(store_id);
CREATE INDEX IF NOT EXISTS idx_pv_created ON page_views(created_at);
CREATE INDEX IF NOT EXISTS idx_pv_session ON page_views(session_id);

-- Conversion funnel events
CREATE TABLE IF NOT EXISTS funnel_events (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    customer_id UUID,
    event_step VARCHAR(30) NOT NULL
        CHECK (event_step IN (
            'landing','product_view','try_on_start','try_on_complete',
            'add_to_cart','checkout_start','payment_init','payment_success',
            'order_placed','repeat_visit'
        )),
    product_id UUID,
    store_id UUID,
    value NUMERIC(12,2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fe_session ON funnel_events(session_id);
CREATE INDEX IF NOT EXISTS idx_fe_step ON funnel_events(event_step);
CREATE INDEX IF NOT EXISTS idx_fe_created ON funnel_events(created_at);

-- Traffic source tracking
CREATE TABLE IF NOT EXISTS traffic_sources (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    source VARCHAR(100),
    medium VARCHAR(50),
    campaign VARCHAR(100),
    referrer_domain VARCHAR(200),
    landing_page TEXT,
    customer_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ts_source ON traffic_sources(source);
CREATE INDEX IF NOT EXISTS idx_ts_session ON traffic_sources(session_id);
CREATE INDEX IF NOT EXISTS idx_ts_created ON traffic_sources(created_at);

-- Daily platform aggregates (materialized for fast dashboard)
CREATE TABLE IF NOT EXISTS platform_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    stat_date DATE NOT NULL DEFAULT CURRENT_DATE UNIQUE,
    total_views INT DEFAULT 0,
    unique_visitors INT DEFAULT 0,
    product_views INT DEFAULT 0,
    try_ons INT DEFAULT 0,
    add_to_carts INT DEFAULT 0,
    orders INT DEFAULT 0,
    revenue NUMERIC(12,2) DEFAULT 0,
    new_customers INT DEFAULT 0,
    returning_customers INT DEFAULT 0,
    conversion_rate NUMERIC(5,2) DEFAULT 0
);

-- Try-on session tracking
CREATE TABLE IF NOT EXISTS tryon_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    customer_id UUID,
    session_id VARCHAR(100),
    duration_seconds INT,
    body_type VARCHAR(30),
    fit_type VARCHAR(20),
    fit_confidence INT,
    result VARCHAR(20) CHECK (result IN ('viewed','added_to_cart','shared','abandoned')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ttry_product ON tryon_sessions(product_id);
CREATE INDEX IF NOT EXISTS idx_ttry_created ON tryon_sessions(created_at);
