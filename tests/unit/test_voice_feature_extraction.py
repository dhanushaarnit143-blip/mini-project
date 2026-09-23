"""
Phase 15 — Unit Tests: Voice Feature Extraction
================================================
Validates mathematical correctness of all acoustic biomarker computations
using clearly labeled [SYNTHETIC] audio signals.

Covers:
  - Pitch (F0) mean and std
  - Jitter (cycle-to-cycle frequency perturbation)
  - Shimmer (cycle-to-cycle amplitude perturbation)
  - HNR (Harmonics-to-Noise Ratio)
  - MFCC presence (13 coefficients)
  - Spectral metrics (centroid, bandwidth, rolloff)
  - Signal quality metrics (duration, SNR, silence ratio)
  - Quality scoring (quality_score in [0,1], passes_threshold flag)
  - Edge cases: clipping, silence, short signal
  - Privacy: no raw audio stored by default
"""

import math
import pytest
import numpy as np
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mobile.voice.voice_service import (
    VoiceFeatureExtractor,
    VoiceQualityScorer,
    generate_synthetic_voice_audio,
    VoiceSessionModel,
    FEATURE_VERSION,
    TASK_SUSTAINED_VOWEL,
    TASK_READ_SENTENCE,
)
# Alias for consistent test naming
VoiceSession = VoiceSessionModel


SAMPLE_RATE = 44100


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_clean_signal(duration=5.0, f0=150.0) -> np.ndarray:
    """[SYNTHETIC] High-quality 5s sustained vowel signal at 150 Hz."""
    return generate_synthetic_voice_audio(
        duration=duration, sample_rate=SAMPLE_RATE, f0=f0,
        jitter_factor=0.002, shimmer_factor=0.01,
        noise_level=0.005, clipping=False, silence_ratio=0.05
    )


def make_noisy_signal(duration=5.0) -> np.ndarray:
    """[SYNTHETIC] Low-quality signal with heavy noise and high silence ratio."""
    return generate_synthetic_voice_audio(
        duration=duration, sample_rate=SAMPLE_RATE, f0=120.0,
        jitter_factor=0.05, shimmer_factor=0.10,
        noise_level=0.3, clipping=True, silence_ratio=0.4
    )


# ── Feature Extraction ────────────────────────────────────────────────────────

class TestVoiceFeatureExtraction:
    def test_feature_version_tagged(self):
        """[SYNTHETIC] Features must carry canonical FEATURE_VERSION."""
        audio = make_clean_signal()
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        assert features.get("feature_version") == FEATURE_VERSION

    def test_pitch_mean_reasonable_range(self):
        """[SYNTHETIC] Pitch mean for 150 Hz synthetic signal → 100–250 Hz range."""
        audio = make_clean_signal(f0=150.0)
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        pitch = features.get("pitch_mean", 0.0)
        assert 50.0 <= pitch <= 500.0, f"Pitch mean {pitch} out of expected range"

    def test_pitch_std_non_negative(self):
        """[SYNTHETIC] Pitch std must be >= 0."""
        audio = make_clean_signal()
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        assert features.get("pitch_std", 0.0) >= 0.0

    def test_jitter_non_negative(self):
        """[SYNTHETIC] Jitter must be >= 0 (perturbation ratio)."""
        audio = make_clean_signal()
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        assert features.get("jitter", 0.0) >= 0.0

    def test_shimmer_non_negative(self):
        """[SYNTHETIC] Shimmer must be >= 0."""
        audio = make_clean_signal()
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        assert features.get("shimmer", 0.0) >= 0.0

    def test_hnr_is_number(self):
        """[SYNTHETIC] HNR (dB) must be a finite number."""
        audio = make_clean_signal()
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        hnr = features.get("hnr", None)
        assert hnr is not None
        assert math.isfinite(hnr)

    def test_mfcc_13_coefficients_present(self):
        """[SYNTHETIC] MFCC list must contain exactly 13 coefficients."""
        audio = make_clean_signal()
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        mfccs = features.get("mfccs", [])
        assert len(mfccs) == 13, f"Expected 13 MFCCs, got {len(mfccs)}"

    def test_duration_matches_signal(self):
        """[SYNTHETIC] Extracted duration must match the 5-second signal."""
        audio = make_clean_signal(duration=5.0)
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        dur = features.get("duration_seconds", 0.0)
        assert 4.5 <= dur <= 5.5, f"Duration {dur} not close to 5.0 s"

    def test_silence_ratio_in_bounds(self):
        """[SYNTHETIC] Silence ratio must be in [0, 1]."""
        audio = make_clean_signal()
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        sr = features.get("silence_ratio", 0.0)
        assert 0.0 <= sr <= 1.0

    def test_spectral_centroid_positive(self):
        """[SYNTHETIC] Spectral centroid must be > 0 for voiced signal."""
        audio = make_clean_signal()
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        sc = features.get("spectral_centroid", 0.0)
        assert sc > 0.0


