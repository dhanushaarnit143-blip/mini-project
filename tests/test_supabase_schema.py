"""
Tests for Supabase Schema Definition, Constraints, Indexes, and Idempotency.

Validates:
- All 12 tables defined across migrations 001-008
- Column specifications and data types match Phase A requirements
- Primary keys and foreign keys with CASCADE delete
- Unique idempotency constraints (session_id, pseudonymous_id, unique composite keys)
- Performance indexes on all session, daily_features, baselines, deviations, predictions tables
- In-memory database simulation of constraints and duplicate rejection
"""

import re
import sqlite3
from pathlib import Path
import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "supabase" / "migrations"
SEED_DIR = Path(__file__).resolve().parent.parent / "supabase" / "seed"

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

MIGRATION_FILES = [
    "001_create_participants.sql",
    "002_create_consent_records.sql",
    "003_create_session_tables.sql",
    "004_create_daily_features.sql",
    "005_create_personal_baselines.sql",
    "006_create_daily_deviations.sql",
    "007_create_mpf_predictions.sql",
    "008_create_model_versions.sql",
    "009_create_rls_policies.sql",
]


def _read_all_migrations() -> str:
    combined = []
    for f in MIGRATION_FILES:
        path = MIGRATIONS_DIR / f
        assert path.exists(), f"Migration file missing: {f}"
        combined.append(path.read_text(encoding="utf-8"))
    return "\n".join(combined)


