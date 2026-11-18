-- Migration 009: Row Level Security (RLS) Policies
-- Enforces complete cross-participant isolation and read-only model versions.

-- ============================================================================
-- 1. ENABLE ROW LEVEL SECURITY ACROSS ALL 12 TABLES
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

CREATE POLICY "Users can view own data" ON participants
    FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own data" ON participants
    FOR INSERT
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own data" ON participants
    FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Users can delete own data" ON participants
    FOR DELETE
    USING (auth.uid() = id);

-- ============================================================================
-- 3. PARTICIPANT-OWNED TABLES POLICIES (auth.uid() = participant_id)
-- ============================================================================

-- Table: consent_records
CREATE POLICY "Users can view own data" ON consent_records
    FOR SELECT
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can insert own data" ON consent_records
    FOR INSERT
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY "Users can update own data" ON consent_records
    FOR UPDATE
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can delete own data" ON consent_records
    FOR DELETE
    USING (auth.uid() = participant_id);

-- Table: typing_sessions
CREATE POLICY "Users can view own data" ON typing_sessions
    FOR SELECT
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can insert own data" ON typing_sessions
    FOR INSERT
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY "Users can update own data" ON typing_sessions
    FOR UPDATE
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can delete own data" ON typing_sessions
    FOR DELETE
    USING (auth.uid() = participant_id);

-- Table: voice_sessions
CREATE POLICY "Users can view own data" ON voice_sessions
    FOR SELECT
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can insert own data" ON voice_sessions
    FOR INSERT
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY "Users can update own data" ON voice_sessions
    FOR UPDATE
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can delete own data" ON voice_sessions
    FOR DELETE
    USING (auth.uid() = participant_id);

-- Table: motor_sessions
CREATE POLICY "Users can view own data" ON motor_sessions
    FOR SELECT
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can insert own data" ON motor_sessions
    FOR INSERT
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY "Users can update own data" ON motor_sessions
    FOR UPDATE
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can delete own data" ON motor_sessions
    FOR DELETE
    USING (auth.uid() = participant_id);

-- Table: visual_sessions
CREATE POLICY "Users can view own data" ON visual_sessions
    FOR SELECT
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can insert own data" ON visual_sessions
    FOR INSERT
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY "Users can update own data" ON visual_sessions
    FOR UPDATE
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can delete own data" ON visual_sessions
    FOR DELETE
    USING (auth.uid() = participant_id);

-- Table: sleep_sessions
CREATE POLICY "Users can view own data" ON sleep_sessions
    FOR SELECT
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can insert own data" ON sleep_sessions
    FOR INSERT
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY "Users can update own data" ON sleep_sessions
    FOR UPDATE
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can delete own data" ON sleep_sessions
    FOR DELETE
    USING (auth.uid() = participant_id);

-- Table: daily_features
CREATE POLICY "Users can view own data" ON daily_features
    FOR SELECT
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can insert own data" ON daily_features
    FOR INSERT
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY "Users can update own data" ON daily_features
    FOR UPDATE
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can delete own data" ON daily_features
    FOR DELETE
    USING (auth.uid() = participant_id);

-- Table: personal_baselines
CREATE POLICY "Users can view own data" ON personal_baselines
    FOR SELECT
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can insert own data" ON personal_baselines
    FOR INSERT
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY "Users can update own data" ON personal_baselines
    FOR UPDATE
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can delete own data" ON personal_baselines
    FOR DELETE
    USING (auth.uid() = participant_id);

-- Table: daily_deviations
CREATE POLICY "Users can view own data" ON daily_deviations
    FOR SELECT
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can insert own data" ON daily_deviations
    FOR INSERT
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY "Users can update own data" ON daily_deviations
    FOR UPDATE
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can delete own data" ON daily_deviations
    FOR DELETE
    USING (auth.uid() = participant_id);

-- Table: mpf_predictions
CREATE POLICY "Users can view own data" ON mpf_predictions
    FOR SELECT
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can insert own data" ON mpf_predictions
    FOR INSERT
    WITH CHECK (auth.uid() = participant_id);

CREATE POLICY "Users can update own data" ON mpf_predictions
    FOR UPDATE
    USING (auth.uid() = participant_id);

CREATE POLICY "Users can delete own data" ON mpf_predictions
    FOR DELETE
    USING (auth.uid() = participant_id);

-- ============================================================================
-- 4. MODEL_VERSIONS POLICY (read-only for authenticated users)
-- ============================================================================

CREATE POLICY "Anyone can read model versions" ON model_versions
    FOR SELECT
    USING (auth.role() = 'authenticated');
