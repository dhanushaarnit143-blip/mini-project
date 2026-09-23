-- Migration 004: Create voice_sessions table
-- Stores acoustic biomarker features extracted on-device. Raw audio is NOT stored.

CREATE TABLE IF NOT EXISTS voice_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_type TEXT NOT NULL CHECK (task_type IN ('sustained_vowel', 'read_sentence', 'free_speech')),
    duration NUMERIC NOT NULL CHECK (duration >= 0),
    signal_quality NUMERIC NOT NULL CHECK (signal_quality BETWEEN 0.0 AND 1.0),
    jitter NUMERIC NOT NULL,
    shimmer NUMERIC NOT NULL,
    hnr NUMERIC NOT NULL,
    pitch_mean NUMERIC NOT NULL,
    pitch_std NUMERIC NOT NULL,
    mfcc_features JSONB NOT NULL,
    spectral_features JSONB NOT NULL,
    quality_score NUMERIC NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_voice_sessions_participant_timestamp ON voice_sessions(participant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_session_id ON voice_sessions(session_id);

COMMENT ON TABLE voice_sessions IS 'Acoustic voice features (jitter, shimmer, HNR, MFCC). Raw audio is discarded locally.';
COMMENT ON COLUMN voice_sessions.session_id IS 'Client-generated UUID idempotency key to prevent duplicate uploads.';
