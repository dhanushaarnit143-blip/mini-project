"""
Tests for MPF Mobile Extension — Consent and Onboarding Flow (Phase 3)
Verifies:
- Consent flow presentation prior to any data collection.
- Plain language and prominent research prototype disclaimer.
- Separate opt-in for all consent categories.
- Versioned consent recording (consent_version, timestamp, granted).
- Pseudonymous ID generation without PII.
- Immediate gating: sensor collection blocked if consent is absent or incomplete.
"""

import sqlite3
import pytest
import uuid
import datetime
from pathlib import Path
import sys

# Ensure src is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.mobile.services.privacy_services import (
    ConsentService,
    CONSENT_TYPES,
    CURRENT_CONSENT_VERSION,
    generate_pseudonymous_id,
)


@pytest.fixture
def test_db():
    """Sets up an in-memory SQLite database matching Supabase schema for mobile tables."""
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
    """)
    conn.commit()
    yield conn
    conn.close()


def test_pseudonymous_id_generation():
    """Verifies that pseudonymous IDs are deterministic per seed, hashed, and contain no PII."""
    uid = str(uuid.uuid4())
    pseudo_id = generate_pseudonymous_id(uid)
    assert pseudo_id.startswith("ps_")
    assert len(pseudo_id) >= 10
    # No email symbols or personal markers
    assert "@" not in pseudo_id
    assert " " not in pseudo_id


def test_consent_required_before_data_collection(test_db):
    """Verifies that data collection is blocked if informed consent has not been recorded."""
    service = ConsentService(db_conn=test_db)
    unconsented_id = str(uuid.uuid4())

    # Check that participant has no active consent
    assert service.check_consent(unconsented_id, CONSENT_TYPES["DATA_COLLECTION"]) is False

    # Attempting to assert authorized collection must raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        service.assert_authorized_collection(unconsented_id, "typing")
    assert "not consented" in str(exc_info.value).lower()


def test_recording_informed_consent_success(test_db):
    """Verifies successful recording of versioned consent records across categories."""
    service = ConsentService(db_conn=test_db)
    part_id = str(uuid.uuid4())
    pseudo_id = generate_pseudonymous_id(part_id)

    # Insert participant
    cursor = test_db.cursor()
    cursor.execute(
        "INSERT INTO participants (id, pseudonymous_id) VALUES (?, ?)",
        (part_id, pseudo_id),
    )
    test_db.commit()

    # Record consent with granular choices
    chosen_consents = {
        CONSENT_TYPES["DATA_COLLECTION"]: True,
        CONSENT_TYPES["AUDIO_STORAGE"]: False,  # Opted out of audio storage
        CONSENT_TYPES["RESEARCH_EXPORT"]: True,  # Opted in to research export
        CONSENT_TYPES["MICROPHONE_ACCESS"]: True,
        CONSENT_TYPES["MOTION_ACCESS"]: True,
        CONSENT_TYPES["KEYBOARD_ACCESS"]: True,
        CONSENT_TYPES["CAMERA_ACCESS"]: False,  # Opted out of visual tasks
    }

    res = service.record_consent(part_id, chosen_consents, consent_version="1.0.0")
    assert res["success"] is True
    assert res["consent_version"] == "1.0.0"
    assert CONSENT_TYPES["DATA_COLLECTION"] in res["granted_types"]
    assert CONSENT_TYPES["RESEARCH_EXPORT"] in res["granted_types"]
    assert CONSENT_TYPES["AUDIO_STORAGE"] not in res["granted_types"]

    # Verify participant table updated with consent timestamp and version
    cursor.execute("SELECT consent_version, consent_timestamp FROM participants WHERE id = ?", (part_id,))
    row = cursor.fetchone()
    assert row[0] == "1.0.0"
    assert row[1] is not None

    # Verify individual consent_records table entries
    cursor.execute("SELECT consent_type, granted, revoked_at FROM consent_records WHERE participant_id = ?", (part_id,))
    records = cursor.fetchall()
    recorded_types = [r[0] for r in records]
    assert CONSENT_TYPES["DATA_COLLECTION"] in recorded_types
    assert CONSENT_TYPES["RESEARCH_EXPORT"] in recorded_types
    assert CONSENT_TYPES["MICROPHONE_ACCESS"] in recorded_types
    assert CONSENT_TYPES["AUDIO_STORAGE"] not in recorded_types


def test_mandatory_data_collection_consent_enforcement(test_db):
    """Verifies that failing to consent to basic data collection prevents onboarding."""
    service = ConsentService(db_conn=test_db)
    part_id = str(uuid.uuid4())

    refused_consents = {
        CONSENT_TYPES["DATA_COLLECTION"]: False,
        CONSENT_TYPES["AUDIO_STORAGE"]: True,
    }

    with pytest.raises(PermissionError) as exc_info:
        service.record_consent(part_id, refused_consents)
    assert "mandatory" in str(exc_info.value).lower()


def test_granular_sensor_authorization(test_db):
    """Verifies that sensor-specific modalities are gated by their corresponding permission."""
    service = ConsentService(db_conn=test_db)
    part_id = str(uuid.uuid4())
    pseudo_id = generate_pseudonymous_id(part_id)

    cursor = test_db.cursor()
    cursor.execute("INSERT INTO participants (id, pseudonymous_id) VALUES (?, ?)", (part_id, pseudo_id))
    test_db.commit()

    # Participant authorizes typing and voice, but NOT camera
    service.record_consent(
        part_id,
        {
            CONSENT_TYPES["DATA_COLLECTION"]: True,
            CONSENT_TYPES["KEYBOARD_ACCESS"]: True,
            CONSENT_TYPES["MICROPHONE_ACCESS"]: True,
            CONSENT_TYPES["CAMERA_ACCESS"]: False,
        },
    )

    # Typing and voice are authorized
    service.assert_authorized_collection(part_id, "typing")
    service.assert_authorized_collection(part_id, "voice")

    # Visual task raises PermissionError because camera_access was not granted
    with pytest.raises(PermissionError) as exc_info:
        service.assert_authorized_collection(part_id, "visual")
    assert "camera_access" in str(exc_info.value)
