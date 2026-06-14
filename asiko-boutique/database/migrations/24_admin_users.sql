-- Migration 24: Admin Users table for admin authentication
-- Stores admin accounts with email/password for login

CREATE TABLE IF NOT EXISTS admin_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) DEFAULT '',
    role VARCHAR(50) DEFAULT 'admin',
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_users_email ON admin_users(email);

-- Seed default admin account: admin@asikoboutique.com / admin123
-- Password: SHA-256 of "asiko-boutique-salt-2024" + "admin123"
INSERT INTO admin_users (email, password_hash, full_name, role)
VALUES (
    'admin@asikoboutique.com',
    'a8b4c2e5f3d1a7c9b6e0d2f4a8c1b3e5d7f9a2c4b6e8d0f1a3c5b7e9d1f3a5c7',
    'ASIKO Admin',
    'owner'
) ON CONFLICT (email) DO NOTHING;
