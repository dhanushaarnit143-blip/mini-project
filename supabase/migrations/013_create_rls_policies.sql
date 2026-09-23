-- Migration 013: Row Level Security (RLS) Policies and Storage Configuration
-- Enforces complete cross-participant isolation, strict participant data ownership,
-- read-only model registry access, and privacy-preserving storage buckets.

-- ============================================================================
-- 1. ENABLE ROW LEVEL SECURITY ACROSS ALL TABLES
-- ============================================================================

ALTER TABLE participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE typing_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE motor_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE visual_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sleep_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_features ENABLE ROW LEVEL SECURITY;
ALTER TABLE personal_baselines ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_deviations ENABLE ROW LEVEL SECURITY;
ALTER TABLE mpf_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_versions ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 2. PARTICIPANTS TABLE POLICIES (auth.uid() = id)
-- ============================================================================

CREATE POLICY participant_select_own_profile ON participants
    FOR SELECT TO authenticated
    USING (auth.uid() = id);

CREATE POLICY participant_insert_own_profile ON participants
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = id);

CREATE POLICY participant_update_own_profile ON participants
    FOR UPDATE TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

CREATE POLICY participant_delete_own_profile ON participants
    FOR DELETE TO authenticated
    USING (auth.uid() = id);

-- ============================================================================
-- 3. CONSENT RECORDS TABLE POLICIES (auth.uid() = participant_id)
-- ============================================================================

CREATE POLICY participant_select_own_consent ON consent_records
    FOR SELECT TO authenticated
    USING (auth.uid() = participant_id);

CREATE POLICY participant_insert_own_consent ON consent_records
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_update_own_consent ON consent_records
    FOR UPDATE TO authenticated
    USING (auth.uid() = participant_id)
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_delete_own_consent ON consent_records
    FOR DELETE TO authenticated
    USING (auth.uid() = participant_id);

-- ============================================================================
-- 4. TYPING SESSIONS POLICIES
-- ============================================================================

CREATE POLICY participant_select_own_typing ON typing_sessions
    FOR SELECT TO authenticated
    USING (auth.uid() = participant_id);

CREATE POLICY participant_insert_own_typing ON typing_sessions
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_update_own_typing ON typing_sessions
    FOR UPDATE TO authenticated
    USING (auth.uid() = participant_id)
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_delete_own_typing ON typing_sessions
    FOR DELETE TO authenticated
    USING (auth.uid() = participant_id);

-- ============================================================================
-- 5. VOICE SESSIONS POLICIES
-- ============================================================================

CREATE POLICY participant_select_own_voice ON voice_sessions
    FOR SELECT TO authenticated
    USING (auth.uid() = participant_id);

CREATE POLICY participant_insert_own_voice ON voice_sessions
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_update_own_voice ON voice_sessions
    FOR UPDATE TO authenticated
    USING (auth.uid() = participant_id)
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_delete_own_voice ON voice_sessions
    FOR DELETE TO authenticated
    USING (auth.uid() = participant_id);

-- ============================================================================
-- 6. MOTOR SESSIONS POLICIES
-- ============================================================================

CREATE POLICY participant_select_own_motor ON motor_sessions
    FOR SELECT TO authenticated
    USING (auth.uid() = participant_id);

CREATE POLICY participant_insert_own_motor ON motor_sessions
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_update_own_motor ON motor_sessions
    FOR UPDATE TO authenticated
    USING (auth.uid() = participant_id)
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_delete_own_motor ON motor_sessions
    FOR DELETE TO authenticated
    USING (auth.uid() = participant_id);

-- ============================================================================
-- 7. VISUAL SESSIONS POLICIES (Ocular/Visual Behavior Module)
-- ============================================================================

CREATE POLICY participant_select_own_visual ON visual_sessions
    FOR SELECT TO authenticated
    USING (auth.uid() = participant_id);

CREATE POLICY participant_insert_own_visual ON visual_sessions
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_update_own_visual ON visual_sessions
    FOR UPDATE TO authenticated
    USING (auth.uid() = participant_id)
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_delete_own_visual ON visual_sessions
    FOR DELETE TO authenticated
    USING (auth.uid() = participant_id);

-- ============================================================================
-- 8. SLEEP SESSIONS POLICIES
-- ============================================================================

CREATE POLICY participant_select_own_sleep ON sleep_sessions
    FOR SELECT TO authenticated
    USING (auth.uid() = participant_id);

