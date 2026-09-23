"""
Tests for MPF Mobile Extension — Quality Filtering Engine (Phase 9)

Validates:
1. Strict session-level quality gating: sessions with quality_score >= 0.50 are passed,
   while sessions with quality_score < 0.50 are excluded from aggregation.
2. Modality status transitions:
   - "missing" if 0 sessions recorded.
   - "low_quality" if all recorded sessions fail (< 0.50).
   - "valid" if at least one session meets threshold.
3. Overall daily quality index computation across valid modalities.
4. Parity between Python test harness and actual JavaScript implementation (qualityFilter.js).

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import subprocess
import pytest
from pathlib import Path

MIN_QUALITY_THRESHOLD = 0.50
JS_MODULE_PATH = Path(__file__).resolve().parents[1] / "qualityFilter.js"


def is_session_quality_acceptable_py(session: dict, threshold: float = MIN_QUALITY_THRESHOLD) -> bool:
    """Python reference mirror of isSessionQualityAcceptable."""
    if not isinstance(session, dict):
        return False
    score = session.get("quality_score")
    if score is None:
        score = session.get("signal_quality")
    if score is None and "score" in session:
        s = session["score"]
        score = s / 100.0 if s > 1.0 else s
    if score is None or not isinstance(score, (int, float)) or score < 0.0:
        return False
    return score >= threshold


def filter_sessions_by_quality_py(sessions: list, threshold: float = MIN_QUALITY_THRESHOLD):
    """Python reference mirror of filterSessionsByQuality."""
    passed = []
    rejected = []
    for s in sessions:
        if is_session_quality_acceptable_py(s, threshold):
            passed.append(s)
        else:
            rejected.append(s)
    return passed, rejected


def evaluate_modality_quality_py(sessions: list, threshold: float = MIN_QUALITY_THRESHOLD):
    """Python reference mirror of evaluateModalityQuality."""
    if not sessions:
        return {
            "status": "missing",
            "quality_score": None,
            "passed_count": 0,
            "total_count": 0,
            "rejected_count": 0,
        }
    passed, rejected = filter_sessions_by_quality_py(sessions, threshold)
    if not passed:
        scores = sorted([s.get("quality_score", 0.0) for s in sessions])
        mid = len(scores) // 2
        med = (scores[mid - 1] + scores[mid]) / 2 if len(scores) % 2 == 0 else scores[mid]
        return {
            "status": "low_quality",
            "quality_score": round(med, 4),
            "passed_count": 0,
            "total_count": len(sessions),
            "rejected_count": len(rejected),
        }
    scores = sorted([s.get("quality_score", 0.0) for s in passed])
    mid = len(scores) // 2
    med = (scores[mid - 1] + scores[mid]) / 2 if len(scores) % 2 == 0 else scores[mid]
    return {
        "status": "valid",
        "quality_score": round(med, 4),
        "passed_count": len(passed),
        "total_count": len(sessions),
        "rejected_count": len(rejected),
    }


def calculate_overall_quality_py(quality_map: dict) -> float:
    """Python reference mirror of calculateOverallQuality."""
    keys = ["typing_quality", "voice_quality", "motor_quality", "visual_quality"]
    valid_scores = [quality_map[k] for k in keys if isinstance(quality_map.get(k), (int, float)) and quality_map[k] >= 0.0]
    if not valid_scores:
        return 0.0
    return round(sum(valid_scores) / len(valid_scores), 4)


# ── Python Unit Tests ────────────────────────────────────────────────────────

def test_session_quality_boundary_conditions():
    """Verify exact 0.50 threshold gating."""
    # [SYNTHETIC] test sessions
    assert is_session_quality_acceptable_py({"quality_score": 0.50}) is True
    assert is_session_quality_acceptable_py({"quality_score": 0.500001}) is True
    assert is_session_quality_acceptable_py({"quality_score": 0.499999}) is False
    assert is_session_quality_acceptable_py({"quality_score": 0.0}) is False
    assert is_session_quality_acceptable_py({"quality_score": 1.0}) is True
    assert is_session_quality_acceptable_py({}) is False
    assert is_session_quality_acceptable_py({"quality_score": -0.2}) is False


def test_filter_sessions_by_quality_partitioning():
    """Verify sessions are properly partitioned into passed and rejected lists."""
    # [SYNTHETIC] mixed-quality sessions
    sessions = [
        {"session_id": "s1", "quality_score": 0.85},
        {"session_id": "s2", "quality_score": 0.35},
        {"session_id": "s3", "quality_score": 0.92},
        {"session_id": "s4", "quality_score": 0.48},
        {"session_id": "s5", "quality_score": 0.50},
    ]
    passed, rejected = filter_sessions_by_quality_py(sessions)
    assert len(passed) == 3
    assert len(rejected) == 2
    passed_ids = [s["session_id"] for s in passed]
    rejected_ids = [s["session_id"] for s in rejected]
    assert passed_ids == ["s1", "s3", "s5"]
    assert rejected_ids == ["s2", "s4"]


def test_evaluate_modality_status_transitions():
    """Verify modality evaluation distinguishes missing, low_quality, and valid states."""
    # 1. No sessions -> missing
    res_empty = evaluate_modality_quality_py([])
    assert res_empty["status"] == "missing"
    assert res_empty["quality_score"] is None
    assert res_empty["passed_count"] == 0

    # 2. All sessions below 0.5 -> low_quality
    # [SYNTHETIC] all low-quality sessions
    bad_sessions = [
        {"quality_score": 0.30},
        {"quality_score": 0.42},
    ]
    res_bad = evaluate_modality_quality_py(bad_sessions)
    assert res_bad["status"] == "low_quality"
    assert res_bad["passed_count"] == 0
    assert res_bad["rejected_count"] == 2
    assert res_bad["quality_score"] == 0.36

    # 3. At least one passed session -> valid
    # [SYNTHETIC] mixed sessions
    mixed_sessions = [
        {"quality_score": 0.30},
        {"quality_score": 0.80},
    ]
    res_mixed = evaluate_modality_quality_py(mixed_sessions)
    assert res_mixed["status"] == "valid"
    assert res_mixed["passed_count"] == 1
    assert res_mixed["rejected_count"] == 1
    assert res_mixed["quality_score"] == 0.80


def test_calculate_overall_quality():
    """Verify overall quality index averages valid modalities and ignores missing."""
    quality_map = {
        "typing_quality": 0.80,
        "voice_quality": 0.90,
        "motor_quality": None,      # missing
        "visual_quality": 0.70,
    }
    overall = calculate_overall_quality_py(quality_map)
    expected = round((0.80 + 0.90 + 0.70) / 3, 4)
    assert overall == expected

    # All missing
    assert calculate_overall_quality_py({"typing_quality": None}) == 0.0


# ── JavaScript Parity Tests (Executing Node.js) ──────────────────────────────

def test_js_quality_filter_module_parity():
    """Verify that qualityFilter.js runs under Node.js and produces identical outputs."""
    js_test_code = f"""
    const {{
      isSessionQualityAcceptable,
      filterSessionsByQuality,
      evaluateModalityQuality,
      calculateOverallQuality
    }} = require({json.dumps(str(JS_MODULE_PATH))});

    // 1. Boundary
    const b1 = isSessionQualityAcceptable({{ quality_score: 0.50 }});
    const b2 = isSessionQualityAcceptable({{ quality_score: 0.499 }});

    // 2. Partition
    const [p, r] = (function() {{
      const res = filterSessionsByQuality([
        {{ quality_score: 0.8 }},
        {{ quality_score: 0.2 }}
      ]);
      return [res.passedSessions.length, res.rejectedSessions.length];
    }})();

    // 3. Evaluation
    const evalEmpty = evaluateModalityQuality([]);
    const evalBad = evaluateModalityQuality([{{ quality_score: 0.25 }}, {{ quality_score: 0.35 }}]);
    const evalGood = evaluateModalityQuality([{{ quality_score: 0.95 }}]);

    // 4. Overall quality
    const overall = calculateOverallQuality({{
      typing_quality: 0.80,
      voice_quality: 0.90,
      motor_quality: null,
      visual_quality: 0.70
    }});

    console.log(JSON.stringify({{
      b1, b2, p, r,
      evalEmptyStatus: evalEmpty.status,
      evalBadStatus: evalBad.status,
      evalGoodStatus: evalGood.status,
      overall
    }}));
    """

    res = subprocess.run(
        ["node", "-e", js_test_code],
        capture_output=True,
        text=True,
        check=True
    )
    data = json.loads(res.stdout.strip())
    assert data["b1"] is True
    assert data["b2"] is False
    assert data["p"] == 1
    assert data["r"] == 1
    assert data["evalEmptyStatus"] == "missing"
    assert data["evalBadStatus"] == "low_quality"
    assert data["evalGoodStatus"] == "valid"
    assert abs(data["overall"] - 0.80) < 1e-4
