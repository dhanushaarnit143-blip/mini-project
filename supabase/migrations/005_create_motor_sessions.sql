-- Migration 005: Create motor_sessions table
-- Stores motor, gait, tapping, and tremor kinematic features.

CREATE TABLE IF NOT EXISTS motor_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_type TEXT NOT NULL CHECK (task_type IN ('walking', 'tapping', 'tremor_hold', 'spiral')),
    duration NUMERIC NOT NULL CHECK (duration >= 0),
    cadence NUMERIC,
    stride_variability NUMERIC,
    movement_variability NUMERIC NOT NULL,
    tapping_rate NUMERIC,
    tapping_interval_variability NUMERIC,
    tremor_frequency NUMERIC,
    tremor_amplitude NUMERIC,
    quality_score NUMERIC NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_motor_sessions_participant_timestamp ON motor_sessions(participant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_motor_sessions_session_id ON motor_sessions(session_id);

COMMENT ON TABLE motor_sessions IS 'Kinematic motor metrics from accelerometer/gyroscope/touch tasks.';
COMMENT ON COLUMN motor_sessions.session_id IS 'Client-generated UUID idempotency key to prevent duplicate uploads.';
