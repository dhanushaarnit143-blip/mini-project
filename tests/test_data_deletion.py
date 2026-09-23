"""
Tests for MPF Mobile Extension — Data Deletion Workflow (Phase 3)
Verifies:
- Irreversible participant data deletion workflow.
- Mandatory confirmation phrase validation ("DELETE MY RESEARCH DATA").
- Pre-execution audit logging in consent_records.
- Complete cascade deletion across all sensor sessions, features, baselines, deviations, and predictions.
- Soft-deletion of participant record (is_deleted=1, deleted_at=timestamp) for audit compliance.
"""

import sqlite3
import pytest
import uuid
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.mobile.services.privacy_services import (
    DeletionService,
    DELETION_CONFIRMATION_PHRASE,
    generate_pseudonymous_id,
)


@pytest.fixture
def populated_db():
    """Populates an in-memory SQLite database with participant data across all tables."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE participants (
        id TEXT PRIMARY KEY,
        pseudonymous_id TEXT UNIQUE NOT NULL,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        deleted_at TEXT
    );

    CREATE TABLE consent_records (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        consent_type TEXT NOT NULL,
        consent_version TEXT NOT NULL,
        granted INTEGER NOT NULL DEFAULT 1,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        revoked_at TEXT
    );

    CREATE TABLE typing_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL
    );

    CREATE TABLE voice_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL
    );

    CREATE TABLE motor_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL
    );

    CREATE TABLE visual_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL
    );

    CREATE TABLE sleep_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL
    );

    CREATE TABLE daily_features (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        feature_date TEXT NOT NULL
    );

    CREATE TABLE personal_baselines (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        baseline_version INTEGER NOT NULL
    );

    CREATE TABLE daily_deviations (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        feature_date TEXT NOT NULL
    );

    CREATE TABLE mpf_predictions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        risk_score REAL NOT NULL
    );
    """)

    part_id = str(uuid.uuid4())
    pseudo_id = generate_pseudonymous_id(part_id)

    cursor.execute("INSERT INTO participants (id, pseudonymous_id) VALUES (?, ?)", (part_id, pseudo_id))
    cursor.execute("INSERT INTO typing_sessions (id, participant_id, session_id) VALUES ('t1', ?, 'ts_1')", (part_id,))
    cursor.execute("INSERT INTO voice_sessions (id, participant_id, session_id) VALUES ('v1', ?, 'vs_1')", (part_id,))
    cursor.execute("INSERT INTO motor_sessions (id, participant_id, session_id) VALUES ('m1', ?, 'ms_1')", (part_id,))
    cursor.execute("INSERT INTO visual_sessions (id, participant_id, session_id) VALUES ('vi1', ?, 'vis_1')", (part_id,))
    cursor.execute("INSERT INTO sleep_sessions (id, participant_id, session_id) VALUES ('s1', ?, 'sl_1')", (part_id,))
    cursor.execute("INSERT INTO daily_features (id, participant_id, feature_date) VALUES ('f1', ?, '2026-09-23')", (part_id,))
    cursor.execute("INSERT INTO personal_baselines (id, participant_id, baseline_version) VALUES ('b1', ?, 1)", (part_id,))
    cursor.execute("INSERT INTO daily_deviations (id, participant_id, feature_date) VALUES ('d1', ?, '2026-09-23')", (part_id,))
    cursor.execute("INSERT INTO mpf_predictions (id, participant_id, risk_score) VALUES ('p1', ?, 0.35)", (part_id,))

    conn.commit()
    yield part_id, conn
    conn.close()


def test_deletion_rejected_without_exact_confirmation(populated_db):
    """Verifies that deletion requests with invalid confirmation phrases are strictly rejected."""
    part_id, db = populated_db
    service = DeletionService(db_conn=db)

    # Invalid confirmation
    with pytest.raises(ValueError) as exc_info:
        service.request_account_deletion(part_id, "delete my account please")
    assert "phrase mismatch" in str(exc_info.value).lower()

    # Verify no data was deleted
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM typing_sessions WHERE participant_id = ?", (part_id,))
    assert cursor.fetchone()[0] == 1


def test_complete_data_purge_lifecycle(populated_db):
    """Verifies that an authorized deletion request purges all research tables and records audit log."""
    part_id, db = populated_db
    service = DeletionService(db_conn=db)

    res = service.request_account_deletion(part_id, DELETION_CONFIRMATION_PHRASE, reason="Subject withdrawn")
    assert res["success"] is True
    assert res["is_irreversible"] is True

    cursor = db.cursor()

    # 1. Verify all research session and calculation tables are wiped clean
    research_tables = [
        "typing_sessions",
        "voice_sessions",
        "motor_sessions",
        "visual_sessions",
        "sleep_sessions",
        "daily_features",
        "personal_baselines",
        "daily_deviations",
        "mpf_predictions",
    ]
    for tbl in research_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {tbl} WHERE participant_id = ?", (part_id,))
        count = cursor.fetchone()[0]
        assert count == 0, f"Table {tbl} was not purged! Remaining rows: {count}"

    # 2. Verify audit entry exists in consent_records with consent_type = 'deletion'
    cursor.execute(
        "SELECT consent_type, granted, timestamp FROM consent_records WHERE participant_id = ? AND consent_type = 'deletion'",
        (part_id,),
    )
    audit_row = cursor.fetchone()
    assert audit_row is not None
    assert audit_row[0] == "deletion"
    assert audit_row[1] == 1

    # 3. Verify participant record is soft-deleted for audit trail
    cursor.execute("SELECT is_deleted, deleted_at FROM participants WHERE id = ?", (part_id,))
    part_row = cursor.fetchone()
    assert part_row[0] == 1
    assert part_row[1] is not None
