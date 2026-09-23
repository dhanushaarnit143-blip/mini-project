-- Migration 012: Create model_versions table
-- Tracks validated model checkpoints and weights for reproducible inference.

CREATE TABLE IF NOT EXISTS model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    feature_schema_version TEXT NOT NULL,
    training_dataset_version TEXT NOT NULL,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_model_versions_name_version UNIQUE (model_name, version)
);

CREATE INDEX IF NOT EXISTS idx_model_versions_active ON model_versions(model_name, active);

COMMENT ON TABLE model_versions IS 'Model version registry for versioned reproducibility. Separate from mobile collection.';
