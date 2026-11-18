-- Migration 001: Create participants table
-- Pseudonymized participant registry.

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
    email TEXT UNIQUE,
    pseudonymous_id TEXT UNIQUE NOT NULL,
    consent_version TEXT NOT NULL DEFAULT '1.0.0',
    consent_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    app_version TEXT NOT NULL DEFAULT '1.0.0',
    model_version TEXT NOT NULL DEFAULT '1.0.0',
    baseline_status TEXT NOT NULL DEFAULT 'collecting' CHECK (baseline_status IN ('collecting', 'established', 'adaptive')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_participants_pseudonymous_id ON participants(pseudonymous_id);
CREATE INDEX IF NOT EXISTS idx_participants_created_at ON participants(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_participants_email ON participants(email);

COMMENT ON TABLE participants IS 'Pseudonymized participant registry.';
COMMENT ON COLUMN participants.pseudonymous_id IS 'Cryptographic pseudonymous identifier unique to the participant.';
