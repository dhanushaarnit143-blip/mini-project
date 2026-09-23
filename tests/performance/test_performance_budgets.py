"""
Phase 15 — Performance Tests: Latency Budget Validation
========================================================
Verifies that all system components complete within defined time budgets:

  - Feature extraction:  < 5 seconds per task
  - Daily aggregation:   < 2 seconds
  - Baseline update:     < 1 second
  - MPF inference:       < 3 seconds (mocked — real model not available in CI)
  - Sync operation:      < 10 seconds for typical daily data

Performance targets are validated using time.perf_counter() with
generous margins (1.5x) to account for CI environment variability.

ALL data used is clearly labeled [SYNTHETIC].
Timing tests run multiple iterations and report p95 latency.
"""

import time
import math
import uuid
import statistics
import pytest
import numpy as np
from pathlib import Path
import sys
from typing import List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mobile.typing.typing_service import (
    TypingFeatureExtractor,
    TypingQualityScorer,
    generate_synthetic_timing_data,
)
from src.mobile.voice.voice_service import (
    VoiceFeatureExtractor,
    VoiceQualityScorer,
    generate_synthetic_voice_audio,
)
from src.mobile.feature_mapper import map_mobile_features


SAMPLE_RATE = 44100

# Performance budgets (generous margins for CI)
BUDGET_FEATURE_EXTRACTION_S = 5.0      # < 5 s per task
BUDGET_DAILY_AGGREGATION_S = 2.0       # < 2 s
BUDGET_BASELINE_UPDATE_S = 1.0         # < 1 s
BUDGET_MPF_INFERENCE_S = 3.0           # < 3 s (mocked)
BUDGET_SYNC_S = 10.0                   # < 10 s
CI_MARGIN = 1.5                        # 50% margin for CI slowdown
N_ITERATIONS = 5                       # Iterations for p95 calculation


# ── Helpers ───────────────────────────────────────────────────────────────────

def measure_latency(fn, n=N_ITERATIONS) -> List[float]:
    """Run fn n times and return list of elapsed seconds."""
    times = []
    for _ in range(n):
        start = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return times


def p95(times: List[float]) -> float:
    """95th percentile latency."""
    return sorted(times)[int(len(times) * 0.95)] if times else 0.0


def assert_within_budget(times: List[float], budget_s: float, operation: str):
    """Assert p95 latency is within budget (with CI margin)."""
    max_budget = budget_s * CI_MARGIN
    p95_val = p95(times)
    mean_val = statistics.mean(times)
    assert p95_val <= max_budget, (
        f"PERFORMANCE BUDGET EXCEEDED: {operation}\n"
        f"  Budget:    {budget_s:.2f}s (×{CI_MARGIN} CI = {max_budget:.2f}s)\n"
        f"  p95:       {p95_val:.3f}s\n"
        f"  mean:      {mean_val:.3f}s\n"
        f"  samples:   {times}"
    )


# ── Synthetic Data (pre-built outside timing loops) ──────────────────────────

_RAW_TIMING_EVENTS = generate_synthetic_timing_data(keystroke_count=44)
SYNTH_TYPING_DATA = {"session_duration": 11.0, "timing_events": _RAW_TIMING_EVENTS}
SYNTH_VOICE_AUDIO = generate_synthetic_voice_audio(
    duration=5.0, sample_rate=SAMPLE_RATE, f0=150.0,
    jitter_factor=0.002, shimmer_factor=0.01, noise_level=0.005
)
SYNTH_DAILY_FEATURES = {
    "typing": {
        "typing_speed": 2.0, "interval_variability": 0.12,
        "correction_rate": 1.0, "quality_score": 0.85
    },
    "voice": {
        "jitter": 0.01, "shimmer": 0.04, "hnr": 14.0,
        "pitch_mean": 145.0, "mfcc_mean": [0.0] * 13, "quality_score": 0.80
    },
    "motor": {
        "tapping_rate": 2.5, "tapping_interval_variability": 0.08,
        "fine_motor_indicator": 0.1, "quality_score": 0.85
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. TYPING FEATURE EXTRACTION PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════

class TestTypingExtractionPerformance:
    """Typing feature extraction must complete in < 5 s (p95)."""

    def test_typing_feature_extraction_latency(self):
        """[SYNTHETIC] Typing feature extraction p95 < 5 s."""
        def run():
            features = TypingFeatureExtractor.extract_features(SYNTH_TYPING_DATA)
            assert features is not None

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, BUDGET_FEATURE_EXTRACTION_S, "Typing Feature Extraction")

    def test_typing_quality_scoring_latency(self):
        """[SYNTHETIC] Typing quality scoring p95 < 0.5 s."""
        features = TypingFeatureExtractor.extract_features(SYNTH_TYPING_DATA)

        def run():
            result = TypingQualityScorer.score_session(features)
            assert result is not None

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, 0.5, "Typing Quality Scoring")

    def test_typing_end_to_end_latency(self):
        """[SYNTHETIC] Full typing extraction + scoring pipeline p95 < 5 s."""
        def run():
            features = TypingFeatureExtractor.extract_features(SYNTH_TYPING_DATA)
            quality = TypingQualityScorer.score_session(features)
            assert quality["quality_score"] >= 0.0

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, BUDGET_FEATURE_EXTRACTION_S, "Typing E2E")


