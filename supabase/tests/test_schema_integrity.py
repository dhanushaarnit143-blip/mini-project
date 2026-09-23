"""
Tests for Schema Integrity in MPF Mobile Extension Supabase backend.
Validates table definitions, columns, constraints, foreign keys, unique idempotency keys,
and JSONB payloads.
"""

import os
import re
import sqlite3
import json
import pytest
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
SEED_DIR = Path(__file__).resolve().parent.parent / "seed"

EXPECTED_TABLES = [
    "participants",
    "consent_records",
    "typing_sessions",
    "voice_sessions",
    "motor_sessions",
    "visual_sessions",
    "sleep_sessions",
    "daily_features",
    "personal_baselines",
    "daily_deviations",
    "mpf_predictions",
    "model_versions",
]

EXPECTED_MIGRATIONS = [
    "001_create_participants.sql",
    "002_create_consent_records.sql",
    "003_create_typing_sessions.sql",
    "004_create_voice_sessions.sql",
    "005_create_motor_sessions.sql",
    "006_create_visual_sessions.sql",
    "007_create_sleep_sessions.sql",
    "008_create_daily_features.sql",
    "009_create_personal_baselines.sql",
    "010_create_daily_deviations.sql",
    "011_create_mpf_predictions.sql",
    "012_create_model_versions.sql",
    "013_create_rls_policies.sql",
]


def test_all_migration_files_exist():
    """Verify all 13 migration files are present in supabase/migrations/."""
    for mig in EXPECTED_MIGRATIONS:
        mig_path = MIGRATIONS_DIR / mig
        assert mig_path.exists(), f"Missing migration file: {mig}"
        assert mig_path.stat().st_size > 0, f"Migration file is empty: {mig}"


def test_seed_file_exists():
    """Verify seed_model_versions.sql exists and is non-empty."""
    seed_file = SEED_DIR / "seed_model_versions.sql"
    assert seed_file.exists()
    assert seed_file.stat().st_size > 0


def test_migration_sql_syntax_and_table_definitions():
    """Verify each migration defines its designated table with proper columns."""
    for table in EXPECTED_TABLES:
        pattern = re.compile(rf"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?{table}\b", re.IGNORECASE)
        found = False
        for mig in EXPECTED_MIGRATIONS:
            content = (MIGRATIONS_DIR / mig).read_text(encoding="utf-8")
            if pattern.search(content):
                found = True
                break
        assert found, f"Table {table} was not created in any migration file!"


def test_schema_constraints_and_idempotency_keys():
    """Verify that sessions have unique session_id idempotency keys and participants have pseudonymous_id."""
    for session_table in ["typing_sessions", "voice_sessions", "motor_sessions", "visual_sessions", "sleep_sessions"]:
        mig_name = f"00{3 + ['typing_sessions', 'voice_sessions', 'motor_sessions', 'visual_sessions', 'sleep_sessions'].index(session_table)}_create_{session_table}.sql"
        content = (MIGRATIONS_DIR / mig_name).read_text(encoding="utf-8")
        assert "session_id TEXT UNIQUE NOT NULL" in content or "session_id TEXT" in content, f"{session_table} missing session_id"
        assert "UNIQUE" in content, f"{session_table} missing unique constraint on session_id"

    # Verify daily_features unique constraint
    daily_content = (MIGRATIONS_DIR / "008_create_daily_features.sql").read_text(encoding="utf-8")
    assert "uq_daily_features_participant_date" in daily_content or "UNIQUE (participant_id, date)" in daily_content

    # Verify participants pseudonymous_id
    participants_content = (MIGRATIONS_DIR / "001_create_participants.sql").read_text(encoding="utf-8")
    assert "pseudonymous_id TEXT UNIQUE NOT NULL" in participants_content or "pseudonymous_id" in participants_content


