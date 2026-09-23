-- Migration 017: Extend visual_sessions for Phase 7 compatibility
-- Ocular/Visual Behavior Module
-- NOTE: Front-camera visual behavior is NOT retinal imaging. No video frames are stored.
--
-- Makes task-specific metric columns nullable because each visual task
-- (tracking, blink, reaction) measures distinct behavioral features.
-- Adds granular metrics: tracking_accuracy, blink_duration_mean,
-- reaction_time_variability, missed_targets, gaze_movement_features.
-- Updates feature_version default to '1.0' matching the Phase 7 JS module.

ALTER TABLE visual_sessions
    ALTER COLUMN blink_rate DROP NOT NULL,
    ALTER COLUMN blink_interval_variability DROP NOT NULL,
    ALTER COLUMN gaze_stability DROP NOT NULL,
    ALTER COLUMN reaction_time DROP NOT NULL;

-- Add tracking task features
ALTER TABLE visual_sessions
    ADD COLUMN IF NOT EXISTS tracking_accuracy NUMERIC,
    ADD COLUMN IF NOT EXISTS gaze_movement_features JSONB;

-- Add blink task features
ALTER TABLE visual_sessions
    ADD COLUMN IF NOT EXISTS blink_duration_mean NUMERIC;

-- Add reaction task features
ALTER TABLE visual_sessions
    ADD COLUMN IF NOT EXISTS reaction_time_variability NUMERIC,
    ADD COLUMN IF NOT EXISTS missed_targets INTEGER DEFAULT 0;

-- Update feature_version default to '1.0'
ALTER TABLE visual_sessions
    ALTER COLUMN feature_version SET DEFAULT '1.0';

-- Documentation comments
COMMENT ON TABLE visual_sessions IS 'Ocular/Visual Behavior Module metrics (blink, gaze stability, reaction). NOT retinal imaging.';
COMMENT ON COLUMN visual_sessions.tracking_accuracy IS 'Visual tracking task: normalized target tracking fidelity [0-1].';
COMMENT ON COLUMN visual_sessions.gaze_movement_features IS 'Visual tracking task: JSONB with velocity and smoothness metrics.';
COMMENT ON COLUMN visual_sessions.blink_duration_mean IS 'Blink task: average blink duration in milliseconds.';
COMMENT ON COLUMN visual_sessions.reaction_time_variability IS 'Reaction task: coefficient of variation of reaction times.';
COMMENT ON COLUMN visual_sessions.missed_targets IS 'Reaction task: count of unacknowledged target appearances.';
