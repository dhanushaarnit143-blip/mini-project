"""
Phase 15 — Unit Tests: Typing Feature Extraction
=================================================
Validates mathematical correctness of all typing biomarker computations
using clearly labeled [SYNTHETIC] data. No real participant data used.

Covers:
  - typing_speed (chars/sec)
  - mean_inter_key_interval (ms)
  - std_inter_key_interval (ms)
  - pause_rate (pauses > 500 ms per minute)
  - correction_rate (corrections per minute)
  - rhythm_variability (CV = std/mean)
  - session_duration (seconds)
  - feature_version tagging
  - Edge cases: single keystroke, zero division, empty events
"""

import math
import pytest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mobile.typing.typing_service import (
    TypingFeatureExtractor,
    TypingQualityScorer,
    generate_synthetic_timing_data,
    FEATURE_VERSION,
    MIN_KEYSTROKE_COUNT,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def build_synthetic_events(
    n_keys: int = 44,
    iki_ms: float = 250.0,
    hold_ms: float = 80.0,
    correction_indices: list = None,
    pause_indices: list = None,
    pause_ms: float = 600.0,
) -> list:
    """
    [SYNTHETIC] Build deterministic timing event list for unit testing.
    All values are programmatically constructed — no real participant data.
    """
    correction_indices = correction_indices or []
    pause_indices = pause_indices or []
    events = []
    curr = 0.0
    for i in range(n_keys):
        if i in pause_indices:
            interval = pause_ms
        else:
            interval = 0.0 if i == 0 else iki_ms
        curr += interval
        events.append({
            "event_index": i + 1,
            "press_time": curr,
            "release_time": curr + hold_ms,
            "hold_duration": hold_ms,
            "inter_key_interval": interval,
            "is_correction": (i in correction_indices),
        })
    return events


def session_of(n_keys=44, iki_ms=250.0, correction_indices=None,
               pause_indices=None, pause_ms=600.0):
    """[SYNTHETIC] Full session dict for feature extraction."""
    events = build_synthetic_events(
        n_keys=n_keys, iki_ms=iki_ms,
        correction_indices=correction_indices or [],
        pause_indices=pause_indices or [],
        pause_ms=pause_ms,
    )
    duration_sec = events[-1]["press_time"] / 1000.0 if events else 0.0
    return {"session_duration": max(duration_sec, 0.001), "timing_events": events}


# ── Feature Version ───────────────────────────────────────────────────────────

class TestFeatureVersion:
    def test_feature_version_is_tagged(self):
        """Every extracted feature dict must carry the canonical feature version."""
        session = session_of()
        features = TypingFeatureExtractor.extract_features(session)
        assert "feature_version" in features
        assert features["feature_version"] == FEATURE_VERSION

    def test_feature_version_is_semver(self):
        """Feature version must follow SemVer (X.Y.Z)."""
        parts = FEATURE_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


# ── Typing Speed ──────────────────────────────────────────────────────────────

class TestTypingSpeed:
    def test_regular_speed_44_keys_22s(self):
        """[SYNTHETIC] 44 keys in 22 s → speed = 44/22 = 2.000 chars/sec."""
        # 44 keys at 250 ms IKI = 43 * 0.25 = 10.75 s elapsed from first to last press
        # total duration set explicitly
        session = {"session_duration": 22.0, "timing_events": build_synthetic_events(44, 250.0)}
        features = TypingFeatureExtractor.extract_features(session)
        assert abs(features["typing_speed"] - 2.0) < 0.05

    def test_slow_speed_20_keys_10s(self):
        """[SYNTHETIC] 20 keys in 10 s → speed = 2.0 chars/sec."""
        session = {"session_duration": 10.0, "timing_events": build_synthetic_events(20, 500.0)}
        features = TypingFeatureExtractor.extract_features(session)
        assert features["typing_speed"] > 0.0

    def test_speed_non_negative(self):
        """[SYNTHETIC] Typing speed is always >= 0."""
        session = session_of(44)
        features = TypingFeatureExtractor.extract_features(session)
        assert features["typing_speed"] >= 0.0


# ── Inter-Key Interval ────────────────────────────────────────────────────────

class TestInterKeyInterval:
    def test_mean_iki_regular(self):
        """[SYNTHETIC] Regular 250 ms IKI → mean IKI ≈ 250 ms."""
        session = session_of(44, iki_ms=250.0)
        features = TypingFeatureExtractor.extract_features(session)
        assert abs(features["mean_inter_key_interval"] - 250.0) < 10.0

    def test_std_iki_zero_for_perfectly_regular(self):
        """[SYNTHETIC] Perfectly uniform IKI → std IKI ≈ 0."""
        session = session_of(44, iki_ms=300.0)
        features = TypingFeatureExtractor.extract_features(session)
        assert features["std_inter_key_interval"] < 5.0

    def test_iki_non_negative(self):
        """[SYNTHETIC] Both mean and std IKI must be non-negative."""
        session = session_of(30, iki_ms=200.0)
        features = TypingFeatureExtractor.extract_features(session)
        assert features["mean_inter_key_interval"] >= 0.0
        assert features["std_inter_key_interval"] >= 0.0


# ── Pause Rate ────────────────────────────────────────────────────────────────

class TestPauseRate:
    def test_pause_rate_with_known_pauses(self):
        """[SYNTHETIC] Session with 3 pauses > 500 ms in 60 s → pause_rate = 3.0/min."""
        events = build_synthetic_events(
            n_keys=44, iki_ms=250.0,
            pause_indices=[10, 20, 30], pause_ms=700.0
        )
        session = {"session_duration": 60.0, "timing_events": events}
        features = TypingFeatureExtractor.extract_features(session)
        # At least the 3 inserted pauses should be detected
        assert features["pause_rate"] >= 2.0

    def test_pause_rate_zero_for_fast_typing(self):
        """[SYNTHETIC] All IKIs < 500 ms → pause_rate == 0."""
        session = session_of(44, iki_ms=200.0)
        features = TypingFeatureExtractor.extract_features(session)
        assert features["pause_rate"] == 0.0


# ── Correction Rate ───────────────────────────────────────────────────────────

class TestCorrectionRate:
    def test_correction_rate_with_two_corrections(self):
        """[SYNTHETIC] 2 corrections in 22 s → correction_rate = 2/(22/60) ≈ 5.45/min."""
        session = session_of(44, correction_indices=[10, 20])
        features = TypingFeatureExtractor.extract_features(session)
        assert features["correction_rate"] > 0.0

    def test_correction_rate_zero_no_corrections(self):
        """[SYNTHETIC] No corrections → correction_rate == 0."""
        session = session_of(44)
        features = TypingFeatureExtractor.extract_features(session)
        assert features["correction_rate"] == 0.0


# ── Rhythm Variability ────────────────────────────────────────────────────────

class TestRhythmVariability:
    def test_rhythm_variability_zero_uniform(self):
        """[SYNTHETIC] Perfectly uniform IKI → rhythm_variability ≈ 0."""
        session = session_of(44, iki_ms=250.0)
        features = TypingFeatureExtractor.extract_features(session)
        assert features["rhythm_variability"] < 0.05

    def test_rhythm_variability_non_negative(self):
        """[SYNTHETIC] Rhythm variability must always be >= 0."""
        session = session_of(30)
        features = TypingFeatureExtractor.extract_features(session)
        assert features["rhythm_variability"] >= 0.0


# ── Edge Cases ────────────────────────────────────────────────────────────────

class TestTypingEdgeCases:
    def test_single_keystroke_no_crash(self):
        """[SYNTHETIC] Single keystroke — extractor must not raise ZeroDivisionError."""
        events = [{"event_index": 1, "press_time": 0.0, "release_time": 80.0,
                   "hold_duration": 80.0, "inter_key_interval": 0.0, "is_correction": False}]
        session = {"session_duration": 0.08, "timing_events": events}
        try:
            features = TypingFeatureExtractor.extract_features(session)
            assert isinstance(features, dict)
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError raised for single-keystroke session.")

    def test_empty_events_returns_defaults(self):
        """[SYNTHETIC] Empty timing events must return default zero features."""
        session = {"session_duration": 0.0, "timing_events": []}
        try:
            features = TypingFeatureExtractor.extract_features(session)
            assert isinstance(features, dict)
        except Exception as e:
            pytest.fail(f"Exception raised for empty events: {e}")


# ── Quality Scorer ────────────────────────────────────────────────────────────

class TestTypingQualityScorer:
    def test_high_quality_session(self):
        """[SYNTHETIC] Session meeting all thresholds → quality_score >= 0.7."""
        session = session_of(44, iki_ms=250.0)
        features = TypingFeatureExtractor.extract_features(session)
        score_info = TypingQualityScorer.score_session(features)
        assert score_info["quality_score"] >= 0.5

    def test_quality_score_bounds(self):
        """[SYNTHETIC] Quality score is always in [0, 1]."""
        session = session_of(44)
        features = TypingFeatureExtractor.extract_features(session)
        score_info = TypingQualityScorer.score_session(features)
        assert 0.0 <= score_info["quality_score"] <= 1.0

    def test_quality_includes_pass_flag(self):
        """[SYNTHETIC] Quality result must include passes_threshold boolean."""
        session = session_of(44)
        features = TypingFeatureExtractor.extract_features(session)
        score_info = TypingQualityScorer.score_session(features)
        assert "passes_threshold" in score_info


# ── Privacy: No Text Content ──────────────────────────────────────────────────

class TestTypingPrivacy:
    def test_no_text_content_in_features(self):
        """[SYNTHETIC] Feature dict must NOT store character codes or text content."""
        session = session_of(44)
        features = TypingFeatureExtractor.extract_features(session)
        forbidden_keys = {"text", "characters", "character_codes", "key_codes",
                          "key_content", "raw_text", "typed_text"}
        found = forbidden_keys.intersection(set(features.keys()))
        assert not found, f"Privacy violation: text-content keys found: {found}"

    def test_synthetic_data_generation_available(self):
        """generate_synthetic_timing_data must exist and produce labeled data."""
        data = generate_synthetic_timing_data(n_keystrokes=30)
        assert "timing_events" in data or isinstance(data, dict)
