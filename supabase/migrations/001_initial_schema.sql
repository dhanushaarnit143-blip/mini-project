-- ============================================================================
-- MPF-PD & Mobile Extension: Complete Consolidated PostgreSQL Schema
-- Migration: 001_initial_schema.sql
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. PROFILES TABLE (Linked to auth.users)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    email TEXT,
    avatar_url TEXT,
    role TEXT NOT NULL DEFAULT 'researcher',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);

-- Automatic trigger to create profile upon user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, email, role)
    VALUES (
        new.id,
        COALESCE(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
        new.email,
        'researcher'
    )
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        updated_at = NOW();
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================================
-- 2. COHORT PARTICIPANTS TABLE (Research Cohort Repository)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.cohort_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    cohort_code TEXT NOT NULL UNIQUE,
    visit_label TEXT NOT NULL DEFAULT 'Visit 1',
    clinical_notes TEXT,
    risk_index NUMERIC CHECK (risk_index BETWEEN 0.0 AND 1.0),
    risk_class TEXT CHECK (risk_class IN ('Low Risk Pattern', 'Intermediate', 'Elevated Pattern')),
    avatar_color TEXT DEFAULT 'emerald',
    demographics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cohort_participants_code ON public.cohort_participants(cohort_code);
CREATE INDEX IF NOT EXISTS idx_cohort_participants_user ON public.cohort_participants(user_id);
CREATE INDEX IF NOT EXISTS idx_cohort_participants_risk ON public.cohort_participants(risk_index DESC);

-- ============================================================================
-- 3. ASSESSMENTS TABLE (Multimodal Clinical & Digital Data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    participant_id UUID REFERENCES public.cohort_participants(id) ON DELETE CASCADE,
    cohort_id TEXT NOT NULL,
    age NUMERIC NOT NULL CHECK (age BETWEEN 18.0 AND 120.0),
    biological_sex TEXT NOT NULL CHECK (biological_sex IN ('male', 'female', 'other', 'Male', 'Female')),
    family_history BOOLEAN DEFAULT FALSE,
    olfactory_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    sleep_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    voice_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    motor_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    retinal_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'analyzed', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assessments_user ON public.assessments(user_id);
CREATE INDEX IF NOT EXISTS idx_assessments_cohort ON public.assessments(cohort_id);
CREATE INDEX IF NOT EXISTS idx_assessments_participant ON public.assessments(participant_id);

-- ============================================================================
-- 4. FUSION RESULTS TABLE (Multimodal Inference Audit & Explanations)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.fusion_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID REFERENCES public.assessments(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    risk_score NUMERIC NOT NULL CHECK (risk_score BETWEEN 0.0 AND 1.0),
    risk_category TEXT NOT NULL,
    radar_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    modality_contributions JSONB NOT NULL DEFAULT '{}'::jsonb,
    shap_explanations JSONB NOT NULL DEFAULT '{}'::jsonb,
    gate_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
    missing_modalities TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fusion_results_assessment ON public.fusion_results(assessment_id);
CREATE INDEX IF NOT EXISTS idx_fusion_results_user ON public.fusion_results(user_id);

-- ============================================================================
-- 5. MOBILE MODALITY SESSIONS & LONGITUDINAL MONITORING TABLES
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'baseline_status_enum') THEN
        CREATE TYPE baseline_status_enum AS ENUM ('collecting', 'established', 'adaptive');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS public.participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consent_version TEXT NOT NULL DEFAULT '1.0.0',
    consent_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    app_version TEXT NOT NULL DEFAULT '1.0.0',
    model_version TEXT NOT NULL DEFAULT '1.0.0',
    baseline_status baseline_status_enum NOT NULL DEFAULT 'collecting',
    pseudonymous_id TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS public.consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL CHECK (consent_type IN ('data_collection', 'audio_storage', 'research_export', 'deletion')),
    consent_version TEXT NOT NULL,
    granted BOOLEAN NOT NULL DEFAULT TRUE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS public.typing_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_type TEXT NOT NULL CHECK (task_type IN ('controlled_phrase', 'free_typing')),
    duration NUMERIC NOT NULL CHECK (duration >= 0),
    typing_speed NUMERIC NOT NULL CHECK (typing_speed >= 0),
    mean_inter_key_interval NUMERIC NOT NULL CHECK (mean_inter_key_interval >= 0),
    std_inter_key_interval NUMERIC NOT NULL CHECK (std_inter_key_interval >= 0),
    pause_rate NUMERIC NOT NULL CHECK (pause_rate >= 0),
    correction_rate NUMERIC NOT NULL CHECK (correction_rate >= 0),
    rhythm_variability NUMERIC NOT NULL CHECK (rhythm_variability >= 0),
    quality_score NUMERIC NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public.voice_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_type TEXT NOT NULL CHECK (task_type IN ('sustained_vowel', 'read_sentence', 'free_speech')),
    duration NUMERIC NOT NULL CHECK (duration >= 0),
    signal_quality NUMERIC NOT NULL CHECK (signal_quality BETWEEN 0.0 AND 1.0),
    jitter NUMERIC NOT NULL,
    shimmer NUMERIC NOT NULL,
    hnr NUMERIC NOT NULL,
    pitch_mean NUMERIC NOT NULL,
    pitch_std NUMERIC NOT NULL,
    mfcc_features JSONB NOT NULL,
    spectral_features JSONB NOT NULL,
    quality_score NUMERIC NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public.motor_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_type TEXT NOT NULL CHECK (task_type IN ('walking', 'tapping', 'tremor_hold', 'spiral')),
    duration NUMERIC NOT NULL CHECK (duration >= 0),
    cadence NUMERIC,
    stride_variability NUMERIC,
    movement_variability NUMERIC NOT NULL,
    tapping_rate NUMERIC,
    tapping_interval_variability NUMERIC,
    tremor_frequency NUMERIC,
    tremor_amplitude NUMERIC,
    quality_score NUMERIC NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public.visual_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_type TEXT NOT NULL CHECK (task_type IN ('tracking', 'blink', 'reaction')),
    duration NUMERIC NOT NULL CHECK (duration >= 0),
    blink_rate NUMERIC NOT NULL,
    blink_interval_variability NUMERIC NOT NULL,
    gaze_stability NUMERIC NOT NULL CHECK (gaze_stability BETWEEN 0.0 AND 1.0),
    reaction_time NUMERIC NOT NULL,
    quality_score NUMERIC NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public.sleep_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sleep_duration NUMERIC NOT NULL CHECK (sleep_duration BETWEEN 0.0 AND 24.0),
    sleep_quality NUMERIC NOT NULL CHECK (sleep_quality BETWEEN 1.0 AND 5.0),
    unusual_movement_self_report BOOLEAN NOT NULL,
    daytime_sleepiness NUMERIC NOT NULL CHECK (daytime_sleepiness BETWEEN 1.0 AND 5.0),
    questionnaire_version TEXT NOT NULL DEFAULT '1.0.0',
    score NUMERIC NOT NULL,
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public.daily_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    typing_features JSONB,
    voice_features JSONB,
    motor_features JSONB,
    visual_features JSONB,
    sleep_features JSONB,
    data_quality JSONB NOT NULL DEFAULT '{}'::jsonb,
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_daily_features_participant_date UNIQUE (participant_id, date)
);

CREATE TABLE IF NOT EXISTS public.personal_baselines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
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

CREATE TABLE IF NOT EXISTS public.daily_deviations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    modality TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    value NUMERIC NOT NULL,
    baseline_value NUMERIC NOT NULL,
    deviation_score NUMERIC NOT NULL,
    trend_score NUMERIC NOT NULL,
    quality_score NUMERIC NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
    algorithm_version TEXT NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.mpf_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_version TEXT NOT NULL,
    input_feature_version TEXT NOT NULL,
    available_modalities TEXT[] NOT NULL,
    missing_modalities TEXT[] NOT NULL,
    risk_score NUMERIC NOT NULL CHECK (risk_score BETWEEN 0.0 AND 1.0),
    prediction_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.model_versions (
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

-- ============================================================================
-- 6. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cohort_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fusion_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.typing_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.voice_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.motor_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visual_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sleep_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_features ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.personal_baselines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_deviations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mpf_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_versions ENABLE ROW LEVEL SECURITY;

-- Profiles: Authenticated users can view profiles, update own profile
CREATE POLICY profiles_select_all ON public.profiles FOR SELECT TO authenticated USING (true);
CREATE POLICY profiles_update_own ON public.profiles FOR UPDATE TO authenticated USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

-- Cohort Participants: Authenticated researchers can view cohort, and manage their records
CREATE POLICY cohort_select_all ON public.cohort_participants FOR SELECT TO authenticated USING (true);
CREATE POLICY cohort_insert_auth ON public.cohort_participants FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
CREATE POLICY cohort_update_auth ON public.cohort_participants FOR UPDATE TO authenticated USING (auth.uid() = user_id OR user_id IS NULL);
CREATE POLICY cohort_delete_auth ON public.cohort_participants FOR DELETE TO authenticated USING (auth.uid() = user_id OR user_id IS NULL);

-- Assessments: Isolated per researcher user
CREATE POLICY assessments_select_own ON public.assessments FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY assessments_insert_own ON public.assessments FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY assessments_update_own ON public.assessments FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY assessments_delete_own ON public.assessments FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- Fusion Results: Isolated per researcher user
CREATE POLICY fusion_results_select_own ON public.fusion_results FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY fusion_results_insert_own ON public.fusion_results FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY fusion_results_update_own ON public.fusion_results FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY fusion_results_delete_own ON public.fusion_results FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- Mobile sessions: Participant self access
CREATE POLICY participant_select_profile ON public.participants FOR SELECT TO authenticated USING (auth.uid() = id);
CREATE POLICY participant_insert_profile ON public.participants FOR INSERT TO authenticated WITH CHECK (auth.uid() = id);
CREATE POLICY participant_update_profile ON public.participants FOR UPDATE TO authenticated USING (auth.uid() = id);
CREATE POLICY participant_delete_profile ON public.participants FOR DELETE TO authenticated USING (auth.uid() = id);

CREATE POLICY consent_select_own ON public.consent_records FOR SELECT TO authenticated USING (auth.uid() = participant_id);
CREATE POLICY consent_insert_own ON public.consent_records FOR INSERT TO authenticated WITH CHECK (auth.uid() = participant_id);

CREATE POLICY typing_select_own ON public.typing_sessions FOR SELECT TO authenticated USING (auth.uid() = participant_id);
CREATE POLICY typing_insert_own ON public.typing_sessions FOR INSERT TO authenticated WITH CHECK (auth.uid() = participant_id);

CREATE POLICY voice_select_own ON public.voice_sessions FOR SELECT TO authenticated USING (auth.uid() = participant_id);
CREATE POLICY voice_insert_own ON public.voice_sessions FOR INSERT TO authenticated WITH CHECK (auth.uid() = participant_id);

CREATE POLICY motor_select_own ON public.motor_sessions FOR SELECT TO authenticated USING (auth.uid() = participant_id);
CREATE POLICY motor_insert_own ON public.motor_sessions FOR INSERT TO authenticated WITH CHECK (auth.uid() = participant_id);

CREATE POLICY visual_select_own ON public.visual_sessions FOR SELECT TO authenticated USING (auth.uid() = participant_id);
CREATE POLICY visual_insert_own ON public.visual_sessions FOR INSERT TO authenticated WITH CHECK (auth.uid() = participant_id);

CREATE POLICY sleep_select_own ON public.sleep_sessions FOR SELECT TO authenticated USING (auth.uid() = participant_id);
CREATE POLICY sleep_insert_own ON public.sleep_sessions FOR INSERT TO authenticated WITH CHECK (auth.uid() = participant_id);

CREATE POLICY daily_features_select_own ON public.daily_features FOR SELECT TO authenticated USING (auth.uid() = participant_id);
CREATE POLICY daily_features_insert_own ON public.daily_features FOR INSERT TO authenticated WITH CHECK (auth.uid() = participant_id);

CREATE POLICY baselines_select_own ON public.personal_baselines FOR SELECT TO authenticated USING (auth.uid() = participant_id);
CREATE POLICY baselines_insert_own ON public.personal_baselines FOR INSERT TO authenticated WITH CHECK (auth.uid() = participant_id);

CREATE POLICY deviations_select_own ON public.daily_deviations FOR SELECT TO authenticated USING (auth.uid() = participant_id);
CREATE POLICY deviations_insert_own ON public.daily_deviations FOR INSERT TO authenticated WITH CHECK (auth.uid() = participant_id);

CREATE POLICY predictions_select_own ON public.mpf_predictions FOR SELECT TO authenticated USING (auth.uid() = participant_id);
CREATE POLICY predictions_insert_own ON public.mpf_predictions FOR INSERT TO authenticated WITH CHECK (auth.uid() = participant_id);

-- Model versions: Read-only for authenticated participants/researchers
CREATE POLICY model_versions_select_all ON public.model_versions FOR SELECT TO authenticated USING (true);

-- ============================================================================
-- 7. STORAGE BUCKETS & STORAGE POLICIES
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'storage' AND table_name = 'buckets') THEN
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES 
            ('profiles', 'profiles', true, 5242880, ARRAY['image/png', 'image/jpeg', 'image/webp']),
            ('uploads', 'uploads', false, 104857600, ARRAY['audio/wav', 'audio/mpeg', 'text/csv', 'image/jpeg', 'image/png', 'application/json']),
            ('consent-documents', 'consent-documents', false, 10485760, ARRAY['application/pdf', 'image/png', 'image/jpeg']),
            ('research-exports', 'research-exports', false, 524288000, ARRAY['application/json', 'application/parquet', 'text/csv'])
        ON CONFLICT (id) DO NOTHING;
    END IF;
END$$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'storage' AND table_name = 'objects') THEN
        DROP POLICY IF EXISTS storage_profiles_public_read ON storage.objects;
        CREATE POLICY storage_profiles_public_read ON storage.objects
            FOR SELECT USING (bucket_id = 'profiles');

        DROP POLICY IF EXISTS storage_profiles_user_manage ON storage.objects;
        CREATE POLICY storage_profiles_user_manage ON storage.objects
            FOR ALL TO authenticated
            USING (bucket_id = 'profiles' AND (storage.foldername(name))[1] = auth.uid()::text)
            WITH CHECK (bucket_id = 'profiles' AND (storage.foldername(name))[1] = auth.uid()::text);

        DROP POLICY IF EXISTS storage_uploads_user_manage ON storage.objects;
        CREATE POLICY storage_uploads_user_manage ON storage.objects
            FOR ALL TO authenticated
            USING (bucket_id = 'uploads' AND (storage.foldername(name))[1] = auth.uid()::text)
            WITH CHECK (bucket_id = 'uploads' AND (storage.foldername(name))[1] = auth.uid()::text);

        DROP POLICY IF EXISTS storage_consent_user_manage ON storage.objects;
        CREATE POLICY storage_consent_user_manage ON storage.objects
            FOR ALL TO authenticated
            USING (bucket_id = 'consent-documents' AND (storage.foldername(name))[1] = auth.uid()::text)
            WITH CHECK (bucket_id = 'consent-documents' AND (storage.foldername(name))[1] = auth.uid()::text);
    END IF;
END$$;
