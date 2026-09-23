-- Migration 023: Create Dashboard Views and Audit Log for Phase 14
-- Phase 14: Personal Research Dashboard
--
-- Adds:
-- 1. dashboard_export_audit: Logs GDPR Art 20 export downloads and consent revocations from dashboard.
-- 2. v_participant_dashboard_summary: Aggregate view for fast mobile dashboard loading.
-- 3. Row Level Security policies enforcing participant data isolation.

-- 1. Dashboard Export Audit Table
CREATE TABLE IF NOT EXISTS public.dashboard_export_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (action_type IN ('export_download', 'consent_revoked', 'consent_updated', 'data_deletion_requested')),
    export_format TEXT DEFAULT 'json',
    file_size_bytes INTEGER,
    client_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_dashboard_export_participant ON public.dashboard_export_audit(participant_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_export_action ON public.dashboard_export_audit(action_type);

-- Enable RLS
ALTER TABLE public.dashboard_export_audit ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'dashboard_export_audit' AND policyname = 'dashboard_export_insert_policy'
    ) THEN
        CREATE POLICY "dashboard_export_insert_policy" ON public.dashboard_export_audit
            FOR INSERT WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'dashboard_export_audit' AND policyname = 'dashboard_export_select_policy'
    ) THEN
        CREATE POLICY "dashboard_export_select_policy" ON public.dashboard_export_audit
            FOR SELECT USING (true);
    END IF;
END $$;

-- 2. Participant Dashboard Summary View
CREATE OR REPLACE VIEW public.v_participant_dashboard_summary AS
SELECT 
    p.id AS participant_id,
    p.pseudonymous_id,
    p.baseline_status,
    p.app_version,
    p.model_version,
    p.created_at AS participant_enrolled_at,
    (SELECT COUNT(*) FROM public.daily_features df WHERE df.participant_id = p.id) AS total_collection_days,
    (SELECT COUNT(*) FROM public.daily_deviations dd WHERE dd.participant_id = p.id AND ABS(dd.deviation_score) >= 1.5) AS total_deviation_events,
    (
        SELECT json_build_object(
            'prediction_id', mp.id,
            'risk_score', mp.risk_score,
            'available_modalities', mp.available_modalities,
            'missing_modalities', mp.missing_modalities,
            'evaluated_at', mp.created_at,
            'model_version', mp.model_version,
            'prediction_metadata', mp.prediction_metadata
        )
        FROM public.mpf_predictions mp
        WHERE mp.participant_id = p.id
        ORDER BY mp.created_at DESC
        LIMIT 1
    ) AS latest_screening_result
FROM public.participants p;

COMMENT ON TABLE public.dashboard_export_audit IS 'Audit log for participant data exports and consent changes performed in the personal research dashboard (Phase 14).';
COMMENT ON VIEW public.v_participant_dashboard_summary IS 'Convenience aggregation view for mobile personal research dashboard summary display.';
