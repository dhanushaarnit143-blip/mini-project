-- Migration 009: Create personal_baselines table
-- Stores individual 14-day calibration baselines and rolling baseline models.

CREATE TABLE IF NOT EXISTS personal_baselines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    modality TEXT NOT NULL CHECK (modality IN ('typing', 'voice', 'motor', 'visual', 'sleep')),
    feature_name TEXT NOT NULL,
    baseline_mean NUMERIC NOT NULL,
    baseline_median NUMERIC NOT NULL,
    baseline_std NUMERIC NOT NULL,
    baseline_mad NUMERIC NOT NULL,
    lower_bound NUMERIC NOT NULL,
    upper_bound NUMERIC NOT NULL,
    sample_count INTEGER NOT NULL CHECK (sample_count >= 1),
    baseline_start_date DATE NOT NULL,
    baseline_end_date DATE NOT NULL,
    baseline_version TEXT NOT NULL DEFAULT '1.0.0',
    algorithm_version TEXT NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_personal_baselines_participant_modality ON personal_baselines(participant_id, modality, feature_name);
CREATE INDEX IF NOT EXISTS idx_personal_baselines_dates ON personal_baselines(participant_id, baseline_start_date, baseline_end_date);

COMMENT ON TABLE personal_baselines IS 'Participant personal normative baselines computed from 14-day calibration period.';
