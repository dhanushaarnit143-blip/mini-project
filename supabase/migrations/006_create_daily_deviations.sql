-- Migration 006: Create daily_deviations table
-- Statistical deviations of daily features relative to established personal baselines.

CREATE TABLE IF NOT EXISTS daily_deviations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    modality TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    value NUMERIC NOT NULL,
    baseline_value NUMERIC NOT NULL,
    deviation_score NUMERIC NOT NULL,
    trend_score NUMERIC NOT NULL DEFAULT 0.0,
    quality_score NUMERIC NOT NULL CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    algorithm_version TEXT NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deviations_participant ON daily_deviations(participant_id, date);

COMMENT ON TABLE daily_deviations IS 'Statistical deviation vectors computed against calibrated personal baselines.';
