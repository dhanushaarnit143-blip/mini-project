-- Migration 019: Extend daily_features for Phase 9 Daily Feature Aggregation
-- Daily Multimodal Feature Vector Aggregation
--
-- CRITICAL COMPLIANCE & RESEARCH PROVENANCE:
-- Combines multiple sessions for each modality using robust median (central tendency)
-- and IQR (variability). Missing modalities are never imputed.
-- Excludes sessions with quality_score < 0.50.
--
-- Extends daily_features with:
-- 1. available_modalities TEXT[]: List of valid modalities present in this daily vector
-- 2. missing_modalities TEXT[]: List of modalities missing or failing quality gating
-- 3. disagreement_flag BOOLEAN: Flag indicating inter-session divergence across multiple daily sessions

ALTER TABLE public.daily_features
    ADD COLUMN IF NOT EXISTS available_modalities TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS missing_modalities TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS disagreement_flag BOOLEAN DEFAULT FALSE;

-- Documentation comments
COMMENT ON TABLE public.daily_features IS 'Daily multimodal feature aggregation vector combining all modality sessions (Phase 9). Feeds the MPF Adapter without imputation.';
COMMENT ON COLUMN public.daily_features.available_modalities IS 'Array of modalities with valid sessions (quality >= 0.50) included in the daily vector.';
COMMENT ON COLUMN public.daily_features.missing_modalities IS 'Array of modalities with no sessions or low quality sessions (strictly un-imputed).';
COMMENT ON COLUMN public.daily_features.disagreement_flag IS 'True if multiple sessions recorded on this day exhibited significant divergence (CV > 0.35).';
