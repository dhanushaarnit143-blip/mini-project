-- Migration 011: Create mpf_predictions table
-- Audit log of MPF risk-screening model inference outputs.

CREATE TABLE IF NOT EXISTS mpf_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_version TEXT NOT NULL,
    input_feature_version TEXT NOT NULL,
    available_modalities TEXT[] NOT NULL,
    missing_modalities TEXT[] NOT NULL,
    risk_score NUMERIC NOT NULL CHECK (risk_score BETWEEN 0.0 AND 1.0),
    prediction_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mpf_predictions_participant_timestamp ON mpf_predictions(participant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_mpf_predictions_metadata_gin ON mpf_predictions USING gin (prediction_metadata);

COMMENT ON TABLE mpf_predictions IS 'MPF pipeline inference outputs. Research screening result — not a clinical diagnosis.';
