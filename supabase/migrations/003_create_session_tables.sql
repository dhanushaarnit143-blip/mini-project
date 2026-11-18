-- Migration 003: Create session tables
-- High-frequency multimodal active and passive session timing dynamics.
-- Zero PII: No raw audio, video frames, or keystroke text stored.

-- 1. Typing Sessions Table
CREATE TABLE IF NOT EXISTS typing_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_type TEXT NOT NULL,
    duration NUMERIC NOT NULL CHECK (duration >= 0),
    typing_speed NUMERIC NOT NULL CHECK (typing_speed >= 0),
    mean_inter_key_interval NUMERIC NOT NULL CHECK (mean_inter_key_interval >= 0),
    std_inter_key_interval NUMERIC NOT NULL CHECK (std_inter_key_interval >= 0),
    pause_rate NUMERIC NOT NULL CHECK (pause_rate >= 0),
    correction_rate NUMERIC NOT NULL CHECK (correction_rate >= 0),
    rhythm_variability NUMERIC NOT NULL CHECK (rhythm_variability >= 0),
    quality_score NUMERIC NOT NULL CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_typing_participant ON typing_sessions(participant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_typing_sessions_session_id ON typing_sessions(session_id);

-- 2. Voice Sessions Table
CREATE TABLE IF NOT EXISTS voice_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_type TEXT NOT NULL,
    duration NUMERIC NOT NULL CHECK (duration >= 0),
    signal_quality NUMERIC NOT NULL,
    jitter NUMERIC NOT NULL CHECK (jitter >= 0),
    shimmer NUMERIC NOT NULL CHECK (shimmer >= 0),
    hnr NUMERIC NOT NULL,
    pitch_mean NUMERIC NOT NULL,
    pitch_std NUMERIC NOT NULL,
    mfcc_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    quality_score NUMERIC NOT NULL CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_voice_participant ON voice_sessions(participant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_session_id ON voice_sessions(session_id);

-- 3. Motor Sessions Table
CREATE TABLE IF NOT EXISTS motor_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_type TEXT NOT NULL CHECK (task_type IN ('walking', 'tapping', 'tremor_hold')),
    duration NUMERIC NOT NULL CHECK (duration >= 0),
    cadence NUMERIC,
    stride_variability NUMERIC,
    tapping_rate NUMERIC,
    tapping_interval_variability NUMERIC,
    tremor_frequency NUMERIC,
    tremor_amplitude NUMERIC,
    quality_score NUMERIC NOT NULL CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_motor_participant ON motor_sessions(participant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_motor_sessions_session_id ON motor_sessions(session_id);

-- 4. Visual Sessions Table (Ocular / Visual Behavior)
CREATE TABLE IF NOT EXISTS visual_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_type TEXT NOT NULL CHECK (task_type IN ('tracking', 'blink', 'reaction')),
    duration NUMERIC NOT NULL CHECK (duration >= 0),
    blink_rate NUMERIC,
    blink_interval_variability NUMERIC,
    gaze_stability NUMERIC,
    reaction_time NUMERIC,
    quality_score NUMERIC NOT NULL CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    feature_version TEXT NOT NULL DEFAULT '1.0.0',
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_visual_participant ON visual_sessions(participant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_visual_sessions_session_id ON visual_sessions(session_id);

-- 5. Sleep Sessions Table
CREATE TABLE IF NOT EXISTS sleep_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sleep_duration NUMERIC NOT NULL CHECK (sleep_duration >= 0),
    sleep_quality NUMERIC NOT NULL CHECK (sleep_quality >= 1 AND sleep_quality <= 5),
    unusual_movement_self_report BOOLEAN NOT NULL DEFAULT FALSE,
    daytime_sleepiness NUMERIC NOT NULL CHECK (daytime_sleepiness >= 1 AND daytime_sleepiness <= 5),
    questionnaire_version TEXT NOT NULL DEFAULT '1.0.0',
    score NUMERIC NOT NULL,
    synced BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_sleep_participant ON sleep_sessions(participant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_sleep_sessions_session_id ON sleep_sessions(session_id);
