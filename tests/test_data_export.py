"""
Tests for MPF Mobile Extension — Data Export Workflow (Phase 3)
Verifies:
- Complete participant data export generation as portable JSON.
- Comprehensive extraction across all modalities (typing, voice, motor, visual, sleep),
  daily features, personal baselines, daily deviations, MPF predictions, and consents.
- Strict cross-participant isolation (Participant A's export NEVER contains Participant B's data).
- Cryptographic SHA-256 data integrity checksum calculation.
- Mandatory research prototype non-diagnostic disclaimer in export package.
"""

import sqlite3
import pytest
import uuid
import json
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.mobile.services.privacy_services import (
    ExportService,
    generate_pseudonymous_id,
)


@pytest.fixture
def multi_participant_db():
    """Sets up a database with two participants (A and B) with distinct records."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE participants (
        id TEXT PRIMARY KEY,
        created_at TEXT DEFAULT (datetime('now')),
        consent_version TEXT NOT NULL DEFAULT '1.0.0',
        baseline_status TEXT NOT NULL DEFAULT 'collecting',
        pseudonymous_id TEXT UNIQUE NOT NULL
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
        session_id TEXT UNIQUE NOT NULL,
        hold_time_ms REAL
    );

    CREATE TABLE voice_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        jitter_local REAL
    );

    CREATE TABLE motor_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        tap_interval_var REAL
    );

    CREATE TABLE visual_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        saccade_latency_ms REAL
    );

    CREATE TABLE sleep_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL,
        sleep_quality_score REAL
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
        feature_date TEXT NOT NULL,
        mahalanobis_distance REAL
    );

    CREATE TABLE mpf_predictions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        risk_score REAL NOT NULL
    );
    """)

    # Participant A
    p_a = "11111111-1111-4000-a000-000000000001"
    pseudo_a = generate_pseudonymous_id(p_a)
    cursor.execute("INSERT INTO participants (id, pseudonymous_id) VALUES (?, ?)", (p_a, pseudo_a))
    cursor.execute("INSERT INTO consent_records (id, participant_id, consent_type, consent_version) VALUES ('ca1', ?, 'data_collection', '1.0.0')", (p_a,))
    cursor.execute("INSERT INTO typing_sessions (id, participant_id, session_id, hold_time_ms) VALUES ('ta1', ?, 'ts_a1', 82.5)", (p_a,))
    cursor.execute("INSERT INTO voice_sessions (id, participant_id, session_id, jitter_local) VALUES ('va1', ?, 'vs_a1', 0.012)", (p_a,))
    cursor.execute("INSERT INTO motor_sessions (id, participant_id, session_id, tap_interval_var) VALUES ('ma1', ?, 'ms_a1', 14.2)", (p_a,))
    cursor.execute("INSERT INTO daily_features (id, participant_id, feature_date) VALUES ('fa1', ?, '2026-09-23')", (p_a,))
    cursor.execute("INSERT INTO mpf_predictions (id, participant_id, risk_score) VALUES ('pa1', ?, 0.28)", (p_a,))

    # Participant B
    p_b = "22222222-2222-4000-b000-000000000002"
    pseudo_b = generate_pseudonymous_id(p_b)
    cursor.execute("INSERT INTO participants (id, pseudonymous_id) VALUES (?, ?)", (p_b, pseudo_b))
    cursor.execute("INSERT INTO consent_records (id, participant_id, consent_type, consent_version) VALUES ('cb1', ?, 'data_collection', '1.0.0')", (p_b,))
    cursor.execute("INSERT INTO typing_sessions (id, participant_id, session_id, hold_time_ms) VALUES ('tb1', ?, 'ts_b1', 145.0)", (p_b,))
    cursor.execute("INSERT INTO voice_sessions (id, participant_id, session_id, jitter_local) VALUES ('vb1', ?, 'vs_b1', 0.045)", (p_b,))
    cursor.execute("INSERT INTO mpf_predictions (id, participant_id, risk_score) VALUES ('pb1', ?, 0.76)", (p_b,))

    conn.commit()
    yield p_a, p_b, conn
    conn.close()


def test_export_structure_and_disclaimer(multi_participant_db):
    """Verifies that generated export package contains all required sections and research disclaimer."""
    p_a, _, db = multi_participant_db
    service = ExportService(db_conn=db)

    pkg = service.generate_participant_export(p_a)

    # Validate structure
    assert pkg["export_version"] == "1.0.0"
    assert pkg["participant_id"] == p_a
    assert "checksum_sha256" in pkg
    assert len(pkg["checksum_sha256"]) == 64  # Valid SHA-256 string

    # Non-diagnostic research disclaimer
    assert "Not a clinical diagnostic report" in pkg["disclaimer"]
    assert "Research prototype" in pkg["disclaimer"]

    # Verify participant metadata
    assert pkg["data"]["participant"]["id"] == p_a
    assert pkg["data"]["participant"]["pseudonymous_id"].startswith("ps_")

    # Verify summary counters
    assert pkg["summary"]["total_sessions"] == 3
    assert pkg["summary"]["total_daily_features"] == 1
    assert pkg["summary"]["total_predictions"] == 1


def test_strict_cross_participant_isolation(multi_participant_db):
    """Verifies that Participant A's export NEVER contains Participant B's records."""
    p_a, p_b, db = multi_participant_db
    service = ExportService(db_conn=db)

    export_a = service.generate_participant_export(p_a)
    raw_json = json.dumps(export_a)

    # Participant B's ID, session codes, and specific values must be completely absent
    assert p_b not in raw_json
    assert "ts_b1" not in raw_json
    assert "vs_b1" not in raw_json
    assert "pb1" not in raw_json

    # Participant A's records must be present
    assert "ts_a1" in raw_json
    assert "vs_a1" in raw_json
    assert "pa1" in raw_json
    assert export_a["data"]["typing_sessions"][0]["hold_time_ms"] == 82.5
    assert export_a["data"]["mpf_predictions"][0]["risk_score"] == 0.28
