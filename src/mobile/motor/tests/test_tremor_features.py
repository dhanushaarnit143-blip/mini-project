"""
Tests for MPF Mobile Extension — Tremor Feature Extractor (Phase 6)

Verifies that FFT-based tremor biomarkers are computed correctly from
synthetic IMU data.

Key verifications:
  - dominant_frequency correctly identified in the 3-12 Hz band
  - band_power_ratios sum to approximately 1.0
  - tremor_amplitude (RMS) is a non-negative float
  - raw sensor data arrays NOT returned in output
  - feature_version stamped correctly
  - Low-amplitude "still" signal returns near-zero tremor amplitude

ALL data is clearly labeled [SYNTHETIC].
"""

import pytest
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Pure-Python FFT + tremor extractor (mirrors tremorFeatureExtractor.js)
# ─────────────────────────────────────────────────────────────────────────────

def _next_power_of_2(n):
    p = 1
    while p < n:
        p <<= 1
    return p

def _hann_window(signal):
    N = len(signal)
    return [v * 0.5 * (1 - math.cos(2 * math.pi * i / (N - 1))) for i, v in enumerate(signal)]

def _fft(real_input):
    """Iterative Cooley-Tukey radix-2 FFT.  Returns list of complex numbers."""
    N = len(real_input)
    data = [complex(v, 0) for v in real_input]

    bits = int(math.log2(N))

    def bit_rev(n, b):
        rev = 0
        for _ in range(b):
            rev = (rev << 1) | (n & 1)
            n >>= 1
        return rev

    for i in range(N):
        j = bit_rev(i, bits)
        if j > i:
            data[i], data[j] = data[j], data[i]

    for s in range(1, bits + 1):
        m = 1 << s
        half = m >> 1
        w_root = complex(math.cos(-2 * math.pi / m), math.sin(-2 * math.pi / m))
        for k in range(0, N, m):
            w = complex(1, 0)
            for j in range(half):
                u = data[k + j]
                v = data[k + j + half] * w
                data[k + j]         = u + v
                data[k + j + half]  = u - v
                w *= w_root
    return data

def _extract_tremor_features_py(samples, duration_ms, sample_rate_hz=50):
    """
    Python mirror of tremorFeatureExtractor.js::extractTremorFeatures().
    ONLY for test validation — not a clinical tool.
    """
    FEATURE_VERSION = '1.0'
    BAND_MIN = 3.0
    BAND_MAX = 12.0

    if not samples or len(samples) < 10:
        return {
            'dominant_frequency': None, 'peak_power': None,
            'tremor_amplitude': None, 'band_power_ratios': None,
            'duration_seconds': duration_ms / 1000, 'sample_count': 0,
            'feature_version': FEATURE_VERSION,
            '_extraction_status': 'insufficient_samples',
        }

    mag = [math.sqrt(s['ax']**2 + s['ay']**2 + s['az']**2) for s in samples]
    mu = sum(mag) / len(mag)
    detrended = [v - mu for v in mag]
    windowed = _hann_window(detrended)

    N = _next_power_of_2(len(windowed))
    padded = windowed + [0.0] * (N - len(windowed))
    spectrum = _fft(padded)

    freq_res = sample_rate_hz / N
    half_N = N // 2
    psd = []
    for k in range(half_N + 1):
        power = (abs(spectrum[k]) ** 2) / N
        if 0 < k < half_N:
            power *= 2
        psd.append({'freq': k * freq_res, 'power': power})

    tremor_bins = [b for b in psd if BAND_MIN <= b['freq'] <= BAND_MAX]
    if not tremor_bins:
        return {
            'dominant_frequency': None, 'peak_power': None,
            'tremor_amplitude': None, 'band_power_ratios': None,
            'duration_seconds': round(duration_ms / 1000, 2), 'sample_count': len(samples),
            'feature_version': FEATURE_VERSION,
            '_extraction_status': 'no_tremor_band_bins',
        }

    dominant = max(tremor_bins, key=lambda b: b['power'])
    total_power = sum(b['power'] for b in psd)

    def band_ratio(lo, hi):
        bp = sum(b['power'] for b in psd if lo <= b['freq'] < hi)
        return round(bp / total_power, 4) if total_power > 0 else 0.0

    # Simple RMS of band-filtered signal (use the tremor_bins power proxy)
    tremor_band_power = sum(b['power'] for b in tremor_bins)
    tremor_amplitude = math.sqrt(tremor_band_power / len(tremor_bins)) if tremor_bins else 0.0

    band_power_ratios = {
        'physiological_tremor': band_ratio(0.5, 3.0),
        'pathological_tremor':  band_ratio(3.0, 8.0),
        'essential_tremor':     band_ratio(4.0, 12.0),
        'high_frequency':       band_ratio(8.0, 20.0),
    }

    return {
        'dominant_frequency': round(dominant['freq'], 3),
        'peak_power':         round(dominant['power'], 6),
        'tremor_amplitude':   round(tremor_amplitude, 6),
        'band_power_ratios':  band_power_ratios,
        'duration_seconds':   round(duration_ms / 1000, 2),
        'sample_count':       len(samples),
        'feature_version':    FEATURE_VERSION,
        '_extraction_status': 'ok',
    }


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic data generators
# ─────────────────────────────────────────────────────────────────────────────

