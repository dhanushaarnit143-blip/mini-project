-- Migration 008: Create model_versions table
-- Read-only model registry tracking frozen model weights and feature schemas.
-- Ensures strict reproducibility with zero uncontrolled runtime retraining.

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

CREATE INDEX IF NOT EXISTS idx_model_versions_active ON model_versions(active);

COMMENT ON TABLE model_versions IS 'Read-only frozen model metadata registry.';
