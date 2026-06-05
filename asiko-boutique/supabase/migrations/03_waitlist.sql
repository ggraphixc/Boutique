-- ASIKO Boutique Migration 03: Out-of-Stock Waitlist
-- Tracks customer requests for restocked variants

CREATE TABLE IF NOT EXISTS product_waitlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    variant_id UUID NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    notified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_email_variant UNIQUE (email, variant_id)
);

CREATE INDEX IF NOT EXISTS idx_waitlist_variant_notified
    ON product_waitlists(variant_id, notified);
