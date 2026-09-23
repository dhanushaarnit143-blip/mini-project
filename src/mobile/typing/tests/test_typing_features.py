"""
Tests for MPF Mobile Extension — Typing Feature Extractor (Phase 4)

Verifies:
- Accurate mathematical computation of timing kinematics:
  - typing_speed (chars/sec)
  - mean_inter_key_interval (ms)
  - std_inter_key_interval (ms)
  - pause_rate (pauses > 500ms per minute)
  - correction_rate (corrections per minute)
  - rhythm_variability (coefficient of variation: std/mean)
  - session_duration (seconds)
- Robust handling of edge cases (zero duration, single keystroke, zero division safety).
- Fully reproducible feature versioning ('1.0.0').
"""

import pytest
import math
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.mobile.typing.typing_service import (
    TypingFeatureExtractor,
    generate_synthetic_timing_data,
    FEATURE_VERSION,
)


class TestTypingFeatures:
    def test_feature_extraction_synthetic_regular_typing(self):
        """
        Tests extraction on a standard synthetic typing session of 44 keystrokes.
        Duration: 22.0 seconds -> Speed: 44 / 22 = 2.000 chars/sec.
        """
        # 44 keystrokes: 1 initial (iki=0), 43 intervals of 250ms
        events = []
        curr = 0.0
        for i in range(44):
            iki = 0.0 if i == 0 else 250.0
            press = curr + iki
            curr = press
            events.append({
                "event_index": i + 1,
                "press_time": press,
                "release_time": press + 80.0,
                "hold_duration": 80.0,
                "inter_key_interval": iki,
                "is_correction": (i == 10 or i == 20)  # 2 corrections
            })

        session_data = {
            "session_duration": 22.0,
            "timing_events": events
        }

        features = TypingFeatureExtractor.extract_features(session_data)

        assert features["session_duration"] == 22.0
        assert features["typing_speed"] == 2.0  # 44 / 22
        assert features["keystroke_count"] == 44
        assert features["mean_inter_key_interval"] == 250.0
        assert features["std_inter_key_interval"] == 0.0  # Identical intervals
        assert features["rhythm_variability"] == 0.0      # std / mean = 0
        assert features["pause_rate"] == 0.0              # No pauses > 500ms
        # 2 corrections in 22 seconds -> 2 / (22 / 60) = 5.45 corrections/min
        assert features["correction_count"] == 2
        assert features["correction_rate"] == round(2.0 / (22.0 / 60.0), 2)
        assert features["feature_version"] == FEATURE_VERSION

    def test_pause_rate_calculation(self):
        """
        Verifies that intervals strictly > 500ms are classified as pauses and scaled per minute.
        """
        # Session duration: 60.0 seconds (1.0 minute)
        # 3 pauses > 500ms: 600ms, 800ms, 1200ms
        events = [
            {"event_index": 1, "inter_key_interval": 0.0, "is_correction": False},
            {"event_index": 2, "inter_key_interval": 300.0, "is_correction": False},
            {"event_index": 3, "inter_key_interval": 600.0, "is_correction": False},  # Pause 1
            {"event_index": 4, "inter_key_interval": 400.0, "is_correction": False},
            {"event_index": 5, "inter_key_interval": 800.0, "is_correction": False},  # Pause 2
            {"event_index": 6, "inter_key_interval": 500.0, "is_correction": False},  # Boundary (not > 500)
            {"event_index": 7, "inter_key_interval": 1200.0, "is_correction": False}, # Pause 3
        ]

        session_data = {
            "session_duration": 60.0,
            "timing_events": events
        }

        features = TypingFeatureExtractor.extract_features(session_data)

        assert features["pause_count"] == 3
        assert features["pause_rate"] == 3.0  # 3 pauses / 1 minute = 3.0 pauses/min

    def test_rhythm_variability_coefficient_of_variation(self):
        """
        Verifies coefficient of variation (CV = std / mean) calculation with varied IKIs.
        """
        # IKIs: [200, 400, 200, 400] -> Mean = 300, Sample Variance = 13333.33 -> Std ~ 115.47
        events = [
            {"event_index": 1, "inter_key_interval": 0.0, "is_correction": False},
            {"event_index": 2, "inter_key_interval": 200.0, "is_correction": False},
            {"event_index": 3, "inter_key_interval": 400.0, "is_correction": False},
            {"event_index": 4, "inter_key_interval": 200.0, "is_correction": False},
            {"event_index": 5, "inter_key_interval": 400.0, "is_correction": False},
        ]

        session_data = {
            "session_duration": 5.0,
            "timing_events": events
        }

        features = TypingFeatureExtractor.extract_features(session_data)

        assert features["mean_inter_key_interval"] == 300.0
        # Expected sample std for [200, 400, 200, 400]:
        # deviations: -100, 100, -100, 100 -> squared: 10000 * 4 = 40000 / 3 = 13333.33 -> sqrt ~ 115.47
        expected_std = round(math.sqrt(40000.0 / 3.0), 2)
        assert features["std_inter_key_interval"] == expected_std
        expected_cv = round(expected_std / 300.0, 4)
        assert features["rhythm_variability"] == expected_cv

    def test_edge_case_zero_duration(self):
        """Zero duration should safely return 0.0 for rates without throwing division-by-zero."""
        session_data = {
            "session_duration": 0.0,
            "timing_events": []
        }
        features = TypingFeatureExtractor.extract_features(session_data)
        assert features["typing_speed"] == 0.0
        assert features["pause_rate"] == 0.0
        assert features["correction_rate"] == 0.0
        assert features["mean_inter_key_interval"] == 0.0
        assert features["std_inter_key_interval"] == 0.0
        assert features["rhythm_variability"] == 0.0

    def test_edge_case_single_keystroke(self):
        """A single keystroke has no consecutive intervals; std and IKI should be 0.0."""
        session_data = {
            "session_duration": 2.0,
            "timing_events": [
                {"event_index": 1, "inter_key_interval": 0.0, "is_correction": False}
            ]
        }
        features = TypingFeatureExtractor.extract_features(session_data)
        assert features["typing_speed"] == 0.5  # 1 / 2.0
        assert features["mean_inter_key_interval"] == 0.0
        assert features["std_inter_key_interval"] == 0.0
        assert features["rhythm_variability"] == 0.0
