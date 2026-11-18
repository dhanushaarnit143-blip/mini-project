-- Migration 007: Create mpf_predictions table
-- Longitudinal multimodal fusion inference risk screening audit trail.
-- Research prototype only: Zero clinical diagnostic claims.

CREATE TABLE IF NOT EXISTS mpf_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_version TEXT NOT NULL DEFAULT '1.0.0',
    input_feature_version TEXT NOT NULL DEFAULT '1.0.0',
    available_modalities TEXT[] NOT NULL,
    missing_modalities TEXT[] NOT NULL,
    risk_score NUMERIC NOT NULL CHECK (risk_score >= 0.0 AND risk_score <= 1.0),
    prediction_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_predictions_participant ON mpf_predictions(participant_id, timestamp);

COMMENT ON TABLE mpf_predictions IS 'Research screening risk logs. Not a clinical diagnostic device.';
