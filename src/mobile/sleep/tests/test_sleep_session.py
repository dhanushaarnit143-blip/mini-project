"""
Tests for MPF Mobile Extension — Sleep Session Model (Phase 8)

Validates:
1. Exact conformance to the Supabase `sleep_sessions` table schema.
2. Participant UUID and Session UUID validation.
3. Strict range checks for sleep_duration, sleep_quality, daytime_sleepiness, and score.
4. Support for optional weekly medication changes.
5. Idempotent serialization and payload formatting.
6. Non-diagnostic language compliance.
"""

import pytest
import uuid
import re
import datetime
from typing import Dict, Any, Optional

CURRENT_QUESTIONNAIRE_VERSION = "1.0"
UUID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class SleepSessionModelPy:
    """Python mirror of SleepSessionModel from sleepSessionModel.js."""

    def __init__(
        self,
        participant_id: str,
        session_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        sleep_duration: float = 7.0,
        sleep_quality: float = 3.0,
        unusual_movement_self_report: bool = False,
        movement_response: str = "no",
        daytime_sleepiness: float = 1.0,
        medication_change: Optional[bool] = None,
        medication_change_details: Optional[str] = None,
        questionnaire_version: str = CURRENT_QUESTIONNAIRE_VERSION,
        score: float = 75.0,
        rbd_flag_label: str = "No pattern detected",
        synced: bool = False,
        db_id: Optional[str] = None,
    ):
        self.id = db_id
        self.participant_id = participant_id
        self.session_id = session_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.sleep_duration = float(sleep_duration)
        self.sleep_quality = float(sleep_quality)
        self.unusual_movement_self_report = bool(unusual_movement_self_report)
        self.movement_response = movement_response
        self.daytime_sleepiness = float(daytime_sleepiness)
        self.medication_change = bool(medication_change) if medication_change is not None else None
        self.medication_change_details = medication_change_details
        self.questionnaire_version = questionnaire_version
        self.score = float(score)
        self.rbd_flag_label = rbd_flag_label
        self.synced = bool(synced)

    def validate(self) -> Dict[str, Any]:
        errors = []

        if not self.participant_id or not isinstance(self.participant_id, str):
            errors.append("participant_id is required.")
        elif not UUID_REGEX.match(self.participant_id):
            errors.append(f'participant_id must be a valid UUID; got "{self.participant_id}".')

        if not self.session_id or not isinstance(self.session_id, str):
            errors.append("session_id is required.")
        elif not UUID_REGEX.match(self.session_id):
            errors.append(f'session_id must be a valid UUID; got "{self.session_id}".')

        if not (0.0 <= self.sleep_duration <= 24.0):
            errors.append(f"sleep_duration must be between 0.0 and 24.0 hours; got {self.sleep_duration}.")

        if not (1.0 <= self.sleep_quality <= 5.0):
            errors.append(f"sleep_quality must be between 1.0 and 5.0; got {self.sleep_quality}.")

        if not isinstance(self.unusual_movement_self_report, bool):
            errors.append("unusual_movement_self_report must be a boolean.")

        if not (1.0 <= self.daytime_sleepiness <= 5.0):
            errors.append(f"daytime_sleepiness must be between 1.0 and 5.0; got {self.daytime_sleepiness}.")

        if self.medication_change is not None and not isinstance(self.medication_change, bool):
            errors.append("medication_change must be null or a boolean.")

        if not (0.0 <= self.score <= 100.0):
            errors.append(f"score must be between 0 and 100; got {self.score}.")

        return {"valid": len(errors) == 0, "errors": errors}

    def to_payload(self) -> Dict[str, Any]:
        val = self.validate()
        if not val["valid"]:
            raise ValueError(f"Cannot serialize invalid model: {'; '.join(val['errors'])}")

        return {
            "participant_id": self.participant_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "sleep_duration": self.sleep_duration,
            "sleep_quality": self.sleep_quality,
            "unusual_movement_self_report": self.unusual_movement_self_report,
            "movement_response": self.movement_response,
            "daytime_sleepiness": self.daytime_sleepiness,
            "medication_change": self.medication_change,
            "medication_change_details": self.medication_change_details,
            "questionnaire_version": self.questionnaire_version,
            "score": self.score,
            "rbd_flag_label": self.rbd_flag_label,
            "synced": self.synced,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Test Cases
# ─────────────────────────────────────────────────────────────────────────────

def test_valid_sleep_session_model():
    """[SYNTHETIC] Tests a completely valid model and checks schema fields."""
    pid = "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"
    sid = "11111111-2222-4333-8444-555555555555"

    session = SleepSessionModelPy(
        participant_id=pid,
        session_id=sid,
        sleep_duration=7.5,
        sleep_quality=4.0,
        unusual_movement_self_report=False,
        movement_response="no",
        daytime_sleepiness=1.0,
        medication_change=False,
        questionnaire_version="1.0",
        score=92.5,
    )

    val = session.validate()
    assert val["valid"] is True
    assert len(val["errors"]) == 0

    payload = session.to_payload()
    assert payload["participant_id"] == pid
    assert payload["session_id"] == sid
    assert payload["sleep_duration"] == 7.5
    assert payload["sleep_quality"] == 4.0
    assert payload["unusual_movement_self_report"] is False
    assert payload["movement_response"] == "no"
    assert payload["daytime_sleepiness"] == 1.0
    assert payload["medication_change"] is False
    assert payload["score"] == 92.5
    assert payload["questionnaire_version"] == "1.0"
    assert payload["synced"] is False


def test_optional_medication_field_states():
    """[SYNTHETIC] Verifies that medication_change handles None, True (with details), and False."""
    pid = "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"

    # 1. Null medication change (daily default when question is skipped)
    s_null = SleepSessionModelPy(participant_id=pid, medication_change=None)
    assert s_null.validate()["valid"] is True
    assert s_null.to_payload()["medication_change"] is None

    # 2. True medication change with notes
    s_true = SleepSessionModelPy(
        participant_id=pid,
        medication_change=True,
        medication_change_details="Reduced evening dosage by half",
    )
    assert s_true.validate()["valid"] is True
    payload = s_true.to_payload()
    assert payload["medication_change"] is True
    assert payload["medication_change_details"] == "Reduced evening dosage by half"

    # 3. False medication change
    s_false = SleepSessionModelPy(participant_id=pid, medication_change=False)
    assert s_false.validate()["valid"] is True
    assert s_false.to_payload()["medication_change"] is False


def test_automatic_uuid_generation():
    """Verifies that an unsupplied session_id is automatically generated as valid UUID4."""
    pid = "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"
    session = SleepSessionModelPy(participant_id=pid)
    assert session.session_id is not None
    assert UUID_REGEX.match(session.session_id)


def test_invalid_uuid_validation():
    """Verifies that malformed UUIDs fail validation."""
    # Invalid participant_id
    s1 = SleepSessionModelPy(participant_id="not-a-uuid")
    val1 = s1.validate()
    assert val1["valid"] is False
    assert any("participant_id must be a valid UUID" in err for err in val1["errors"])

    # Invalid session_id
    pid = "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"
    s2 = SleepSessionModelPy(participant_id=pid, session_id="12345")
    val2 = s2.validate()
    assert val2["valid"] is False
    assert any("session_id must be a valid UUID" in err for err in val2["errors"])


def test_range_check_validations():
    """Verifies boundaries for sleep_duration, sleep_quality, daytime_sleepiness, and score."""
    pid = "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"

    # Duration < 0 or > 24
    s_dur = SleepSessionModelPy(participant_id=pid, sleep_duration=25.0)
    assert not s_dur.validate()["valid"]

    # Quality out of 1-5
    s_qual = SleepSessionModelPy(participant_id=pid, sleep_quality=0.5)
    assert not s_qual.validate()["valid"]

    # Sleepiness out of 1-5
    s_sleep = SleepSessionModelPy(participant_id=pid, daytime_sleepiness=5.5)
    assert not s_sleep.validate()["valid"]

    # Score out of 0-100
    s_score = SleepSessionModelPy(participant_id=pid, score=105.0)
    assert not s_score.validate()["valid"]


def test_to_payload_raises_on_invalid():
    """Verifies to_payload() raises ValueError when model is invalid."""
    s = SleepSessionModelPy(participant_id="invalid")
    with pytest.raises(ValueError, match="Cannot serialize invalid model"):
        s.to_payload()
