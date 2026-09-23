"""
Tests for MPF Mobile Extension — Baseline Establishment (Phase 10)

Validates:
1. 14-day calibration baseline establishment from daily feature vectors.
2. Correct mathematical calculation of all 8 core statistics:
   - mean
   - median
   - standard deviation (sample std, ddof=1)
   - median absolute deviation (MAD)
   - lower quantile (Q1)
   - upper quantile (Q3)
   - coefficient of variation (CV = std / mean)
   - sample count
3. Status transitions:
   - < 14 days -> 'calibrating'
   - >= 14 days -> 'established'
4. Quality gating: Low-quality observations (quality_score < 0.50) are excluded.
5. Edge cases: Single observations, identical values, zero division safety.
6. Non-diagnostic phrasing compliance (no diagnostic claims).

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import subprocess
import math
import uuid
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
JS_CALCULATOR = BASE_DIR / "baselineCalculator.js"
JS_ENGINE = BASE_DIR / "baselineEngine.js"

DISALLOWED_DIAGNOSTIC_TERMS = [
    "you have parkinson's",
    "parkinson's detected",
    "diagnosed parkinson",
    "confirmed parkinson",
    "parkinson's progression",
]


def run_node_eval(js_code: str):
    """Executes small JavaScript snippet using Node.js and parses JSON output."""
    res = subprocess.run(
        ["node", "-e", js_code],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(res.stdout)


# ── Python Reference Math ───────────────────────────────────────────────────

def py_mean(vals):
    clean = [float(v) for v in vals if v is not None]
    return round(sum(clean) / len(clean), 4) if clean else None


def py_median(vals):
    clean = sorted([float(v) for v in vals if v is not None])
    if not clean:
        return None
    n = len(clean)
    mid = n // 2
    med = (clean[mid - 1] + clean[mid]) / 2.0 if n % 2 == 0 else clean[mid]
    return round(med, 4)


def py_std(vals):
    clean = [float(v) for v in vals if v is not None]
    if len(clean) < 2:
        return 0.0
    mean = sum(clean) / len(clean)
    var = sum((x - mean) ** 2 for x in clean) / (len(clean) - 1)
    return round(math.sqrt(var), 4)


def py_mad(vals):
    clean = sorted([float(v) for v in vals if v is not None])
    if not clean:
        return None
    med = py_median(clean)
    devs = sorted([abs(x - med) for x in clean])
    return py_median(devs)


# ── Tests ───────────────────────────────────────────────────────────────────

def test_calculator_core_statistics():
    """Verify JS baselineCalculator statistics against reference calculations on [SYNTHETIC] 14-day data."""
    # [SYNTHETIC] 14 daily values representing typing speed (chars/sec)
    synthetic_speeds = [
        4.2, 4.5, 4.1, 4.6, 4.3, 4.4, 4.8,
        4.2, 4.5, 4.3, 4.4, 4.7, 4.3, 4.5
    ]

    js_code = f"""
    const calc = require({json.dumps(str(JS_CALCULATOR))});
    const vals = {json.dumps(synthetic_speeds)};
    const stats = calc.calculateFeatureBaseline(vals, {{
      featureName: 'typing_speed',
      modality: 'typing'
    }});
    console.log(JSON.stringify(stats));
    """

    res = run_node_eval(js_code)

    assert res["sample_count"] == 14
    assert res["baseline_status"] == "established"

    # Compare statistics within 0.01 tolerance
    assert abs(res["baseline_mean"] - py_mean(synthetic_speeds)) < 0.01
    assert abs(res["baseline_median"] - py_median(synthetic_speeds)) < 0.01
    assert abs(res["baseline_std"] - py_std(synthetic_speeds)) < 0.01
    assert abs(res["baseline_mad"] - py_mad(synthetic_speeds)) < 0.01

    # Verify Q1 <= median <= Q3
    assert res["q1"] <= res["baseline_median"]
    assert res["baseline_median"] <= res["q3"]

    # Verify CV = std / mean
    expected_cv = round(res["baseline_std"] / res["baseline_mean"], 4)
    assert abs(res["coefficient_of_variation"] - expected_cv) < 0.01


def test_baseline_status_transition():
    """Verify baseline_status is 'calibrating' under 14 days and 'established' at 14+ days."""
    # [SYNTHETIC] 10 days vs 14 days
    js_code = f"""
    const calc = require({json.dumps(str(JS_CALCULATOR))});
    const day10 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    const day14 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14];

    const res10 = calc.calculateFeatureBaseline(day10, {{ featureName: 'cadence', modality: 'motor' }});
    const res14 = calc.calculateFeatureBaseline(day14, {{ featureName: 'cadence', modality: 'motor' }});

    console.log(JSON.stringify({{ res10, res14 }}));
    """

    data = run_node_eval(js_code)
    assert data["res10"]["sample_count"] == 10
    assert data["res10"]["baseline_status"] == "calibrating"

    assert data["res14"]["sample_count"] == 14
    assert data["res14"]["baseline_status"] == "established"


def test_baseline_engine_multi_modality_14_days():
    """Verify establishPersonalBaselines on full 14-day multimodal daily feature vectors [SYNTHETIC]."""
    participant_id = str(uuid.uuid4())

    # Build 14 daily vectors [SYNTHETIC]
    daily_vectors = []
    for day_idx in range(1, 15):
        date_str = f"2026-09-{day_idx:02d}"
        daily_vectors.append({
            "participant_id": participant_id,
            "feature_date": date_str,
            "quality_scores": {
                "typing": 0.92,
                "voice": 0.88,
                "motor": 0.95,
                "visual": 0.85,
                "sleep": 0.90,
            },
            "typing": {
                "typing_speed": 4.2 + (day_idx % 3) * 0.1,
                "mean_hold_duration": 82.0 + (day_idx % 4) * 1.5,
            },
            "voice": {
                "jitter": 0.0050 + (day_idx % 2) * 0.0003,
                "shimmer": 0.032 + (day_idx % 3) * 0.001,
            },
            "motor": {
                "cadence": 105.0 + (day_idx % 5) * 0.5,
                "tapping_rate": 5.4 + (day_idx % 4) * 0.1,
            },
            "visual": {
                "blink_rate": 18.0 + (day_idx % 3) * 0.5,
            },
            "sleep": {
                "total_sleep_hours": 7.2 + (day_idx % 2) * 0.4,
                "rbd_score": 1.0,
            }
        })

    js_code = f"""
    const engine = require({json.dumps(str(JS_ENGINE))});
    const vectors = {json.dumps(daily_vectors)};
    const result = engine.establishPersonalBaselines({{
      participantId: {json.dumps(participant_id)},
      dailyVectors: vectors,
      minDays: 14
    }});
    console.log(JSON.stringify(result));
    """

    res = run_node_eval(js_code)

    assert res["participantId"] == participant_id
    assert res["overallStatus"] == "established"
    assert res["totalFeatures"] > 0
    assert res["establishedFeatures"] == res["totalFeatures"]

    # Check that each baseline has required schema fields
    for base in res["baselines"]:
        assert base["sample_count"] == 14
        assert base["baseline_status"] == "established"
        assert base["baseline_version"] == "1.0.0"
        assert base["algorithm_version"] == "1.0.0"
        assert base["baseline_mean"] is not None
        assert base["baseline_median"] is not None
        assert base["baseline_std"] is not None
        assert base["baseline_mad"] is not None
        assert base["q1"] is not None
        assert base["q3"] is not None
        assert base["coefficient_of_variation"] is not None
        assert base["lower_bound"] < base["upper_bound"]


def test_quality_filtering_in_establishment():
    """Verify that days with quality < 0.50 are excluded from 14-day calibration."""
    participant_id = str(uuid.uuid4())

    # Build 14 daily vectors, but 3 days have low quality (< 0.50) [SYNTHETIC]
    daily_vectors = []
    for day_idx in range(1, 15):
        date_str = f"2026-09-{day_idx:02d}"
        q = 0.30 if day_idx in [3, 7, 11] else 0.90
        daily_vectors.append({
            "participant_id": participant_id,
            "feature_date": date_str,
            "quality_scores": {"motor": q},
            "motor": {"cadence": 105.0}
        })

    js_code = f"""
    const engine = require({json.dumps(str(JS_ENGINE))});
    const vectors = {json.dumps(daily_vectors)};
    const result = engine.establishPersonalBaselines({{
      participantId: {json.dumps(participant_id)},
      dailyVectors: vectors,
      minDays: 14,
      minQuality: 0.50
    }});
    console.log(JSON.stringify(result));
    """

    res = run_node_eval(js_code)
    # 14 days total, but 3 excluded -> 11 valid samples -> status should be calibrating
    cadence_base = next(b for b in res["baselines"] if b["feature_name"] == "cadence")
    assert cadence_base["sample_count"] == 11
    assert cadence_base["baseline_status"] == "calibrating"


def test_calculator_edge_cases():
    """Verify calculator handles zero variance and single observation gracefully."""
    js_code = f"""
    const calc = require({json.dumps(str(JS_CALCULATOR))});

    // Zero variance (all 100)
    const identical = [100, 100, 100, 100, 100];
    const resId = calc.calculateFeatureBaseline(identical, {{ featureName: 'test', modality: 'motor' }});

    // Single item
    const single = [42];
    const resSingle = calc.calculateFeatureBaseline(single, {{ featureName: 'test', modality: 'motor' }});

    console.log(JSON.stringify({{ resId, resSingle }}));
    """

    data = run_node_eval(js_code)

    res_id = data["resId"]
    assert res_id["baseline_mean"] == 100.0
    assert res_id["baseline_median"] == 100.0
    assert res_id["baseline_std"] == 0.0
    assert res_id["baseline_mad"] == 0.0
    assert res_id["coefficient_of_variation"] == 0.0

    res_single = data["resSingle"]
    assert res_single["sample_count"] == 1
    assert res_single["baseline_mean"] == 42.0
    assert res_single["baseline_std"] == 0.0
    assert res_single["baseline_status"] == "calibrating"


def test_non_diagnostic_compliance():
    """Verify no prohibited clinical diagnostic phrases are produced."""
    participant_id = str(uuid.uuid4())
    js_code = f"""
    const engine = require({json.dumps(str(JS_ENGINE))});
    const vectors = [{{
      participant_id: {json.dumps(participant_id)},
      feature_date: '2026-09-01',
      quality_scores: {{ motor: 0.9 }},
      motor: {{ cadence: 100.0 }}
    }}];
    const result = engine.establishPersonalBaselines({{
      participantId: {json.dumps(participant_id)},
      dailyVectors: vectors
    }});
    console.log(JSON.stringify(result));
    """
    raw_output = subprocess.run(["node", "-e", js_code], capture_output=True, text=True, check=True).stdout.lower()
    for term in DISALLOWED_DIAGNOSTIC_TERMS:
        assert term not in raw_output, f"Prohibited diagnostic term found: {term}"
