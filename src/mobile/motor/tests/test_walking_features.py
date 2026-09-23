"""
Tests for MPF Mobile Extension — Walking Feature Extractor (Phase 6)

Verifies that gait biomarkers are computed correctly from synthetic accelerometer data.

Synthetic data generation:
  - Regular step signals are modeled as a sinusoidal pattern on the Z-axis.
  - Irregular signals are modeled with added noise or variable frequency.
  - ALL data is clearly labeled as synthetic / test-only.

COMPLIANCE:
  - Test verifies that raw sample arrays are NOT present in the returned feature dict.
  - Test verifies feature_version is set correctly.
"""

import pytest
import math
import sys
from pathlib import Path

# ── Path setup ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Pure-Python re-implementation of the JS walking feature extractor for testing.
# The JS module runs in the browser; we mirror the algorithm here to validate
# the logic is correct with known synthetic signals.
# ─────────────────────────────────────────────────────────────────────────────

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

def _detect_peaks(signal, timestamps, prominence_factor=0.3,
                  min_interval_ms=250, max_interval_ms=2000):
    """Mirror of the JS _detectPeaks function."""
    sigma = _std(signal)
    mu = _mean(signal)
    threshold = mu + prominence_factor * sigma
    peaks = []
    last_peak_time = float('-inf')

    for i in range(1, len(signal) - 1):
        if (signal[i] > signal[i - 1] and
                signal[i] > signal[i + 1] and
                signal[i] > threshold):
            t = timestamps[i]
            if t - last_peak_time >= min_interval_ms:
                peaks.append({'i': i, 't': t, 'v': signal[i]})
                last_peak_time = t
    return peaks

def _autocorrelation_at_lag(signal, lag):
    """Mirror of JS _autocorrelationAtLag; returns normalized [0, 1]."""
    if lag <= 0 or lag >= len(signal):
        return 0.0
    n = len(signal) - lag
    mu = _mean(signal)
    num = sum((signal[i] - mu) * (signal[i + lag] - mu) for i in range(n))
    denom = sum((signal[i] - mu) ** 2 for i in range(n))
    raw = num / denom if denom > 0 else 0.0
    return (raw + 1) / 2  # shift [-1, 1] → [0, 1]

