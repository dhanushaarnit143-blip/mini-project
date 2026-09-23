"""
Tests for MPF Mobile Extension — Trend Detection (Phase 11)

Validates:
1. Rolling 7-day average calculation.
2. Rolling 7-day variability (sample standard deviation).
3. 14-day linear regression slope computation (ordinary least squares).
4. Missingness calculation (proportion of days without valid data in 14-day window).
5. 7-day rolling data quality average.
6. Trend pattern classification:
   - "Progressive deviation from personal baseline"
   - "Stable within baseline"
   - "Improving toward baseline"
7. Complete non-diagnostic phrasing compliance.

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import subprocess
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
JS_TREND = BASE_DIR / "trendDetector.js"

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


def test_linear_regression_slope_calculation():
    """Verify ordinary least squares linear regression slope calculation [SYNTHETIC]."""
    js_code = f"""
    const {{ calculateLinearSlope }} = require({json.dumps(str(JS_TREND))});

    // Perfectly linear points: y = 2x + 10 -> slope = 2.0
    const pointsLinear = [
      {{ x: 0, y: 10 }},
      {{ x: 1, y: 12 }},
      {{ x: 2, y: 14 }},
      {{ x: 3, y: 16 }},
    ];
    const slopeLinear = calculateLinearSlope(pointsLinear);

    // Negative slope: y = -1.5x + 50 -> slope = -1.5
    const pointsNegative = [
      {{ x: 0, y: 50 }},
      {{ x: 1, y: 48.5 }},
      {{ x: 2, y: 47.0 }},
      {{ x: 3, y: 45.5 }},
    ];
    const slopeNegative = calculateLinearSlope(pointsNegative);

    // Flat line: y = 25 -> slope = 0.0
    const pointsFlat = [
      {{ x: 0, y: 25 }},
      {{ x: 1, y: 25 }},
      {{ x: 2, y: 25 }},
    ];
    const slopeFlat = calculateLinearSlope(pointsFlat);

    console.log(JSON.stringify({{
      slopeLinear,
      slopeNegative,
      slopeFlat,
    }}));
    """
    res = run_node_eval(js_code)

    assert res["slopeLinear"] == 2.0
    assert res["slopeNegative"] == -1.5
    assert res["slopeFlat"] == 0.0


def test_seven_day_metrics():
    """Verify 7-day average and 7-day variability calculation [SYNTHETIC]."""
    js_code = f"""
    const {{ calculateMean, calculateSampleStd }} = require({json.dumps(str(JS_TREND))});

    // 7 measurements: [100, 102, 98, 104, 101, 99, 103]
    // Mean = 707 / 7 = 101.0
    // Sum sq diffs = 1+1+9+9+0+4+4 = 28; variance = 28 / 6 = 4.6667; std = sqrt(4.6667) = 2.1602
    const values = [100, 102, 98, 104, 101, 99, 103];
    const mean = calculateMean(values);
    const std = calculateSampleStd(values);

    console.log(JSON.stringify({{ mean, std }}));
    """
    res = run_node_eval(js_code)

    assert res["mean"] == 101.0
    assert abs(res["std"] - 2.1602) < 0.001


def test_missingness_and_quality_tracking():
    """Verify 14-day missingness proportion and rolling 7-day data quality [SYNTHETIC]."""
    js_code = f"""
    const {{ computeLongitudinalTrends }} = require({json.dumps(str(JS_TREND))});

    const baseline = {{
      baseline_mean: 100.0,
      baseline_std: 5.0,
      baseline_median: 100.0,
      baseline_mad: 3.5,
    }};

    // 10 valid days out of 14 -> missingness should be (14 - 10) / 14 = 4/14 = 0.2857
    const history = [];
    for (let i = 0; i < 14; i++) {{
      if (i === 2 || i === 5 || i === 8 || i === 11) {{
        history.push({{ value: null, quality: null }});
      }} else {{
        history.push({{ value: 100 + i, quality: 0.90 }});
      }}
    }}

    const result = computeLongitudinalTrends(history, baseline);
    console.log(JSON.stringify(result));
    """
    res = run_node_eval(js_code)

    assert res["missingness"] == 0.2857
    assert res["data_quality"] == 0.90


def test_trend_classification_progressive_deviation():
    """Verify progressive deviation detection when slope moves away from personal baseline [SYNTHETIC]."""
    js_code = f"""
    const {{ classifyTrendDirection, TREND_PROGRESSIVE_DEVIATION }} = require({json.dumps(str(JS_TREND))});

    const baseline = {{ baseline_mean: 100.0, baseline_median: 100.0 }};

    // Case 1: Daily value is 120 (above baseline) and slope is +1.5 (increasing further away)
    const labelAbove = classifyTrendDirection(1.5, 120.0, baseline);

    // Case 2: Daily value is 80 (below baseline) and slope is -1.5 (decreasing further away)
    const labelBelow = classifyTrendDirection(-1.5, 80.0, baseline);

    console.log(JSON.stringify({{
      labelAbove,
      labelBelow,
      expected: TREND_PROGRESSIVE_DEVIATION,
    }}));
    """
    res = run_node_eval(js_code)

    assert res["labelAbove"] == "Progressive deviation from personal baseline"
    assert res["labelBelow"] == "Progressive deviation from personal baseline"


def test_trend_classification_improving_toward_baseline():
    """Verify improving trend detection when slope moves back toward personal baseline [SYNTHETIC]."""
    js_code = f"""
    const {{ classifyTrendDirection, TREND_IMPROVING_TOWARD_BASELINE }} = require({json.dumps(str(JS_TREND))});

    const baseline = {{ baseline_mean: 100.0, baseline_median: 100.0 }};

    // Case 1: Daily value is 120 (above baseline) and slope is -1.5 (moving down toward baseline)
    const labelAbove = classifyTrendDirection(-1.5, 120.0, baseline);

    // Case 2: Daily value is 80 (below baseline) and slope is +1.5 (moving up toward baseline)
    const labelBelow = classifyTrendDirection(1.5, 80.0, baseline);

    console.log(JSON.stringify({{
      labelAbove,
      labelBelow,
      expected: TREND_IMPROVING_TOWARD_BASELINE,
    }}));
    """
    res = run_node_eval(js_code)

    assert res["labelAbove"] == "Improving toward baseline"
    assert res["labelBelow"] == "Improving toward baseline"


def test_trend_classification_stable_within_baseline():
    """Verify stable baseline detection when slope is insignificant (< 0.01) [SYNTHETIC]."""
    js_code = f"""
    const {{ classifyTrendDirection, TREND_STABLE_BASELINE }} = require({json.dumps(str(JS_TREND))});

    const baseline = {{ baseline_mean: 100.0, baseline_median: 100.0 }};

    const labelFlat = classifyTrendDirection(0.003, 100.2, baseline);

    console.log(JSON.stringify({{
      labelFlat,
      expected: TREND_STABLE_BASELINE,
    }}));
    """
    res = run_node_eval(js_code)

    assert res["labelFlat"] == "Stable within baseline"


def test_full_longitudinal_trend_evaluation():
    """Verify complete computeLongitudinalTrends integration outputs all 8 required metrics [SYNTHETIC]."""
    js_code = f"""
    const {{ computeLongitudinalTrends }} = require({json.dumps(str(JS_TREND))});

    const baseline = {{
      baseline_mean: 100.0,
      baseline_std: 5.0,
      baseline_median: 100.0,
      baseline_mad: 3.5,
    }};

    // 14-day history with increasing values
    const history = [];
    for (let i = 0; i < 14; i++) {{
      history.push({{
        value: 100 + i * 1.5, // 100, 101.5, ..., 119.5
        quality_score: 0.95,
      }});
    }}

    const result = computeLongitudinalTrends(history, baseline);
    console.log(JSON.stringify(result));
    """
    res = run_node_eval(js_code)

    # 1. daily_value
    assert res["daily_value"] == 119.5
    # 2. 7_day_average: mean of last 7 entries (110.5, 112, 113.5, 115, 116.5, 118, 119.5) = 115.0
    assert res["seven_day_average"] == 115.0
    # 3. 7_day_variability
    assert res["seven_day_variability"] > 0
    # 4. 14_day_trend: slope should be 1.5
    assert res["fourteen_day_trend"] == 1.5
    # 5. baseline_deviation: (119.5 - 100) / 5 = 3.9
    assert res["baseline_deviation"] == 3.9
    # 6. sustained_deviation
    assert isinstance(res["sustained_deviation"], int)
    # 7. missingness (0 out of 14 missing)
    assert res["missingness"] == 0.0
    # 8. data_quality
    assert res["data_quality"] == 0.95
    # Trend label
    assert res["trend_label"] == "Progressive deviation from personal baseline"

    # Strict compliance check
    for term in DISALLOWED_DIAGNOSTIC_TERMS:
        assert term not in res["trend_label"].lower()
        assert term not in res["disclaimer"].lower()