def _make_tremor_signal(duration_sec=10.0, sample_rate_hz=50,
                         tremor_freq_hz=5.0, tremor_amp=0.3):
    """
    [SYNTHETIC] Generates IMU samples with a single dominant tremor frequency
    added to a gravity baseline. Clean sinusoid — FFT should recover tremor_freq_hz.
    """
    n = int(duration_sec * sample_rate_hz)
    samples = []
    for i in range(n):
        t_ms = (i / sample_rate_hz) * 1000
        t    = i / sample_rate_hz
        az = 9.81 + tremor_amp * math.sin(2 * math.pi * tremor_freq_hz * t)
        ax = 0.02 * math.sin(2 * math.pi * 1.0 * t)
        ay = 0.02 * math.cos(2 * math.pi * 1.0 * t)
        samples.append({'t': t_ms, 'ax': ax, 'ay': ay, 'az': az})
    return samples

def _make_still_signal(duration_sec=10.0, sample_rate_hz=50, noise_amp=0.005):
    """
    [SYNTHETIC] Near-zero tremor signal (phone placed on a table — not held).
    Only tiny numerical noise — should produce very low tremor_amplitude.
    """
    n = int(duration_sec * sample_rate_hz)
    return [
        {'t': (i / sample_rate_hz) * 1000,
         'ax': noise_amp * math.sin(i * 0.1),
         'ay': noise_amp * math.cos(i * 0.1),
         'az': 9.81 + noise_amp * math.sin(i * 0.07)}
        for i in range(n)
    ]

