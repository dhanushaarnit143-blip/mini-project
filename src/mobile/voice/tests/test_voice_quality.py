"""
Tests for MPF Mobile Extension — Voice Quality Scorer & Data Model (Phase 5)

Verifies:
- Standardized multi-factor quality scoring:
  - Duration > 3.0s (+0.30)
  - Good SNR / signal_quality >= 0.50 (+0.30)
  - No clipping (+0.20)
  - Low silence ratio < 30% (+0.20)
- Baseline Engine Gating:
  - Sessions with quality_score < 0.50 are flagged and strictly rejected from baseline updates.
  - Sessions with quality_score >= 0.50 are marked eligible.
- VoiceSessionModel validation against Supabase PostgreSQL check constraints.
- Idempotency via client-generated UUID session_id.
"""

import pytest
import uuid
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.mobile.voice.voice_service import (
    VoiceQualityScorer,
    VoiceSessionModel,
    MIN_BASELINE_QUALITY_THRESHOLD,
    TASK_SUSTAINED_VOWEL,
    TASK_READ_SENTENCE,
    TASK_FREE_SPEECH,
    FEATURE_VERSION,
)


class TestVoiceQualityAndModel:
    def test_quality_scoring_full_credit(self):
        """
        Verifies that a high-fidelity voice session receives a full 1.00 quality score:
        - duration 5.0s > 3.0s: +0.30
        - signal_quality 0.85 >= 0.50: +0.30
        - no clipping: +0.20
        - silence_ratio 0.10 < 0.30: +0.20
        Total = 1.00
        """
        metrics = {
            "duration": 5.0,
            "signal_quality": 0.85,
            "clipping_detected": False,
            "silence_ratio": 0.10
        }

        result = VoiceQualityScorer.calculate_quality_score(metrics)

        assert result["quality_score"] == 1.00
        assert result["is_baseline_eligible"] is True
        assert result["breakdown"]["sufficient_duration"] == 0.30
        assert result["breakdown"]["good_snr"] == 0.30
        assert result["breakdown"]["no_clipping"] == 0.20
        assert result["breakdown"]["low_silence"] == 0.20
        assert len(result["rejection_reasons"]) == 0

    def test_duration_penalty(self):
        """
        Verifies that duration <= 3.0s loses 0.30 points.
        """
        metrics = {
            "duration": 2.5,  # <= 3.0s
            "signal_quality": 0.85,
            "clipping_detected": False,
            "silence_ratio": 0.10
        }

        result = VoiceQualityScorer.calculate_quality_score(metrics)

        assert result["breakdown"]["sufficient_duration"] == 0.0
        assert result["quality_score"] == 0.70
        assert result["is_baseline_eligible"] is True  # 0.70 >= 0.50
        assert any("Insufficient duration" in r for r in result["rejection_reasons"])

    def test_snr_penalty(self):
        """
        Verifies that low signal quality (< 0.50) loses 0.30 points.
        """
        metrics = {
            "duration": 5.0,
            "signal_quality": 0.35,  # Low SNR
            "clipping_detected": False,
            "silence_ratio": 0.10
        }

        result = VoiceQualityScorer.calculate_quality_score(metrics)

        assert result["breakdown"]["good_snr"] == 0.0
        assert result["quality_score"] == 0.70
        assert any("Low signal-to-noise quality" in r for r in result["rejection_reasons"])

    def test_clipping_penalty(self):
        """
        Verifies that clipping detection loses 0.20 points.
        """
        metrics = {
            "duration": 5.0,
            "signal_quality": 0.85,
            "clipping_detected": True,  # Overload
            "silence_ratio": 0.10
        }

        result = VoiceQualityScorer.calculate_quality_score(metrics)

        assert result["breakdown"]["no_clipping"] == 0.0
        assert result["quality_score"] == 0.80
        assert any("clipping" in r.lower() for r in result["rejection_reasons"])

    def test_silence_penalty(self):
        """
        Verifies that excessive silence (>= 30%) loses 0.20 points.
        """
        metrics = {
            "duration": 5.0,
            "signal_quality": 0.85,
            "clipping_detected": False,
            "silence_ratio": 0.45  # Excessive pauses/silence
        }

        result = VoiceQualityScorer.calculate_quality_score(metrics)

        assert result["breakdown"]["low_silence"] == 0.0
        assert result["quality_score"] == 0.80
        assert any("silence" in r.lower() for r in result["rejection_reasons"])

    def test_low_quality_session_gated_and_rejected_for_baseline(self):
        """
        CRITICAL BASELINE GATING RULE:
        A recording with multiple defects (e.g. short duration + low SNR + clipping)
        must yield quality_score < 0.50 and be strictly flagged as NOT baseline eligible.
        """
        metrics = {
            "duration": 2.0,            # 0.0
            "signal_quality": 0.20,     # 0.0
            "clipping_detected": True,  # 0.0
            "silence_ratio": 0.10       # 0.20
        }

        result = VoiceQualityScorer.calculate_quality_score(metrics)

        assert result["quality_score"] == 0.20
        assert result["quality_score"] < MIN_BASELINE_QUALITY_THRESHOLD
        assert result["is_baseline_eligible"] is False
        assert "Rejected" in result["summary"]

    def test_session_model_validation_against_schema(self):
        """
        Verifies that VoiceSessionModel validates fields against Supabase table constraints.
        """
        participant_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        features = {
            "duration": 5.2,
            "signal_quality": 0.88,
            "jitter": 0.0075,
            "shimmer": 0.021,
            "hnr": 19.4,
            "pitch_mean": 148.6,
            "pitch_std": 3.8,
            "mfcc_features": [0.5] * 13,
            "spectral_features": {
                "spectral_centroid": 1250.0,
                "spectral_bandwidth": 800.0,
                "spectral_rolloff": 2300.0
            },
            "feature_version": FEATURE_VERSION
        }

        model = VoiceSessionModel.from_features(
            participant_id=participant_id,
            session_id=session_id,
            task_type=TASK_SUSTAINED_VOWEL,
            features=features,
            quality_score=0.90
        )

        is_valid, errors = model.validate()
        assert is_valid is True, f"Validation errors: {errors}"

        payload = model.to_supabase_payload()
        assert payload["participant_id"] == participant_id
        assert payload["session_id"] == session_id
        assert payload["task_type"] == TASK_SUSTAINED_VOWEL
        assert payload["duration"] == 5.2
        assert payload["signal_quality"] == 0.88
        assert payload["jitter"] == 0.0075
        assert payload["shimmer"] == 0.021
        assert payload["hnr"] == 19.4
        assert payload["pitch_mean"] == 148.6
        assert payload["pitch_std"] == 3.8
        assert len(payload["mfcc_features"]) == 13
        assert payload["quality_score"] == 0.90
        assert payload["feature_version"] == FEATURE_VERSION
        assert payload["synced"] is False

    def test_session_model_catches_invalid_data(self):
        """
        Verifies that invalid UUIDs, negative duration, or invalid task types are caught.
        """
        # Invalid UUID
        model_bad_uuid = VoiceSessionModel({
            "participant_id": "not-a-uuid",
            "session_id": "invalid",
            "task_type": TASK_SUSTAINED_VOWEL
        })
        is_valid, errors = model_bad_uuid.validate()
        assert is_valid is False
        assert any("participant_id" in e for e in errors)

        # Invalid task type
        model_bad_task = VoiceSessionModel({
            "participant_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "task_type": "unknown_task",
            "duration": 5.0,
            "signal_quality": 0.8,
            "mfcc_features": [1.0] * 13,
            "spectral_features": {"spectral_centroid": 100}
        })
        is_valid, errors = model_bad_task.validate()
        assert is_valid is False
        assert any("task_type" in e for e in errors)
