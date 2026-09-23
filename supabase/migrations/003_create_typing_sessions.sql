-- Migration 003: Create typing_sessions table
-- Stores keystroke timing dynamics. Keystroke text is NEVER stored.

CREATE TABLE IF NOT EXISTS typing_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_type TEXT NOT NULL CHECK (task_type IN ('controlled_phrase', 'free_typing')),
    duration NUMERIC NOT NULL CHECK (duration >= 0),
    typing_speed NUMERIC NOT NULL CHECK (typing_speed >= 0),
    mean_inter_key_interval NUMERIC NOT NULL CHECK (mean_inter_key_interval >= 0),
    std_inter_key_interval NUMERIC NOT NULL CHECK (std_inter_key_interval >= 0),
    pause_rate NUMERIC NOT NULL CHECK (pause_rate >= 0),
    correction_rate NUMERIC NOT NULL CHECK (correction_rate >= 0),
    rhythm_variability NUMERIC NOT NULL CHECK (rhythm_variability >= 0),
    quality_score NUMERIC NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_typing_sessions_participant_timestamp ON typing_sessions(participant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_typing_sessions_session_id ON typing_sessions(session_id);

COMMENT ON TABLE typing_sessions IS 'Keystroke timing kinematics. No key text is ever recorded.';
COMMENT ON COLUMN typing_sessions.session_id IS 'Client-generated UUID idempotency key to prevent duplicate uploads.';
