"""
Tests for MPF Mobile Extension — Consent Revocation Workflow (Phase 3)
Verifies:
- Participant can revoke consent at any time.
- Setting of revoked_at timestamp in consent_records.
- Immediate halt of data collection upon revocation.
- Granular revocation (e.g. revoking audio storage or camera without breaking typing).
- Audit trail preservation during revocation.
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
    ConsentService,
    CONSENT_TYPES,
    generate_pseudonymous_id,
)


@pytest.fixture
def active_participant(test_db):
    """Creates a participant with active consent for all categories."""
    part_id = str(uuid.uuid4())
    pseudo_id = generate_pseudonymous_id(part_id)

    cursor = test_db.cursor()
    cursor.execute("INSERT INTO participants (id, pseudonymous_id) VALUES (?, ?)", (part_id, pseudo_id))
    test_db.commit()

    service = ConsentService(db_conn=test_db)
    service.record_consent(
        part_id,
        {
            CONSENT_TYPES["DATA_COLLECTION"]: True,
            CONSENT_TYPES["AUDIO_STORAGE"]: True,
            CONSENT_TYPES["RESEARCH_EXPORT"]: True,
            CONSENT_TYPES["CAMERA_ACCESS"]: True,
            CONSENT_TYPES["MICROPHONE_ACCESS"]: True,
            CONSENT_TYPES["MOTION_ACCESS"]: True,
            CONSENT_TYPES["KEYBOARD_ACCESS"]: True,
        },
    )
    return part_id, service, test_db


@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE participants (
        id TEXT PRIMARY KEY,
        created_at TEXT DEFAULT (datetime('now')),
        consent_version TEXT NOT NULL DEFAULT '1.0.0',
        consent_timestamp TEXT DEFAULT (datetime('now')),
        app_version TEXT NOT NULL DEFAULT '1.0.0',
        model_version TEXT NOT NULL DEFAULT '1.0.0',
        baseline_status TEXT NOT NULL DEFAULT 'collecting',
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
    """)
    conn.commit()
    yield conn
    conn.close()


def test_granular_revocation_audio_storage(active_participant):
    """Verifies that revoking audio_storage stops audio upload while preserving general data collection."""
    part_id, service, db = active_participant

    # Verify initial state: both active
    assert service.check_consent(part_id, CONSENT_TYPES["DATA_COLLECTION"]) is True
    assert service.check_consent(part_id, CONSENT_TYPES["AUDIO_STORAGE"]) is True

    # Revoke audio storage only
    rev_res = service.revoke_consent(part_id, consent_type=CONSENT_TYPES["AUDIO_STORAGE"], reason="Privacy concern")
    assert rev_res["success"] is True
    assert rev_res["revoked_type"] == CONSENT_TYPES["AUDIO_STORAGE"]
    assert rev_res["revoked_at"] is not None

    # Verify check_consent reflects revocation immediately
    assert service.check_consent(part_id, CONSENT_TYPES["AUDIO_STORAGE"]) is False
    # General data collection remains authorized
    assert service.check_consent(part_id, CONSENT_TYPES["DATA_COLLECTION"]) is True
    assert service.check_consent(part_id, CONSENT_TYPES["KEYBOARD_ACCESS"]) is True

    # Verify database revoked_at timestamp is set
    cursor = db.cursor()
    cursor.execute(
        "SELECT revoked_at, granted FROM consent_records WHERE participant_id = ? AND consent_type = ?",
        (part_id, CONSENT_TYPES["AUDIO_STORAGE"]),
    )
    row = cursor.fetchone()
    assert row[0] is not None
    assert row[1] == 0


def test_full_study_revocation_halts_all_collection(active_participant):
    """Verifies that revoking all consent halts every data collection modality immediately."""
    part_id, service, db = active_participant

    # Revoke all
    rev_res = service.revoke_consent(part_id, consent_type="all", reason="Withdrawing from study")
    assert rev_res["success"] is True

    # All checks must now return False
    assert service.check_consent(part_id, CONSENT_TYPES["DATA_COLLECTION"]) is False
    assert service.check_consent(part_id, CONSENT_TYPES["MICROPHONE_ACCESS"]) is False
    assert service.check_consent(part_id, CONSENT_TYPES["KEYBOARD_ACCESS"]) is False

    # Attempting any task assertion must raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        service.assert_authorized_collection(part_id, "voice")
    assert "unauthorized" in str(exc_info.value).lower()


def test_revocation_leaves_audit_record(active_participant):
    """Verifies that revoked consent records are NOT deleted from the database, preserving audit trails."""
    part_id, service, db = active_participant

    service.revoke_consent(part_id, consent_type=CONSENT_TYPES["CAMERA_ACCESS"])

    cursor = db.cursor()
    cursor.execute(
        "SELECT id, consent_type, granted, revoked_at FROM consent_records WHERE participant_id = ? AND consent_type = ?",
        (part_id, CONSENT_TYPES["CAMERA_ACCESS"]),
    )
    row = cursor.fetchone()
    assert row is not None  # Record exists for audit
    assert row[2] == 0      # granted is False
    assert row[3] is not None  # revoked_at has timestamp
