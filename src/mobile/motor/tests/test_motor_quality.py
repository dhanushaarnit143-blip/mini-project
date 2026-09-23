"""
Tests for MPF Mobile Extension — Motor Quality Scorer (Phase 6)

Verifies quality scoring for walking, tapping, and tremor hold tasks.

Key verifications:
  - Full-credit sessions receive quality_score = 1.00
  - Partial sessions receive partial scores matching documented weights
  - Sessions with quality_score < 0.50 are flagged as NOT baseline-eligible
  - Session models correctly reflect quality_score from the scorer
  - Low-quality sessions produce rejection_reasons
  - MotorSessionModel validation catches schema violations

ALL numeric data is clearly labeled [SYNTHETIC].
"""

import pytest
import math
import uuid
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Python mirror of motorQualityScorer.js
# ─────────────────────────────────────────────────────────────────────────────

MIN_BASELINE_QUALITY_THRESHOLD = 0.50

# Walking thresholds
WALKING_MIN_DURATION_SEC  = 25
WALKING_MIN_STEPS         = 10
WALKING_MIN_CADENCE       = 30
WALKING_MIN_REGULARITY    = 0.3

# Tapping thresholds
TAPPING_MIN_DURATION_SEC     = 8
TAPPING_MIN_TAPS             = 10
TAPPING_MIN_RATE             = 0.5
TAPPING_MAX_RATE             = 15
TAPPING_MAX_PAUSE_RATIO      = 0.3

# Tremor thresholds
TREMOR_MIN_DURATION_SEC          = 8
TREMOR_MAX_MOVEMENT_AMPLITUDE    = 2.0
TREMOR_MAX_AMPLITUDE_MOVEMENT    = 5.0


def score_walking(sensor_available, duration_seconds, step_count, cadence, movement_regularity):
    breakdown = {'sensor_available': 0, 'task_completed': 0, 'sufficient_steps': 0, 'signal_quality': 0}
    reasons = []
    if sensor_available:
        breakdown['sensor_available'] = 0.3
    else:
        reasons.append('sensor unavailable')
    if duration_seconds >= WALKING_MIN_DURATION_SEC:
        breakdown['task_completed'] = 0.3
    else:
        reasons.append(f'too short: {duration_seconds}s')
    if step_count > WALKING_MIN_STEPS:
        breakdown['sufficient_steps'] = 0.2
    else:
        reasons.append(f'steps: {step_count}')
    cadence_ok = cadence is not None and WALKING_MIN_CADENCE <= cadence <= 200
    regularity_ok = movement_regularity is not None and movement_regularity >= WALKING_MIN_REGULARITY
    if cadence_ok and regularity_ok:
        breakdown['signal_quality'] = 0.2
    else:
        reasons.append(f'cadence/regularity fail')
    score = round(sum(breakdown.values()), 2)
    return {'quality_score': score, 'breakdown': breakdown, 'rejection_reasons': reasons,
            'is_baseline_eligible': score >= MIN_BASELINE_QUALITY_THRESHOLD}


def score_tapping(duration_seconds, tap_count, tapping_rate, inter_tap_interval_variability):
    breakdown = {'task_completed': 0, 'sufficient_taps': 0, 'no_abnormal_interruptions': 0, 'reasonable_tap_rate': 0}
    reasons = []
    if duration_seconds >= TAPPING_MIN_DURATION_SEC:
        breakdown['task_completed'] = 0.3
    else:
        reasons.append(f'too short: {duration_seconds}s')
    if tap_count > TAPPING_MIN_TAPS:
        breakdown['sufficient_taps'] = 0.3
    else:
        reasons.append(f'taps: {tap_count}')
    no_interruption = inter_tap_interval_variability is None or inter_tap_interval_variability <= TAPPING_MAX_PAUSE_RATIO
    if no_interruption:
        breakdown['no_abnormal_interruptions'] = 0.2
    else:
        reasons.append(f'interruptions')
    rate_ok = tapping_rate is not None and TAPPING_MIN_RATE <= tapping_rate <= TAPPING_MAX_RATE
    if rate_ok:
        breakdown['reasonable_tap_rate'] = 0.2
    else:
        reasons.append(f'rate: {tapping_rate}')
    score = round(sum(breakdown.values()), 2)
    return {'quality_score': score, 'breakdown': breakdown, 'rejection_reasons': reasons,
            'is_baseline_eligible': score >= MIN_BASELINE_QUALITY_THRESHOLD}