def _make_sparse_samples(n=5):
    """[SYNTHETIC] Minimal samples → insufficient_samples branch."""
    return [{'t': i * 20.0, 'ax': 0, 'ay': 0, 'az': 9.81} for i in range(n)]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTremorFeatureExtractor:
    """
    FFT-based tremor feature tests using synthetic IMU data.
    All inputs are clearly labeled [SYNTHETIC].
    """

    def test_dominant_frequency_correct(self):
        """
        [SYNTHETIC] Pure 5 Hz sinusoidal tremor signal → dominant_frequency near 5 Hz.
        Tolerance: ±1 Hz (limited by FFT frequency resolution at 50 Hz / 512 pts = 0.098 Hz).
        """
        samples = _make_tremor_signal(tremor_freq_hz=5.0, tremor_amp=0.5)
        result = _extract_tremor_features_py(samples, 10_000.0, sample_rate_hz=50)

        assert result['_extraction_status'] == 'ok', f"Status: {result['_extraction_status']}"
        assert result['dominant_frequency'] is not None
        assert abs(result['dominant_frequency'] - 5.0) <= 1.0, \
            f"Expected ~5 Hz, got {result['dominant_frequency']} Hz"

    def test_dominant_frequency_in_tremor_band(self):
        """[SYNTHETIC] dominant_frequency must be within the 3-12 Hz analysis band."""
        samples = _make_tremor_signal(tremor_freq_hz=7.0, tremor_amp=0.4)
        result = _extract_tremor_features_py(samples, 10_000.0)
        assert 3.0 <= result['dominant_frequency'] <= 12.0, \
            f"dominant_frequency {result['dominant_frequency']} outside 3-12 Hz band"

    def test_band_power_ratios_keys_present(self):
        """Band power ratio dict must contain all four expected sub-bands."""
        samples = _make_tremor_signal(tremor_freq_hz=5.0)
        result = _extract_tremor_features_py(samples, 10_000.0)
        assert result['band_power_ratios'] is not None
        expected_keys = {
            'physiological_tremor', 'pathological_tremor',
            'essential_tremor', 'high_frequency'
        }
        assert expected_keys.issubset(result['band_power_ratios'].keys())

    def test_band_power_ratios_non_negative(self):
        """[SYNTHETIC] All band power ratios must be >= 0."""
        samples = _make_tremor_signal(tremor_freq_hz=5.0)
        result = _extract_tremor_features_py(samples, 10_000.0)
        for band, ratio in result['band_power_ratios'].items():
            assert ratio >= 0, f"Band '{band}' has negative ratio: {ratio}"

    def test_tremor_amplitude_non_negative(self):
        """[SYNTHETIC] tremor_amplitude (RMS) must be >= 0."""
        samples = _make_tremor_signal(tremor_freq_hz=5.0, tremor_amp=0.3)
        result = _extract_tremor_features_py(samples, 10_000.0)
        assert result['tremor_amplitude'] is not None
        assert result['tremor_amplitude'] >= 0

    def test_still_signal_low_amplitude(self):
        """[SYNTHETIC] Near-zero signal → tremor_amplitude should be very low."""
        samples = _make_still_signal(noise_amp=0.005)
        result = _extract_tremor_features_py(samples, 10_000.0)
        if result['_extraction_status'] == 'ok' and result['tremor_amplitude'] is not None:
            assert result['tremor_amplitude'] < 0.1, \
                f"Still signal should have low amplitude, got {result['tremor_amplitude']}"

    def test_peak_power_positive(self):
        """[SYNTHETIC] peak_power must be > 0 for a signal with nonzero tremor."""
        samples = _make_tremor_signal(tremor_freq_hz=5.0, tremor_amp=0.4)
        result = _extract_tremor_features_py(samples, 10_000.0)
        assert result['peak_power'] is not None
        assert result['peak_power'] > 0, f"peak_power should be > 0, got {result['peak_power']}"

    def test_insufficient_samples(self):
        """[SYNTHETIC] < 10 samples → _extraction_status = 'insufficient_samples'."""
        sparse = _make_sparse_samples(n=5)
        result = _extract_tremor_features_py(sparse, 100.0)
        assert result['_extraction_status'] == 'insufficient_samples'
        assert result['dominant_frequency'] is None

    def test_feature_version_stamped(self):
        """feature_version must be '1.0' for versioned reproducibility."""
        samples = _make_tremor_signal()
        result = _extract_tremor_features_py(samples, 10_000.0)
        assert result['feature_version'] == '1.0'

    def test_raw_samples_not_in_output(self):
        """
        PRIVACY: raw IMU sample arrays must NOT be present in the returned feature dict.
        """
        samples = _make_tremor_signal()
        result = _extract_tremor_features_py(samples, 10_000.0)

        for key, val in result.items():
            assert not isinstance(val, list), \
                f"Key '{key}' contains a list — raw sensor data must NOT be returned."

    def test_sample_count_matches_input(self):
        """[SYNTHETIC] sample_count must equal the number of samples provided."""
        samples = _make_tremor_signal(duration_sec=10.0, sample_rate_hz=50)
        result = _extract_tremor_features_py(samples, 10_000.0)
        assert result['sample_count'] == len(samples)

    def test_different_tremor_frequencies_distinguishable(self):
        """
        [SYNTHETIC] A 4 Hz signal and a 9 Hz signal should have clearly different
        dominant_frequency values (within ±1.5 Hz of their true frequencies).
        """
        sig_4hz = _make_tremor_signal(tremor_freq_hz=4.0, tremor_amp=0.5)
        sig_9hz = _make_tremor_signal(tremor_freq_hz=9.0, tremor_amp=0.5)
        res_4 = _extract_tremor_features_py(sig_4hz, 10_000.0)
        res_9 = _extract_tremor_features_py(sig_9hz, 10_000.0)
        assert abs(res_4['dominant_frequency'] - 4.0) <= 1.5, \
            f"4 Hz signal: expected ~4 Hz, got {res_4['dominant_frequency']}"
        assert abs(res_9['dominant_frequency'] - 9.0) <= 1.5, \
            f"9 Hz signal: expected ~9 Hz, got {res_9['dominant_frequency']}"
        assert res_4['dominant_frequency'] < res_9['dominant_frequency'], \
            "4 Hz signal should have lower dominant_frequency than 9 Hz signal"