CREATE POLICY participant_insert_own_sleep ON sleep_sessions
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_update_own_sleep ON sleep_sessions
    FOR UPDATE TO authenticated
    USING (auth.uid() = participant_id)
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_delete_own_sleep ON sleep_sessions
    FOR DELETE TO authenticated
    USING (auth.uid() = participant_id);

-- ============================================================================
-- 9. DAILY FEATURES POLICIES
-- ============================================================================

CREATE POLICY participant_select_own_daily_features ON daily_features
    FOR SELECT TO authenticated
    USING (auth.uid() = participant_id);

CREATE POLICY participant_insert_own_daily_features ON daily_features
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_update_own_daily_features ON daily_features
    FOR UPDATE TO authenticated
    USING (auth.uid() = participant_id)
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_delete_own_daily_features ON daily_features
    FOR DELETE TO authenticated
    USING (auth.uid() = participant_id);

-- ============================================================================
-- 10. PERSONAL BASELINES POLICIES
-- ============================================================================

CREATE POLICY participant_select_own_baselines ON personal_baselines
    FOR SELECT TO authenticated
    USING (auth.uid() = participant_id);

CREATE POLICY participant_insert_own_baselines ON personal_baselines
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_update_own_baselines ON personal_baselines
    FOR UPDATE TO authenticated
    USING (auth.uid() = participant_id)
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_delete_own_baselines ON personal_baselines
    FOR DELETE TO authenticated
    USING (auth.uid() = participant_id);

-- ============================================================================
-- 11. DAILY DEVIATIONS POLICIES
-- ============================================================================

CREATE POLICY participant_select_own_deviations ON daily_deviations
    FOR SELECT TO authenticated
    USING (auth.uid() = participant_id);

CREATE POLICY participant_insert_own_deviations ON daily_deviations
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_update_own_deviations ON daily_deviations
    FOR UPDATE TO authenticated
    USING (auth.uid() = participant_id)
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_delete_own_deviations ON daily_deviations
    FOR DELETE TO authenticated
    USING (auth.uid() = participant_id);

-- ============================================================================
-- 12. MPF PREDICTIONS POLICIES
-- ============================================================================

CREATE POLICY participant_select_own_predictions ON mpf_predictions
    FOR SELECT TO authenticated
    USING (auth.uid() = participant_id);

-- Insert/Update/Delete for predictions typically executed by backend service-role,
-- but if client writes offline inference result:
CREATE POLICY participant_insert_own_predictions ON mpf_predictions
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_update_own_predictions ON mpf_predictions
    FOR UPDATE TO authenticated
    USING (auth.uid() = participant_id)
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY participant_delete_own_predictions ON mpf_predictions
    FOR DELETE TO authenticated
    USING (auth.uid() = participant_id);

-- ============================================================================
-- 13. MODEL VERSIONS POLICIES (Read-Only for Authenticated Participants)
-- ============================================================================

CREATE POLICY participant_select_model_versions ON model_versions
    FOR SELECT TO authenticated
    USING (true);

-- No INSERT, UPDATE, or DELETE policies created for authenticated participants.
-- Only the service_role key (which bypasses RLS) can register or modify model versions.

-- ============================================================================
-- 14. SUPABASE STORAGE BUCKETS CONFIGURATION & POLICIES
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'storage' AND table_name = 'buckets') THEN
        -- Consent Documents bucket (Private, participant-scoped)
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES ('consent-documents', 'consent-documents', false, 10485760, ARRAY['application/pdf', 'image/png', 'image/jpeg'])
        ON CONFLICT (id) DO NOTHING;

        -- Research Exports bucket (Private, service-role only)
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES ('research-exports', 'research-exports', false, 524288000, ARRAY['application/json', 'application/parquet', 'text/csv'])
        ON CONFLICT (id) DO NOTHING;
    END IF;
END$$;

-- Storage object policies for consent documents (scoped to participant folder: {participant_id}/*)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'storage' AND table_name = 'objects') THEN
        DROP POLICY IF EXISTS participant_access_own_consent_documents ON storage.objects;
        CREATE POLICY participant_access_own_consent_documents ON storage.objects
            FOR ALL TO authenticated
            USING (bucket_id = 'consent-documents' AND (storage.foldername(name))[1] = auth.uid()::text)
            WITH CHECK (bucket_id = 'consent-documents' AND (storage.foldername(name))[1] = auth.uid()::text);

        -- Note: No policies exist on 'research-exports' for role authenticated or anon.
        -- Only service-role key can read/write to 'research-exports'.
    END IF;
END$$;
