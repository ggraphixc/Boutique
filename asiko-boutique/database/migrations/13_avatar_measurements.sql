-- ASIKO Boutique Migration 13: Avatar Measurements
-- Stores body measurements for virtual try-on fitting

CREATE TABLE IF NOT EXISTS avatar_measurements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(128) DEFAULT NULL,
    height NUMERIC(5,3) DEFAULT 1.70,
    chest NUMERIC(5,3) DEFAULT 0.92,
    waist NUMERIC(5,3) DEFAULT 0.72,
    hip NUMERIC(5,3) DEFAULT 0.95,
    shoulder NUMERIC(5,3) DEFAULT 0.44,
    inseam NUMERIC(5,3) DEFAULT 0.76,
    neck_circumference NUMERIC(5,3) DEFAULT 0.38,
    arm_length NUMERIC(5,3) DEFAULT 0.65,
    gender VARCHAR(12) DEFAULT 'female',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_avatar_measurements_session ON avatar_measurements(session_id);
