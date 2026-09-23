-- Migration 010: Create daily_deviations table
-- Longitudinal monitoring of feature shifts relative to personal baseline.

CREATE TABLE IF NOT EXISTS daily_deviations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    modality TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    value NUMERIC NOT NULL,
    baseline_value NUMERIC NOT NULL,
    deviation_score NUMERIC NOT NULL, -- normalized z-score or robust deviation
    trend_score NUMERIC NOT NULL,
    quality_score NUMERIC NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
    algorithm_version TEXT NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_deviations_participant_date ON daily_deviations(participant_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_deviations_modality ON daily_deviations(participant_id, modality, date DESC);

COMMENT ON TABLE daily_deviations IS 'Statistical deviation and trend tracking relative to personal baseline.';
