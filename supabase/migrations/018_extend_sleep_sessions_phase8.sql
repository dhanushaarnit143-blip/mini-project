-- Migration 018: Extend sleep_sessions for Phase 8 compatibility
-- Sleep/RBD Questionnaire Module
--
-- CRITICAL RESEARCH & NON-DIAGNOSTIC COMPLIANCE:
-- This table captures self-reported subjective sleep behavior and probable RBD survey responses.
-- It is NOT equivalent to polysomnography-confirmed RBD, video-confirmed dream enactment,
-- or a clinical diagnosis. Output labels must strictly reflect self-report provenance.
--
-- Extends sleep_sessions with:
-- 1. medication_change: nullable boolean indicating if medication changed this week
-- 2. medication_change_details: optional text describing the changes
-- 3. movement_response: string capturing exact choice ('yes', 'no', 'not_sure', 'dont_know')
-- 4. rbd_flag_label: non-diagnostic evaluation flag based on multi-day self-reports

ALTER TABLE public.sleep_sessions
    ADD COLUMN IF NOT EXISTS medication_change BOOLEAN,
    ADD COLUMN IF NOT EXISTS medication_change_details TEXT,
    ADD COLUMN IF NOT EXISTS movement_response TEXT,
    ADD COLUMN IF NOT EXISTS rbd_flag_label TEXT DEFAULT 'No pattern detected';

-- Update questionnaire_version default to '1.0'
ALTER TABLE public.sleep_sessions
    ALTER COLUMN questionnaire_version SET DEFAULT '1.0';

-- Documentation comments
COMMENT ON TABLE public.sleep_sessions IS 'Self-reported sleep behavior and probable RBD questionnaire survey data. NOT clinical diagnosis or polysomnography.';
COMMENT ON COLUMN public.sleep_sessions.medication_change IS 'Optional weekly indicator: whether any participant medication changed recently.';
COMMENT ON COLUMN public.sleep_sessions.medication_change_details IS 'Optional free-text details accompanying a self-reported medication change.';
COMMENT ON COLUMN public.sleep_sessions.movement_response IS 'Exact response choice for Q3 dream enactment survey (yes, no, not_sure, dont_know).';
COMMENT ON COLUMN public.sleep_sessions.rbd_flag_label IS 'Non-diagnostic research label: e.g. Self-reported sleep movement pattern noted or No pattern detected.';
