"""
Tests for MPF Mobile Extension — Typing Quality Scorer & Session Model (Phase 4)

Verifies:
- Standardized additive quality scoring (+0.3, +0.2, +0.2, +0.15, +0.15).
- Low-quality sessions (quality_score < 0.5) are flagged and blocked from baseline engine.
- High-quality sessions (quality_score >= 0.5) are accepted.
- Session model strictly satisfies Supabase typing_sessions schema constraints.
- Idempotency key (session_id) prevents duplicate insertions.
"""

import pytest
import uuid
import sqlite3
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.mobile.typing.typing_service import (
    TypingQualityScorer,
    TypingSession,
    generate_synthetic_timing_data,
    MIN_BASELINE_QUALITY_THRESHOLD,
)


@pytest.fixture
def sqlite_test_db():
    """In-memory SQLite database matching Supabase typing_sessions schema."""
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
    """)
    conn.commit()
    yield conn
    conn.close()


class TestTypingQualityAndModel:
    def test_quality_scoring_full_credit(self):
        """
        A completed session with 44 keystrokes, speed 2.2 cps, no abnormal pauses,
        and <= 50% error rate must receive full score: 1.0.
        """
        timing_events = generate_synthetic_timing_data(
            keystroke_count=44,
            pauses=1,
            corrections=2
        )

        res = TypingQualityScorer.calculate_quality_score(
            completed=True,
            timing_events=timing_events,
            typing_speed=2.2,
            keystroke_count=44,
            correction_count=2
        )

        assert res["quality_score"] == 1.0
        assert res["is_baseline_eligible"] is True
        assert res["breakdown"]["task_completed"] == 0.30
        assert res["breakdown"]["sufficient_samples"] == 0.20
        assert res["breakdown"]["no_abnormal_interruptions"] == 0.20
        assert res["breakdown"]["reasonable_speed"] == 0.15
        assert res["breakdown"]["no_excessive_corrections"] == 0.15
        assert len(res["rejection_reasons"]) == 0

    def test_low_quality_session_flagged_and_rejected_for_baseline(self):
        """
        Incomplete session with only 10 keystrokes and speed 0.3 cps
        must receive score < 0.5 and be flagged as ineligible for baseline.
        """
        timing_events = generate_synthetic_timing_data(
            keystroke_count=10,
            pauses=0,
            corrections=1
        )

        res = TypingQualityScorer.calculate_quality_score(
            completed=False,  # 0.0
            timing_events=timing_events,
            typing_speed=0.3, # <= 0.5 -> 0.0
            keystroke_count=10, # <= 20 -> 0.0
            correction_count=1  # 1/10 = 10% <= 50% -> 0.15
        )

        # Expected score: 0.0 (not completed) + 0.0 (count <= 20) + 0.20 (no abnormal pause) + 0.0 (speed <= 0.5) + 0.15 (errors <= 50%) = 0.35
        assert res["quality_score"] == 0.35
        assert res["is_baseline_eligible"] is False
        assert res["quality_score"] < MIN_BASELINE_QUALITY_THRESHOLD
        assert len(res["rejection_reasons"]) > 0

    def test_abnormal_interruption_penalized(self):
        """
        A session with an abnormal interruption (pause > 10,000ms / 10s)
        loses the 0.20 interruption credit.
        """
        timing_events = generate_synthetic_timing_data(
            keystroke_count=44,
            abnormal_pause_ms=12500.0  # 12.5 seconds pause
        )

        res = TypingQualityScorer.calculate_quality_score(
            completed=True,
            timing_events=timing_events,
            typing_speed=1.5,
            keystroke_count=44,
            correction_count=1
        )

        assert res["breakdown"]["no_abnormal_interruptions"] == 0.0
        assert res["quality_score"] == 0.80  # 1.0 - 0.20
        assert "Abnormal pause" in " ".join(res["rejection_reasons"])

    def test_excessive_corrections_penalized(self):
        """
        A session with > 50% error rate loses the 0.15 error rate credit.
        """
        timing_events = generate_synthetic_timing_data(
            keystroke_count=30,
            corrections=18  # 18/30 = 60% > 50%
        )

        res = TypingQualityScorer.calculate_quality_score(
            completed=True,
            timing_events=timing_events,
            typing_speed=1.2,
            keystroke_count=30,
            correction_count=18
        )

        assert res["breakdown"]["no_excessive_corrections"] == 0.0
        assert res["quality_score"] == 0.85  # 1.0 - 0.15
        assert any("Excessive error rate" in r for r in res["rejection_reasons"])

    def test_session_model_validation_against_schema(self):
        """Verifies TypingSession validation against PostgreSQL constraints."""
        valid_pid = str(uuid.uuid4())
        valid_sid = str(uuid.uuid4())

        session = TypingSession(
            participant_id=valid_pid,
            session_id=valid_sid,
            duration=18.5,
            typing_speed=2.37,
            mean_inter_key_interval=275.4,
            std_inter_key_interval=48.2,
            pause_rate=3.24,
            correction_rate=1.62,
            rhythm_variability=0.175,
            quality_score=0.85
        )

        is_valid, errors = session.validate()
        assert is_valid is True
        assert len(errors) == 0

        # Negative duration violates check constraint
        invalid_session = TypingSession(
            participant_id=valid_pid,
            session_id=valid_sid,
            duration=-5.0,
            typing_speed=2.0,
            mean_inter_key_interval=200.0,
            std_inter_key_interval=30.0,
            pause_rate=1.0,
            correction_rate=1.0,
            rhythm_variability=0.15,
            quality_score=1.5  # Invalid quality score > 1.0
        )
        is_valid, errors = invalid_session.validate()
        assert is_valid is False
        assert any("duration must be >= 0" in e for e in errors)
        assert any("quality_score must be between" in e for e in errors)

    def test_idempotency_prevents_duplicate_uploads(self, sqlite_test_db):
        """
        Verifies that using client-generated session_id as an idempotency key
        prevents duplicate uploads in the database.
        """
        participant_id = str(uuid.uuid4())
        cursor = sqlite_test_db.cursor()

        # Seed participant
        cursor.execute(
            "INSERT INTO participants (id, pseudonymous_id) VALUES (?, ?)",
            (participant_id, "ps_test_typing_01")
        )

        session_id = str(uuid.uuid4())
        session = TypingSession(
            participant_id=participant_id,
            session_id=session_id,
            duration=20.0,
            typing_speed=2.2,
            mean_inter_key_interval=250.0,
            std_inter_key_interval=35.0,
            pause_rate=2.0,
            correction_rate=1.0,
            rhythm_variability=0.14,
            quality_score=0.90,
            synced=True
        )

        payload = session.to_dict()

        # First insert: succeeds
        cursor.execute("""
        INSERT INTO typing_sessions (
            id, participant_id, session_id, timestamp, task_type,
            duration, typing_speed, mean_inter_key_interval, std_inter_key_interval,
            pause_rate, correction_rate, rhythm_variability, quality_score,
            feature_version, synced
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()), payload["participant_id"], payload["session_id"],
            payload["timestamp"], payload["task_type"], payload["duration"],
            payload["typing_speed"], payload["mean_inter_key_interval"],
            payload["std_inter_key_interval"], payload["pause_rate"],
            payload["correction_rate"], payload["rhythm_variability"],
            payload["quality_score"], payload["feature_version"], 1
        ))
        sqlite_test_db.commit()

        # Second insert with identical session_id (idempotency conflict) must raise IntegrityError
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
            INSERT INTO typing_sessions (
                id, participant_id, session_id, timestamp, task_type,
                duration, typing_speed, mean_inter_key_interval, std_inter_key_interval,
                pause_rate, correction_rate, rhythm_variability, quality_score,
                feature_version, synced
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), payload["participant_id"], payload["session_id"],
                payload["timestamp"], payload["task_type"], payload["duration"],
                payload["typing_speed"], payload["mean_inter_key_interval"],
                payload["std_inter_key_interval"], payload["pause_rate"],
                payload["correction_rate"], payload["rhythm_variability"],
                payload["quality_score"], payload["feature_version"], 1
            ))
            sqlite_test_db.commit()

        # Confirm count remains exactly 1
        cursor.execute("SELECT count(*) FROM typing_sessions WHERE session_id = ?", (session_id,))
        count = cursor.fetchone()[0]
        assert count == 1
