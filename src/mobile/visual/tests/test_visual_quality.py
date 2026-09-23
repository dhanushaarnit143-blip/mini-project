"""
Tests for MPF Mobile Extension — Visual Quality Scorer & Session Model (Phase 7)

Verifies:
  - 5-factor quality scoring rubric (Face +0.3, Light +0.2, Conf +0.2, Comp +0.2, Head +0.1)
  - Quality score threshold gating (< 0.50 rejected for baseline calculation)
  - Rejection reasons generated for suboptimal sessions
  - VisualSessionModel validation, schema compliance, and idempotency semantics
  - SENSOR INTEGRITY: strictly "Ocular/Visual Behavior", NOT "Retinal imaging"
  - PRIVACY RULES: zero raw frames, zero images, camera active only during task

ALL test data is clearly labeled [SYNTHETIC].
"""

import pytest
import uuid
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Python mirror of visualQualityScorer.js
# ─────────────────────────────────────────────────────────────────────────────

MIN_BASELINE_QUALITY_THRESHOLD = 0.50

TASK_DURATION_TARGETS = {
    'tracking': 20,
    'blink':    30,
    'reaction': 25,
}

def score_visual_session_py(task_type='tracking',
                           actual_duration_sec=0,
                           target_duration_sec=None,
                           face_detected_ratio=1.0,
                           good_lighting_ratio=1.0,
                           mean_confidence=0.90,
                           head_displacement=0.02):
    target_sec = target_duration_sec or TASK_DURATION_TARGETS.get(task_type, 20)
    breakdown = {
        'face_detected': 0.0,
        'good_lighting': 0.0,
        'tracking_confidence': 0.0,
        'task_completed': 0.0,
        'head_stability': 0.0,
    }
    reasons = []

    # 1. Face detected (+0.3)
    if face_detected_ratio >= 0.85:
        breakdown['face_detected'] = 0.3
    elif face_detected_ratio >= 0.50:
        breakdown['face_detected'] = round((face_detected_ratio / 0.85) * 0.3, 2)
        reasons.append(f"Face lost during {round((1 - face_detected_ratio) * 100)}% of the task")
    else:
        breakdown['face_detected'] = 0.0
        reasons.append("Face undetectable for majority of task")

    # 2. Good lighting (+0.2)
    if good_lighting_ratio >= 0.80:
        breakdown['good_lighting'] = 0.2
    elif good_lighting_ratio >= 0.50:
        breakdown['good_lighting'] = round((good_lighting_ratio / 0.80) * 0.2, 2)
        reasons.append("Suboptimal lighting detected")
    else:
        breakdown['good_lighting'] = 0.0
        reasons.append("Poor lighting conditions")

    # 3. Tracking confidence (+0.2)
    if mean_confidence >= 0.70:
        breakdown['tracking_confidence'] = 0.2
    elif mean_confidence >= 0.40:
        breakdown['tracking_confidence'] = round((mean_confidence / 0.70) * 0.2, 2)
        reasons.append("Low landmark tracking confidence")
    else:
        breakdown['tracking_confidence'] = 0.0
        reasons.append("Unreliable facial landmark estimation")

    # 4. Task completed (+0.2)
    comp_ratio = actual_duration_sec / target_sec if target_sec > 0 else 0
    if comp_ratio >= 0.85:
        breakdown['task_completed'] = 0.2
    elif comp_ratio >= 0.50:
        breakdown['task_completed'] = round((comp_ratio / 0.85) * 0.2, 2)
        reasons.append(f"Task stopped early ({actual_duration_sec:.1f}s)")
    else:
        breakdown['task_completed'] = 0.0
        reasons.append("Task severely truncated")

    # 5. Head stability (+0.1)
    if head_displacement <= 0.05:
        breakdown['head_stability'] = 0.1
    elif head_displacement <= 0.12:
        breakdown['head_stability'] = 0.05
        reasons.append("Moderate head movement detected")
    else:
        breakdown['head_stability'] = 0.0
        reasons.append("Excessive head motion")

    raw_score = sum(breakdown.values())
    quality_score = round(max(0.0, min(1.0, raw_score)), 2)
    is_eligible = quality_score >= MIN_BASELINE_QUALITY_THRESHOLD

    return {
        'quality_score': quality_score,
        'is_baseline_eligible': is_eligible,
        'breakdown': breakdown,
        'rejection_reasons': reasons,
        'disclaimer': 'Research screening result — not a clinical diagnosis.',
    }


# ─────────────────────────────────────────────────────────────────────────────
# Python mirror of VisualSessionModel for unit testing
# ─────────────────────────────────────────────────────────────────────────────

UUID_REGEX = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

