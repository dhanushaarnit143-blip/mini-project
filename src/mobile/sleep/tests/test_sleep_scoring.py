"""
Tests for MPF Mobile Extension — Sleep & RBD Scorer (Phase 8)

Verifies:
1. Standardized 0-100 sleep scoring logic across duration, quality, movement, and sleepiness.
2. Longitudinal rolling-window evaluation of self-reported dream-enacting movements.
3. Strict adherence to non-diagnostic terminology and research provenance labeling.

COMPLIANCE RULES:
- Never say: "You have Parkinson's", "RBD detected", "Diagnosed RBD", "Confirmed RBD", "Parkinson's progression".
- Always say: "Self-reported sleep movement pattern noted", "Deviation from personal baseline",
              "Research screening result — not a clinical diagnosis".
- Distinguish self-reported probable RBD from polysomnography-confirmed RBD.
- Label all synthetic test data as [SYNTHETIC].
"""

import pytest
import datetime
from typing import Dict, List, Any

QUESTIONNAIRE_VERSION = "1.0"
SCORER_VERSION = "1.0"

SLEEP_LABELS = {
    "MOVEMENT_NOTED": "Self-reported sleep movement pattern noted",
    "NO_PATTERN": "No pattern detected",
    "PROVENANCE": "Self-reported sleep behavior",
    "INDICATOR": "Questionnaire-based indicator",
    "PROBABLE_RBD": "Probable RBD pattern (self-report)",
    "RESEARCH_DISCLAIMER": "Research screening result — not a clinical diagnosis",
    "BASELINE_DEVIATION": "Progressive deviation from personal baseline",
}

DISALLOWED_TERMS = [
    "rbd detected",
    "you have rbd",
    "confirmed rbd",
    "diagnosed rbd",
    "parkinson's detected",
    "you have parkinson's",
    "parkinson's progression",
]


def compute_sleep_score_py(
    sleep_duration: float,
    sleep_quality: float,
    unusual_movement: Any,
    daytime_sleepiness: float,
) -> Dict[str, Any]:
    """Python mirror of computeSleepScore from sleepScorer.js."""
    duration = float(sleep_duration)
    quality = float(sleep_quality)
    sleepiness = float(daytime_sleepiness)

    if duration < 0 or duration > 24:
        raise ValueError(f"sleep_duration must be between 0 and 24; received {duration}")
    if quality < 1 or quality > 5:
        raise ValueError(f"sleep_quality must be between 1 and 5; received {quality}")
    if sleepiness < 1 or sleepiness > 5:
        raise ValueError(f"daytime_sleepiness must be between 1 and 5; received {sleepiness}")

    # 1. Duration subscore (0-30 points)
    if 7.0 <= duration <= 9.0:
        duration_score = 30.0
    elif (6.5 <= duration < 7.0) or (9.0 < duration <= 9.5):
        duration_score = 26.0
    elif (6.0 <= duration < 6.5) or (9.5 < duration <= 10.0):
        duration_score = 22.0
    elif (5.0 <= duration < 6.0) or (10.0 < duration <= 11.0):
        duration_score = 15.0
    elif (4.0 <= duration < 5.0) or (11.0 < duration <= 12.0):
        duration_score = 8.0
    else:
        duration_score = 0.0

    # 2. Quality subscore (0-30 points)
    quality_score = max(0.0, min(30.0, ((quality - 1.0) / 4.0) * 30.0))

    # 3. Movement / Dream enactment subscore (0-25 points)
    is_yes = (unusual_movement is True) or (
        isinstance(unusual_movement, str) and unusual_movement.strip().lower() == "yes"
    )
    is_uncertain = isinstance(unusual_movement, str) and unusual_movement.strip().lower() in [
        "not_sure",
        "dont_know",
        "not sure",
        "i don't know",
    ]

    if is_yes:
        movement_score = 0.0
    elif is_uncertain:
        movement_score = 15.0
    else:
        movement_score = 25.0

    # 4. Daytime sleepiness subscore (0-15 points)
    sleepiness_score = max(0.0, min(15.0, ((5.0 - sleepiness) / 4.0) * 15.0))

    total = round(duration_score + quality_score + movement_score + sleepiness_score, 1)
    clamped = max(0.0, min(100.0, total))

    return {
        "score": clamped,
        "breakdown": {
            "duration_score": duration_score,
            "quality_score": round(quality_score, 1),
            "movement_score": movement_score,
            "sleepiness_score": round(sleepiness_score, 1),
        },
        "version": SCORER_VERSION,
        "labels": {
            "provenance": SLEEP_LABELS["PROVENANCE"],
            "disclaimer": SLEEP_LABELS["RESEARCH_DISCLAIMER"],
        },
    }


