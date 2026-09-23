-- Migration 008: Create daily_features table
-- Standardized daily aggregation of multimodal mobile features.

CREATE TABLE IF NOT EXISTS daily_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    typing_features JSONB,
    voice_features JSONB,
    motor_features JSONB,
    visual_features JSONB,
    sleep_features JSONB,
    data_quality JSONB NOT NULL DEFAULT '{}'::jsonb,
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_daily_features_participant_date UNIQUE (participant_id, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_features_participant_date ON daily_features(participant_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_features_typing_gin ON daily_features USING gin (typing_features);
CREATE INDEX IF NOT EXISTS idx_daily_features_voice_gin ON daily_features USING gin (voice_features);
CREATE INDEX IF NOT EXISTS idx_daily_features_motor_gin ON daily_features USING gin (motor_features);
CREATE INDEX IF NOT EXISTS idx_daily_features_visual_gin ON daily_features USING gin (visual_features);
CREATE INDEX IF NOT EXISTS idx_daily_features_sleep_gin ON daily_features USING gin (sleep_features);

COMMENT ON TABLE daily_features IS 'Daily multimodal feature aggregation vector feeding the MPF Adapter.';