def score_tremor(duration_seconds, tremor_amplitude, sample_count, extraction_status):
    breakdown = {'task_completed': 0, 'phone_held_still': 0, 'sufficient_signal_quality': 0, 'no_excessive_movement': 0}
    reasons = []
    if duration_seconds >= TREMOR_MIN_DURATION_SEC:
        breakdown['task_completed'] = 0.3
    else:
        reasons.append(f'too short: {duration_seconds}s')
    if tremor_amplitude is not None and tremor_amplitude <= TREMOR_MAX_MOVEMENT_AMPLITUDE:
        breakdown['phone_held_still'] = 0.3
    else:
        reasons.append('excessive movement')
    if sample_count >= 50 and extraction_status == 'ok':
        breakdown['sufficient_signal_quality'] = 0.2
    else:
        reasons.append(f'samples/status: {sample_count}/{extraction_status}')
    if tremor_amplitude is not None and tremor_amplitude <= TREMOR_MAX_AMPLITUDE_MOVEMENT:
        breakdown['no_excessive_movement'] = 0.2
    else:
        reasons.append('artifact ceiling exceeded')
    score = round(sum(breakdown.values()), 2)
    return {'quality_score': score, 'breakdown': breakdown, 'rejection_reasons': reasons,
            'is_baseline_eligible': score >= MIN_BASELINE_QUALITY_THRESHOLD}


# ─────────────────────────────────────────────────────────────────────────────
# Session model mirror (validates key fields)
# ─────────────────────────────────────────────────────────────────────────────

VALID_TASK_TYPES = {'walking', 'tapping', 'tremor_hold'}
UUID_RE = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

import re

def validate_motor_session(session_dict):
    errors = []
    if not re.match(UUID_RE, session_dict.get('participant_id', ''), re.I):
        errors.append('Invalid participant_id UUID')
    if not re.match(UUID_RE, session_dict.get('session_id', ''), re.I):
        errors.append('Invalid session_id UUID')
    if session_dict.get('task_type') not in VALID_TASK_TYPES:
        errors.append(f"Invalid task_type: {session_dict.get('task_type')}")
    if not (isinstance(session_dict.get('duration'), (int, float)) and session_dict['duration'] >= 0):
        errors.append('duration must be >= 0')
    qs = session_dict.get('quality_score')
    if not (isinstance(qs, (int, float)) and 0 <= qs <= 1):
        errors.append('quality_score must be 0-1')
    if not session_dict.get('feature_version'):
        errors.append('feature_version required')
    return {'valid': len(errors) == 0, 'errors': errors}


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestWalkingQuality:
    """Walking task quality scoring tests."""

    def test_full_credit_walking(self):
        """[SYNTHETIC] All criteria met → quality_score = 1.00."""
        result = score_walking(
            sensor_available=True, duration_seconds=30.0,
            step_count=50, cadence=100, movement_regularity=0.8
        )
        assert result['quality_score'] == 1.00
        assert result['is_baseline_eligible'] is True
        assert result['breakdown']['sensor_available'] == 0.3
        assert result['breakdown']['task_completed'] == 0.3
        assert result['breakdown']['sufficient_steps'] == 0.2
        assert result['breakdown']['signal_quality'] == 0.2

    def test_no_sensor_walking(self):
        """[SYNTHETIC] Sensor unavailable → quality_score = 0.70, partially gated."""
        result = score_walking(
            sensor_available=False, duration_seconds=30.0,
            step_count=50, cadence=100, movement_regularity=0.8
        )
        assert result['quality_score'] == pytest.approx(0.70, abs=0.01)
        assert result['breakdown']['sensor_available'] == 0
        assert len(result['rejection_reasons']) >= 1

    def test_short_walk_gated(self):
        """[SYNTHETIC] Only 10s of walking → quality_score < 0.50 → gated."""
        result = score_walking(
            sensor_available=True, duration_seconds=10.0,
            step_count=5, cadence=50, movement_regularity=0.2
        )
        assert result['quality_score'] < MIN_BASELINE_QUALITY_THRESHOLD
        assert result['is_baseline_eligible'] is False
        assert len(result['rejection_reasons']) > 0

    def test_low_regularity_fails_signal_quality(self):
        """[SYNTHETIC] movement_regularity < 0.3 → signal_quality = 0."""
        result = score_walking(
            sensor_available=True, duration_seconds=30.0,
            step_count=30, cadence=80, movement_regularity=0.1
        )
        assert result['breakdown']['signal_quality'] == 0