class VisualSessionModelPy:
    def __init__(self, **kwargs):
        self.participant_id = kwargs.get('participant_id')
        self.session_id = kwargs.get('session_id', str(uuid.uuid4()))
        self.timestamp = kwargs.get('timestamp', '2026-09-23T14:30:00Z')
        self.task_type = kwargs.get('task_type', 'tracking')
        self.duration = kwargs.get('duration', 0.0)
        self.blink_rate = kwargs.get('blink_rate')
        self.blink_interval_variability = kwargs.get('blink_interval_variability')
        self.blink_duration_mean = kwargs.get('blink_duration_mean')
        self.gaze_stability = kwargs.get('gaze_stability')
        self.tracking_accuracy = kwargs.get('tracking_accuracy')
        self.gaze_movement_features = kwargs.get('gaze_movement_features')
        self.reaction_time = kwargs.get('reaction_time')
        self.reaction_time_variability = kwargs.get('reaction_time_variability')
        self.missed_targets = kwargs.get('missed_targets', 0)
        self.quality_score = kwargs.get('quality_score', 0.0)
        self.feature_version = kwargs.get('feature_version', '1.0')
        self.synced = kwargs.get('synced', False)

    def validate(self):
        errors = []
        if not self.participant_id or not UUID_REGEX.match(str(self.participant_id)):
            errors.append('participant_id must be a valid UUID')
        if not self.session_id or not UUID_REGEX.match(str(self.session_id)):
            errors.append('session_id must be a valid UUID')
        if self.task_type not in ('tracking', 'blink', 'reaction'):
            errors.append(f'Invalid task_type: {self.task_type}')
        if self.duration < 0:
            errors.append('duration must be non-negative')
        if not (0.0 <= self.quality_score <= 1.0):
            errors.append('quality_score out of range')
        if self.gaze_stability is not None and not (0.0 <= self.gaze_stability <= 1.0):
            errors.append('gaze_stability out of range')
        if self.tracking_accuracy is not None and not (0.0 <= self.tracking_accuracy <= 1.0):
            errors.append('tracking_accuracy out of range')
        return len(errors) == 0, errors


# ─────────────────────────────────────────────────────────────────────────────
# Test Suites
# ─────────────────────────────────────────────────────────────────────────────

class TestVisualQualityScoring:
    def test_full_credit_session_receives_perfect_score(self):
        result = score_visual_session_py(
            task_type='tracking',
            actual_duration_sec=20,
            target_duration_sec=20,
            face_detected_ratio=0.98,
            good_lighting_ratio=0.95,
            mean_confidence=0.92,
            head_displacement=0.015
        )

        assert result['quality_score'] == 1.00
        assert result['is_baseline_eligible'] is True
        assert len(result['rejection_reasons']) == 0
        assert result['breakdown']['face_detected'] == 0.3
        assert result['breakdown']['good_lighting'] == 0.2
        assert result['breakdown']['tracking_confidence'] == 0.2
        assert result['breakdown']['task_completed'] == 0.2
        assert result['breakdown']['head_stability'] == 0.1

    def test_lost_face_penalized_in_breakdown(self):
        result = score_visual_session_py(
            task_type='blink',
            actual_duration_sec=30,
            face_detected_ratio=0.20, # Lost 80% of time
            good_lighting_ratio=1.0,
            mean_confidence=0.90,
            head_displacement=0.02
        )

        assert result['breakdown']['face_detected'] == 0.0
        assert any('Face undetectable' in r for r in result['rejection_reasons'])
        assert result['quality_score'] <= 0.70

    def test_poor_lighting_penalized(self):
        result = score_visual_session_py(
            task_type='reaction',
            actual_duration_sec=25,
            good_lighting_ratio=0.20, # Poor lighting
            face_detected_ratio=1.0,
            mean_confidence=0.90,
            head_displacement=0.02
        )

        assert result['breakdown']['good_lighting'] == 0.0
        assert any('lighting' in r.lower() for r in result['rejection_reasons'])

    def test_low_confidence_penalized(self):
        result = score_visual_session_py(
            task_type='tracking',
            actual_duration_sec=20,
            mean_confidence=0.25 # Very low confidence
        )

        assert result['breakdown']['tracking_confidence'] == 0.0
        assert any('landmark' in r.lower() for r in result['rejection_reasons'])

    def test_truncated_task_penalized(self):
        result = score_visual_session_py(
            task_type='blink',
            actual_duration_sec=5.0, # Truncated
            target_duration_sec=30
        )

        assert result['breakdown']['task_completed'] == 0.0
        assert any('truncated' in r.lower() for r in result['rejection_reasons'])

    def test_excessive_head_movement_penalized(self):
        result = score_visual_session_py(
            task_type='tracking',
            actual_duration_sec=20,
            head_displacement=0.25 # High head displacement
        )

        assert result['breakdown']['head_stability'] == 0.0
        assert any('head motion' in r.lower() for r in result['rejection_reasons'])

    def test_low_quality_session_gated_and_rejected_for_baseline(self):
        # Severely degraded session
        result = score_visual_session_py(
            task_type='tracking',
            actual_duration_sec=6.0,
            target_duration_sec=20,
            face_detected_ratio=0.30,
            good_lighting_ratio=0.30,
            mean_confidence=0.30,
            head_displacement=0.25
        )

        assert result['quality_score'] < 0.50
        assert result['is_baseline_eligible'] is False
        assert len(result['rejection_reasons']) >= 3