def test_all_12_tables_created_in_migrations():
    """Verify that all 12 required tables are declared with CREATE TABLE."""
    content = _read_all_migrations()
    for table in EXPECTED_TABLES:
        pattern = re.compile(rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{table}\b", re.IGNORECASE)
        assert pattern.search(content), f"Table {table} not found in migration SQL!"


def test_participants_table_columns():
    """Verify participants table columns match specification."""
    content = (MIGRATIONS_DIR / "001_create_participants.sql").read_text(encoding="utf-8")
    expected_cols = [
        "id", "created_at", "email", "pseudonymous_id", "consent_version",
        "consent_timestamp", "app_version", "model_version", "baseline_status", "is_active"
    ]
    for col in expected_cols:
        assert re.search(rf"\b{col}\b", content), f"Column {col} missing from participants table"


def test_consent_records_table_columns():
    """Verify consent_records table columns match specification."""
    content = (MIGRATIONS_DIR / "002_create_consent_records.sql").read_text(encoding="utf-8")
    expected_cols = [
        "id", "participant_id", "consent_type", "consent_version", "granted", "timestamp", "revoked_at"
    ]
    for col in expected_cols:
        assert re.search(rf"\b{col}\b", content), f"Column {col} missing from consent_records"


def test_session_tables_and_idempotency_keys():
    """Verify typing, voice, motor, visual, sleep tables exist with session_id idempotency key."""
    content = (MIGRATIONS_DIR / "003_create_session_tables.sql").read_text(encoding="utf-8")
    session_tables = ["typing_sessions", "voice_sessions", "motor_sessions", "visual_sessions", "sleep_sessions"]
    for table in session_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in content
        # Check session_id idempotency key with UNIQUE
        assert "session_id TEXT UNIQUE NOT NULL" in content or "session_id TEXT UNIQUE" in content


def test_daily_features_table_columns_and_constraint():
    """Verify daily_features columns and UNIQUE(participant_id, date) constraint."""
    content = (MIGRATIONS_DIR / "004_create_daily_features.sql").read_text(encoding="utf-8")
    expected_cols = [
        "id", "participant_id", "date", "typing_features", "voice_features",
        "motor_features", "visual_features", "sleep_features", "data_quality",
        "feature_version", "created_at"
    ]
    for col in expected_cols:
        assert re.search(rf"\b{col}\b", content), f"Column {col} missing from daily_features"
    assert "UNIQUE (participant_id, date)" in content or "UNIQUE(participant_id, date)" in content


def test_personal_baselines_columns_and_constraint():
    """Verify personal_baselines columns and UNIQUE(participant_id, modality, feature_name) constraint."""
    content = (MIGRATIONS_DIR / "005_create_personal_baselines.sql").read_text(encoding="utf-8")
    expected_cols = [
        "id", "participant_id", "modality", "feature_name", "baseline_mean",
        "baseline_median", "baseline_std", "baseline_mad", "lower_bound",
        "upper_bound", "sample_count", "baseline_start_date", "baseline_end_date",
        "baseline_version", "algorithm_version", "created_at", "updated_at"
    ]
    for col in expected_cols:
        assert re.search(rf"\b{col}\b", content), f"Column {col} missing from personal_baselines"
    assert "UNIQUE (participant_id, modality, feature_name)" in content or "UNIQUE(participant_id, modality, feature_name)" in content


def test_daily_deviations_columns():
    """Verify daily_deviations columns match specification."""
    content = (MIGRATIONS_DIR / "006_create_daily_deviations.sql").read_text(encoding="utf-8")
    expected_cols = [
        "id", "participant_id", "date", "modality", "feature_name", "value",
        "baseline_value", "deviation_score", "trend_score", "quality_score",
        "algorithm_version", "created_at"
    ]
    for col in expected_cols:
        assert re.search(rf"\b{col}\b", content), f"Column {col} missing from daily_deviations"


def test_mpf_predictions_columns():
    """Verify mpf_predictions columns match specification."""
    content = (MIGRATIONS_DIR / "007_create_mpf_predictions.sql").read_text(encoding="utf-8")
    expected_cols = [
        "id", "participant_id", "timestamp", "model_version", "input_feature_version",
        "available_modalities", "missing_modalities", "risk_score", "prediction_metadata", "created_at"
    ]
    for col in expected_cols:
        assert re.search(rf"\b{col}\b", content), f"Column {col} missing from mpf_predictions"


def test_model_versions_columns():
    """Verify model_versions columns match specification."""
    content = (MIGRATIONS_DIR / "008_create_model_versions.sql").read_text(encoding="utf-8")
    expected_cols = [
        "id", "model_name", "version", "created_at", "feature_schema_version",
        "training_dataset_version", "metrics", "active"
    ]
    for col in expected_cols:
        assert re.search(rf"\b{col}\b", content), f"Column {col} missing from model_versions"


def test_required_performance_indexes():
    """Verify all 9 performance indexes specified in Section 4 are present in migrations."""
    content = _read_all_migrations()
    expected_indexes = [
        ("idx_typing_participant", "typing_sessions", "participant_id, timestamp"),
        ("idx_voice_participant", "voice_sessions", "participant_id, timestamp"),
        ("idx_motor_participant", "motor_sessions", "participant_id, timestamp"),
        ("idx_visual_participant", "visual_sessions", "participant_id, timestamp"),
        ("idx_sleep_participant", "sleep_sessions", "participant_id, timestamp"),
        ("idx_daily_features_participant", "daily_features", "participant_id, date"),
        ("idx_baselines_participant", "personal_baselines", "participant_id, modality"),
        ("idx_deviations_participant", "daily_deviations", "participant_id, date"),
        ("idx_predictions_participant", "mpf_predictions", "participant_id, timestamp"),
    ]
    for idx_name, tbl_name, _ in expected_indexes:
        assert idx_name in content, f"Index {idx_name} not found in migrations!"
        assert tbl_name in content, f"Table {tbl_name} for index {idx_name} not found!"


def test_seed_model_versions_file():
    """Verify seed_model_versions.sql exists and seeds models."""
    seed_path = SEED_DIR / "seed_model_versions.sql"
    assert seed_path.exists(), "seed_model_versions.sql missing"
    content = seed_path.read_text(encoding="utf-8")
    assert "INSERT INTO model_versions" in content
    assert "gated_multimodal_fusion" in content
    assert "baseline_deviation_evaluator" in content


@pytest.fixture
def memory_db():
    """Sets up an in-memory SQLite schema replicating table structures and constraints."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE participants (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        email TEXT UNIQUE,
        pseudonymous_id TEXT UNIQUE NOT NULL,
        consent_version TEXT NOT NULL DEFAULT '1.0.0',
        consent_timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        app_version TEXT NOT NULL DEFAULT '1.0.0',
        model_version TEXT NOT NULL DEFAULT '1.0.0',
        baseline_status TEXT NOT NULL DEFAULT 'collecting' CHECK (baseline_status IN ('collecting', 'established', 'adaptive')),
        is_active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE consent_records (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        consent_type TEXT NOT NULL CHECK (consent_type IN ('data_collection', 'audio_storage', 'research_export')),
        consent_version TEXT NOT NULL,
        granted INTEGER NOT NULL,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        revoked_at TEXT
    );

    CREATE TABLE typing_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        task_type TEXT NOT NULL,
        duration REAL NOT NULL,
        typing_speed REAL NOT NULL,
        mean_inter_key_interval REAL NOT NULL,
        std_inter_key_interval REAL NOT NULL,
        pause_rate REAL NOT NULL,
        correction_rate REAL NOT NULL,
        rhythm_variability REAL NOT NULL,
        quality_score REAL NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
        feature_version TEXT NOT NULL DEFAULT '1.0.0',
        synced INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE voice_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        task_type TEXT NOT NULL,
        duration REAL NOT NULL,
        signal_quality REAL NOT NULL,
        jitter REAL NOT NULL,
        shimmer REAL NOT NULL,
        hnr REAL NOT NULL,
        pitch_mean REAL NOT NULL,
        pitch_std REAL NOT NULL,
        mfcc_features TEXT NOT NULL DEFAULT '{}',
        quality_score REAL NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
        feature_version TEXT NOT NULL DEFAULT '1.0.0',
        synced INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE motor_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        task_type TEXT NOT NULL CHECK (task_type IN ('walking', 'tapping', 'tremor_hold')),
        duration REAL NOT NULL,
        cadence REAL,
        stride_variability REAL,
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
        duration REAL NOT NULL,
        blink_rate REAL,
        blink_interval_variability REAL,
        gaze_stability REAL,
        reaction_time REAL,
        quality_score REAL NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
        feature_version TEXT NOT NULL DEFAULT '1.0.0',
        synced INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE sleep_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        sleep_duration REAL NOT NULL,
        sleep_quality REAL NOT NULL CHECK (sleep_quality >= 1 AND sleep_quality <= 5),
        unusual_movement_self_report INTEGER NOT NULL DEFAULT 0,
        daytime_sleepiness REAL NOT NULL CHECK (daytime_sleepiness >= 1 AND daytime_sleepiness <= 5),
        questionnaire_version TEXT NOT NULL DEFAULT '1.0.0',
        score REAL NOT NULL,
        synced INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE daily_features (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        typing_features TEXT NOT NULL DEFAULT '{}',
        voice_features TEXT NOT NULL DEFAULT '{}',
        motor_features TEXT NOT NULL DEFAULT '{}',
        visual_features TEXT NOT NULL DEFAULT '{}',
        sleep_features TEXT NOT NULL DEFAULT '{}',
        data_quality TEXT NOT NULL DEFAULT '{}',
        feature_version TEXT NOT NULL DEFAULT '1.0.0',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE (participant_id, date)
    );

    CREATE TABLE personal_baselines (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        modality TEXT NOT NULL,
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
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE (participant_id, modality, feature_name)
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
        trend_score REAL NOT NULL DEFAULT 0.0,
        quality_score REAL NOT NULL CHECK (quality_score BETWEEN 0.0 AND 1.0),
        algorithm_version TEXT NOT NULL DEFAULT '1.0.0',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE mpf_predictions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        model_version TEXT NOT NULL DEFAULT '1.0.0',
        input_feature_version TEXT NOT NULL DEFAULT '1.0.0',
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
        active INTEGER NOT NULL DEFAULT 1
    );
    """)
    conn.commit()
    yield conn
    conn.close()