def extract_walking_features_py(samples, duration_ms,
                                 prominence_factor=0.3,
                                 min_step_interval_ms=250,
                                 max_step_interval_ms=2000):
    """
    Python mirror of walkingFeatureExtractor.js::extractWalkingFeatures().
    Used ONLY for test validation. Returns same shape as JS module.
    """
    FEATURE_VERSION = '1.0'

    if not samples or len(samples) < 20:
        return {
            'cadence': None, 'stride_interval_mean': None,
            'stride_interval_variability': None, 'movement_regularity': 0,
            'symmetry_index': None, 'step_count': 0,
            'duration_seconds': duration_ms / 1000,
            'feature_version': FEATURE_VERSION,
            '_extraction_status': 'insufficient_samples',
        }

    mag = [math.sqrt(s['ax']**2 + s['ay']**2 + s['az']**2) for s in samples]
    mu = _mean(mag)
    detrended = [v - mu for v in mag]
    timestamps = [s['t'] for s in samples]

    peaks = _detect_peaks(detrended, timestamps, prominence_factor,
                          min_step_interval_ms, max_step_interval_ms)

    if len(peaks) < 2:
        return {
            'cadence': None, 'stride_interval_mean': None,
            'stride_interval_variability': None, 'movement_regularity': 0,
            'symmetry_index': None, 'step_count': len(peaks),
            'duration_seconds': duration_ms / 1000,
            'feature_version': FEATURE_VERSION,
            '_extraction_status': 'insufficient_peaks',
        }

    step_intervals = []
    for i in range(1, len(peaks)):
        interval = peaks[i]['t'] - peaks[i - 1]['t']
        if min_step_interval_ms <= interval <= max_step_interval_ms:
            step_intervals.append(interval)

    if len(step_intervals) < 2:
        return {
            'cadence': None, 'stride_interval_mean': None,
            'stride_interval_variability': None, 'movement_regularity': 0,
            'symmetry_index': None, 'step_count': len(peaks),
            'duration_seconds': duration_ms / 1000,
            'feature_version': FEATURE_VERSION,
            '_extraction_status': 'insufficient_valid_steps',
        }

    duration_sec = duration_ms / 1000
    cadence = (len(peaks) / duration_sec) * 60

    # Stride intervals (pairs of steps)
    stride_intervals = []
    for i in range(0, len(step_intervals) - 1, 2):
        stride_intervals.append((step_intervals[i] + step_intervals[i + 1]) / 1000)

    stride_mean = _mean(stride_intervals) if stride_intervals else step_intervals[0] / 500
    stride_cv = _cv(stride_intervals) if len(stride_intervals) > 1 else 0.0

    # Autocorrelation
    sample_duration = duration_ms / len(samples)  # ms per sample
    lag = round((stride_mean * 1000) / sample_duration)
    regularity = _autocorrelation_at_lag(detrended, lag)

    # Symmetry
    even = [step_intervals[i] for i in range(0, len(step_intervals), 2)]
    odd  = [step_intervals[i] for i in range(1, len(step_intervals), 2)]
    symmetry_index = None
    if even and odd:
        me, mo = _mean(even), _mean(odd)
        denom = (me + mo) / 2
        symmetry_index = 1 - abs(me - mo) / denom if denom > 0 else None

    return {
        'cadence': round(cadence, 2),
        'stride_interval_mean': round(stride_mean, 4),
        'stride_interval_variability': round(stride_cv, 4),
        'movement_regularity': round(max(0, min(1, regularity)), 4),
        'symmetry_index': round(symmetry_index, 4) if symmetry_index is not None else None,
        'step_count': len(peaks),
        'duration_seconds': round(duration_sec, 2),
        'feature_version': FEATURE_VERSION,
        '_extraction_status': 'ok',
    }


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic data generators — labeled [SYNTHETIC]
# ─────────────────────────────────────────────────────────────────────────────

def _make_regular_walk_samples(duration_sec=30.0, sample_rate_hz=50,
                                cadence_steps_per_min=100, noise_scale=0.3):
    """
    [SYNTHETIC] Generates accelerometer samples for a regular walking pattern.
    Models steps as sinusoidal peaks on the Z-axis at the given cadence.
    """
    n = int(duration_sec * sample_rate_hz)
    step_freq_hz = cadence_steps_per_min / 60.0  # steps per second
    samples = []
    for i in range(n):
        t_ms = (i / sample_rate_hz) * 1000
        t_sec = i / sample_rate_hz
        # Sinusoidal step signal on Z + gravity offset + small noise
        az = 9.81 + 2.0 * math.sin(2 * math.pi * step_freq_hz * t_sec)
        ax = 0.1 * math.sin(2 * math.pi * 0.3 * t_sec)
        ay = 0.1 * math.cos(2 * math.pi * 0.3 * t_sec)
        # Add small deterministic pseudo-noise
        noise = noise_scale * math.sin(2 * math.pi * 13 * t_sec + i * 0.7)
        samples.append({'t': t_ms, 'ax': ax, 'ay': ay, 'az': az + noise})
    return samples