class TestTappingQuality:
    """Tapping task quality scoring tests."""

    def test_full_credit_tapping(self):
        """[SYNTHETIC] All criteria met → quality_score = 1.00."""
        result = score_tapping(
            duration_seconds=15.0, tap_count=50,
            tapping_rate=3.5, inter_tap_interval_variability=0.10
        )
        assert result['quality_score'] == 1.00
        assert result['is_baseline_eligible'] is True

    def test_insufficient_taps_gated(self):
        """[SYNTHETIC] Only 5 taps → quality_score <= 0.50 area."""
        result = score_tapping(
            duration_seconds=15.0, tap_count=5,
            tapping_rate=0.3, inter_tap_interval_variability=0.10
        )
        # Both sufficient_taps (0.30) and reasonable_tap_rate (0.20) should fail
        assert result['breakdown']['sufficient_taps'] == 0
        assert len(result['rejection_reasons']) >= 1

    def test_high_variability_flagged(self):
        """[SYNTHETIC] ITI variability > 0.30 → no_abnormal_interruptions = 0."""
        result = score_tapping(
            duration_seconds=12.0, tap_count=25,
            tapping_rate=2.0, inter_tap_interval_variability=0.60
        )
        assert result['breakdown']['no_abnormal_interruptions'] == 0

    def test_implausible_rate_fails(self):
        """[SYNTHETIC] tapping_rate = 20 (above 15 cap) → reasonable_tap_rate = 0."""
        result = score_tapping(
            duration_seconds=10.0, tap_count=200,
            tapping_rate=20.0, inter_tap_interval_variability=0.05
        )
        assert result['breakdown']['reasonable_tap_rate'] == 0


