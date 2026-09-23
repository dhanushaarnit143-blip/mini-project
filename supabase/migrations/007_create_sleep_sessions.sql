-- Migration 007: Create sleep_sessions table
-- Captures subjective sleep architecture, dream-enacting movements (prodromal RBD survey), and sleep quality.

CREATE TABLE IF NOT EXISTS sleep_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sleep_duration NUMERIC NOT NULL CHECK (sleep_duration BETWEEN 0.0 AND 24.0),
    sleep_quality NUMERIC NOT NULL CHECK (sleep_quality BETWEEN 1.0 AND 5.0),
    unusual_movement_self_report BOOLEAN NOT NULL,
    daytime_sleepiness NUMERIC NOT NULL CHECK (daytime_sleepiness BETWEEN 1.0 AND 5.0),
    questionnaire_version TEXT NOT NULL DEFAULT '1.0.0',
    score NUMERIC NOT NULL,
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_sleep_sessions_participant_timestamp ON sleep_sessions(participant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sleep_sessions_session_id ON sleep_sessions(session_id);

COMMENT ON TABLE sleep_sessions IS 'Sleep architecture metrics and prodromal REM sleep behavior survey data.';
COMMENT ON COLUMN sleep_sessions.session_id IS 'Client-generated UUID idempotency key to prevent duplicate uploads.';