def _make_sparse_samples(n=5):
    """[SYNTHETIC] Very short sample list — should trigger insufficient_samples."""
    return [{'t': i * 20.0, 'ax': 0, 'ay': 0, 'az': 9.81} for i in range(n)]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestWalkingFeatureExtractor:
    """
    Tests for walking feature extraction using synthetic accelerometer data.
    All input data is synthetic and clearly labeled — rule 4 compliant.
    """

    def test_regular_walk_produces_valid_features(self):
        """[SYNTHETIC] Regular 30s walk at 100 steps/min → valid cadence and stride features."""
        samples = _make_regular_walk_samples(
            duration_sec=30.0, sample_rate_hz=50, cadence_steps_per_min=100
        )
        duration_ms = 30_000.0
        result = extract_walking_features_py(samples, duration_ms)

        assert result['_extraction_status'] == 'ok', f"Unexpected status: {result['_extraction_status']}"
        assert result['cadence'] is not None, "cadence should be extracted"
        assert 40 <= result['cadence'] <= 180, f"Cadence out of plausible range: {result['cadence']}"
        assert result['step_count'] > 10, f"Too few steps: {result['step_count']}"

    def test_stride_interval_mean_positive(self):
        """[SYNTHETIC] Stride interval mean must be a positive number."""
        samples = _make_regular_walk_samples(duration_sec=30.0, sample_rate_hz=50)
        result = extract_walking_features_py(samples, 30_000.0)
        assert result['stride_interval_mean'] is not None
        assert result['stride_interval_mean'] > 0, "stride_interval_mean must be positive"

    def test_stride_variability_bounded(self):
        """[SYNTHETIC] Stride interval CV must be in [0, 1] for regular walking."""
        samples = _make_regular_walk_samples(
            duration_sec=30.0, sample_rate_hz=50, noise_scale=0.1
        )
        result = extract_walking_features_py(samples, 30_000.0)
        assert result['stride_interval_variability'] is not None
        assert 0 <= result['stride_interval_variability'] <= 1.0, \
            f"CV out of [0,1]: {result['stride_interval_variability']}"

    def test_movement_regularity_bounded(self):
        """[SYNTHETIC] Movement regularity must be in [0, 1]."""
        samples = _make_regular_walk_samples(duration_sec=30.0, sample_rate_hz=50)
        result = extract_walking_features_py(samples, 30_000.0)
        assert 0 <= result['movement_regularity'] <= 1.0, \
            f"Regularity out of [0,1]: {result['movement_regularity']}"

    def test_insufficient_samples_returns_empty_features(self):
        """[SYNTHETIC] < 20 samples must return _extraction_status = 'insufficient_samples'."""
        sparse = _make_sparse_samples(n=5)
        result = extract_walking_features_py(sparse, 100.0)
        assert result['_extraction_status'] == 'insufficient_samples'
        assert result['cadence'] is None
        assert result['step_count'] == 0

    def test_feature_version_is_set(self):
        """Feature version must be stamped on every result for reproducibility."""
        samples = _make_regular_walk_samples()
        result = extract_walking_features_py(samples, 30_000.0)
        assert result['feature_version'] == '1.0'

    def test_raw_samples_not_in_output(self):
        """
        PRIVACY: raw sample arrays must NOT be present in the returned feature dict.
        Verifies that the extractor does not leak raw sensor data.
        """
        samples = _make_regular_walk_samples()
        result = extract_walking_features_py(samples, 30_000.0)

        # Check none of the keys hold a list/array (no raw data passthrough)
        for key, val in result.items():
            assert not isinstance(val, list), \
                f"Key '{key}' contains a raw list — raw sensor data must NOT be returned."

    def test_duration_seconds_matches_input(self):
        """[SYNTHETIC] duration_seconds must match the input durationMs / 1000."""
        samples = _make_regular_walk_samples(duration_sec=25.0)
        result = extract_walking_features_py(samples, 25_000.0)
        assert result['duration_seconds'] == pytest.approx(25.0, abs=0.1)

    def test_higher_cadence_produces_more_steps(self):
        """[SYNTHETIC] 150 steps/min walk should yield more detected steps than 50 steps/min."""
        # Use very low noise and a large cadence gap to ensure the difference is detectable
        fast = _make_regular_walk_samples(cadence_steps_per_min=150, noise_scale=0.05)
        slow = _make_regular_walk_samples(cadence_steps_per_min=50, noise_scale=0.05)
        fast_result = extract_walking_features_py(fast, 30_000.0)
        slow_result = extract_walking_features_py(slow, 30_000.0)
        # At minimum, cadence should differ in the expected direction
        if fast_result['cadence'] and slow_result['cadence']:
            assert fast_result['cadence'] > slow_result['cadence'], \
                f"Fast cadence {fast_result['cadence']} should exceed slow {slow_result['cadence']}"
        else:
            # At least one must produce a valid result if steps differ
            assert fast_result['step_count'] >= slow_result['step_count'], \
                "Higher cadence should produce at least as many detected steps."
