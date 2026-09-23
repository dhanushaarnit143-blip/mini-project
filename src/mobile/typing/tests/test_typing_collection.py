"""
Tests for MPF Mobile Extension — Typing Collector (Phase 4)

Verifies:
- Controlled in-app typing task records timing kinematics correctly (press, release, hold, IKI).
- No keystroke character, text, code, or private message content is ever recorded (Zero Text Capture).
- Backspace/correction events are logged as a boolean flag without character data.
- Guard against collection outside an active session.
- Client-side UUID session_id generation for idempotency.
"""

import pytest
import uuid
from pathlib import Path
import sys

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.mobile.typing.typing_service import (
    TypingCollector,
    TARGET_PHRASE,
)


class TestTypingCollection:
    def test_start_session_initialization(self):
        """Verifies session initialization with valid participant ID and target phrase."""
        collector = TypingCollector()
        participant_id = str(uuid.uuid4())
        
        info = collector.start_session(participant_id)
        
        assert collector.is_collecting is True
        assert info["participant_id"] == participant_id
        assert info["target_phrase"] == TARGET_PHRASE
        assert uuid.UUID(info["session_id"])  # Valid UUID
        assert len(collector.timing_events) == 0

    def test_start_session_requires_participant_id(self):
        """Verifies that an error is raised if participant_id is omitted."""
        collector = TypingCollector()
        with pytest.raises(ValueError, match="Participant ID is mandatory"):
            collector.start_session("")

    def test_timing_capture_hold_and_iki(self):
        """Verifies accurate calculation of hold duration and inter-key intervals."""
        collector = TypingCollector()
        collector.start_session(str(uuid.uuid4()))

        # Key 1: down at 100ms, up at 180ms (hold = 80ms, IKI = 0ms)
        p1 = collector.record_key_down(100.0, is_correction=False)
        e1 = collector.record_key_up(p1, 180.0)

        assert e1["hold_duration"] == 80.0
        assert e1["inter_key_interval"] == 0.0
        assert e1["is_correction"] is False

        # Key 2: down at 350ms, up at 420ms (hold = 70ms, IKI = 350 - 100 = 250ms)
        p2 = collector.record_key_down(350.0, is_correction=False)
        e2 = collector.record_key_up(p2, 420.0)

        assert e2["hold_duration"] == 70.0
        assert e2["inter_key_interval"] == 250.0
        assert e2["is_correction"] is False

        # Key 3 (backspace/correction): down at 600ms, up at 690ms (hold = 90ms, IKI = 250ms)
        p3 = collector.record_key_down(600.0, is_correction=True)
        e3 = collector.record_key_up(p3, 690.0)

        assert e3["hold_duration"] == 90.0
        assert e3["inter_key_interval"] == 250.0
        assert e3["is_correction"] is True

        summary = collector.end_session(end_timestamp_ms=1000.0, completed=True)
        assert summary["keystroke_count"] == 3
        assert summary["completed"] is True
        assert summary["session_duration"] == 1.0  # 1000ms / 1000

    def test_strict_privacy_zero_text_stored(self):
        """
        NON-NEGOTIABLE PRIVACY RULE:
        Verify that NO keystroke character, text string, password, or key code exists in timing data.
        """
        collector = TypingCollector()
        collector.start_session(str(uuid.uuid4()))

        p1 = collector.record_key_down(100.0, is_correction=False)
        collector.record_key_up(p1, 180.0)
        p2 = collector.record_key_down(300.0, is_correction=True)
        collector.record_key_up(p2, 380.0)

        summary = collector.end_session(end_timestamp_ms=500.0)

        # Audit all keys in timing events
        forbidden_attributes = ["text", "char", "key", "code", "letter", "symbol", "word", "content"]
        for event in summary["timing_events"]:
            for attr in forbidden_attributes:
                assert attr not in event, f"Privacy violation: '{attr}' found in timing event!"
            
            # Ensure only timing-specific kinematic keys exist
            assert set(event.keys()) == {
                "event_index", 
                "press_time", 
                "release_time", 
                "hold_duration", 
                "inter_key_interval", 
                "is_correction"
            }

    def test_record_outside_active_session_raises_error(self):
        """Verifies collector rejects keystroke events when session is inactive."""
        collector = TypingCollector()
        
        with pytest.raises(RuntimeError, match="session is not active"):
            collector.record_key_down(100.0)

        with pytest.raises(RuntimeError, match="session is not active"):
            collector.record_key_up(1, 200.0)

        with pytest.raises(RuntimeError, match="Session is not active"):
            collector.end_session(500.0)

    def test_privacy_audit_detects_contamination(self):
        """Verifies that verify_no_text_stored catches contaminated event data."""
        collector = TypingCollector()
        collector.start_session(str(uuid.uuid4()))
        p = collector.record_key_down(100.0)
        collector.record_key_up(p, 150.0)
        
        # Artificially inject forbidden text
        collector.timing_events[0]["char"] = "a"
        
        with pytest.raises(ValueError, match="PRIVACY VIOLATION"):
            collector.verify_no_text_stored()
