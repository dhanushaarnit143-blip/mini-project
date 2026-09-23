"""
Tests for MPF Mobile Extension — Outlier Resistance (Phase 10)

Validates:
1. Outlier detection (> 3 MAD from personal baseline).
2. Outlier resistance:
   - Observations > 3 MAD are rejected from adaptive baseline updating.
   - Baseline statistics (mean, median, std, mad, sample_count, version) remain intact.
3. Outlier annotation:
   - Flagged explicitly as 'anomalous observation'.
   - Detailed deviation record generated for daily_deviations table with mad_distance.
4. Normal observation acceptance:
   - Observations within 3 MAD are accepted and incorporated.
5. Strict non-diagnostic language compliance:
   - Asserts zero occurrences of prohibited clinical diagnosis terms.
   - Asserts non-diagnostic phrases like 'personal baseline' or 'anomalous observation'.

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import subprocess
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
JS_OUTLIER = BASE_DIR / "outlierDetector.js"
JS_UPDATER = BASE_DIR / "adaptiveBaselineUpdater.js"
JS_ENGINE = BASE_DIR / "baselineEngine.js"

DISALLOWED_DIAGNOSTIC_TERMS = [
    "you have parkinson's",
    "parkinson's detected",
    "diagnosed parkinson",
    "confirmed parkinson",
    "parkinson's progression",
]


def run_node_eval(js_code: str):
    res = subprocess.run(
        ["node", "-e", js_code],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(res.stdout)


def test_detect_outlier_threshold_boundary():
    """Verify detectOutlier distinguishes observations at boundary (> 3.0 MAD vs <= 3.0 MAD) [SYNTHETIC]."""
    # Baseline: median = 100.0, MAD = 5.0 -> 3 MAD = 15.0 -> Range: [85.0, 115.0]
    js_code = f"""
    const {{ detectOutlier }} = require({json.dumps(str(JS_OUTLIER))});

    const baseline = {{
      baseline_median: 100.0,
      baseline_mad: 5.0,
      baseline_std: 6.0
    }};

    const normal = detectOutlier(114.0, baseline); // 14 / 5 = 2.8 MAD -> Normal
    const boundary = detectOutlier(115.0, baseline); // 15 / 5 = 3.0 MAD -> Borderline (not > 3.0)
    const outlier = detectOutlier(116.0, baseline); // 16 / 5 = 3.2 MAD -> Outlier
    const extreme = detectOutlier(150.0, baseline); // 50 / 5 = 10.0 MAD -> Extreme Outlier

    console.log(JSON.stringify({{ normal, boundary, outlier, extreme }}));
    """

    res = run_node_eval(js_code)

    assert res["normal"]["isOutlier"] is False
    assert res["normal"]["anomalyFlag"] is None
    assert res["normal"]["madDistance"] == 2.8

    assert res["boundary"]["isOutlier"] is False
    assert res["boundary"]["madDistance"] == 3.0

    assert res["outlier"]["isOutlier"] is True
    assert res["outlier"]["anomalyFlag"] == "anomalous observation"
    assert res["outlier"]["madDistance"] == 3.2

    assert res["extreme"]["isOutlier"] is True
    assert res["extreme"]["anomalyFlag"] == "anomalous observation"
    assert res["extreme"]["madDistance"] == 10.0


def test_outlier_does_not_corrupt_baseline():
    """Verify extreme outlier is rejected from update, preserving baseline uncorrupted [SYNTHETIC]."""
    js_code = f"""
    const {{ updateAdaptiveBaseline }} = require({json.dumps(str(JS_UPDATER))});

    const baseline = {{
      participant_id: 'p-001',
      modality: 'motor',
      feature_name: 'stride_variability',
      baseline_mean: 3.0,
      baseline_median: 3.0,
      baseline_std: 0.3,
      baseline_mad: 0.2,
      sample_count: 14,
      baseline_version: '1.0.0',
      baseline_created_at: '2026-09-14T10:00:00.000Z',
      baseline_updated_at: '2026-09-14T10:00:00.000Z'
    }};

    // Extreme outlier: value = 9.0 (delta = 6.0 = 30 MAD!)
    const result = updateAdaptiveBaseline(baseline, {{
      value: 9.0,
      quality_score: 0.95,
      date: '2026-09-15'
    }});

    console.log(JSON.stringify(result));
    """

    res = run_node_eval(js_code)

    assert res["status"] == "rejected_outlier"
    assert res["wasBaselineUpdated"] is False
    assert res["anomalyFlag"] == "anomalous observation"
    assert res["madDistance"] == 30.0

    # Baseline remains unchanged
    updated = res["updatedBaseline"]
    assert updated["baseline_mean"] == 3.0
    assert updated["baseline_median"] == 3.0
    assert updated["baseline_std"] == 0.3
    assert updated["baseline_mad"] == 0.2
    assert updated["sample_count"] == 14
    assert updated["baseline_version"] == "1.0.0"
    assert updated["baseline_updated_at"] == "2026-09-14T10:00:00.000Z"

    # Deviation record was generated for auditing
    dev = res["deviationRecord"]
    assert dev is not None
    assert dev["is_outlier"] is True
    assert dev["anomaly_flag"] == "anomalous observation"
    assert dev["value"] == 9.0
    assert dev["baseline_value"] == 3.0


def test_deviation_record_schema_conformance():
    """Verify createDeviationRecord produces fields matching daily_deviations Supabase schema [SYNTHETIC]."""
    js_code = f"""
    const {{ createDeviationRecord }} = require({json.dumps(str(JS_OUTLIER))});

    const baseline = {{
      participant_id: 'p-user',
      modality: 'typing',
      feature_name: 'mean_hold_duration',
      baseline_median: 80.0,
      baseline_mad: 4.0,
      baseline_std: 5.0
    }};

    const record = createDeviationRecord({{
      participantId: 'p-user',
      date: '2026-09-16',
      modality: 'typing',
      featureName: 'mean_hold_duration',
      value: 95.0, // (95 - 80) = 15.0 = 3.75 MAD -> Outlier
      baseline,
      qualityScore: 0.92
    }});

    console.log(JSON.stringify(record));
    """

    res = run_node_eval(js_code)

    assert res["participant_id"] == "p-user"
    assert res["date"] == "2026-09-16"
    assert res["modality"] == "typing"
    assert res["feature_name"] == "mean_hold_duration"
    assert res["value"] == 95.0
    assert res["baseline_value"] == 80.0
    assert res["quality_score"] == 0.92
    assert res["is_outlier"] is True
    assert res["anomaly_flag"] == "anomalous observation"
    assert res["mad_distance"] == 3.75
    assert res["deviation_score"] > 0
    assert res["trend_score"] == 15.0


def test_engine_outlier_filtering_in_process_adaptive_day():
    """Verify baselineEngine.processAdaptiveDay rejects outliers and retains normal features [SYNTHETIC]."""
    participant_id = "p-engine-test"
    baselines = [
        {
            "participant_id": participant_id,
            "modality": "motor",
            "feature_name": "cadence",
            "baseline_mean": 100.0,
            "baseline_median": 100.0,
            "baseline_std": 3.0,
            "baseline_mad": 2.0,
            "sample_count": 14,
            "baseline_version": "1.0.0",
            "baseline_created_at": "2026-09-14T00:00:00.000Z",
            "baseline_updated_at": "2026-09-14T00:00:00.000Z"
        },
        {
            "participant_id": participant_id,
            "modality": "motor",
            "feature_name": "tapping_rate",
            "baseline_mean": 5.0,
            "baseline_median": 5.0,
            "baseline_std": 0.4,
            "baseline_mad": 0.2,
            "sample_count": 14,
            "baseline_version": "1.0.0",
            "baseline_created_at": "2026-09-14T00:00:00.000Z",
            "baseline_updated_at": "2026-09-14T00:00:00.000Z"
        }
    ]

    # cadence is normal (102.0, delta 2.0 = 1.0 MAD <= 3.0)
    # tapping_rate is extreme outlier (7.0, delta 2.0 = 10.0 MAD > 3.0)
    daily_obs = {
        "participant_id": participant_id,
        "feature_date": "2026-09-15",
        "quality_scores": {"motor": 0.95},
        "motor": {
            "cadence": 102.0,
            "tapping_rate": 7.0
        }
    }

    js_code = f"""
    const engine = require({json.dumps(str(JS_ENGINE))});
    const result = engine.processAdaptiveDay({{
      participantId: {json.dumps(participant_id)},
      date: '2026-09-15',
      currentBaselines: {json.dumps(baselines)},
      dailyObservation: {json.dumps(daily_obs)}
    }});
    console.log(JSON.stringify(result));
    """

    res = run_node_eval(js_code)

    assert res["totalEvaluated"] == 2
    assert res["updatedCount"] == 1        # cadence was updated
    assert res["rejectedOutlierCount"] == 1 # tapping_rate was rejected
    assert res["hasAnomalies"] is True

    # Check anomalies list
    anomaly = res["anomalies"][0]
    assert anomaly["featureName"] == "tapping_rate"
    assert anomaly["flag"] == "anomalous observation"
    assert anomaly["madDistance"] == 10.0

    # Verify updated cadence baseline
    cadence_updated = next(b for b in res["updatedBaselines"] if b["feature_name"] == "cadence")
    assert cadence_updated["baseline_version"] == "1.0.1"
    assert cadence_updated["sample_count"] == 15

    # Verify uncorrupted tapping_rate baseline
    tapping_retained = next(b for b in res["updatedBaselines"] if b["feature_name"] == "tapping_rate")
    assert tapping_retained["baseline_version"] == "1.0.0"
    assert tapping_retained["sample_count"] == 14
    assert tapping_retained["baseline_mean"] == 5.0


def test_non_diagnostic_compliance_in_outlier_summary():
    """Verify that outlier summaries contain strictly research and non-diagnostic phrasing."""
    js_code = f"""
    const {{ createDeviationRecord }} = require({json.dumps(str(JS_OUTLIER))});

    const baseline = {{
      participant_id: 'p-test',
      modality: 'motor',
      feature_name: 'tremor_frequency',
      baseline_median: 4.5,
      baseline_mad: 0.3
    }};

    const record = createDeviationRecord({{
      participantId: 'p-test',
      date: '2026-09-15',
      modality: 'motor',
      featureName: 'tremor_frequency',
      value: 8.0, // Outlier
      baseline,
      qualityScore: 0.90
    }});

    console.log(JSON.stringify(record));
    """

    output_str = subprocess.run(["node", "-e", js_code], capture_output=True, text=True, check=True).stdout.lower()

    for term in DISALLOWED_DIAGNOSTIC_TERMS:
        assert term not in output_str, f"Prohibited clinical term found: {term}"

    assert "anomalous observation" in output_str
    assert "personal baseline" in output_str
