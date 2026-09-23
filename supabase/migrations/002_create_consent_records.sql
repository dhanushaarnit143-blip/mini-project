-- Migration 002: Create consent_records table
-- Audit trail of all informed consent grants and revocations.

CREATE TABLE IF NOT EXISTS consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL CHECK (consent_type IN ('data_collection', 'audio_storage', 'research_export', 'deletion')),
    consent_version TEXT NOT NULL,
    granted BOOLEAN NOT NULL DEFAULT TRUE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_consent_records_participant_id ON consent_records(participant_id);
CREATE INDEX IF NOT EXISTS idx_consent_records_timestamp ON consent_records(participant_id, timestamp DESC);

COMMENT ON TABLE consent_records IS 'Immutable participant consent records and revocations.';
