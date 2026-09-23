-- Migration 001: Create participants table
-- Pseudonymized participant registry. Zero PII stored.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'baseline_status_enum') THEN
        CREATE TYPE baseline_status_enum AS ENUM ('collecting', 'established', 'adaptive');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consent_version TEXT NOT NULL DEFAULT '1.0.0',
    consent_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    app_version TEXT NOT NULL DEFAULT '1.0.0',
    model_version TEXT NOT NULL DEFAULT '1.0.0',
    baseline_status baseline_status_enum NOT NULL DEFAULT 'collecting',
    pseudonymous_id TEXT UNIQUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_participants_pseudonymous_id ON participants(pseudonymous_id);
CREATE INDEX IF NOT EXISTS idx_participants_created_at ON participants(created_at DESC);

COMMENT ON TABLE participants IS 'Pseudonymized participant registry. Zero PII stored.';
COMMENT ON COLUMN participants.pseudonymous_id IS 'Cryptographic pseudonymous identifier unique to the participant.';
