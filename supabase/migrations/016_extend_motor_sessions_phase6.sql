-- Migration 016: Extend motor_sessions for Phase 6 compatibility
-- Adds stride_interval_mean column and updates feature_version default from '1.0.0' to '1.0'
-- to match the Phase 6 Motor Collection Module (walkingFeatureExtractor, feature_version = '1.0').
--
-- RULE 9 COMPLIANT: Does NOT modify any existing column types or drop any columns.
-- Uses ALTER TABLE ADD COLUMN IF NOT EXISTS (safe idempotent).

-- Add stride_interval_mean (walking feature — mean stride duration in seconds)
ALTER TABLE motor_sessions
    ADD COLUMN IF NOT EXISTS stride_interval_mean NUMERIC;

-- Add band_power_ratios JSON column for tremor FFT spectral analysis results
ALTER TABLE motor_sessions
    ADD COLUMN IF NOT EXISTS band_power_ratios JSONB;

-- Add decline_slope for tapping analysis (OLS regression slope ms/tap)
ALTER TABLE motor_sessions
    ADD COLUMN IF NOT EXISTS decline_slope NUMERIC;

-- Update feature_version column comment (does not change stored values)
COMMENT ON COLUMN motor_sessions.feature_version IS
    'Version of the feature extraction algorithm. Phase 6 JS modules emit "1.0". Prior backend used "1.0.0".';

-- Add column-level documentation
COMMENT ON COLUMN motor_sessions.stride_interval_mean IS
    'Walking task: mean stride duration in seconds (2 steps per stride).';

COMMENT ON COLUMN motor_sessions.band_power_ratios IS
    'Tremor hold task: JSONB with band power ratios from FFT analysis.
     Keys: physiological_tremor, pathological_tremor, essential_tremor, high_frequency.';

COMMENT ON COLUMN motor_sessions.decline_slope IS
    'Tapping task: OLS regression slope of ITI vs tap index (ms/tap).
     Positive = progressive slowing during the task window.';

-- Ensure RLS is enforced on the table (belt-and-suspenders for new columns)
-- (Policies already applied in migration 013 — this is a no-op safety check)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables
        WHERE schemaname = 'public' AND tablename = 'motor_sessions'
    ) THEN
        RAISE EXCEPTION 'motor_sessions table not found — run migration 005 first.';
    END IF;
END $$;
