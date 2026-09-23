"""
Tests for MPF Mobile Extension — Blink Detection & Dynamics (Phase 7)

Verifies that blink detection, blink rate, blink interval variability, and mean
blink duration are accurately computed from synthetic Eye Aspect Ratio (EAR) time series.

COMPLIANCE:
  - "Ocular/Visual Behavior Module" — NOT retinal imaging.
  - Zero raw video frames or landmark streams stored in feature output.
  - feature_version stamped as '1.0'.
  - All test data is clearly labeled [SYNTHETIC].
"""

import pytest
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Python mirror of visualFeatureExtractor.js blink logic
# ─────────────────────────────────────────────────────────────────────────────

EAR_BLINK_THRESHOLD = 0.21
MIN_BLINK_DURATION_MS = 50
MAX_BLINK_DURATION_MS = 600
VISUAL_FEATURE_VERSION = '1.0'

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

def extract_blink_features_py(samples, duration_ms):
    duration_sec = duration_ms / 1000.0 if duration_ms > 0 else 0.0

    if not samples or len(samples) < 15:
        return {
            'blink_rate': None,
            'blink_interval_variability': None,
            'blink_duration_mean': None,
            'blink_count': 0,
            'duration_seconds': round(duration_sec, 2),
            'feature_version': VISUAL_FEATURE_VERSION,
        }

    blinks = []
    in_blink = False
    blink_start_t = 0

    for i in range(len(samples)):
        s = samples[i]
        if s['ear'] < EAR_BLINK_THRESHOLD:
            if not in_blink:
                in_blink = True
                blink_start_t = s['t']
        else:
            if in_blink:
                in_blink = False
                dur = s['t'] - blink_start_t
                if MIN_BLINK_DURATION_MS <= dur <= MAX_BLINK_DURATION_MS:
                    blinks.append({
                        'startT': blink_start_t,
                        'endT': s['t'],
                        'duration': dur,
                    })

    if in_blink:
        dur = samples[-1]['t'] - blink_start_t
        if MIN_BLINK_DURATION_MS <= dur <= MAX_BLINK_DURATION_MS:
            blinks.append({
                'startT': blink_start_t,
                'endT': samples[-1]['t'],
                'duration': dur,
            })

    blink_count = len(blinks)
    blink_rate = (blink_count / duration_sec) * 60.0 if duration_sec > 0 else 0.0

    ibis = []
    for i in range(1, len(blinks)):
        ibi = (blinks[i]['startT'] - blinks[i - 1]['startT']) / 1000.0
        if ibi > 0:
            ibis.append(ibi)

    blink_interval_variability = _cv(ibis) if len(ibis) >= 2 else 0.0
    durations = [b['duration'] for b in blinks]
    blink_duration_mean = _mean(durations) if durations else None

    return {
        'blink_rate': round(blink_rate, 2),
        'blink_interval_variability': round(blink_interval_variability, 4),
        'blink_duration_mean': round(blink_duration_mean, 2) if blink_duration_mean is not None else None,
        'blink_count': blink_count,
        'duration_seconds': round(duration_sec, 2),
        'feature_version': VISUAL_FEATURE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic Fixture Generators
# ─────────────────────────────────────────────────────────────────────────────

def generate_synthetic_blink_stream(duration_sec=30, blink_timestamps_sec=None, blink_duration_ms=150, fps=30):
    """
    Generates synthetic EAR samples with defined blink events.
    Eyes open EAR = 0.32, eyes closed during blink EAR = 0.14.
    """
    if blink_timestamps_sec is None:
        blink_timestamps_sec = [3.0, 7.0, 12.0, 16.0, 21.0, 26.0] # 6 blinks in 30s -> 12 blinks/min

    dt_ms = 1000.0 / fps
    total_frames = int(duration_sec * fps)
    samples = []

    for i in range(total_frames):
        t_ms = i * dt_ms
        t_sec = t_ms / 1000.0

        is_blinking = False
        for bt in blink_timestamps_sec:
            bt_ms = bt * 1000.0
            if bt_ms <= t_ms <= (bt_ms + blink_duration_ms):
                is_blinking = True
                break

        ear = 0.14 if is_blinking else 0.32
        samples.append({
            't': t_ms,
            'ear': ear,
            'confidence': 0.95,
        })

    return samples


# ─────────────────────────────────────────────────────────────────────────────
# Test Suites
# ─────────────────────────────────────────────────────────────────────────────

class TestBlinkDetection:
    def test_blink_rate_calculated_accurately(self):
        # 6 blinks in 30 seconds -> exactly 12.0 blinks/min
        samples = generate_synthetic_blink_stream(
            duration_sec=30,
            blink_timestamps_sec=[3.0, 7.0, 12.0, 16.0, 21.0, 26.0],
            blink_duration_ms=150
        )
        feat = extract_blink_features_py(samples, 30000)

        assert feat['blink_count'] == 6
        assert feat['blink_rate'] == 12.0
        assert feat['duration_seconds'] == 30.0
        assert feat['feature_version'] == '1.0'

    def test_blink_rate_higher_frequency(self):
        # 10 blinks in 30 seconds -> 20.0 blinks/min
        blinks_sec = [2.0, 5.0, 8.0, 11.0, 14.0, 17.0, 20.0, 23.0, 26.0, 28.5]
        samples = generate_synthetic_blink_stream(
            duration_sec=30,
            blink_timestamps_sec=blinks_sec,
            blink_duration_ms=150
        )
        feat = extract_blink_features_py(samples, 30000)

        assert feat['blink_count'] == 10
        assert feat['blink_rate'] == 20.0

    def test_blink_duration_mean_accurately_measured(self):
        # Fixed 200 ms duration blinks
        samples = generate_synthetic_blink_stream(
            duration_sec=20,
            blink_timestamps_sec=[2.0, 6.0, 10.0, 14.0],
            blink_duration_ms=200
        )
        feat = extract_blink_features_py(samples, 20000)

        assert feat['blink_duration_mean'] is not None
        # Allow small +/- 1 frame discretization tolerance (~33ms)
        assert abs(feat['blink_duration_mean'] - 200.0) <= 35.0

    def test_blink_interval_variability(self):
        # Regular intervals: 4s spacing (4, 8, 12, 16, 20) -> very low CV
        reg_samples = generate_synthetic_blink_stream(
            duration_sec=25,
            blink_timestamps_sec=[4.0, 8.0, 12.0, 16.0, 20.0],
            blink_duration_ms=150
        )
        # Irregular intervals: 1s, 6s, 2s, 8s -> high CV
        irreg_samples = generate_synthetic_blink_stream(
            duration_sec=25,
            blink_timestamps_sec=[2.0, 3.0, 9.0, 11.0, 19.0],
            blink_duration_ms=150
        )

        reg_feat = extract_blink_features_py(reg_samples, 25000)
        irreg_feat = extract_blink_features_py(irreg_samples, 25000)

        assert irreg_feat['blink_interval_variability'] > reg_feat['blink_interval_variability']

    def test_zero_blinks_edge_case(self):
        # Participant eyes remain open for entire duration (no drops below threshold)
        samples = generate_synthetic_blink_stream(duration_sec=30, blink_timestamps_sec=[])
        feat = extract_blink_features_py(samples, 30000)

        assert feat['blink_count'] == 0
        assert feat['blink_rate'] == 0.0
        assert feat['blink_interval_variability'] == 0.0
        assert feat['blink_duration_mean'] is None

    def test_prolonged_closure_is_excluded_from_normal_blinks(self):
        # Eye closure for 1500 ms (e.g. microsleep / eye closure), well above MAX_BLINK_DURATION_MS (600ms)
        samples = generate_synthetic_blink_stream(
            duration_sec=20,
            blink_timestamps_sec=[5.0],
            blink_duration_ms=1500
        )
        feat = extract_blink_features_py(samples, 20000)

        # Prolonged closure must not be registered as a normal blink
        assert feat['blink_count'] == 0
        assert feat['blink_rate'] == 0.0

    def test_noise_flutter_below_50ms_is_filtered(self):
        # Brief 20 ms flicker (e.g. single-frame artifact)
        samples = generate_synthetic_blink_stream(
            duration_sec=15,
            blink_timestamps_sec=[3.0],
            blink_duration_ms=20
        )
        feat = extract_blink_features_py(samples, 15000)

        assert feat['blink_count'] == 0

    def test_insufficient_samples_returns_empty_record(self):
        feat = extract_blink_features_py([], 5000)
        assert feat['blink_rate'] is None
        assert feat['blink_interval_variability'] is None
        assert feat['blink_duration_mean'] is None
        assert feat['blink_count'] == 0
        assert feat['feature_version'] == '1.0'

    def test_zero_raw_images_or_frames_in_output(self):
        samples = generate_synthetic_blink_stream(duration_sec=10)
        feat = extract_blink_features_py(samples, 10000)
        assert 'samples' not in feat
        assert 'ear_series' not in feat
        assert 'frames' not in feat
        assert 'images' not in feat
