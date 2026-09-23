"""
MPF Mobile Extension — Typing Dynamics Biomarker Service (Phase 4)

Provides backend and test-compatible implementation of:
1. In-app controlled timing kinematics collection.
2. Feature extraction (speed, IKI mean/std, pause rate, correction rate, rhythm variability).
3. Standardized quality scoring with personal baseline gating (quality_score >= 0.5).
4. TypingSession data model conforming to Supabase typing_sessions table schema.
5. Strict privacy verification: zero text content, keystroke codes, or PII stored.
"""

import math
import uuid
import datetime
from typing import Dict, List, Any, Optional, Tuple

TARGET_PHRASE = "The quick brown fox jumps over the lazy dog."
FEATURE_VERSION = "1.0.0"
MIN_BASELINE_QUALITY_THRESHOLD = 0.50
MIN_KEYSTROKE_COUNT = 20
MIN_TYPING_SPEED_CPS = 0.50
MAX_ALLOWED_INTERRUPTION_MS = 10000.0  # 10s
MAX_ALLOWED_CORRECTION_RATIO = 0.50


class TypingCollector:
    """
    Controlled in-app timing kinematics collector.
    Records press/release timestamps, hold duration, IKI, and correction flag.
    STRICT PRIVACY: Never records character codes or text content.
    """
    def __init__(self):
        self.session_id: Optional[str] = None
        self.participant_id: Optional[str] = None
        self.is_collecting: bool = False
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.timing_events: List[Dict[str, Any]] = []
        self._last_press_time: Optional[float] = None
        self._pending_presses: Dict[int, Dict[str, Any]] = {}
        self._counter: int = 0

    def start_session(self, participant_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        if not participant_id:
            raise ValueError("Participant ID is mandatory.")
        self.participant_id = participant_id
        self.session_id = session_id or str(uuid.uuid4())
        self.is_collecting = True
        self.start_time = 0.0  # Normalized start ms
        self.end_time = None
        self.timing_events = []
        self._pending_presses.clear()
        self._last_press_time = None
        self._counter = 0

        return {
            "session_id": self.session_id,
            "participant_id": self.participant_id,
            "target_phrase": TARGET_PHRASE
        }

    def record_key_down(self, timestamp_ms: float, is_correction: bool = False) -> int:
        if not self.is_collecting:
            raise RuntimeError("Cannot record keystroke: session is not active.")

        iki = 0.0
        if self._last_press_time is not None:
            iki = max(0.0, timestamp_ms - self._last_press_time)

        self._last_press_time = timestamp_ms
        self._counter += 1
        press_id = self._counter

        self._pending_presses[press_id] = {
            "press_time": timestamp_ms,
            "iki": iki,
            "is_correction": bool(is_correction)
        }
        return press_id

    def record_key_up(self, press_id: int, timestamp_ms: float) -> Dict[str, Any]:
        if not self.is_collecting:
            raise RuntimeError("Cannot record key release: session is not active.")

        pending = self._pending_presses.pop(press_id, None)
        if not pending:
            raise ValueError(f"No active press found for press_id {press_id}")

        hold_duration = max(0.0, timestamp_ms - pending["press_time"])

        event = {
            "event_index": len(self.timing_events) + 1,
            "press_time": round(pending["press_time"], 2),
            "release_time": round(timestamp_ms, 2),
            "hold_duration": round(hold_duration, 2),
            "inter_key_interval": round(pending["iki"], 2),
            "is_correction": pending["is_correction"]
        }
        self.timing_events.append(event)
        return event

    def end_session(self, end_timestamp_ms: float, completed: bool = True) -> Dict[str, Any]:
        if not self.is_collecting:
            raise RuntimeError("Session is not active.")

        self.end_time = end_timestamp_ms
        self.is_collecting = False
        duration_seconds = max(0.0, (self.end_time - (self.start_time or 0.0)) / 1000.0)

        # Audit privacy guarantee
        self.verify_no_text_stored()

        return {
            "session_id": self.session_id,
            "participant_id": self.participant_id,
            "task_type": "controlled_phrase",
            "session_duration": round(duration_seconds, 3),
            "keystroke_count": len(self.timing_events),
            "completed": bool(completed),
            "timing_events": [dict(e) for e in self.timing_events]
        }

    def verify_no_text_stored(self) -> bool:
        forbidden_keys = {"text", "char", "key", "letter", "code", "password", "content"}
        for event in self.timing_events:
            if any(k in event for k in forbidden_keys):
                raise ValueError("PRIVACY VIOLATION: Keystroke text or character stored in timing event!")
        return True


class TypingFeatureExtractor:
    """
    Extracts digital biomarker features from raw keystroke timing kinematics.
    """
    @staticmethod
    def extract_features(raw_session_data: Dict[str, Any]) -> Dict[str, Any]:
        timing_events = raw_session_data.get("timing_events", [])
        duration_seconds = max(0.0, float(raw_session_data.get("session_duration", 0.0)))
        keystroke_count = len(timing_events)

        # 1. Typing speed (chars / sec)
        typing_speed = round(keystroke_count / duration_seconds, 3) if duration_seconds > 0 else 0.0

        # 2. Inter-key intervals (for presses >= 2)
        ikis: List[float] = []
        pause_count = 0
        correction_count = 0

        for i, event in enumerate(timing_events):
            if i > 0:
                iki = max(0.0, float(event.get("inter_key_interval", 0.0)))
                ikis.append(iki)
                if iki > 500.0:
                    pause_count += 1

            if event.get("is_correction", False):
                correction_count += 1

        # 3. Mean & Standard Deviation of IKIs
        mean_iki = 0.0
        std_iki = 0.0
        if ikis:
            mean_iki = round(sum(ikis) / len(ikis), 2)
            if len(ikis) > 1:
                variance = sum((x - mean_iki) ** 2 for x in ikis) / (len(ikis) - 1)
                std_iki = round(math.sqrt(variance), 2)

        # 4. Pause Rate (pauses > 500ms per minute)
        duration_min = duration_seconds / 60.0
        pause_rate = round(pause_count / duration_min, 2) if duration_min > 0 else 0.0

        # 5. Correction Rate (corrections per minute)
        correction_rate = round(correction_count / duration_min, 2) if duration_min > 0 else 0.0

        # 6. Rhythm Variability (CV = std / mean)
        rhythm_variability = round(std_iki / mean_iki, 4) if mean_iki > 0 else 0.0

        return {
            "session_duration": round(duration_seconds, 2),
            "typing_speed": typing_speed,
            "mean_inter_key_interval": mean_iki,
            "std_inter_key_interval": std_iki,
            "pause_rate": pause_rate,
            "correction_rate": correction_rate,
            "rhythm_variability": rhythm_variability,
            "keystroke_count": keystroke_count,
            "pause_count": pause_count,
            "correction_count": correction_count,
            "feature_version": FEATURE_VERSION
        }


class TypingQualityScorer:
    """
    Evaluates quality score across 5 standardized components.
    Gating: quality_score >= 0.5 for baseline eligibility.
    """
    @staticmethod
    def calculate_quality_score(
        completed: bool,
        timing_events: List[Dict[str, Any]],
        typing_speed: float,
        keystroke_count: Optional[int] = None,
        correction_count: Optional[int] = None
    ) -> Dict[str, Any]:
        count = keystroke_count if keystroke_count is not None else len(timing_events)
        corrections = (
            correction_count 
            if correction_count is not None 
            else sum(1 for e in timing_events if e.get("is_correction", False))
        )

        breakdown = {
            "task_completed": 0.0,
            "sufficient_samples": 0.0,
            "no_abnormal_interruptions": 0.0,
            "reasonable_speed": 0.0,
            "no_excessive_corrections": 0.0
        }
        reasons = []

        # 1. Task completed (+0.30)
        if completed:
            breakdown["task_completed"] = 0.30
        else:
            reasons.append("Task incomplete")

        # 2. Sufficient keystrokes > 20 (+0.20)
        if count > MIN_KEYSTROKE_COUNT:
            breakdown["sufficient_samples"] = 0.20
        else:
            reasons.append(f"Insufficient keystrokes: {count} <= {MIN_KEYSTROKE_COUNT}")

        # 3. No abnormal interruptions (+0.20)
        has_abnormal_pause = any(
            float(e.get("inter_key_interval", 0.0)) > MAX_ALLOWED_INTERRUPTION_MS 
            for e in timing_events
        )
        if not has_abnormal_pause and count > 0:
            breakdown["no_abnormal_interruptions"] = 0.20
        elif has_abnormal_pause:
            reasons.append("Abnormal pause (>10s) detected")

        # 4. Reasonable typing speed > 0.5 chars/sec (+0.15)
        if typing_speed > MIN_TYPING_SPEED_CPS:
            breakdown["reasonable_speed"] = 0.15
        else:
            reasons.append(f"Typing speed too low: {typing_speed} <= {MIN_TYPING_SPEED_CPS}")

        # 5. No excessive corrections: error rate <= 50% (+0.15)
        error_rate = (corrections / count) if count > 0 else 0.0
        if error_rate <= MAX_ALLOWED_CORRECTION_RATIO and count > 0:
            breakdown["no_excessive_corrections"] = 0.15
        elif error_rate > MAX_ALLOWED_CORRECTION_RATIO:
            reasons.append(f"Excessive error rate: {error_rate*100:.1f}% > 50%")

        total_score = sum(breakdown.values())
        quality_score = round(min(1.0, max(0.0, total_score)), 3)
        is_baseline_eligible = quality_score >= MIN_BASELINE_QUALITY_THRESHOLD

        return {
            "quality_score": quality_score,
            "is_baseline_eligible": is_baseline_eligible,
            "min_threshold": MIN_BASELINE_QUALITY_THRESHOLD,
            "breakdown": breakdown,
            "rejection_reasons": reasons
        }


class TypingSession:
    """
    Standardized TypingSession entity strictly mirroring Supabase typing_sessions schema.
    """
    def __init__(
        self,
        participant_id: str,
        duration: float,
        typing_speed: float,
        mean_inter_key_interval: float,
        std_inter_key_interval: float,
        pause_rate: float,
        correction_rate: float,
        rhythm_variability: float,
        quality_score: float,
        session_id: Optional[str] = None,
        task_type: str = "controlled_phrase",
        feature_version: str = FEATURE_VERSION,
        timestamp: Optional[str] = None,
        synced: bool = False,
        id: Optional[str] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.participant_id = participant_id
        self.session_id = session_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.task_type = task_type
        self.duration = float(duration)
        self.typing_speed = float(typing_speed)
        self.mean_inter_key_interval = float(mean_inter_key_interval)
        self.std_inter_key_interval = float(std_inter_key_interval)
        self.pause_rate = float(pause_rate)
        self.correction_rate = float(correction_rate)
        self.rhythm_variability = float(rhythm_variability)
        self.quality_score = float(quality_score)
        self.feature_version = feature_version
        self.synced = synced

    def validate(self) -> Tuple[bool, List[str]]:
        errors = []
        try:
            uuid.UUID(self.participant_id)
        except (ValueError, TypeError):
            errors.append(f"Invalid participant_id UUID: {self.participant_id}")

        try:
            uuid.UUID(self.session_id)
        except (ValueError, TypeError):
            errors.append(f"Invalid session_id UUID: {self.session_id}")

        if self.task_type not in ("controlled_phrase", "free_typing"):
            errors.append(f"Invalid task_type: {self.task_type}")

        if self.duration < 0: errors.append("duration must be >= 0")
        if self.typing_speed < 0: errors.append("typing_speed must be >= 0")
        if self.mean_inter_key_interval < 0: errors.append("mean_inter_key_interval must be >= 0")
        if self.std_inter_key_interval < 0: errors.append("std_inter_key_interval must be >= 0")
        if self.pause_rate < 0: errors.append("pause_rate must be >= 0")
        if self.correction_rate < 0: errors.append("correction_rate must be >= 0")
        if self.rhythm_variability < 0: errors.append("rhythm_variability must be >= 0")
        if not (0.0 <= self.quality_score <= 1.0):
            errors.append(f"quality_score must be between 0.0 and 1.0 (got {self.quality_score})")

        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        is_valid, errors = self.validate()
        if not is_valid:
            raise ValueError(f"TypingSession validation failure: {'; '.join(errors)}")

        return {
            "participant_id": self.participant_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "task_type": self.task_type,
            "duration": self.duration,
            "typing_speed": self.typing_speed,
            "mean_inter_key_interval": self.mean_inter_key_interval,
            "std_inter_key_interval": self.std_inter_key_interval,
            "pause_rate": self.pause_rate,
            "correction_rate": self.correction_rate,
            "rhythm_variability": self.rhythm_variability,
            "quality_score": self.quality_score,
            "feature_version": self.feature_version,
            "synced": self.synced
        }

    def is_baseline_eligible(self) -> bool:
        return self.quality_score >= MIN_BASELINE_QUALITY_THRESHOLD


def generate_synthetic_timing_data(
    keystroke_count: int = 44,
    mean_iki_ms: float = 250.0,
    std_iki_ms: float = 40.0,
    hold_duration_ms: float = 80.0,
    pauses: int = 1,
    corrections: int = 2,
    abnormal_pause_ms: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Generates deterministic synthetic timing events for unit testing.
    Zero text content is included.
    """
    events = []
    current_time = 1000.0

    # Determine pause indices
    pause_indices = set([10, 25][:pauses]) if pauses > 0 else set()
    correction_indices = set([5, 18, 30][:corrections]) if corrections > 0 else set()

    for i in range(keystroke_count):
        if i == 0:
            iki = 0.0
        elif abnormal_pause_ms and i == 15:
            iki = abnormal_pause_ms
        elif i in pause_indices:
            iki = 650.0  # Pause > 500ms
        else:
            # Deterministic variation
            offset = ((i % 5) - 2) * (std_iki_ms / 2.0)
            iki = max(50.0, mean_iki_ms + offset)

        press_time = current_time + iki
        release_time = press_time + hold_duration_ms
        current_time = press_time

        events.append({
            "event_index": i + 1,
            "press_time": round(press_time, 2),
            "release_time": round(release_time, 2),
            "hold_duration": round(hold_duration_ms, 2),
            "inter_key_interval": round(iki, 2),
            "is_correction": (i in correction_indices)
        })

    return events
