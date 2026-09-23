"""
Tests for MPF Mobile Extension — Sustained Deviation Detection (Phase 11)

Validates:
1. Streak counting of consecutive days with |z| > 2.0.
2. Threshold trigger: Flagging "Sustained deviation detected" when consecutive days >= 5.
3. Sub-threshold streaks: 1-4 days do NOT trigger sustained classification.
4. Streak resets when |z| <= 2.0.
5. Historical run analysis with analyzeSustainedRuns().
6. Absence of diagnostic terms in sustained deviation outputs.

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import subprocess
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
JS_SUSTAINED = BASE_DIR / "sustainedDeviationDetector.js"

DISALLOWED_DIAGNOSTIC_TERMS = [
    "parkinson's detected",
    "parkinsons detected",
    "disease progression",
    "clinical deterioration",
    "parkinson's progression",
    "disease worsening",
    "clinical decline",
]


def run_node_eval(js_code: str):
    res = subprocess.run(
        ["node", "-e", js_code],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(res.stdout)


def test_sustained_deviation_trigger_at_five_days():
    """Verify consecutive streak of 5 days with |z| > 2.0 triggers 'Sustained deviation detected' [SYNTHETIC]."""
    js_code = f"""
    const {{ calculateSustainedDeviation }} = require({json.dumps(str(JS_SUSTAINED))});

    // 5 consecutive days with z = 2.4 (|z| > 2.0)
    const history5 = [2.2, 2.5, 2.1, 2.8, 2.4];
    const res5 = calculateSustainedDeviation(history5);

    // 6 consecutive days with negative deviations z = -2.3
    const history6 = [-2.1, -2.4, -2.6, -2.2, -2.5, -2.3];
    const res6 = calculateSustainedDeviation(history6);

    console.log(JSON.stringify({{ res5, res6 }}));
    """
    res = run_node_eval(js_code)

    assert res["res5"]["consecutiveDays"] == 5
    assert res["res5"]["isSustained"] is True
    assert res["res5"]["classification"] == "Sustained deviation detected"

    assert res["res6"]["consecutiveDays"] == 6
    assert res["res6"]["isSustained"] is True
    assert res["res6"]["classification"] == "Sustained deviation detected"


def test_sub_threshold_streak_does_not_trigger():
    """Verify streaks of 1 to 4 days with |z| > 2.0 do not flag sustained deviation [SYNTHETIC]."""
    js_code = f"""
    const {{ calculateSustainedDeviation }} = require({json.dumps(str(JS_SUSTAINED))});

    // 4 consecutive days with |z| > 2.0
    const history4 = [0.2, 0.5, 2.4, 2.5, 2.1, 2.3];
    const res4 = calculateSustainedDeviation(history4);

    // 2 consecutive days
    const history2 = [0.1, 1.2, 2.5, 2.7];
    const res2 = calculateSustainedDeviation(history2);

    console.log(JSON.stringify({{ res4, res2 }}));
    """
    res = run_node_eval(js_code)

    assert res["res4"]["consecutiveDays"] == 4
    assert res["res4"]["isSustained"] is False
    assert res["res4"]["classification"] is None

    assert res["res2"]["consecutiveDays"] == 2
    assert res["res2"]["isSustained"] is False
    assert res["res2"]["classification"] is None


def test_streak_resets_on_normal_measurement():
    """Verify streak resets to 0 when latest day is within normal baseline (|z| <= 2.0) [SYNTHETIC]."""
    js_code = f"""
    const {{ calculateSustainedDeviation }} = require({json.dumps(str(JS_SUSTAINED))});

    // 5 high days followed by a normal day (z = 0.8)
    const history = [2.2, 2.5, 2.1, 2.8, 2.4, 0.8];
    const res = calculateSustainedDeviation(history);

    console.log(JSON.stringify(res));
    """
    res = run_node_eval(js_code)

    assert res["consecutiveDays"] == 0
    assert res["isSustained"] is False
    assert res["classification"] is None


def test_historical_runs_analysis():
    """Verify analyzeSustainedRuns captures past sustained periods correctly [SYNTHETIC]."""
    js_code = f"""
    const {{ analyzeSustainedRuns }} = require({json.dumps(str(JS_SUSTAINED))});

    const records = [
      {{ date: '2026-09-01', z_score: 2.5 }},
      {{ date: '2026-09-02', z_score: 2.4 }},
      {{ date: '2026-09-03', z_score: 2.6 }},
      {{ date: '2026-09-04', z_score: 2.2 }},
      {{ date: '2026-09-05', z_score: 2.7 }}, // 5-day sustained run (Sept 1-5)
      {{ date: '2026-09-06', z_score: 0.5 }}, // Reset
      {{ date: '2026-09-07', z_score: 0.8 }},
      {{ date: '2026-09-08', z_score: 2.9 }}, // New run started (1 day)
    ];

    const result = analyzeSustainedRuns(records);
    console.log(JSON.stringify(result));
    """
    res = run_node_eval(js_code)

    assert res["maxStreak"] == 5
    assert res["currentStreak"] == 1
    assert res["isCurrentlySustained"] is False
    assert len(res["sustainedPeriods"]) == 1
    assert res["sustainedPeriods"][0]["startDate"] == "2026-09-01"
    assert res["sustainedPeriods"][0]["endDate"] == "2026-09-05"
    assert res["sustainedPeriods"][0]["durationDays"] == 5


def test_sustained_deviation_disclaimers():
    """Verify output includes disclaimer and contains zero diagnostic claims [SYNTHETIC]."""
    js_code = f"""
    const {{ calculateSustainedDeviation }} = require({json.dumps(str(JS_SUSTAINED))});

    const history = [2.2, 2.5, 2.1, 2.8, 2.4];
    const res = calculateSustainedDeviation(history);

    console.log(JSON.stringify(res));
    """
    res = run_node_eval(js_code)

    for term in DISALLOWED_DIAGNOSTIC_TERMS:
        assert term not in res["status"].lower()
        assert term not in res["disclaimer"].lower()
        if res["classification"]:
            assert term not in res["classification"].lower()
