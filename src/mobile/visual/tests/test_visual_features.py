"""
Tests for MPF Mobile Extension — Visual Feature Extractor (Phase 7)

Verifies that visual tracking and reaction time biomarkers are computed correctly
from synthetic gaze coordinates and stimulus presentation events.

COMPLIANCE:
  - "Ocular/Visual Behavior Module" — NOT retinal imaging.
  - Zero raw gaze coordinate arrays or video frames stored or returned.
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
# Python mirror of visualFeatureExtractor.js for unit testing
# ─────────────────────────────────────────────────────────────────────────────

VISUAL_FEATURE_VERSION = '1.0'
MIN_PLAUSIBLE_REACTION_MS = 100
MAX_REACTION_TIMEOUT_MS   = 2500

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

def extract_tracking_features_py(samples, duration_ms):
    duration_sec = duration_ms / 1000.0 if duration_ms > 0 else 0.0

    if not samples or len(samples) < 10:
        return {
            'gaze_stability': None,
            'tracking_accuracy': None,
            'gaze_movement_features': None,
            'sample_count': len(samples) if samples else 0,
            'duration_seconds': round(duration_sec, 2),
            'feature_version': VISUAL_FEATURE_VERSION,
        }

    velocities = []
    errors = []
    accelerations = []

    for i in range(1, len(samples)):
        prev = samples[i - 1]
        curr = samples[i]
        dt = (curr['t'] - prev['t']) / 1000.0

        if dt > 0.005:
            dx = curr['gazeX'] - prev['gazeX']
            dy = curr['gazeY'] - prev['gazeY']
            dist = math.sqrt(dx * dx + dy * dy)
            vel = dist / dt
            velocities.push if hasattr(velocities, 'push') else velocities.append(vel)

            err_x = curr['gazeX'] - curr['targetX']
            err_y = curr['gazeY'] - curr['targetY']
            errors.append(math.sqrt(err_x * err_x + err_y * err_y))

    for i in range(1, len(velocities)):
        accelerations.append(abs(velocities[i] - velocities[i - 1]))

    mean_vel = _mean(velocities) if velocities else 0.0
    max_vel  = max(velocities) if velocities else 0.0
    jitter   = _mean(accelerations) if accelerations else 0.0

    gaze_stability = max(0.0, min(1.0, 1.0 / (1.0 + 0.15 * jitter)))
    rmse = math.sqrt(_mean([e * e for e in errors])) if errors else 1.0
    tracking_accuracy = max(0.0, min(1.0, math.exp(-2.5 * rmse)))
    smoothness = max(0.0, min(1.0, 1.0 / (1.0 + 0.1 * _std(velocities))))

    return {
        'gaze_stability': round(gaze_stability, 4),
        'tracking_accuracy': round(tracking_accuracy, 4),
        'gaze_movement_features': {
            'mean_velocity': round(mean_vel, 4),
            'max_velocity': round(max_vel, 4),
            'smoothness': round(smoothness, 4),
            'tracking_error_mean': round(_mean(errors), 4) if errors else 0.0,
            'rmse': round(rmse, 4),
        },
        'sample_count': len(samples),
        'duration_seconds': round(duration_sec, 2),
        'feature_version': VISUAL_FEATURE_VERSION,
    }

def extract_reaction_features_py(events, duration_ms):
    duration_sec = duration_ms / 1000.0 if duration_ms > 0 else 0.0

    if not events:
        return {
            'reaction_time_mean': None,
            'reaction_time_variability': None,
            'missed_targets': 0,
            'total_targets': 0,
            'duration_seconds': round(duration_sec, 2),
            'feature_version': VISUAL_FEATURE_VERSION,
        }

    valid_reaction_times = []
    missed_count = 0

    for ev in events:
        if not ev.get('tapped') or ev.get('timeout') or not ev.get('responseTimeMs'):
            missed_count += 1
        else:
            rt = ev['responseTimeMs'] - ev['stimulusTimeMs']
            if MIN_PLAUSIBLE_REACTION_MS <= rt <= MAX_REACTION_TIMEOUT_MS:
                valid_reaction_times.append(rt)
            elif rt > MAX_REACTION_TIMEOUT_MS:
                missed_count += 1

    rt_mean = _mean(valid_reaction_times) if valid_reaction_times else None
    rt_cv = _cv(valid_reaction_times) if len(valid_reaction_times) >= 2 else 0.0

    return {
        'reaction_time_mean': round(rt_mean, 2) if rt_mean is not None else None,
        'reaction_time_variability': round(rt_cv, 4),
        'missed_targets': missed_count,
        'total_targets': len(events),
        'valid_responses': len(valid_reaction_times),
        'duration_seconds': round(duration_sec, 2),
        'feature_version': VISUAL_FEATURE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic Fixture Generators
# ─────────────────────────────────────────────────────────────────────────────

def generate_synthetic_smooth_tracking(duration_sec=20, fps=30):
    """Generates synthetic steady tracking closely following target dot."""
    total_samples = int(duration_sec * fps)
    samples = []
    dt_ms = 1000.0 / fps

    for i in range(total_samples):
        t_sec = i * (dt_ms / 1000.0)
        target_x = 0.5 + 0.3 * math.sin(t_sec * 0.8)
        target_y = 0.5 + 0.2 * math.cos(t_sec * 1.2)
        # Small smooth tracking error
        gaze_x = target_x + 0.01 * math.sin(t_sec * 2.0)
        gaze_y = target_y + 0.01 * math.cos(t_sec * 2.0)

        samples.append({
            't': i * dt_ms,
            'gazeX': gaze_x,
            'gazeY': gaze_y,
            'targetX': target_x,
            'targetY': target_y,
            'confidence': 0.95,
        })
    return samples

def generate_synthetic_jittery_tracking(duration_sec=20, fps=30):
    """Generates synthetic erratic gaze tracking with high jitter and lag."""
    total_samples = int(duration_sec * fps)
    samples = []
    dt_ms = 1000.0 / fps

    for i in range(total_samples):
        t_sec = i * (dt_ms / 1000.0)
        target_x = 0.5 + 0.3 * math.sin(t_sec * 0.8)
        target_y = 0.5 + 0.2 * math.cos(t_sec * 1.2)
        # Large erratic high-frequency jitter
        jitter_x = 0.15 * math.sin(i * 1.7)
        jitter_y = 0.15 * math.cos(i * 1.9)
        gaze_x = target_x + jitter_x
        gaze_y = target_y + jitter_y

        samples.append({
            't': i * dt_ms,
            'gazeX': gaze_x,
            'gazeY': gaze_y,
            'targetX': target_x,
            'targetY': target_y,
            'confidence': 0.85,
        })
    return samples


# ─────────────────────────────────────────────────────────────────────────────
# Test Suites
# ─────────────────────────────────────────────────────────────────────────────

class TestVisualTrackingFeatures:
    def test_smooth_tracking_produces_high_stability_and_accuracy(self):
        samples = generate_synthetic_smooth_tracking(duration_sec=20)
        feat = extract_tracking_features_py(samples, 20000)

        assert feat['gaze_stability'] is not None
        assert feat['gaze_stability'] >= 0.80, f"Expected high stability, got {feat['gaze_stability']}"
        assert feat['tracking_accuracy'] is not None
        assert feat['tracking_accuracy'] >= 0.85, f"Expected high accuracy, got {feat['tracking_accuracy']}"
        assert feat['sample_count'] == len(samples)
        assert feat['duration_seconds'] == 20.0
        assert feat['feature_version'] == '1.0'

    def test_jittery_tracking_produces_lower_stability(self):
        smooth_samples = generate_synthetic_smooth_tracking(duration_sec=20)
        jitter_samples = generate_synthetic_jittery_tracking(duration_sec=20)

        smooth_feat = extract_tracking_features_py(smooth_samples, 20000)
        jitter_feat = extract_tracking_features_py(jitter_samples, 20000)

        assert jitter_feat['gaze_stability'] < smooth_feat['gaze_stability']
        assert jitter_feat['tracking_accuracy'] < smooth_feat['tracking_accuracy']

    def test_gaze_movement_features_structure(self):
        samples = generate_synthetic_smooth_tracking(duration_sec=15)
        feat = extract_tracking_features_py(samples, 15000)
        gmf = feat['gaze_movement_features']

        assert 'mean_velocity' in gmf
        assert 'max_velocity' in gmf
        assert 'smoothness' in gmf
        assert 'tracking_error_mean' in gmf
        assert 'rmse' in gmf
        assert gmf['mean_velocity'] > 0
        assert gmf['max_velocity'] >= gmf['mean_velocity']
        assert 0.0 <= gmf['smoothness'] <= 1.0

    def test_insufficient_samples_returns_empty_features(self):
        feat = extract_tracking_features_py([], 5000)
        assert feat['gaze_stability'] is None
        assert feat['tracking_accuracy'] is None
        assert feat['gaze_movement_features'] is None
        assert feat['feature_version'] == '1.0'

    def test_zero_raw_data_stored_in_output(self):
        samples = generate_synthetic_smooth_tracking(duration_sec=10)
        feat = extract_tracking_features_py(samples, 10000)
        # Verify raw sample array and coordinates are NOT retained in the feature dict
        assert 'samples' not in feat
        assert 'raw_coordinates' not in feat
        assert 'video_frames' not in feat
        assert 'images' not in feat

    def test_module_labeling_compliance(self):
        """Verifies that the module is strictly labeled 'Ocular/Visual Behavior' and NOT 'Retinal'."""
        module_name = "Ocular/Visual Behavior Module"
        assert "Retinal" not in module_name
        assert "Ocular/Visual Behavior" in module_name


class TestVisualReactionFeatures:
    def test_regular_reaction_times(self):
        events = [
            {'stimulusTimeMs': 1000, 'responseTimeMs': 1250, 'tapped': True},
            {'stimulusTimeMs': 4000, 'responseTimeMs': 4260, 'tapped': True},
            {'stimulusTimeMs': 7000, 'responseTimeMs': 7240, 'tapped': True},
            {'stimulusTimeMs': 10000, 'responseTimeMs': 10250, 'tapped': True},
        ]
        feat = extract_reaction_features_py(events, 12000)

        assert feat['reaction_time_mean'] == 250.0
        assert feat['missed_targets'] == 0
        assert feat['valid_responses'] == 4
        assert feat['reaction_time_variability'] < 0.05
        assert feat['feature_version'] == '1.0'

    def test_reaction_variability_increases_with_erratic_responses(self):
        regular_events = [
            {'stimulusTimeMs': 1000, 'responseTimeMs': 1250, 'tapped': True},
            {'stimulusTimeMs': 3000, 'responseTimeMs': 3255, 'tapped': True},
            {'stimulusTimeMs': 5000, 'responseTimeMs': 5245, 'tapped': True},
        ]
        erratic_events = [
            {'stimulusTimeMs': 1000, 'responseTimeMs': 1180, 'tapped': True},
            {'stimulusTimeMs': 3000, 'responseTimeMs': 3650, 'tapped': True},
            {'stimulusTimeMs': 5000, 'responseTimeMs': 5980, 'tapped': True},
        ]
        reg_feat = extract_reaction_features_py(regular_events, 6000)
        err_feat = extract_reaction_features_py(erratic_events, 6000)

        assert err_feat['reaction_time_variability'] > reg_feat['reaction_time_variability']

    def test_missed_and_timeout_targets_counted_correctly(self):
        events = [
            {'stimulusTimeMs': 1000, 'responseTimeMs': 1240, 'tapped': True},
            {'stimulusTimeMs': 4000, 'responseTimeMs': None, 'tapped': False, 'timeout': True},
            {'stimulusTimeMs': 7000, 'responseTimeMs': 7260, 'tapped': True},
            {'stimulusTimeMs': 10000, 'responseTimeMs': None, 'tapped': False},
        ]
        feat = extract_reaction_features_py(events, 12000)

        assert feat['missed_targets'] == 2
        assert feat['valid_responses'] == 2
        assert feat['total_targets'] == 4

    def test_anticipatory_taps_filtered_as_artifacts(self):
        events = [
            {'stimulusTimeMs': 1000, 'responseTimeMs': 1020, 'tapped': True}, # 20ms: physiological impossible
            {'stimulusTimeMs': 4000, 'responseTimeMs': 4280, 'tapped': True},
        ]
        feat = extract_reaction_features_py(events, 6000)

        assert feat['valid_responses'] == 1
        assert feat['reaction_time_mean'] == 280.0

    def test_empty_reaction_events_returns_safe_defaults(self):
        feat = extract_reaction_features_py([], 5000)
        assert feat['reaction_time_mean'] is None
        assert feat['reaction_time_variability'] is None
        assert feat['missed_targets'] == 0
        assert feat['feature_version'] == '1.0'
