"""
Tests for MPF Mobile Extension — Daily Feature Aggregator & Vector Builder (Phase 9)

Validates:
1. Standardized daily feature vector structure matching Phase 9 schema specification.
2. Robust aggregation of multiple sessions using median (central tendency) and IQR (variability).
3. Inter-session disagreement detection across multiple sessions.
4. Non-imputation of missing modalities.
5. Quality filtering integration (omits sessions < 0.50).
6. Supabase record serialization matching daily_features table schema.
7. Strict non-diagnostic terminology and research provenance compliance.
8. JavaScript execution under Node.js for complete mobile frontend compatibility.

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import subprocess
import uuid
import pytest
from pathlib import Path

JS_AGGREGATOR_PATH = Path(__file__).resolve().parents[1] / "dailyFeatureAggregator.js"
JS_BUILDER_PATH = Path(__file__).resolve().parents[1] / "featureVectorBuilder.js"

DISALLOWED_DIAGNOSTIC_TERMS = [
    "you have parkinson's",
    "parkinson's detected",
    "diagnosed parkinson",
    "confirmed parkinson",
    "parkinson's progression",
]


def median_py(values: list):
    """Python reference median."""
    filtered = sorted([float(v) for v in values if v is not None])
    if not filtered:
        return None
    mid = len(filtered) // 2
    med = (filtered[mid - 1] + filtered[mid]) / 2.0 if len(filtered) % 2 == 0 else filtered[mid]
    return round(med, 4)


def iqr_py(values: list):
    """Python reference IQR."""
    filtered = sorted([float(v) for v in values if v is not None])
    if len(filtered) < 2:
        return 0.0
    if len(filtered) == 2:
        return round(abs(filtered[1] - filtered[0]), 4)
    mid = len(filtered) // 2
    lower = filtered[:mid]
    upper = filtered[mid:] if len(filtered) % 2 == 0 else filtered[mid + 1:]
    q25 = median_py(lower)
    q75 = median_py(upper)
    return round(q75 - q25, 4)


# ── Python Unit Tests ────────────────────────────────────────────────────────

def test_math_median_and_iqr_computation():
    """Verify median and IQR calculations on sample session distributions."""
    # [SYNTHETIC] 3 sessions
    vals = [100.0, 110.0, 150.0]
    assert median_py(vals) == 110.0
    assert iqr_py(vals) == round(150.0 - 100.0, 4)

    # [SYNTHETIC] 4 sessions
    vals4 = [10.0, 20.0, 30.0, 40.0]
    assert median_py(vals4) == 25.0
    assert iqr_py(vals4) == 20.0


def test_schema_conformance_of_daily_vector():
    """Verify schema shape of daily feature vector against Phase 9 specification."""
    participant_id = str(uuid.uuid4())
    date_str = "2026-09-24"

    # [SYNTHETIC] Sessions for typing, voice, motor
    typing_sessions = [
        {"typing_speed": 240.0, "interval_variability": 22.0, "correction_rate": 0.04, "quality_score": 0.90},
        {"typing_speed": 260.0, "interval_variability": 24.0, "correction_rate": 0.05, "quality_score": 0.85},
    ]
    voice_sessions = [
        {"jitter": 0.005, "shimmer": 0.035, "hnr": 21.0, "pitch_mean": 130.0, "quality_score": 0.88}
    ]
    motor_sessions = [
        {"cadence": 104.0, "stride_variability": 3.2, "quality_score": 0.92}, # Walking
        {"tapping_rate": 5.4, "quality_score": 0.89},                         # Tapping
        {"tremor_frequency": 4.8, "quality_score": 0.91},                     # Tremor
    ]

    # Run JS aggregator to test real output
    js_script = f"""
    const {{ aggregateDay }} = require({json.dumps(str(JS_AGGREGATOR_PATH))});
    const {{ buildDailyFeatureVector, toSupabaseRecord, validateDailyFeatureVector }} = require({json.dumps(str(JS_BUILDER_PATH))});

    const sessions = {{
      typing: {json.dumps(typing_sessions)},
      voice: {json.dumps(voice_sessions)},
      motor: {json.dumps(motor_sessions)},
      visual: [],
      sleep: []
    }};

    const agg = aggregateDay({{
      participantId: {json.dumps(participant_id)},
      date: {json.dumps(date_str)},
      sessions
    }});

    const vector = buildDailyFeatureVector({{
      participantId: {json.dumps(participant_id)},
      date: {json.dumps(date_str)},
      aggregationResult: agg
    }});

    const validation = validateDailyFeatureVector(vector);
    const dbRecord = toSupabaseRecord(vector);

    console.log(JSON.stringify({{ vector, validation, dbRecord }}));
    """

    res = subprocess.run(["node", "-e", js_script], capture_output=True, text=True, check=True)
    out = json.loads(res.stdout.strip())
    vector = out["vector"]
    validation = out["validation"]
    db_record = out["dbRecord"]

    assert validation["valid"] is True
    assert validation["errors"] == []

    # Check top-level keys
    assert vector["participant_id"] == participant_id
    assert vector["date"] == date_str
    assert vector["feature_version"] == "1.0"
    assert vector["available_modalities"] == ["typing", "voice", "motor"]
    assert vector["missing_modalities"] == ["visual", "sleep"]

    # Check typing block
    assert vector["typing"]["typing_speed"] == 250.0  # Median of 240 and 260
    assert vector["typing"]["interval_variability"] == 23.0
    assert vector["typing"]["correction_rate"] == 0.045
    assert vector["typing"]["quality_score"] == 0.875

    # Check voice block
    assert vector["voice"]["jitter"] == 0.005
    assert vector["voice"]["hnr"] == 21.0

    # Check motor block
    assert vector["motor"]["cadence"] == 104.0
    assert vector["motor"]["tapping_rate"] == 5.4
    assert vector["motor"]["tremor_frequency"] == 4.8

    # Check missing blocks are strictly null
    assert vector["visual"] is None
    assert vector["sleep"] is None

    # Check quality block
    assert "typing_quality" in vector["quality"]
    assert "voice_quality" in vector["quality"]
    assert "motor_quality" in vector["quality"]
    assert "visual_quality" in vector["quality"]
    assert "overall_quality" in vector["quality"]
    assert vector["quality"]["overall_quality"] > 0.80

    # Check Supabase record structure
    assert db_record["participant_id"] == participant_id
    assert db_record["date"] == date_str
    assert db_record["typing_features"] == vector["typing"]
    assert db_record["voice_features"] == vector["voice"]
    assert db_record["motor_features"] == vector["motor"]
    assert db_record["visual_features"] is None
    assert db_record["sleep_features"] is None
    assert db_record["feature_version"] == "1.0"


def test_multiple_sessions_disagreement_detection():
    """Verify aggregator detects and flags widely disagreeing sessions within a single day."""
    participant_id = str(uuid.uuid4())
    date_str = "2026-09-24"

    # [SYNTHETIC] 2 sessions with starkly disagreeing cadence (e.g. 60 vs 130 steps/min)
    motor_disagreeing = [
        {"cadence": 60.0, "quality_score": 0.80},
        {"cadence": 130.0, "quality_score": 0.85},
    ]

    js_script = f"""
    const {{ aggregateDay }} = require({json.dumps(str(JS_AGGREGATOR_PATH))});
    const res = aggregateDay({{
      participantId: {json.dumps(participant_id)},
      date: {json.dumps(date_str)},
      sessions: {{ motor: {json.dumps(motor_disagreeing)} }}
    }});
    console.log(JSON.stringify(res));
    """
    res = subprocess.run(["node", "-e", js_script], capture_output=True, text=True, check=True)
    out = json.loads(res.stdout.strip())

    assert out["has_disagreements"] is True
    disagreement_features = [d["feature"] for d in out["disagreements"]]
    assert "motor_cadence" in disagreement_features
    # Robust median is still computed
    assert out["features"]["motor"]["cadence"] == 95.0


def test_quality_exclusion_within_aggregation():
    """Verify that sessions with quality_score < 0.50 are excluded from feature computation."""
    participant_id = str(uuid.uuid4())
    date_str = "2026-09-24"

    # [SYNTHETIC] One high quality session (speed 250), one low quality corrupted session (speed 50)
    typing_sessions = [
        {"typing_speed": 250.0, "quality_score": 0.90},
        {"typing_speed": 50.0, "quality_score": 0.30},  # Should be excluded!
    ]

    js_script = f"""
    const {{ aggregateDay }} = require({json.dumps(str(JS_AGGREGATOR_PATH))});
    const res = aggregateDay({{
      participantId: {json.dumps(participant_id)},
      date: {json.dumps(date_str)},
      sessions: {{ typing: {json.dumps(typing_sessions)} }}
    }});
    console.log(JSON.stringify(res));
    """
    res = subprocess.run(["node", "-e", js_script], capture_output=True, text=True, check=True)
    out = json.loads(res.stdout.strip())

    # Only the passed session (250) should determine the feature
    assert out["features"]["typing"]["typing_speed"] == 250.0
    assert out["features"]["typing"]["quality_score"] == 0.90


def test_non_diagnostic_compliance_in_vector():
    """Verify that the daily feature vector and serialization contain zero disallowed diagnostic terms."""
    participant_id = str(uuid.uuid4())
    date_str = "2026-09-24"

    js_script = f"""
    const {{ buildDailyFeatureVector }} = require({json.dumps(str(JS_BUILDER_PATH))});
    const vector = buildDailyFeatureVector({{
      participantId: {json.dumps(participant_id)},
      date: {json.dumps(date_str)},
      sessions: {{}}
    }});
    console.log(JSON.stringify(vector));
    """
    res = subprocess.run(["node", "-e", js_script], capture_output=True, text=True, check=True)
    vector_json_str = res.stdout.strip().lower()

    for term in DISALLOWED_DIAGNOSTIC_TERMS:
        assert term not in vector_json_str, f"Disallowed diagnostic phrase found in daily vector: {term}"
