-- Migration 014: Extend consent records and participant soft-delete audit fields
-- Adds granular sensor permission types to consent_records
-- Adds is_deleted and deleted_at to participants for audit tracking and GDPR/research compliance

-- 1. Extend consent_type check constraint to support granular permissions
ALTER TABLE consent_records DROP CONSTRAINT IF EXISTS consent_records_consent_type_check;

ALTER TABLE consent_records ADD CONSTRAINT consent_records_consent_type_check CHECK (
    consent_type IN (
        'data_collection',
        'audio_storage',
        'research_export',
        'deletion',
        'camera_access',
        'microphone_access',
        'motion_access',
        'keyboard_access'
    )
);

-- 2. Add soft-delete and audit fields to participants table
ALTER TABLE participants ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE participants ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- 3. Create index for non-deleted participants
CREATE INDEX IF NOT EXISTS idx_participants_is_deleted ON participants(is_deleted);

COMMENT ON COLUMN consent_records.consent_type IS 'Category of consent: core collection, storage, export, deletion, or hardware sensor access.';
COMMENT ON COLUMN participants.is_deleted IS 'Audit flag marking participant account as deleted without breaking historical audit trails.';
COMMENT ON COLUMN participants.deleted_at IS 'Timestamp of irreversible data deletion execution.';