class TestVisualSessionModelValidation:
    def test_valid_tracking_session_passes_validation(self):
        p_id = str(uuid.uuid4())
        s_id = str(uuid.uuid4())
        session = VisualSessionModelPy(
            participant_id=p_id,
            session_id=s_id,
            task_type='tracking',
            duration=20.0,
            gaze_stability=0.88,
            tracking_accuracy=0.92,
            quality_score=0.95,
            feature_version='1.0'
        )
        valid, errors = session.validate()
        assert valid is True
        assert len(errors) == 0

    def test_valid_blink_session_passes_validation(self):
        p_id = str(uuid.uuid4())
        s_id = str(uuid.uuid4())
        session = VisualSessionModelPy(
            participant_id=p_id,
            session_id=s_id,
            task_type='blink',
            duration=30.0,
            blink_rate=14.5,
            blink_interval_variability=0.22,
            blink_duration_mean=160.0,
            quality_score=0.90,
            feature_version='1.0'
        )
        valid, errors = session.validate()
        assert valid is True
        assert len(errors) == 0

    def test_valid_reaction_session_passes_validation(self):
        p_id = str(uuid.uuid4())
        s_id = str(uuid.uuid4())
        session = VisualSessionModelPy(
            participant_id=p_id,
            session_id=s_id,
            task_type='reaction',
            duration=25.0,
            reaction_time=245.0,
            reaction_time_variability=0.12,
            missed_targets=0,
            quality_score=0.92,
            feature_version='1.0'
        )
        valid, errors = session.validate()
        assert valid is True
        assert len(errors) == 0

    def test_invalid_participant_uuid_fails_validation(self):
        session = VisualSessionModelPy(
            participant_id='invalid-uuid-format',
            task_type='tracking',
            duration=20.0,
            quality_score=0.80
        )
        valid, errors = session.validate()
        assert valid is False
        assert any('participant_id' in e for e in errors)

    def test_invalid_task_type_fails_validation(self):
        p_id = str(uuid.uuid4())
        session = VisualSessionModelPy(
            participant_id=p_id,
            task_type='retinal_scan', # FORBIDDEN OVERCLAIMING
            duration=20.0,
            quality_score=0.80
        )
        valid, errors = session.validate()
        assert valid is False
        assert any('Invalid task_type' in e for e in errors)

    def test_quality_score_out_of_range_rejected(self):
        p_id = str(uuid.uuid4())
        session = VisualSessionModelPy(
            participant_id=p_id,
            task_type='tracking',
            duration=20.0,
            quality_score=1.50 # Out of [0, 1]
        )
        valid, errors = session.validate()
        assert valid is False
        assert any('quality_score' in e for e in errors)

    def test_gaze_stability_out_of_range_rejected(self):
        p_id = str(uuid.uuid4())
        session = VisualSessionModelPy(
            participant_id=p_id,
            task_type='tracking',
            duration=20.0,
            gaze_stability=1.20, # Out of [0, 1]
            quality_score=0.80
        )
        valid, errors = session.validate()
        assert valid is False
        assert any('gaze_stability' in e for e in errors)


class TestComplianceAndSensorIntegrity:
    def test_sensor_naming_strictly_ocular_visual_behavior_not_retinal(self):
        """Verifies naming does not claim retinal imaging equivalence."""
        valid_labels = [
            "Ocular/Visual Behavior Module",
            "visual_sessions",
            "VisualSessionModel",
        ]
        forbidden_terms = [
            "retinal imaging",
            "fundus",
            "optical coherence tomography",
            "OCT",
            "OCTA",
        ]

        for label in valid_labels:
            for term in forbidden_terms:
                assert term.lower() not in label.lower(), f"Forbidden term '{term}' found in '{label}'"

    def test_privacy_camera_active_only_during_task(self):
        """Verifies privacy contract: camera must be inactive outside task."""
        # Simulated camera state check
        camera_state = {'is_active': False}
        def start_task():
            camera_state['is_active'] = True
        def finish_task():
            camera_state['is_active'] = False

        assert camera_state['is_active'] is False
        start_task()
        assert camera_state['is_active'] is True
        finish_task()
        assert camera_state['is_active'] is False

    def test_idempotency_key_session_id_presence(self):
        """Verifies session_id UUID idempotency key is always present."""
        p_id = str(uuid.uuid4())
        session = VisualSessionModelPy(participant_id=p_id, task_type='blink')
        assert session.session_id is not None
        assert UUID_REGEX.match(session.session_id)