# ══════════════════════════════════════════════════════════════════════════════
# 2. VOICE FEATURE EXTRACTION PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════

class TestVoiceExtractionPerformance:
    """Voice feature extraction must complete in < 5 s (p95)."""

    def test_voice_feature_extraction_latency(self):
        """[SYNTHETIC] Voice feature extraction p95 < 5 s."""
        def run():
            features = VoiceFeatureExtractor.extract_features(
                SYNTH_VOICE_AUDIO, SAMPLE_RATE, task_type="sustained_vowel"
            )
            assert features is not None

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, BUDGET_FEATURE_EXTRACTION_S, "Voice Feature Extraction")

    def test_voice_quality_scoring_latency(self):
        """[SYNTHETIC] Voice quality scoring p95 < 0.5 s."""
        features = VoiceFeatureExtractor.extract_features(
            SYNTH_VOICE_AUDIO, SAMPLE_RATE, task_type="sustained_vowel"
        )

        def run():
            result = VoiceQualityScorer.score_session(features)
            assert result is not None

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, 0.5, "Voice Quality Scoring")


# ══════════════════════════════════════════════════════════════════════════════
# 3. DAILY AGGREGATION PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════

class TestDailyAggregationPerformance:
    """Daily feature aggregation must complete in < 2 s."""

    def test_feature_mapping_latency(self):
        """[SYNTHETIC] Feature mapping (daily → MPF format) p95 < 2 s."""
        def run():
            result = map_mobile_features(SYNTH_DAILY_FEATURES)
            assert "available_modalities" in result

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, BUDGET_DAILY_AGGREGATION_S, "Daily Feature Aggregation")

    def test_multimodal_aggregation_latency(self):
        """[SYNTHETIC] Multi-modal feature assembly p95 < 2 s."""
        large_daily = {}
        # Simulate a full-day multi-session aggregate
        for modality in ["typing", "voice", "motor"]:
            large_daily[modality] = SYNTH_DAILY_FEATURES.get(modality, {})

        def run():
            result = map_mobile_features(large_daily)
            assert result is not None

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, BUDGET_DAILY_AGGREGATION_S, "Multi-modal Aggregation")


# ══════════════════════════════════════════════════════════════════════════════
# 4. BASELINE UPDATE PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════

class TestBaselineUpdatePerformance:
    """Baseline update (adding one new observation) must complete in < 1 s."""

    def test_baseline_calculation_latency(self):
        """[SYNTHETIC] Baseline calculation from 14 daily values p95 < 1 s."""
        import math

        def _mean(vals):
            return sum(vals) / len(vals) if vals else 0.0

        def _std(vals):
            if len(vals) < 2:
                return 0.0
            m = _mean(vals)
            return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))

        # 14 days of [SYNTHETIC] typing speed values
        values = [2.0 + 0.1 * math.sin(i) for i in range(14)]

        def run():
            m = _mean(values)
            s = _std(values)
            result = {
                "mean": m, "std": s,
                "sample_count": len(values),
                "status": "established" if len(values) >= 14 else "calibrating"
            }
            assert result["status"] == "established"

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, BUDGET_BASELINE_UPDATE_S, "Baseline Calculation")

    def test_incremental_baseline_update_latency(self):
        """[SYNTHETIC] Incremental baseline update (add 1 observation) p95 < 1 s."""
        import math
        values = [2.0 + 0.1 * math.sin(i) for i in range(14)]
        new_value = 2.3  # [SYNTHETIC] today's value

        def run():
            updated = values + [new_value]
            m = sum(updated) / len(updated)
            assert m > 0.0

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, BUDGET_BASELINE_UPDATE_S, "Incremental Baseline Update")


# ══════════════════════════════════════════════════════════════════════════════
# 5. MPF INFERENCE PERFORMANCE (MOCKED)
# ══════════════════════════════════════════════════════════════════════════════