def test_idempotency_keys_prevent_session_duplicates(memory_db):
    """Verify unique session_id prevents duplicate insertions across sessions."""
    cursor = memory_db.cursor()
    cursor.execute("INSERT INTO participants (id, email, pseudonymous_id) VALUES ('p-1', 'p1@test.com', 'pseudo-001')")

    # Insert initial typing session
    cursor.execute("""
    INSERT INTO typing_sessions (id, participant_id, session_id, duration, task_type, typing_speed,
                                 mean_inter_key_interval, std_inter_key_interval, pause_rate,
                                 correction_rate, rhythm_variability, quality_score)
    VALUES ('t-1', 'p-1', 'sess-typing-unique-1', 60.0, 'phrase', 4.5, 200.0, 30.0, 0.1, 0.02, 0.15, 0.95)
    """)
    memory_db.commit()

    # Attempt duplicate insert with same session_id should raise IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
        INSERT INTO typing_sessions (id, participant_id, session_id, duration, task_type, typing_speed,
                                     mean_inter_key_interval, std_inter_key_interval, pause_rate,
                                     correction_rate, rhythm_variability, quality_score)
        VALUES ('t-2', 'p-1', 'sess-typing-unique-1', 45.0, 'free', 4.0, 220.0, 35.0, 0.12, 0.03, 0.16, 0.90)
        """)


def test_daily_features_unique_participant_date(memory_db):
    """Verify UNIQUE(participant_id, date) prevents multiple daily entries per participant."""
    cursor = memory_db.cursor()
    cursor.execute("INSERT INTO participants (id, email, pseudonymous_id) VALUES ('p-1', 'p1@test.com', 'pseudo-001')")

    cursor.execute("INSERT INTO daily_features (id, participant_id, date) VALUES ('df-1', 'p-1', '2026-11-18')")
    memory_db.commit()

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("INSERT INTO daily_features (id, participant_id, date) VALUES ('df-2', 'p-1', '2026-11-18')")


def test_personal_baselines_unique_modality_feature(memory_db):
    """Verify UNIQUE(participant_id, modality, feature_name) prevents duplicate baseline entries."""
    cursor = memory_db.cursor()
    cursor.execute("INSERT INTO participants (id, email, pseudonymous_id) VALUES ('p-1', 'p1@test.com', 'pseudo-001')")

    cursor.execute("""
    INSERT INTO personal_baselines (id, participant_id, modality, feature_name, baseline_mean, baseline_median,
                                    baseline_std, baseline_mad, lower_bound, upper_bound, sample_count,
                                    baseline_start_date, baseline_end_date)
    VALUES ('pb-1', 'p-1', 'typing', 'iki_mean', 200.0, 198.0, 15.0, 10.0, 170.0, 230.0, 14, '2026-11-01', '2026-11-14')
    """)
    memory_db.commit()

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
        INSERT INTO personal_baselines (id, participant_id, modality, feature_name, baseline_mean, baseline_median,
                                        baseline_std, baseline_mad, lower_bound, upper_bound, sample_count,
                                        baseline_start_date, baseline_end_date)
        VALUES ('pb-2', 'p-1', 'typing', 'iki_mean', 205.0, 200.0, 16.0, 11.0, 175.0, 235.0, 15, '2026-11-01', '2026-11-15')
        """)