def evaluate_rbd_concern_window_py(
    sessions: List[Dict[str, Any]],
    window_days: int = 7,
    threshold_count: int = 2,
    now: datetime.datetime = None,
) -> Dict[str, Any]:
    """Python mirror of evaluateRbdConcernWindow from sleepScorer.js."""
    if not isinstance(sessions, list):
        raise TypeError("sessions must be a list.")

    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)

    cutoff = now - datetime.timedelta(days=window_days)

    positive_days = set()
    evaluated_count = 0

    for s in sessions:
        ts_str = s.get("timestamp")
        if not ts_str:
            continue
        try:
            ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            continue

        if ts >= cutoff:
            evaluated_count += 1
            is_yes = (s.get("unusual_movement_self_report") is True) or (
                str(s.get("movement_response", "")).strip().lower() == "yes"
            )
            if is_yes:
                positive_days.add(ts.date())

    positive_count = len(positive_days)
    is_flagged = positive_count >= threshold_count

    return {
        "flagged": is_flagged,
        "positive_days_count": positive_count,
        "threshold": threshold_count,
        "window_days": window_days,
        "evaluated_sessions_count": evaluated_count,
        "label": SLEEP_LABELS["MOVEMENT_NOTED"] if is_flagged else SLEEP_LABELS["NO_PATTERN"],
        "provenance": SLEEP_LABELS["PROBABLE_RBD"],
        "indicator_type": SLEEP_LABELS["INDICATOR"],
        "disclaimer": SLEEP_LABELS["RESEARCH_DISCLAIMER"],
        "clinical_distinction": (
            "This evaluation is based solely on daily self-reported questionnaire answers. "
            "It does NOT substitute for polysomnography, video EEG, or formal neurological diagnosis."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite: Sleep Score Computations
# ─────────────────────────────────────────────────────────────────────────────

def test_perfect_sleep_score():
    """[SYNTHETIC] 8 hours, excellent quality, no movements, no daytime sleepiness."""
    res = compute_sleep_score_py(
        sleep_duration=8.0,
        sleep_quality=5.0,
        unusual_movement="no",
        daytime_sleepiness=1.0,
    )
    assert res["score"] == 100.0
    assert res["breakdown"]["duration_score"] == 30.0
    assert res["breakdown"]["quality_score"] == 30.0
    assert res["breakdown"]["movement_score"] == 25.0
    assert res["breakdown"]["sleepiness_score"] == 15.0


def test_worst_sleep_score():
    """[SYNTHETIC] Extreme deprivation (2h), very poor quality (1), movements present (yes), extremely sleepy (5)."""
    res = compute_sleep_score_py(
        sleep_duration=2.0,
        sleep_quality=1.0,
        unusual_movement="yes",
        daytime_sleepiness=5.0,
    )
    assert res["score"] == 0.0
    assert res["breakdown"]["duration_score"] == 0.0
    assert res["breakdown"]["quality_score"] == 0.0
    assert res["breakdown"]["movement_score"] == 0.0
    assert res["breakdown"]["sleepiness_score"] == 0.0


def test_intermediate_sleep_score():
    """[SYNTHETIC] 6.5 hours (26 pts), quality 3 (15 pts), movement uncertain (15 pts), sleepiness 2 (11.2 pts)."""
    res = compute_sleep_score_py(
        sleep_duration=6.5,
        sleep_quality=3.0,
        unusual_movement="not_sure",
        daytime_sleepiness=2.0,
    )
    expected_total = 26.0 + 15.0 + 15.0 + 11.2
    assert abs(res["score"] - expected_total) < 0.2
    assert 0 <= res["score"] <= 100


@pytest.mark.parametrize(
    "duration,expected_subscore",
    [
        (8.0, 30.0),
        (7.0, 30.0),
        (9.0, 30.0),
        (6.8, 26.0),
        (9.2, 26.0),
        (6.2, 22.0),
        (9.8, 22.0),
        (5.5, 15.0),
        (10.5, 15.0),
        (4.5, 8.0),
        (11.5, 8.0),
        (3.5, 0.0),
        (13.0, 0.0),
    ],
)
def test_duration_subscore_ranges(duration, expected_subscore):
    """[SYNTHETIC] Verifies all graduated duration tiers."""
    res = compute_sleep_score_py(
        sleep_duration=duration,
        sleep_quality=1.0,
        unusual_movement="yes",
        daytime_sleepiness=5.0,
    )
    assert res["breakdown"]["duration_score"] == expected_subscore


def test_movement_response_variations():
    """[SYNTHETIC] Verifies boolean and text variations for movement question."""
    # Boolean true -> 0 pts
    res_bool_true = compute_sleep_score_py(8.0, 5.0, True, 1.0)
    assert res_bool_true["breakdown"]["movement_score"] == 0.0

    # Boolean false -> 25 pts
    res_bool_false = compute_sleep_score_py(8.0, 5.0, False, 1.0)
    assert res_bool_false["breakdown"]["movement_score"] == 25.0

    # String variations
    assert compute_sleep_score_py(8.0, 5.0, "yes", 1.0)["breakdown"]["movement_score"] == 0.0
    assert compute_sleep_score_py(8.0, 5.0, "YES", 1.0)["breakdown"]["movement_score"] == 0.0
    assert compute_sleep_score_py(8.0, 5.0, "no", 1.0)["breakdown"]["movement_score"] == 25.0
    assert compute_sleep_score_py(8.0, 5.0, "not_sure", 1.0)["breakdown"]["movement_score"] == 15.0
    assert compute_sleep_score_py(8.0, 5.0, "dont_know", 1.0)["breakdown"]["movement_score"] == 15.0


def test_invalid_input_rejection():
    """Verifies that out-of-range inputs raise descriptive ValueErrors."""
    with pytest.raises(ValueError, match="sleep_duration"):
        compute_sleep_score_py(-1.0, 3.0, "no", 1.0)

    with pytest.raises(ValueError, match="sleep_duration"):
        compute_sleep_score_py(25.0, 3.0, "no", 1.0)

    with pytest.raises(ValueError, match="sleep_quality"):
        compute_sleep_score_py(7.0, 0.0, "no", 1.0)

    with pytest.raises(ValueError, match="sleep_quality"):
        compute_sleep_score_py(7.0, 6.0, "no", 1.0)

    with pytest.raises(ValueError, match="daytime_sleepiness"):
        compute_sleep_score_py(7.0, 3.0, "no", 0.0)

    with pytest.raises(ValueError, match="daytime_sleepiness"):
        compute_sleep_score_py(7.0, 3.0, "no", 6.0)


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite: Longitudinal Rolling Window RBD Concern Evaluation
# ─────────────────────────────────────────────────────────────────────────────

def test_rbd_window_no_movements():
    """[SYNTHETIC] 7 days of logs with 'no' movements -> No flag."""
    ref_time = datetime.datetime(2026, 9, 23, 12, 0, 0, tzinfo=datetime.timezone.utc)
    sessions = [
        {
            "timestamp": (ref_time - datetime.timedelta(days=i)).isoformat(),
            "unusual_movement_self_report": False,
            "movement_response": "no",
        }
        for i in range(7)
    ]

    report = evaluate_rbd_concern_window_py(sessions, window_days=7, threshold_count=2, now=ref_time)
    assert report["flagged"] is False
    assert report["positive_days_count"] == 0
    assert report["label"] == "No pattern detected"


def test_rbd_window_single_movement_day():
    """[SYNTHETIC] 1 isolated day of movements -> Under threshold (2), no flag."""
    ref_time = datetime.datetime(2026, 9, 23, 12, 0, 0, tzinfo=datetime.timezone.utc)
    sessions = [
        {
            "timestamp": (ref_time - datetime.timedelta(days=0)).isoformat(),
            "unusual_movement_self_report": True,
            "movement_response": "yes",
        },
        {
            "timestamp": (ref_time - datetime.timedelta(days=1)).isoformat(),
            "unusual_movement_self_report": False,
            "movement_response": "no",
        },
        {
            "timestamp": (ref_time - datetime.timedelta(days=2)).isoformat(),
            "unusual_movement_self_report": False,
            "movement_response": "no",
        },
    ]

    report = evaluate_rbd_concern_window_py(sessions, window_days=7, threshold_count=2, now=ref_time)
    assert report["flagged"] is False
    assert report["positive_days_count"] == 1
    assert report["label"] == "No pattern detected"


def test_rbd_window_multiple_movement_days_triggers_flag():
    """[SYNTHETIC] 2 distinct days with 'yes' within 7 days -> Flag triggered."""
    ref_time = datetime.datetime(2026, 9, 23, 12, 0, 0, tzinfo=datetime.timezone.utc)
    sessions = [
        {
            "timestamp": (ref_time - datetime.timedelta(days=1)).isoformat(),
            "unusual_movement_self_report": True,
            "movement_response": "yes",
        },
        {
            "timestamp": (ref_time - datetime.timedelta(days=3)).isoformat(),
            "unusual_movement_self_report": True,
            "movement_response": "yes",
        },
        {
            "timestamp": (ref_time - datetime.timedelta(days=5)).isoformat(),
            "unusual_movement_self_report": False,
            "movement_response": "no",
        },
    ]

    report = evaluate_rbd_concern_window_py(sessions, window_days=7, threshold_count=2, now=ref_time)
    assert report["flagged"] is True
    assert report["positive_days_count"] == 2
    assert report["label"] == "Self-reported sleep movement pattern noted"


def test_rbd_window_old_movements_ignored():
    """[SYNTHETIC] 2 positive days, but one occurred 10 days ago (outside 7-day window) -> No flag."""
    ref_time = datetime.datetime(2026, 9, 23, 12, 0, 0, tzinfo=datetime.timezone.utc)
    sessions = [
        {
            "timestamp": (ref_time - datetime.timedelta(days=1)).isoformat(),
            "unusual_movement_self_report": True,
            "movement_response": "yes",
        },
        {
            "timestamp": (ref_time - datetime.timedelta(days=10)).isoformat(),  # Outside window!
            "unusual_movement_self_report": True,
            "movement_response": "yes",
        },
    ]

    report = evaluate_rbd_concern_window_py(sessions, window_days=7, threshold_count=2, now=ref_time)
    assert report["flagged"] is False
    assert report["positive_days_count"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite: Non-Diagnostic Compliance Assertions
# ─────────────────────────────────────────────────────────────────────────────

def test_strictly_no_diagnostic_language():
    """
    CRITICAL NON-NEGOTIABLE CHECK:
    Ensures no forbidden clinical diagnostic words appear in any labels, breakdowns, or clinical notes.
    """
    score_out = compute_sleep_score_py(7.0, 3.0, "yes", 3.0)
    for text in [
        score_out["labels"]["provenance"],
        score_out["labels"]["disclaimer"],
    ]:
        for disallowed in DISALLOWED_TERMS:
            assert disallowed not in text.lower(), f"Disallowed diagnostic phrase '{disallowed}' found in: {text}"

    report_out = evaluate_rbd_concern_window_py(
        [
            {
                "timestamp": "2026-09-23T10:00:00Z",
                "unusual_movement_self_report": True,
                "movement_response": "yes",
            },
            {
                "timestamp": "2026-09-22T10:00:00Z",
                "unusual_movement_self_report": True,
                "movement_response": "yes",
            },
        ],
        window_days=7,
        threshold_count=2,
    )

    for field in ["label", "provenance", "indicator_type", "disclaimer", "clinical_distinction"]:
        text = report_out[field]
        for disallowed in DISALLOWED_TERMS:
            assert disallowed not in text.lower(), f"Disallowed diagnostic phrase '{disallowed}' found in {field}: {text}"

    # Specific compliance label matches exactly
    assert report_out["label"] == "Self-reported sleep movement pattern noted"
    assert report_out["provenance"] == "Probable RBD pattern (self-report)"
    assert report_out["indicator_type"] == "Questionnaire-based indicator"
