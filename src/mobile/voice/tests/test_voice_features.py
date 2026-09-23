"""
Tests for MPF Mobile Extension — Voice Feature Extractor (Phase 5)

Verifies:
- Accurate extraction of acoustic biomarkers from synthetic signals:
  - Fundamental frequency F0 (mean and std in Hz)
  - Jitter (relative period perturbation)
  - Shimmer (relative amplitude perturbation)
  - Harmonics-to-Noise Ratio (HNR in dB)
  - 13 Mel-Frequency Cepstral Coefficients (MFCCs)
  - Spectral features (centroid, bandwidth, rolloff 85%)
  - Signal quality metrics (duration, SNR estimate, clipping, silence ratio)
- Handling of edge cases: silence, clipped signals, zero duration.
"""

import pytest
import math
import numpy as np
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.mobile.voice.voice_service import (
    VoiceFeatureExtractor,
    generate_synthetic_voice_audio,
    FEATURE_VERSION,
)


class TestVoiceFeatures:
    def test_pitch_tracking_on_synthetic_vowel(self):
        """
        Tests fundamental frequency (F0) estimation on a synthetic vowel with known F0 = 150.0 Hz.
        """
        sample_rate = 44100
        target_f0 = 150.0
        audio = generate_synthetic_voice_audio(
            duration=4.0,
            sample_rate=sample_rate,
            f0=target_f0,
            jitter_factor=0.002,
            shimmer_factor=0.01,
            noise_level=0.005
        )

        features = VoiceFeatureExtractor.extract_features(audio, sample_rate)

        assert features["feature_version"] == FEATURE_VERSION
        assert features["duration"] == 4.0
        # Pitch estimation should be within +-5 Hz of ground truth 150 Hz
        assert abs(features["pitch_mean"] - target_f0) < 5.0
        assert features["pitch_std"] < 10.0  # Stable sustained vowel

    def test_higher_f0_pitch_tracking(self):
        """
        Tests fundamental frequency estimation on a higher pitch vowel (F0 = 220.0 Hz).
        """
        sample_rate = 44100
        target_f0 = 220.0
        audio = generate_synthetic_voice_audio(
            duration=4.0,
            sample_rate=sample_rate,
            f0=target_f0,
            jitter_factor=0.002,
            shimmer_factor=0.01
        )

        features = VoiceFeatureExtractor.extract_features(audio, sample_rate)
        assert abs(features["pitch_mean"] - target_f0) < 5.0

    def test_jitter_sensitivity(self):
        """
        Verifies that higher period perturbation correctly yields higher jitter values.
        """
        sample_rate = 44100
        # Low jitter
        audio_low_jitter = generate_synthetic_voice_audio(
            duration=3.5,
            sample_rate=sample_rate,
            f0=150.0,
            jitter_factor=0.001
        )
        # Higher jitter
        audio_high_jitter = generate_synthetic_voice_audio(
            duration=3.5,
            sample_rate=sample_rate,
            f0=150.0,
            jitter_factor=0.025
        )

        f_low = VoiceFeatureExtractor.extract_features(audio_low_jitter, sample_rate)
        f_high = VoiceFeatureExtractor.extract_features(audio_high_jitter, sample_rate)

        assert f_high["jitter"] > f_low["jitter"]
        assert f_low["jitter"] >= 0.0

    def test_shimmer_sensitivity(self):
        """
        Verifies that higher amplitude perturbation correctly yields higher shimmer values.
        """
        sample_rate = 44100
        # Low shimmer
        audio_low_shimmer = generate_synthetic_voice_audio(
            duration=3.5,
            sample_rate=sample_rate,
            f0=150.0,
            shimmer_factor=0.005
        )
        # High shimmer
        audio_high_shimmer = generate_synthetic_voice_audio(
            duration=3.5,
            sample_rate=sample_rate,
            f0=150.0,
            shimmer_factor=0.08
        )

        f_low = VoiceFeatureExtractor.extract_features(audio_low_shimmer, sample_rate)
        f_high = VoiceFeatureExtractor.extract_features(audio_high_shimmer, sample_rate)

        assert f_high["shimmer"] > f_low["shimmer"]
        assert f_low["shimmer"] >= 0.0

    def test_harmonics_to_noise_ratio(self):
        """
        Verifies HNR is higher for clean signals than for noisy signals.
        """
        sample_rate = 44100
        clean_audio = generate_synthetic_voice_audio(
            duration=3.5,
            sample_rate=sample_rate,
            f0=160.0,
            noise_level=0.001
        )
        noisy_audio = generate_synthetic_voice_audio(
            duration=3.5,
            sample_rate=sample_rate,
            f0=160.0,
            noise_level=0.15
        )

        f_clean = VoiceFeatureExtractor.extract_features(clean_audio, sample_rate)
        f_noisy = VoiceFeatureExtractor.extract_features(noisy_audio, sample_rate)

        assert f_clean["hnr"] > f_noisy["hnr"]
        assert f_clean["hnr"] > 10.0  # Clean voice typically > 10-15 dB

    def test_mfcc_coefficients_structure(self):
        """
        Verifies that exactly 13 MFCC coefficients are extracted and are valid finite numbers.
        """
        sample_rate = 44100
        audio = generate_synthetic_voice_audio(duration=3.5, sample_rate=sample_rate)
        features = VoiceFeatureExtractor.extract_features(audio, sample_rate)

        mfccs = features["mfcc_features"]
        assert isinstance(mfccs, list)
        assert len(mfccs) == 13
        for val in mfccs:
            assert isinstance(val, (int, float))
            assert not math.isnan(val)
            assert not math.isinf(val)

    def test_spectral_features_structure(self):
        """
        Verifies spectral centroid, bandwidth, and rolloff are non-zero, positive numbers.
        """
        sample_rate = 44100
        audio = generate_synthetic_voice_audio(duration=3.5, sample_rate=sample_rate, f0=150.0)
        features = VoiceFeatureExtractor.extract_features(audio, sample_rate)

        spec = features["spectral_features"]
        assert spec["spectral_centroid"] > 0
        assert spec["spectral_bandwidth"] > 0
        assert spec["spectral_rolloff"] > 0
        # Rolloff frequency should be higher than centroid
        assert spec["spectral_rolloff"] >= spec["spectral_centroid"]

    def test_clipping_detection(self):
        """
        Verifies clipping detection flags clipped signals.
        """
        sample_rate = 44100
        clean_audio = generate_synthetic_voice_audio(duration=3.0, clipping=False)
        clipped_audio = generate_synthetic_voice_audio(duration=3.0, clipping=True)

        f_clean = VoiceFeatureExtractor.extract_features(clean_audio, sample_rate)
        f_clipped = VoiceFeatureExtractor.extract_features(clipped_audio, sample_rate)

        assert f_clean["clipping_detected"] is False
        assert f_clipped["clipping_detected"] is True

    def test_edge_case_silence(self):
        """
        Verifies robust handling of complete silence without crashing or dividing by zero.
        """
        sample_rate = 44100
        silent_audio = np.zeros(sample_rate * 3, dtype=np.float32)
        features = VoiceFeatureExtractor.extract_features(silent_audio, sample_rate)

        assert features["duration"] == 3.0
        assert features["pitch_mean"] == 0.0
        assert features["jitter"] == 0.0
        assert features["shimmer"] == 0.0
        assert features["silence_ratio"] == 1.0

    def test_edge_case_empty_array(self):
        """
        Verifies graceful handling of empty audio array.
        """
        empty_audio = np.array([], dtype=np.float32)
        features = VoiceFeatureExtractor.extract_features(empty_audio, 44100)
        assert features["duration"] == 0.0
        assert features["silence_ratio"] == 1.0