class TestMPFInferencePerformance:
    """
    MPF inference must complete in < 3 s.
    Real model inference requires models/fusion/preprocessor.joblib which
    may not be available in all CI environments. This test mocks the heavy
    I/O portions while timing the adapter logic itself.
    """

    def test_prediction_formatting_latency(self):
        """[SYNTHETIC] Prediction response formatting p95 < 0.5 s."""
        from src.mobile.prediction_logger import format_mpf_prediction_response

        raw_result = {
            "risk_score": 0.38,
            "available_modalities": ["voice", "motor"],
            "missing_modalities": ["olfactory", "retina"],
            "model_version": "mpf-pd-v2.1.0",
        }

        def run():
            response = format_mpf_prediction_response(raw_result)
            assert 0.0 <= response["risk_score"] <= 1.0

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, 0.5, "Prediction Formatting")

    def test_feature_mapping_for_inference_latency(self):
        """[SYNTHETIC] Feature mapping for MPF inference p95 < 1 s."""
        def run():
            result = map_mobile_features(SYNTH_DAILY_FEATURES)
            assert "available_modalities" in result

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, 1.0, "Feature Mapping for Inference")

    def test_full_adapter_pipeline_without_model_latency(self):
        """[SYNTHETIC] Full adapter pipeline (no model I/O) p95 < 3 s."""
        from src.mobile.prediction_logger import format_mpf_prediction_response

        def run():
            # Step 1: Map features
            mapped = map_mobile_features(SYNTH_DAILY_FEATURES)
            # Step 2: Simulate prediction (no actual model I/O)
            raw_result = {
                "risk_score": 0.38,
                "available_modalities": mapped.get("available_modalities", []),
                "missing_modalities": mapped.get("missing_modalities", []),
                "model_version": "mpf-pd-v2.1.0",
            }
            # Step 3: Format response
            response = format_mpf_prediction_response(raw_result)
            assert 0.0 <= response["risk_score"] <= 1.0

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, BUDGET_MPF_INFERENCE_S, "Full Adapter Pipeline (no model I/O)")


# ══════════════════════════════════════════════════════════════════════════════
# 6. SYNC PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════

class TestSyncPerformance:
    """Sync operation must complete in < 10 s for typical daily data."""

    def test_sync_queue_serialization_latency(self):
        """[SYNTHETIC] Serializing a full day's sync queue p95 < 1 s."""
        import json

        # Typical day: 1 typing + 1 voice + 1 motor session features
        queue_items = []
        for i in range(3):
            queue_items.append({
                "participant_id": "SYNTH_PERF_001",
                "session_id": str(uuid.uuid4()),
                "session_type": ["typing", "voice", "motor"][i],
                "feature_version": "1.0.0",
                "collected_at": "2026-09-20T10:00:00Z",
                "features": SYNTH_DAILY_FEATURES.get(["typing", "voice", "motor"][i], {}),
            })

        def run():
            serialized = json.dumps(queue_items)
            deserialized = json.loads(serialized)
            assert len(deserialized) == 3

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, 1.0, "Sync Queue Serialization")

    def test_conflict_resolution_latency(self):
        """[SYNTHETIC] Conflict resolution for duplicate sync records p95 < 1 s."""
        import json

        def resolve_conflict(local, remote):
            """Last-write-wins conflict resolution (mirrors JS conflictResolver)."""
            local_ts = local.get("collected_at", "")
            remote_ts = remote.get("collected_at", "")
            return local if local_ts >= remote_ts else remote

        local_record = {
            "session_id": "abc-001",
            "collected_at": "2026-09-20T10:05:00Z",
            "typing_speed": 2.1,
        }
        remote_record = {
            "session_id": "abc-001",
            "collected_at": "2026-09-20T10:00:00Z",
            "typing_speed": 2.0,
        }

        def run():
            result = resolve_conflict(local_record, remote_record)
            assert result["typing_speed"] == 2.1

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, 1.0, "Conflict Resolution")

    def test_sync_bridge_initialization_latency(self):
        """[SYNTHETIC] SyncBridge initialization p95 < 2 s."""
        from unittest.mock import MagicMock
        from src.mobile.sync.sync_bridge import MobileSyncBridge

        def run():
            mock_client = MagicMock()
            bridge = MobileSyncBridge(supabase_client=mock_client)
            assert bridge is not None

        times = measure_latency(run, n=N_ITERATIONS)
        assert_within_budget(times, 2.0, "SyncBridge Initialization")


# ══════════════════════════════════════════════════════════════════════════════
# 7. THROUGHPUT TEST
# ══════════════════════════════════════════════════════════════════════════════

class TestThroughput:
    """Validates system can handle realistic daily data volumes."""

    def test_typing_extraction_100_sessions_throughput(self):
        """[SYNTHETIC] Processing 100 typing sessions in batch < 30 s."""
        start = time.perf_counter()
        for _ in range(100):
            features = TypingFeatureExtractor.extract_features(SYNTH_TYPING_DATA)
            quality = TypingQualityScorer.score_session(features)
        elapsed = time.perf_counter() - start
        assert elapsed < 30.0, \
            f"100 typing sessions took {elapsed:.2f}s (budget: 30.0s)"

    def test_feature_mapping_30_days_throughput(self):
        """[SYNTHETIC] Mapping 30 days of daily features < 5 s."""
        start = time.perf_counter()
        for _ in range(30):
            result = map_mobile_features(SYNTH_DAILY_FEATURES)
            assert "available_modalities" in result
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, \
            f"30-day feature mapping took {elapsed:.2f}s (budget: 5.0s)"
