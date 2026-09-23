-- Migration 020: Extend personal_baselines and daily_deviations for Phase 10
-- Phase 10: Personal Baseline Engine & Outlier-Resistant Longitudinal Calibration
--
-- Adds:
-- 1. personal_baselines:
--    - baseline_status: ('calibrating', 'established', 'adaptive_updated')
--    - q1: 25th percentile (lower quantile)
--    - q3: 75th percentile (upper quantile)
--    - coefficient_of_variation: std / mean
--    - baseline_created_at: timestamp when calibration baseline was first established
--    - baseline_updated_at: timestamp when baseline was last updated
--
-- 2. daily_deviations:
--    - is_outlier: boolean flag for observations > 3 MAD
--    - anomaly_flag: e.g. 'anomalous observation'
--    - mad_distance: absolute distance in MAD units (|x - median| / MAD)

ALTER TABLE public.personal_baselines
    ADD COLUMN IF NOT EXISTS baseline_status TEXT DEFAULT 'calibrating',
    ADD COLUMN IF NOT EXISTS q1 NUMERIC,
    ADD COLUMN IF NOT EXISTS q3 NUMERIC,
    ADD COLUMN IF NOT EXISTS coefficient_of_variation NUMERIC,
    ADD COLUMN IF NOT EXISTS baseline_created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS baseline_updated_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE public.daily_deviations
    ADD COLUMN IF NOT EXISTS is_outlier BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS anomaly_flag TEXT,
    ADD COLUMN IF NOT EXISTS mad_distance NUMERIC;

-- Comments for research provenance
COMMENT ON COLUMN public.personal_baselines.baseline_status IS 'Status of personal baseline calibration: calibrating (days 1-13), established (day 14), or adaptive_updated (day 15+).';
COMMENT ON COLUMN public.personal_baselines.coefficient_of_variation IS 'Normalized measure of dispersion (std / mean) over the 14-day calibration window.';
COMMENT ON COLUMN public.daily_deviations.is_outlier IS 'True if daily observation diverges by > 3 MAD from personal baseline; rejected from adaptive baseline update.';
COMMENT ON COLUMN public.daily_deviations.anomaly_flag IS 'Descriptive flag (e.g. anomalous observation) without diagnostic claims.';
