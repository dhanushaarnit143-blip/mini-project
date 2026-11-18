-- Migration 004: Create daily_features table
-- Standardized multimodal daily aggregations combining sessions into daily feature vectors.

CREATE TABLE IF NOT EXISTS daily_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    typing_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    voice_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    motor_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    visual_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    sleep_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    data_quality JSONB NOT NULL DEFAULT '{}'::jsonb,
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_daily_features_participant_date UNIQUE (participant_id, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_features_participant ON daily_features(participant_id, date);

COMMENT ON TABLE daily_features IS 'Aggregated daily multimodal digital biomarkers.';
