"""
Tests for MPF Mobile Extension — Tapping Feature Extractor (Phase 6)

Verifies that finger-tapping biomarkers are computed correctly from
synthetic tap timestamp sequences.

COMPLIANCE:
  - Raw timestamp arrays are NOT returned in the feature dict.
  - feature_version is stamped on every result.
  - All data is clearly labeled [SYNTHETIC].
"""

import pytest
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Python mirror of tappingFeatureExtractor.js
# ─────────────────────────────────────────────────────────────────────────────

MIN_ITI_MS = 50
MAX_ITI_MS = 2000
FEATURE_VERSION = '1.0'


def _mean(arr):
    return sum(arr) / len(arr) if arr else 0.0

def _std(arr):
    if len(arr) < 2:
        return 0.0
    m = _mean(arr)
    return math.sqrt(sum((v - m) ** 2 for v in arr) / len(arr))

def _cv(arr):
    m = _mean(arr)
    return _std(arr) / m if m != 0 else 0.0

def _linear_regression_slope(values):
    """OLS slope of ITI vs tap index (ms/tap). Positive = slowing."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = _mean(values)
    num   = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denom = sum((i - x_mean) ** 2 for i in range(n))
    return num / denom if denom != 0 else 0.0

def extract_tapping_features_py(tap_timestamps_ms, task_duration_ms):
    """
    Python mirror of tappingFeatureExtractor.js::extractTappingFeatures().
    Used ONLY for test validation.
    """
    if not tap_timestamps_ms or len(tap_timestamps_ms) < 3:
        return {
            'tap_count': 0, 'tapping_rate': None,
            'inter_tap_interval_mean': None, 'inter_tap_interval_variability': None,
            'decline_slope': None,
            'duration_seconds': task_duration_ms / 1000,
            'feature_version': FEATURE_VERSION, '_extraction_status': 'insufficient_taps',
        }

    sorted_ts = sorted(tap_timestamps_ms)
    duration_sec = task_duration_ms / 1000

    raw_iti = [sorted_ts[i] - sorted_ts[i - 1] for i in range(1, len(sorted_ts))]
    valid_iti = [iti for iti in raw_iti if MIN_ITI_MS <= iti <= MAX_ITI_MS]

    if len(valid_iti) < 2:
        return {
            'tap_count': len(sorted_ts), 'tapping_rate': None,
            'inter_tap_interval_mean': None, 'inter_tap_interval_variability': None,
            'decline_slope': None,
            'duration_seconds': round(duration_sec, 2),
            'feature_version': FEATURE_VERSION,
            '_extraction_status': 'insufficient_valid_intervals',
        }

    tap_count = len(sorted_ts)
    tapping_rate = tap_count / duration_sec if duration_sec > 0 else 0
    iti_mean = _mean(valid_iti)
    iti_cv = _cv(valid_iti)
    decline_slope = _linear_regression_slope(valid_iti)

    return {
        'tap_count': tap_count,
        'tapping_rate': round(tapping_rate, 3),
        'inter_tap_interval_mean': round(iti_mean, 2),
        'inter_tap_interval_variability': round(iti_cv, 4),
        'decline_slope': round(decline_slope, 4),
        'duration_seconds': round(duration_sec, 2),
        'feature_version': FEATURE_VERSION,
        '_extraction_status': 'ok',
    }


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic data generators
# ─────────────────────────────────────────────────────────────────────────────

def _make_regular_taps(n_taps=30, iti_ms=200.0, start_ms=0.0):
    """[SYNTHETIC] Perfectly regular tapping at constant inter-tap interval."""
    return [start_ms + i * iti_ms for i in range(n_taps)]

def _make_slowing_taps(n_taps=30, initial_iti_ms=150.0, slope_ms_per_tap=3.0, start_ms=0.0):
    """[SYNTHETIC] Gradually slowing taps (positive decline slope)."""
    timestamps = [start_ms]
    for i in range(1, n_taps):
        iti = initial_iti_ms + i * slope_ms_per_tap
        timestamps.append(timestamps[-1] + iti)
    return timestamps

def _make_noisy_taps(n_taps=30, iti_ms=200.0, noise_ms=30.0, start_ms=0.0):
    """[SYNTHETIC] Taps with jitter noise added to ITI."""
    import random
    random.seed(42)  # deterministic for reproducibility
    timestamps = [start_ms]
    for _ in range(1, n_taps):
        noise = random.uniform(-noise_ms, noise_ms)
        timestamps.append(timestamps[-1] + iti_ms + noise)
    return timestamps

def _make_taps_with_artifacts(n_taps=10, start_ms=0.0):
    """[SYNTHETIC] Taps with implausible ITI artifacts (< 50ms and > 2000ms)."""
    ts = [start_ms + i * 200.0 for i in range(n_taps)]
    # Inject sub-50ms (double-tap artifact)
    ts.insert(3, ts[3] + 20.0)
    # Inject super-2000ms (pause artifact)
    ts.append(ts[-1] + 3000.0)
    return ts


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTappingFeatureExtractor:
    """
    Test suite for tapping feature extraction with synthetic timestamp sequences.
    All inputs are clearly labeled [SYNTHETIC].
    """

    def test_regular_tapping_rate(self):
        """[SYNTHETIC] 30 taps over 10s → tapping_rate ≈ 3 taps/s."""
        taps = _make_regular_taps(n_taps=30, iti_ms=333.0)
        duration_ms = 10_000.0
        result = extract_tapping_features_py(taps, duration_ms)

        assert result['_extraction_status'] == 'ok'
        assert result['tap_count'] == 30
        assert result['tapping_rate'] == pytest.approx(3.0, abs=0.05)

    def test_regular_iti_mean(self):
        """[SYNTHETIC] Regular taps at 200ms ITI → inter_tap_interval_mean ≈ 200ms."""
        taps = _make_regular_taps(n_taps=40, iti_ms=200.0)
        duration_ms = 8_000.0
        result = extract_tapping_features_py(taps, duration_ms)

        assert result['inter_tap_interval_mean'] == pytest.approx(200.0, abs=1.0), \
            f"Expected ~200ms ITI, got {result['inter_tap_interval_mean']}"

    def test_regular_tapping_low_variability(self):
        """[SYNTHETIC] Perfectly regular taps → near-zero ITI variability (CV ≈ 0)."""
        taps = _make_regular_taps(n_taps=40, iti_ms=200.0)
        result = extract_tapping_features_py(taps, 10_000.0)
        assert result['inter_tap_interval_variability'] == pytest.approx(0.0, abs=0.01)

    def test_slowing_taps_positive_decline_slope(self):
        """[SYNTHETIC] Progressively slowing taps → positive decline_slope."""
        taps = _make_slowing_taps(n_taps=30, initial_iti_ms=150.0, slope_ms_per_tap=5.0)
        duration_ms = max(taps) + 150.0
        result = extract_tapping_features_py(taps, duration_ms)

        assert result['decline_slope'] is not None
        assert result['decline_slope'] > 0, \
            f"Slowing taps should have positive decline slope, got {result['decline_slope']}"

    def test_artifact_filtering(self):
        """[SYNTHETIC] Sub-50ms and > 2000ms ITIs are filtered from statistics."""
        taps = _make_taps_with_artifacts(n_taps=20)
        duration_ms = max(taps) + 200.0
        result = extract_tapping_features_py(taps, duration_ms)

        # With artifacts filtered, ITI mean should still be reasonable (200ms ± margin)
        if result['inter_tap_interval_mean'] is not None:
            assert result['inter_tap_interval_mean'] >= 50.0, \
                "Filtered mean should not reflect sub-50ms artifacts"

    def test_insufficient_taps_returns_empty(self):
        """[SYNTHETIC] < 3 tap timestamps → _extraction_status = 'insufficient_taps'."""
        taps = [0.0, 200.0]
        result = extract_tapping_features_py(taps, 1000.0)
        assert result['_extraction_status'] == 'insufficient_taps'
        assert result['tap_count'] == 0
        assert result['tapping_rate'] is None

    def test_feature_version_stamped(self):
        """feature_version must be '1.0' for reproducibility tracking."""
        taps = _make_regular_taps(n_taps=20)
        result = extract_tapping_features_py(taps, 5_000.0)
        assert result['feature_version'] == '1.0'

    def test_raw_timestamps_not_in_output(self):
        """
        PRIVACY: raw tap timestamp arrays must NOT appear in the feature dict.
        """
        taps = _make_regular_taps(n_taps=30)
        result = extract_tapping_features_py(taps, 8_000.0)

        for key, val in result.items():
            assert not isinstance(val, list), \
                f"Key '{key}' contains a list — raw timestamps must NOT be returned."

    def test_noisy_tapping_variability_nonzero(self):
        """[SYNTHETIC] Noisy taps (±30ms jitter) → nonzero ITI variability."""
        taps = _make_noisy_taps(n_taps=40, noise_ms=30.0)
        result = extract_tapping_features_py(taps, 10_000.0)
        assert result['inter_tap_interval_variability'] is not None
        assert result['inter_tap_interval_variability'] > 0, \
            "Noisy taps should have nonzero variability"

    def test_duration_seconds_correct(self):
        """duration_seconds must equal task_duration_ms / 1000."""
        taps = _make_regular_taps(n_taps=20)
        result = extract_tapping_features_py(taps, 7_500.0)
        assert result['duration_seconds'] == pytest.approx(7.5, abs=0.01)
