"""
Phase 12 Tests: Adapter Output Format and Non-Diagnostic Integrity.

Verifies:
1. Output format strictly matches existing MPF specification:
   - risk_score: 0.0-1.0
   - available_modalities: [...]
   - missing_modalities: [...]
   - model_version: "..."
   - prediction_metadata: {
       source: "mobile_extension",
       feature_mapping_version: "...",
       baseline_deviation_context: {...},
       timestamp: "..."
     }
2. Non-diagnostic phrasing enforcement:
   - "Elevated Parkinson's risk pattern detected" / "Standard risk pattern observed"
   - "Research screening result — not a clinical diagnosis."
   - Zero occurrences of "You have Parkinson's" or "Parkinson's progression".
3. Audit logging records metadata for reproducibility.
"""

import json
from pathlib import Path
import pytest
from src.mobile.mpf_adapter import MPFAdapter
from src.mobile.prediction_logger import (
    format_mpf_prediction_response,
    log_prediction,
    FORBIDDEN_DIAGNOSTIC_TERMS,
    RESEARCH_DISCLAIMER,
)


def test_adapter_output_format_conformance():
    """Verify output dictionary structure matches Section 5 specification."""
    adapter = MPFAdapter(log_file_path=None)
    mobile_data = {
        "participant_id": "TEST_P020",
        "date": "2026-09-23",
        "voice": {"jitter": 0.0065, "shimmer": 0.045, "hnr": 18.5, "pitch_mean": 190.0},
        "motor": {"cadence": 102.0, "stride_variability": 3.4, "tapping_rate": 5.1},
        "sleep": {"unusual_movement_self_report": 1.0, "sleep_quality": 8.0},
    }

    baseline_ctx = {
        "baseline_version": 1,
        "mahalanobis_distance": 2.14,
        "significant_deviations": ["voice.jitter", "motor.cadence"],
    }

    res = adapter.run_inference(
        mobile_daily_features=mobile_data,
        baseline_deviation_context=baseline_ctx,
        log_to_db=False,
    )

    # Core required Section 5 keys
    assert "risk_score" in res
    assert isinstance(res["risk_score"], float)
    assert 0.0 <= res["risk_score"] <= 1.0

    assert "available_modalities" in res
    assert isinstance(res["available_modalities"], list)

    assert "missing_modalities" in res
    assert isinstance(res["missing_modalities"], list)

    assert "model_version" in res
    assert isinstance(res["model_version"], str)

    assert "prediction_metadata" in res
    meta = res["prediction_metadata"]
    assert meta["source"] == "mobile_extension"
    assert "feature_mapping_version" in meta
    assert meta["baseline_deviation_context"] == baseline_ctx
    assert "timestamp" in meta


def test_non_diagnostic_language_enforcement():
    """Verify that output strings never claim a clinical diagnosis."""
    adapter = MPFAdapter(log_file_path=None)
    mobile_data = {
        "participant_id": "TEST_P021",
        "date": "2026-09-23",
        "voice": {"jitter": 0.015, "shimmer": 0.09, "hnr": 12.0},  # Elevated risk features
        "motor": {"cadence": 75.0, "stride_variability": 8.5, "tapping_rate": 2.8},
        "sleep": {"unusual_movement_self_report": 1.0, "sleep_quality": 10.0},
    }

    res = adapter.run_inference(mobile_data, log_to_db=False)
    res_str = json.dumps(res).lower()

    for forbidden in FORBIDDEN_DIAGNOSTIC_TERMS:
        assert forbidden not in res_str, f"Forbidden diagnostic phrase '{forbidden}' found in output!"

    assert "research screening result" in res_str
    assert "not a clinical diagnosis" in res_str
    assert "risk pattern" in res_str


def test_prediction_audit_logging(tmp_path):
    """Verify prediction metadata logging to local audit log."""
    log_file = tmp_path / "test_predictions.jsonl"
    adapter = MPFAdapter(log_file_path=str(log_file))

    mobile_data = {
        "participant_id": "TEST_P022",
        "date": "2026-09-23",
        "voice": {"jitter": 0.005, "shimmer": 0.035, "hnr": 22.0},
    }

    res = adapter.run_inference(mobile_data, feature_date="2026-09-23", log_to_db=True)
    assert log_file.exists()

    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["prediction"]["risk_score"] == res["risk_score"]
    assert entry["db_record"]["participant_id"] == "TEST_P022"
    assert entry["db_record"]["prediction_metadata"]["feature_date"] == "2026-09-23"