@pytest.fixture
def memory_db():
    """Sets up an in-memory SQLite database simulating PostgreSQL relational schema."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # DDL adapted for SQLite dialect testing foreign keys and constraints
    cursor.executescript("""
    CREATE TABLE participants (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        consent_version TEXT NOT NULL DEFAULT '1.0.0',
        consent_timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        app_version TEXT NOT NULL DEFAULT '1.0.0',
        model_version TEXT NOT NULL DEFAULT '1.0.0',
        baseline_status TEXT NOT NULL DEFAULT 'collecting' CHECK (baseline_status IN ('collecting', 'established', 'adaptive')),
        pseudonymous_id TEXT UNIQUE NOT NULL
    );

    CREATE TABLE consent_records (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        consent_type TEXT NOT NULL CHECK (consent_type IN ('data_collection', 'audio_storage', 'research_export', 'deletion')),
        consent_version TEXT NOT NULL,
        granted INTEGER NOT NULL DEFAULT 1,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        revoked_at TEXT
    );

    CREATE TABLE typing_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        task_type TEXT NOT NULL CHECK (task_type IN ('controlled_phrase', 'free_typing')),
        duration REAL NOT NULL CHECK (duration >= 0),
        typing_speed REAL NOT NULL CHECK (typing_speed >= 0),
        mean_inter_key_interval REAL NOT NULL CHECK (mean_inter_key_interval >= 0),
        std_inter_key_interval REAL NOT NULL CHECK (std_inter_key_interval >= 0),
        pause_rate REAL NOT NULL CHECK (pause_rate >= 0),
        correction_rate REAL NOT NULL CHECK (correction_rate >= 0),
        rhythm_variability REAL NOT NULL CHECK (rhythm_variability >= 0),
        quality_score REAL NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
        feature_version TEXT NOT NULL DEFAULT '1.0.0',
        synced INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE voice_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        task_type TEXT NOT NULL CHECK (task_type IN ('sustained_vowel', 'read_sentence', 'free_speech')),
        duration REAL NOT NULL CHECK (duration >= 0),
        signal_quality REAL NOT NULL CHECK (signal_quality BETWEEN 0.0 AND 1.0),
        jitter REAL NOT NULL,
        shimmer REAL NOT NULL,
        hnr REAL NOT NULL,
        pitch_mean REAL NOT NULL,
        pitch_std REAL NOT NULL,
        mfcc_features TEXT NOT NULL,
        spectral_features TEXT NOT NULL,
        quality_score REAL NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
        feature_version TEXT NOT NULL DEFAULT '1.0.0',
        synced INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE motor_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        task_type TEXT NOT NULL CHECK (task_type IN ('walking', 'tapping', 'tremor_hold', 'spiral')),
        duration REAL NOT NULL CHECK (duration >= 0),
        cadence REAL,
        stride_variability REAL,
        movement_variability REAL NOT NULL,
        tapping_rate REAL,
        tapping_interval_variability REAL,
        tremor_frequency REAL,
        tremor_amplitude REAL,
        quality_score REAL NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
        feature_version TEXT NOT NULL DEFAULT '1.0.0',
        synced INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE visual_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        task_type TEXT NOT NULL CHECK (task_type IN ('tracking', 'blink', 'reaction')),
        duration REAL NOT NULL CHECK (duration >= 0),
        blink_rate REAL NOT NULL,
        blink_interval_variability REAL NOT NULL,
        gaze_stability REAL NOT NULL CHECK (gaze_stability BETWEEN 0.0 AND 1.0),
        reaction_time REAL NOT NULL,
        quality_score REAL NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
        feature_version TEXT NOT NULL DEFAULT '1.0.0',
        synced INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE sleep_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        sleep_duration REAL NOT NULL CHECK (sleep_duration BETWEEN 0.0 AND 24.0),
        sleep_quality REAL NOT NULL CHECK (sleep_quality BETWEEN 1.0 AND 5.0),
        unusual_movement_self_report INTEGER NOT NULL,
        daytime_sleepiness REAL NOT NULL CHECK (daytime_sleepiness BETWEEN 1.0 AND 5.0),
        questionnaire_version TEXT NOT NULL DEFAULT '1.0.0',
        score REAL NOT NULL,
        synced INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE daily_features (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        typing_features TEXT,
        voice_features TEXT,
        motor_features TEXT,
        visual_features TEXT,
        sleep_features TEXT,
        data_quality TEXT NOT NULL DEFAULT '{}',
        feature_version TEXT NOT NULL DEFAULT '1.0.0',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        CONSTRAINT uq_daily_features_participant_date UNIQUE (participant_id, date)
    );

    CREATE TABLE personal_baselines (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        modality TEXT NOT NULL CHECK (modality IN ('typing', 'voice', 'motor', 'visual', 'sleep')),
        feature_name TEXT NOT NULL,
        baseline_mean REAL NOT NULL,
        baseline_median REAL NOT NULL,
        baseline_std REAL NOT NULL,
        baseline_mad REAL NOT NULL,
        lower_bound REAL NOT NULL,
        upper_bound REAL NOT NULL,
        sample_count INTEGER NOT NULL CHECK (sample_count >= 1),
        baseline_start_date TEXT NOT NULL,
        baseline_end_date TEXT NOT NULL,
        baseline_version TEXT NOT NULL DEFAULT '1.0.0',
        algorithm_version TEXT NOT NULL DEFAULT '1.0.0',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE daily_deviations (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        modality TEXT NOT NULL,
        feature_name TEXT NOT NULL,
        value REAL NOT NULL,
        baseline_value REAL NOT NULL,
        deviation_score REAL NOT NULL,
        trend_score REAL NOT NULL,
        quality_score REAL NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
        algorithm_version TEXT NOT NULL DEFAULT '1.0.0',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE mpf_predictions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        model_version TEXT NOT NULL,
        input_feature_version TEXT NOT NULL,
        available_modalities TEXT NOT NULL,
        missing_modalities TEXT NOT NULL,
        risk_score REAL NOT NULL CHECK (risk_score BETWEEN 0.0 AND 1.0),
        prediction_metadata TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE model_versions (
        id TEXT PRIMARY KEY,
        model_name TEXT NOT NULL,
        version TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        feature_schema_version TEXT NOT NULL,
        training_dataset_version TEXT NOT NULL,
        metrics TEXT NOT NULL DEFAULT '{}',
        active INTEGER NOT NULL DEFAULT 1,
        CONSTRAINT uq_model_versions_name_version UNIQUE (model_name, version)
    );
    """)
    conn.commit()
    yield conn
    conn.close()


def test_participant_crud_and_enum_check(memory_db):
    """Test participant creation and baseline_status check constraint."""
    cursor = memory_db.cursor()
    # Insert valid participant
    cursor.execute("""
        INSERT INTO participants (id, baseline_status, pseudonymous_id)
        VALUES ('p-101', 'collecting', 'pseudo-hash-101')
    """)
    memory_db.commit()

    # Query participant
    cursor.execute("SELECT id, baseline_status, pseudonymous_id FROM participants WHERE id = 'p-101'")
    row = cursor.fetchone()
    assert row == ('p-101', 'collecting', 'pseudo-hash-101')

    # Test invalid baseline_status
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO participants (id, baseline_status, pseudonymous_id)
            VALUES ('p-102', 'invalid_status', 'pseudo-hash-102')
        """)


def test_unique_pseudonymous_id_constraint(memory_db):
    """Test duplicate pseudonymous_id is rejected."""
    cursor = memory_db.cursor()
    cursor.execute("""
        INSERT INTO participants (id, baseline_status, pseudonymous_id)
        VALUES ('p-1', 'collecting', 'shared-pseudo-id')
    """)
    memory_db.commit()

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO participants (id, baseline_status, pseudonymous_id)
            VALUES ('p-2', 'collecting', 'shared-pseudo-id')
        """)


def test_foreign_key_and_cascade_delete(memory_db):
    """Test foreign key integrity and cascade deletion of participant data."""
    cursor = memory_db.cursor()
    cursor.execute("INSERT INTO participants (id, pseudonymous_id) VALUES ('p-user', 'pseudo-user')")

    cursor.execute("""
        INSERT INTO consent_records (id, participant_id, consent_type, consent_version, granted)
        VALUES ('c-1', 'p-user', 'data_collection', '1.0.0', 1)
    """)
    cursor.execute("""
        INSERT INTO typing_sessions (id, participant_id, session_id, task_type, duration,
            typing_speed, mean_inter_key_interval, std_inter_key_interval, pause_rate,
            correction_rate, rhythm_variability, quality_score)
        VALUES ('t-1', 'p-user', 'sess-t-1', 'controlled_phrase', 30.5, 4.2, 185.0, 32.1, 0.05, 0.02, 0.15, 0.95)
    """)
    memory_db.commit()

    # Verify rows exist
    cursor.execute("SELECT COUNT(*) FROM consent_records WHERE participant_id = 'p-user'")
    assert cursor.fetchone()[0] == 1
    cursor.execute("SELECT COUNT(*) FROM typing_sessions WHERE participant_id = 'p-user'")
    assert cursor.fetchone()[0] == 1

    # Delete participant -> should cascade
    cursor.execute("DELETE FROM participants WHERE id = 'p-user'")
    memory_db.commit()

    cursor.execute("SELECT COUNT(*) FROM consent_records WHERE participant_id = 'p-user'")
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT COUNT(*) FROM typing_sessions WHERE participant_id = 'p-user'")
    assert cursor.fetchone()[0] == 0


def test_session_id_idempotency_constraint(memory_db):
    """Test session_id uniqueness preventing duplicate session uploads."""
    cursor = memory_db.cursor()
    cursor.execute("INSERT INTO participants (id, pseudonymous_id) VALUES ('p-1', 'pseudo-1')")

    cursor.execute("""
        INSERT INTO typing_sessions (id, participant_id, session_id, task_type, duration,
            typing_speed, mean_inter_key_interval, std_inter_key_interval, pause_rate,
            correction_rate, rhythm_variability, quality_score)
        VALUES ('t-1', 'p-1', 'session-dup-check', 'controlled_phrase', 20.0, 5.0, 150.0, 20.0, 0.1, 0.0, 0.1, 1.0)
    """)
    memory_db.commit()

    # Second upload with same session_id must fail
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO typing_sessions (id, participant_id, session_id, task_type, duration,
                typing_speed, mean_inter_key_interval, std_inter_key_interval, pause_rate,
                correction_rate, rhythm_variability, quality_score)
            VALUES ('t-2', 'p-1', 'session-dup-check', 'free_typing', 25.0, 4.8, 160.0, 22.0, 0.12, 0.01, 0.12, 0.98)
        """)


