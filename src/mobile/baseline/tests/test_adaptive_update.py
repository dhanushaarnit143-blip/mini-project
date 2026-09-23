"""
Tests for MPF Mobile Extension — Adaptive Baseline Updater (Phase 10)

Validates:
1. Exponentially Weighted Moving Average (EWMA) updates for Day 15+:
   - Formula: EWMA_new = alpha * obs + (1 - alpha) * EWMA_old
   - Default alpha = 0.1, configurable to any valid alpha in (0, 1].
2. Multi-day longitudinal simulation showing smooth baseline tracking.
3. Quality filtering integration:
   - Observations with quality < 0.50 are rejected.
   - Baseline is left completely unmodified.
4. Version incrementing and timestamp updates:
   - baseline_version increments on each accepted update.
   - baseline_updated_at advances, baseline_created_at is strictly preserved.
   - sample_count increments.
5. Full engine orchestration with processAdaptiveDay().

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import subprocess
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
JS_UPDATER = BASE_DIR / "adaptiveBaselineUpdater.js"
JS_ENGINE = BASE_DIR / "baselineEngine.js"


def run_node_eval(js_code: str):
    res = subprocess.run(
        ["node", "-e", js_code],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(res.stdout)


def test_ewma_mathematical_update():
    """Verify EWMA mathematical calculation matches exact formula with alpha = 0.1 [SYNTHETIC]."""
    initial_mean = 100.0
    obs_val = 110.0
    alpha = 0.1
    expected_new_mean = round(alpha * obs_val + (1.0 - alpha) * initial_mean, 4)  # 101.0

    js_code = f"""
    const {{ updateAdaptiveBaseline }} = require({json.dumps(str(JS_UPDATER))});

    const baseline = {{
      participant_id: 'part-123',
      modality: 'motor',
      feature_name: 'cadence',
      baseline_mean: {initial_mean},
      baseline_median: {initial_mean},
      baseline_std: 5.0,
      baseline_mad: 3.5,
      sample_count: 14,
      baseline_version: '1.0.0',
      baseline_created_at: '2026-09-14T00:00:00.000Z',
      baseline_updated_at: '2026-09-14T00:00:00.000Z'
    }};

    const result = updateAdaptiveBaseline(baseline, {{
      value: {obs_val},
      quality_score: 0.95,
      date: '2026-09-15'
    }}, {{ alpha: {alpha} }});

    console.log(JSON.stringify(result));
    """

    res = run_node_eval(js_code)
    assert res["status"] == "updated"
    assert res["wasBaselineUpdated"] is True

    updated = res["updatedBaseline"]
    assert abs(updated["baseline_mean"] - expected_new_mean) < 0.01
    assert updated["baseline_version"] == "1.0.1"
    assert updated["sample_count"] == 15
    assert updated["baseline_status"] == "adaptive_updated"
    assert updated["baseline_created_at"] == "2026-09-14T00:00:00.000Z"


def test_configurable_alpha_parameter():
    """Verify that different alpha values (0.2 vs 0.05) modulate adaptation rate [SYNTHETIC]."""
    js_code = f"""
    const {{ updateAdaptiveBaseline }} = require({json.dumps(str(JS_UPDATER))});

    const baseline = {{
      participant_id: 'part-123',
      modality: 'typing',
      feature_name: 'typing_speed',
      baseline_mean: 4.0,
      baseline_median: 4.0,
      baseline_std: 0.4,
      baseline_mad: 0.3,
      sample_count: 14,
      baseline_version: '1.0.0'
    }};

    const resFast = updateAdaptiveBaseline(baseline, {{ value: 4.5, quality_score: 1.0 }}, {{ alpha: 0.20 }});
    const resSlow = updateAdaptiveBaseline(baseline, {{ value: 4.5, quality_score: 1.0 }}, {{ alpha: 0.05 }});

    console.log(JSON.stringify({{
      fastMean: resFast.updatedBaseline.baseline_mean,
      slowMean: resSlow.updatedBaseline.baseline_mean
    }}));
    """

    res = run_node_eval(js_code)
    # Fast (alpha=0.2): 0.2 * 4.5 + 0.8 * 4.0 = 4.10
    # Slow (alpha=0.05): 0.05 * 4.5 + 0.95 * 4.0 = 4.025
    assert abs(res["fastMean"] - 4.10) < 0.01
    assert abs(res["slowMean"] - 4.025) < 0.01
    assert res["fastMean"] > res["slowMean"]


def test_quality_filtering_rejection():
    """Verify observations with quality < 0.50 are rejected and baseline is uncorrupted [SYNTHETIC]."""
    js_code = f"""
    const {{ updateAdaptiveBaseline }} = require({json.dumps(str(JS_UPDATER))});

    const baseline = {{
      participant_id: 'part-123',
      modality: 'voice',
      feature_name: 'jitter',
      baseline_mean: 0.0050,
      baseline_median: 0.0050,
      baseline_std: 0.0008,
      baseline_mad: 0.0006,
      sample_count: 14,
      baseline_version: '1.0.0',
      baseline_created_at: '2026-09-14T00:00:00.000Z',
      baseline_updated_at: '2026-09-14T00:00:00.000Z'
    }};

    const result = updateAdaptiveBaseline(baseline, {{
      value: 0.0052,
      quality_score: 0.40, // Below minimum 0.50
      date: '2026-09-15'
    }});

    console.log(JSON.stringify(result));
    """

    res = run_node_eval(js_code)
    assert res["status"] == "rejected_low_quality"
    assert res["wasBaselineUpdated"] is False
    assert res["updatedBaseline"]["baseline_mean"] == 0.0050
    assert res["updatedBaseline"]["baseline_version"] == "1.0.0"
    assert res["updatedBaseline"]["sample_count"] == 14


def test_multi_day_adaptive_tracking():
    """Simulate 5 consecutive days (Days 15 to 19) of updates [SYNTHETIC]."""
    js_code = f"""
    const {{ updateAdaptiveBaseline }} = require({json.dumps(str(JS_UPDATER))});

    let baseline = {{
      participant_id: 'p-sim',
      modality: 'motor',
      feature_name: 'cadence',
      baseline_mean: 100.0,
      baseline_median: 100.0,
      baseline_std: 4.0,
      baseline_mad: 3.0,
      sample_count: 14,
      baseline_version: '1.0.0',
      baseline_created_at: '2026-09-14T00:00:00.000Z',
      baseline_updated_at: '2026-09-14T00:00:00.000Z'
    }};

    const observations = [102.0, 103.0, 101.5, 104.0, 102.5];
    const history = [];

    for (let i = 0; i < observations.length; i++) {{
      const dayNum = 15 + i;
      const res = updateAdaptiveBaseline(baseline, {{
        value: observations[i],
        quality_score: 0.90,
        date: `2026-09-${{dayNum}}`
      }}, {{ alpha: 0.1 }});

      baseline = res.updatedBaseline;
      history.push({{
        day: dayNum,
        mean: baseline.baseline_mean,
        version: baseline.baseline_version,
        sampleCount: baseline.sample_count
      }});
    }}

    console.log(JSON.stringify({{ finalBaseline: baseline, history }}));
    """

    res = run_node_eval(js_code)
    history = res["history"]
    assert len(history) == 5

    # Day 19 should have version 1.0.5 and sample_count 19
    final = res["finalBaseline"]
    assert final["baseline_version"] == "1.0.5"
    assert final["sample_count"] == 19
    assert final["baseline_created_at"] == "2026-09-14T00:00:00.000Z"
    # Progressive tracking: mean shifted from 100 upwards toward ~102
    assert final["baseline_mean"] > 100.5


def test_engine_process_adaptive_day():
    """Verify baselineEngine.processAdaptiveDay processes multiple modality features [SYNTHETIC]."""
    participant_id = "p-multi"
    baselines = [
        {
            "participant_id": participant_id,
            "modality": "motor",
            "feature_name": "cadence",
            "baseline_mean": 105.0,
            "baseline_median": 105.0,
            "baseline_std": 3.0,
            "baseline_mad": 2.2,
            "sample_count": 14,
            "baseline_version": "1.0.0",
            "baseline_created_at": "2026-09-14T00:00:00.000Z",
            "baseline_updated_at": "2026-09-14T00:00:00.000Z"
        },
        {
            "participant_id": participant_id,
            "modality": "typing",
            "feature_name": "typing_speed",
            "baseline_mean": 4.5,
            "baseline_median": 4.5,
            "baseline_std": 0.3,
            "baseline_mad": 0.2,
            "sample_count": 14,
            "baseline_version": "1.0.0",
            "baseline_created_at": "2026-09-14T00:00:00.000Z",
            "baseline_updated_at": "2026-09-14T00:00:00.000Z"
        }
    ]

    daily_obs = {
        "participant_id": participant_id,
        "feature_date": "2026-09-15",
        "quality_scores": {"motor": 0.92, "typing": 0.88},
        "motor": {"cadence": 106.0},
        "typing": {"typing_speed": 4.6}
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
    assert res["updatedCount"] == 2
    assert res["rejectedOutlierCount"] == 0
    assert len(res["deviationRecords"]) == 2
