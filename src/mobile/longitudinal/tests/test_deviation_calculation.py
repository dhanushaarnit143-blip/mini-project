"""
Tests for MPF Mobile Extension — Deviation Calculation (Phase 11)

Validates:
1. Parametric z-score deviation calculation:
   z = (today_value - baseline_mean) / baseline_std
2. Robust MAD-based fallback when baseline_std is 0 or very small (< 1e-6):
   z = 0.6745 * (today_value - baseline_median) / baseline_mad
3. Zero dispersion safety handling (both std and mad are zero).
4. Missing / invalid inputs (NaN, null, undefined baseline).
5. Database record construction via buildDeviationRecord().

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import subprocess
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
JS_CALCULATOR = BASE_DIR / "deviationCalculator.js"


def run_node_eval(js_code: str):
    """Executes small JavaScript snippet using Node.js and parses JSON output."""
    res = subprocess.run(
        ["node", "-e", js_code],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(res.stdout)


def test_parametric_z_score_calculation():
    """Verify standard parametric z-score calculation with positive, negative, and zero values [SYNTHETIC]."""
    js_code = f"""
    const {{ calculateDeviation }} = require({json.dumps(str(JS_CALCULATOR))});

    const baseline = {{
      baseline_mean: 100.0,
      baseline_std: 5.0,
      baseline_median: 100.0,
      baseline_mad: 3.5,
    }};

    // Positive deviation: (110 - 100) / 5 = +2.0
    const devPositive = calculateDeviation(110.0, baseline);

    // Negative deviation: (85 - 100) / 5 = -3.0
    const devNegative = calculateDeviation(85.0, baseline);

    // Zero deviation: (100 - 100) / 5 = 0.0
    const devZero = calculateDeviation(100.0, baseline);

    console.log(JSON.stringify({{
      positive: devPositive,
      negative: devNegative,
      zero: devZero,
    }}));
    """
    res = run_node_eval(js_code)

    assert res["positive"]["z_score"] == 2.0
    assert res["positive"]["method"] == "parametric_std"
    assert res["positive"]["isValid"] is True

    assert res["negative"]["z_score"] == -3.0
    assert res["negative"]["method"] == "parametric_std"
    assert res["negative"]["isValid"] is True

    assert res["zero"]["z_score"] == 0.0
    assert res["zero"]["method"] == "parametric_std"
    assert res["zero"]["isValid"] is True


def test_mad_fallback_when_std_is_zero():
    """Verify MAD-based fallback when baseline_std is 0.0 or near-zero [SYNTHETIC]."""
    # z = 0.6745 * (105 - 100) / 2.0 = 0.6745 * 2.5 = 1.68625 -> 1.6863
    js_code = f"""
    const {{ calculateDeviation }} = require({json.dumps(str(JS_CALCULATOR))});

    const baseline = {{
      baseline_mean: 100.0,
      baseline_std: 0.0, // Zero standard deviation triggers MAD fallback
      baseline_median: 100.0,
      baseline_mad: 2.0,
    }};

    const dev = calculateDeviation(105.0, baseline);
    console.log(JSON.stringify(dev));
    """
    res = run_node_eval(js_code)

    assert res["method"] == "mad_fallback"
    assert res["z_score"] == 1.6863
    assert res["diff"] == 5.0
    assert res["isValid"] is True


def test_mad_fallback_when_std_is_epsilon():
    """Verify MAD-based fallback when baseline_std is < 1e-6 [SYNTHETIC]."""
    js_code = f"""
    const {{ calculateDeviation }} = require({json.dumps(str(JS_CALCULATOR))});

    const baseline = {{
      baseline_mean: 50.0,
      baseline_std: 1e-7, // smaller than MIN_DISPERSION_EPSILON
      baseline_median: 50.0,
      baseline_mad: 1.5,
    }};

    // z = 0.6745 * (47.0 - 50.0) / 1.5 = 0.6745 * -2.0 = -1.349
    const dev = calculateDeviation(47.0, baseline);
    console.log(JSON.stringify(dev));
    """
    res = run_node_eval(js_code)

    assert res["method"] == "mad_fallback"
    assert res["z_score"] == -1.349
    assert res["isValid"] is True


def test_zero_dispersion_safety():
    """Verify behavior when both std and MAD are zero [SYNTHETIC]."""
    js_code = f"""
    const {{ calculateDeviation }} = require({json.dumps(str(JS_CALCULATOR))});

    const baseline = {{
      baseline_mean: 100.0,
      baseline_std: 0.0,
      baseline_median: 100.0,
      baseline_mad: 0.0,
    }};

    // Value matches median: deviation is safely 0.0
    const devIdentical = calculateDeviation(100.0, baseline);

    // Value differs from median: safely capped without NaN or Infinity
    const devDifferent = calculateDeviation(110.0, baseline);

    console.log(JSON.stringify({{
      identical: devIdentical,
      different: devDifferent,
    }}));
    """
    res = run_node_eval(js_code)

    assert res["identical"]["z_score"] == 0.0
    assert res["identical"]["method"] == "zero_dispersion"
    assert res["identical"]["isValid"] is True

    assert res["different"]["z_score"] == 10.0
    assert res["different"]["method"] == "zero_dispersion_extreme"
    assert res["different"]["isValid"] is True


def test_invalid_and_missing_inputs():
    """Verify graceful handling of NaN, null, and missing baseline [SYNTHETIC]."""
    js_code = f"""
    const {{ calculateDeviation }} = require({json.dumps(str(JS_CALCULATOR))});

    const resNaN = calculateDeviation(NaN, {{ baseline_mean: 100, baseline_std: 5 }});
    const resNull = calculateDeviation(null, {{ baseline_mean: 100, baseline_std: 5 }});
    const resNoBase = calculateDeviation(105.0, null);

    console.log(JSON.stringify({{
      resNaN,
      resNull,
      resNoBase,
    }}));
    """
    res = run_node_eval(js_code)

    assert res["resNaN"]["isValid"] is False
    assert res["resNull"]["isValid"] is False
    assert res["resNoBase"]["isValid"] is False


def test_build_deviation_record():
    """Verify buildDeviationRecord creates standard database record matching daily_deviations schema [SYNTHETIC]."""
    js_code = f"""
    const {{ buildDeviationRecord }} = require({json.dumps(str(JS_CALCULATOR))});

    const baseline = {{
      baseline_mean: 104.5,
      baseline_std: 3.2,
      baseline_median: 104.0,
      baseline_mad: 2.1,
    }};

    const record = buildDeviationRecord({{
      participantId: 'p-123',
      date: '2026-09-23',
      modality: 'motor',
      featureName: 'cadence',
      value: 110.9,
      baseline,
      qualityScore: 0.95,
      algorithmVersion: '1.1.0',
      trendScore: 0.25,
    }});

    console.log(JSON.stringify(record));
    """
    record = run_node_eval(js_code)

    assert record["participant_id"] == "p-123"
    assert record["date"] == "2026-09-23"
    assert record["modality"] == "motor"
    assert record["feature_name"] == "cadence"
    assert record["value"] == 110.9
    assert record["baseline_value"] == 104.5
    # (110.9 - 104.5) / 3.2 = 6.4 / 3.2 = 2.0
    assert record["deviation_score"] == 2.0
    assert record["trend_score"] == 0.25
    assert record["quality_score"] == 0.95
    assert record["algorithm_version"] == "1.1.0"