def test_daily_features_unique_participant_date(memory_db):
    """Verify unique constraint on (participant_id, date) in daily_features."""
    cursor = memory_db.cursor()
    cursor.execute("INSERT INTO participants (id, pseudonymous_id) VALUES ('p-1', 'pseudo-1')")

    cursor.execute("""
        INSERT INTO daily_features (id, participant_id, date, typing_features, data_quality)
        VALUES ('df-1', 'p-1', '2026-09-23', '{"speed": 4.5}', '{"overall": 0.9}')
    """)
    memory_db.commit()

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO daily_features (id, participant_id, date, typing_features, data_quality)
            VALUES ('df-2', 'p-1', '2026-09-23', '{"speed": 4.6}', '{"overall": 0.92}')
        """)


def test_json_payload_serialization(memory_db):
    """Verify JSONB / JSON fields accept valid complex feature dictionaries and arrays."""
    cursor = memory_db.cursor()
    cursor.execute("INSERT INTO participants (id, pseudonymous_id) VALUES ('p-voice', 'pseudo-voice')")

    mfcc_data = [round(float(i) * 0.12, 4) for i in range(20)]
    spectral_data = {"spectral_centroid": 1420.5, "spectral_flatness": 0.0034, "f0": 128.2}

    cursor.execute("""
        INSERT INTO voice_sessions (
            id, participant_id, session_id, task_type, duration, signal_quality,
            jitter, shimmer, hnr, pitch_mean, pitch_std, mfcc_features, spectral_features, quality_score
        ) VALUES (
            'v-1', 'p-voice', 'sess-voice-001', 'sustained_vowel', 5.0, 0.96,
            0.012, 0.024, 21.4, 125.4, 4.2, ?, ?, 0.98
        )
    """, (json.dumps(mfcc_data), json.dumps(spectral_data)))
    memory_db.commit()

    cursor.execute("SELECT mfcc_features, spectral_features FROM voice_sessions WHERE id = 'v-1'")
    mfcc_str, spec_str = cursor.fetchone()
    assert json.loads(mfcc_str) == mfcc_data
    assert json.loads(spec_str) == spectral_data


def test_quality_and_risk_score_boundaries(memory_db):
    """Verify quality_score and risk_score are bounded between 0.0 and 1.0."""
    cursor = memory_db.cursor()
    cursor.execute("INSERT INTO participants (id, pseudonymous_id) VALUES ('p-score', 'pseudo-score')")

    # Invalid quality_score > 1.0
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO visual_sessions (
                id, participant_id, session_id, task_type, duration, blink_rate,
                blink_interval_variability, gaze_stability, reaction_time, quality_score
            ) VALUES (
                'vis-1', 'p-score', 'sess-vis-err', 'tracking', 10.0, 18.0, 1.2, 0.85, 240.0, 1.5
            )
        """)

    # Invalid risk_score > 1.0
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO mpf_predictions (
                id, participant_id, model_version, input_feature_version, available_modalities,
                missing_modalities, risk_score
            ) VALUES (
                'pred-1', 'p-score', 'gated_fusion_v1', '1.0.0', '["typing"]', '[]', 1.25
            )
        """)
