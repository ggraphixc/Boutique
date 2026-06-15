-- Migration 28: Email templates and email logs tables
-- Email templates for transactional and marketing emails
-- Email logs for tracking delivery, opens, and clicks

CREATE TABLE IF NOT EXISTS email_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'custom',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_email VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    template_id UUID REFERENCES email_templates(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'sent',
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_email_templates_category ON email_templates(category);
CREATE INDEX IF NOT EXISTS idx_email_logs_recipient ON email_logs(recipient_email);
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status);
CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at ON email_logs(sent_at DESC);

-- Seed 3 default templates
INSERT INTO email_templates (name, subject, body, category) VALUES
('Welcome to ASIKO', 'Welcome to ASIKO Boutique! 🎉', '<h2>Welcome to ASIKO!</h2><p>Hi {{name}},</p><p>Thank you for joining ASIKO Boutique. We''re excited to have you!</p><p>Explore our curated collection of authentic Nigerian fashion with transparent pricing.</p><p>Happy shopping!</p><p>— The ASIKO Team</p>', 'welcome'),
('Order Confirmation', 'Your ASIKO Order #{{order_id}} is Confirmed ✓', '<h2>Order Confirmed!</h2><p>Hi {{name}},</p><p>Your order <strong>#{{order_id}}</strong> has been confirmed.</p><p><strong>Total:</strong> {{total}}</p><p>We''ll send you a shipping update soon.</p><p>— The ASIKO Team</p>', 'order'),
('Shipping Update', 'Your ASIKO Order Has Been Shipped! 📦', '<h2>Your Order is On Its Way!</h2><p>Hi {{name}},</p><p>Great news! Your order <strong>#{{order_id}}</strong> has been shipped.</p><p><strong>Carrier:</strong> {{carrier}}</p><p><strong>Tracking:</strong> {{tracking_number}}</p><p>— The ASIKO Team</p>', 'order');

COMMENT ON TABLE email_templates IS 'Admin-managed email templates for transactional and marketing emails.';
COMMENT ON TABLE email_logs IS 'Log of all emails sent through ASIKO. Tracks delivery, opens, and clicks.';
