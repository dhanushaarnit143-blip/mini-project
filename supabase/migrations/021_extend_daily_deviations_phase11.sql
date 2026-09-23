-- Migration 021: Extend daily_deviations for Phase 11
-- Phase 11: Longitudinal Deviation and Trend Engine
--
-- Adds:
-- 1. Rolling 7-day and 14-day longitudinal trend metrics:
--    - seven_day_average: Rolling 7-day mean of quality-vetted daily measurements
--    - seven_day_variability: Rolling 7-day sample standard deviation
--    - fourteen_day_trend: Linear regression slope over 14 calendar days
--    - sustained_deviation_count: Number of consecutive days with |z| > 2.0
--    - missingness_ratio: Proportion of days without valid measurements in 14-day window
--    - seven_day_quality: Rolling average data quality score over the last 7 days
--    - deviation_classification: Non-diagnostic classification label (e.g. "Within personal baseline")
--    - trend_classification: Non-diagnostic trend label (e.g. "Progressive deviation from personal baseline")

ALTER TABLE public.daily_deviations
    ADD COLUMN IF NOT EXISTS seven_day_average NUMERIC,
    ADD COLUMN IF NOT EXISTS seven_day_variability NUMERIC,
    ADD COLUMN IF NOT EXISTS fourteen_day_trend NUMERIC,
    ADD COLUMN IF NOT EXISTS sustained_deviation_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS missingness_ratio NUMERIC,
    ADD COLUMN IF NOT EXISTS seven_day_quality NUMERIC,
    ADD COLUMN IF NOT EXISTS deviation_classification TEXT,
    ADD COLUMN IF NOT EXISTS trend_classification TEXT;

-- Descriptive comments confirming research provenance and non-diagnostic framing
COMMENT ON COLUMN public.daily_deviations.seven_day_average IS 'Rolling 7-day mean of valid daily feature values.';
COMMENT ON COLUMN public.daily_deviations.seven_day_variability IS 'Rolling 7-day sample standard deviation reflecting personal temporal variance.';
COMMENT ON COLUMN public.daily_deviations.fourteen_day_trend IS 'Linear regression slope over 14 days representing trajectory direction and rate.';
COMMENT ON COLUMN public.daily_deviations.sustained_deviation_count IS 'Count of consecutive calendar days with |z_score| > 2.0.';
COMMENT ON COLUMN public.daily_deviations.missingness_ratio IS 'Proportion of missing daily observations in the 14-day evaluation window.';
COMMENT ON COLUMN public.daily_deviations.seven_day_quality IS 'Mean observation quality score over the preceding 7-day window.';
COMMENT ON COLUMN public.daily_deviations.deviation_classification IS 'Safe research classification of deviation magnitude relative to personal baseline.';
COMMENT ON COLUMN public.daily_deviations.trend_classification IS 'Safe research classification of 14-day trajectory relative to personal baseline.';
