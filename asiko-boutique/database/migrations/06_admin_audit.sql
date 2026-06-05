-- ASIKO Boutique Migration 06: Admin Audit Ledger
-- Immutable audit trail for Control Center administrative actions

-- Create an immutable ledger system to trace administrative actions and metadata updates
CREATE TABLE IF NOT EXISTS administrative_audit_logs (
    id SERIAL PRIMARY KEY,
    operator_session_token VARCHAR(255) NOT NULL,
    execution_vector VARCHAR(128) NOT NULL,
    target_resource_id INT DEFAULT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_vectors ON administrative_audit_logs(execution_vector);