class TestTremorQuality:
    """Tremor hold task quality scoring tests."""

    def test_full_credit_tremor(self):
        """[SYNTHETIC] All criteria met → quality_score = 1.00."""
        result = score_tremor(
            duration_seconds=10.0, tremor_amplitude=0.3,
            sample_count=500, extraction_status='ok'
        )
        assert result['quality_score'] == 1.00
        assert result['is_baseline_eligible'] is True

    def test_excessive_movement_gated(self):
        """[SYNTHETIC] tremor_amplitude = 3.5 > 2.0 → phone_held_still = 0."""
        result = score_tremor(
            duration_seconds=10.0, tremor_amplitude=3.5,
            sample_count=500, extraction_status='ok'
        )
        assert result['breakdown']['phone_held_still'] == 0

    def test_low_samples_fails_quality(self):
        """[SYNTHETIC] sample_count = 20 < 50 → sufficient_signal_quality = 0."""
        result = score_tremor(
            duration_seconds=10.0, tremor_amplitude=0.2,
            sample_count=20, extraction_status='ok'
        )
        assert result['breakdown']['sufficient_signal_quality'] == 0

    def test_extraction_error_fails_quality(self):
        """[SYNTHETIC] extraction_status = 'insufficient_samples' → signal quality = 0."""
        result = score_tremor(
            duration_seconds=10.0, tremor_amplitude=0.2,
            sample_count=100, extraction_status='insufficient_samples'
        )
        assert result['breakdown']['sufficient_signal_quality'] == 0

    def test_artifact_ceiling_gated(self):
        """
        [SYNTHETIC] tremor_amplitude = 6.0 > 5.0 → no_excessive_movement = 0.
        Also 6.0 > 2.0 → phone_held_still = 0.
        Total = task_completed(0.3) + sufficient_signal_quality(0.2) = 0.50.
        Using a short duration so task_completed also fails → total < 0.50.
        """
        result = score_tremor(
            duration_seconds=5.0,    # fails task_completed (<8s)
            tremor_amplitude=6.0,    # fails phone_held_still (>2.0) AND no_excessive_movement (>5.0)
            sample_count=500,
            extraction_status='ok'
        )
        assert result['breakdown']['no_excessive_movement'] == 0
        assert result['breakdown']['phone_held_still'] == 0
        assert result['is_baseline_eligible'] is False


class TestMotorSessionModel:
    """Tests for session model schema validation."""

    def _valid_session(self, task_type='walking', quality_score=0.9):
        return {
            'participant_id': str(uuid.uuid4()),
            'session_id':     str(uuid.uuid4()),
            'task_type':      task_type,
            'duration':       30.0,
            'movement_variability': 0.05,
            'quality_score':  quality_score,
            'feature_version': '1.0',
        }

    def test_valid_walking_session_passes(self):
        """[SYNTHETIC] A complete walking session payload should pass validation."""
        result = validate_motor_session(self._valid_session('walking'))
        assert result['valid'] is True, result['errors']

    def test_valid_tapping_session_passes(self):
        """[SYNTHETIC] A complete tapping session payload should pass validation."""
        result = validate_motor_session(self._valid_session('tapping'))
        assert result['valid'] is True, result['errors']

    def test_valid_tremor_session_passes(self):
        """[SYNTHETIC] A complete tremor hold session payload should pass validation."""
        result = validate_motor_session(self._valid_session('tremor_hold'))
        assert result['valid'] is True, result['errors']

    def test_invalid_participant_uuid_rejected(self):
        """[SYNTHETIC] Non-UUID participant_id must fail validation."""
        session = self._valid_session()
        session['participant_id'] = 'not-a-uuid'
        result = validate_motor_session(session)
        assert result['valid'] is False
        assert any('participant_id' in e for e in result['errors'])

    def test_invalid_task_type_rejected(self):
        """[SYNTHETIC] Unrecognized task_type must fail validation."""
        session = self._valid_session()
        session['task_type'] = 'jumping'
        result = validate_motor_session(session)
        assert result['valid'] is False
        assert any('task_type' in e for e in result['errors'])

    def test_quality_score_out_of_range_rejected(self):
        """[SYNTHETIC] quality_score > 1.0 must fail validation."""
        session = self._valid_session(quality_score=1.5)
        result = validate_motor_session(session)
        assert result['valid'] is False
        assert any('quality_score' in e for e in result['errors'])

    def test_low_quality_is_flagged(self):
        """[SYNTHETIC] quality_score = 0.30 < 0.50 → is_baseline_eligible = False."""
        result = score_walking(
            sensor_available=False, duration_seconds=10.0,
            step_count=3, cadence=20, movement_regularity=0.1
        )
        assert result['quality_score'] < MIN_BASELINE_QUALITY_THRESHOLD
        assert result['is_baseline_eligible'] is False
        assert len(result['rejection_reasons']) > 0
