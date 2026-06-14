-- Migration 21: AI Training Data — admin-configurable brand knowledge, Q&A, style rules
-- Allows the AI Stylist to learn about ASIKO brand and give non-generic answers.

CREATE TABLE IF NOT EXISTS ai_training_data (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category    VARCHAR(50) NOT NULL DEFAULT 'faq',
        -- faq: frequently asked questions and answers
        -- brand: brand story, values, mission facts
        -- product: product-specific knowledge, styling tips
        -- style: style rules, Nigerian fashion expertise
        -- voice: brand voice guidelines, tone instructions
        -- custom: any other admin-entered context
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_training_category ON ai_training_data(category) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_ai_training_active ON ai_training_data(is_active);

COMMENT ON TABLE ai_training_data IS 'Admin-managed training data for the AI Fashion Stylist. Injected into the system prompt at chat time.';
COMMENT ON COLUMN ai_training_data.category IS 'faq | brand | product | style | voice | custom';
