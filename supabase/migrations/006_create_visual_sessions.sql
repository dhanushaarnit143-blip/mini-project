-- Migration 006: Create visual_sessions table
-- Ocular/Visual Behavior Module.
-- NOTE: Front-camera visual behavior is NOT retinal imaging. No video frames are stored.

CREATE TABLE IF NOT EXISTS visual_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_type TEXT NOT NULL CHECK (task_type IN ('tracking', 'blink', 'reaction')),
    duration NUMERIC NOT NULL CHECK (duration >= 0),
    blink_rate NUMERIC NOT NULL,
    blink_interval_variability NUMERIC NOT NULL,
    gaze_stability NUMERIC NOT NULL CHECK (gaze_stability BETWEEN 0.0 AND 1.0),
    reaction_time NUMERIC NOT NULL,
    quality_score NUMERIC NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_visual_sessions_participant_timestamp ON visual_sessions(participant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_visual_sessions_session_id ON visual_sessions(session_id);

COMMENT ON TABLE visual_sessions IS 'Ocular/Visual Behavior Module metrics (blink, gaze stability, reaction). NOT retinal imaging.';
COMMENT ON COLUMN visual_sessions.session_id IS 'Client-generated UUID idempotency key to prevent duplicate uploads.';