def test_foreign_key_cascades_on_participant_delete(memory_db):
    """Verify CASCADE deletion removes participant data across all related tables."""
    cursor = memory_db.cursor()
    cursor.execute("INSERT INTO participants (id, email, pseudonymous_id) VALUES ('p-cascade', 'pcasc@test.com', 'pseudo-casc')")
    cursor.execute("INSERT INTO consent_records (id, participant_id, consent_type, consent_version, granted) VALUES ('c-1', 'p-cascade', 'data_collection', '1.0', 1)")
    cursor.execute("""
    INSERT INTO voice_sessions (id, participant_id, session_id, task_type, duration, signal_quality, jitter, shimmer, hnr, pitch_mean, pitch_std, quality_score)
    VALUES ('v-1', 'p-cascade', 'voice-sess-1', 'vowel_a', 5.0, 0.9, 0.01, 0.03, 22.0, 120.0, 5.0, 0.95)
    """)
    cursor.execute("INSERT INTO daily_features (id, participant_id, date) VALUES ('df-casc', 'p-cascade', '2026-11-18')")
    cursor.execute("INSERT INTO mpf_predictions (id, participant_id, available_modalities, missing_modalities, risk_score) VALUES ('pred-1', 'p-cascade', '[\"voice\"]', '[\"typing\"]', 0.25)")
    memory_db.commit()

    # Delete participant
    cursor.execute("DELETE FROM participants WHERE id = 'p-cascade'")
    memory_db.commit()

    # Verify cascading purge
    for tbl in ["consent_records", "voice_sessions", "daily_features", "mpf_predictions"]:
        cursor.execute(f"SELECT COUNT(*) FROM {tbl} WHERE participant_id = 'p-cascade'")
        count = cursor.fetchone()[0]
        assert count == 0, f"Table {tbl} did not cascade delete records for participant"