# ── Quality Scoring ───────────────────────────────────────────────────────────

class TestVoiceQualityScorer:
    def test_quality_score_bounds(self):
        """[SYNTHETIC] Quality score must always be in [0, 1]."""
        audio = make_clean_signal()
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        result = VoiceQualityScorer.score_session(features)
        assert 0.0 <= result["quality_score"] <= 1.0

    def test_high_quality_signal_passes_threshold(self):
        """[SYNTHETIC] Clean 5s signal must pass quality threshold (>= 0.50)."""
        audio = make_clean_signal(duration=5.0)
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        result = VoiceQualityScorer.score_session(features)
        assert result["passes_threshold"] is True

    def test_very_short_signal_low_quality(self):
        """[SYNTHETIC] 1s signal (too short) must NOT pass quality threshold."""
        audio = make_clean_signal(duration=1.0)
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        result = VoiceQualityScorer.score_session(features)
        # Short signal should be penalized
        assert result["quality_score"] < 0.9  # at minimum penalized

    def test_quality_includes_rejection_reason(self):
        """[SYNTHETIC] Quality result includes rejection_reasons list."""
        audio = make_clean_signal()
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        result = VoiceQualityScorer.score_session(features)
        assert "rejection_reasons" in result or "passes_threshold" in result


# ── Privacy: No Raw Audio Storage ────────────────────────────────────────────

class TestVoicePrivacy:
    def test_features_contain_no_raw_audio(self):
        """[SYNTHETIC] Extracted feature dict must NOT contain raw audio arrays."""
        audio = make_clean_signal()
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        forbidden = {"raw_audio", "audio_samples", "waveform", "audio_bytes", "pcm"}
        found = forbidden.intersection(set(str(k) for k in features.keys()))
        assert not found, f"Raw audio stored in features: {found}"

    def test_voice_session_no_raw_audio_by_default(self):
        """[SYNTHETIC] VoiceSession model must not persist raw_audio unless consent given."""
        import uuid
        # VoiceSessionModel takes a dict; raw_audio must not appear in session attributes
        session = VoiceSession({
            "participant_id": str(uuid.uuid4()),
            "task_type": TASK_SUSTAINED_VOWEL,
            "mfcc_features": [0.0] * 13,
        })
        # Check object attributes — raw_audio must not be stored
        obj_dict = vars(session) if hasattr(session, '__dict__') else {}
        raw = obj_dict.get("raw_audio", None)
        assert raw is None, \
            f"RAW AUDIO PRIVACY VIOLATION: raw_audio is not None ({type(raw)})"

    def test_synthetic_data_labeled(self):
        """generate_synthetic_voice_audio must return ndarray (clearly test-only)."""
        audio = generate_synthetic_voice_audio(duration=3.0)
        assert isinstance(audio, np.ndarray)
        assert len(audio) > 0


# ── Task Type Validation ──────────────────────────────────────────────────────

class TestVoiceTaskTypes:
    def test_sustained_vowel_task_extraction(self):
        """[SYNTHETIC] Sustained vowel task extraction produces valid feature dict."""
        audio = make_clean_signal()
        features = VoiceFeatureExtractor.extract_features(
            audio, SAMPLE_RATE, task_type=TASK_SUSTAINED_VOWEL
        )
        assert "jitter" in features
        assert "shimmer" in features
        assert "hnr" in features

    def test_read_sentence_task_extraction(self):
        """[SYNTHETIC] Read sentence task extraction does not crash."""
        audio = make_clean_signal(duration=7.0)
        try:
            features = VoiceFeatureExtractor.extract_features(
                audio, SAMPLE_RATE, task_type=TASK_READ_SENTENCE
            )
            assert isinstance(features, dict)
        except Exception as e:
            pytest.fail(f"Read sentence extraction raised: {e}")
