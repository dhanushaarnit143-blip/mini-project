"""
Phase 9 Integration Tests for MPF-PD Central Inference Pipeline.

Tests all 11 required integration scenarios:
1. All modalities present.
2. One modality missing.
3. Multiple modalities missing.
4. Invalid input structure.
5. Corrupted image.
6. Invalid audio file.
7. Malformed motor file.
8. Olfactory score out of range.
9. RBDSQ score out of range.
10. Missing fusion model.
11. Missing SHAP explainer.

Verifies:
- Pipeline does not crash on missing optional modalities.
- Output schema conforms to standardized specification.
- Status values are correct ("success", "partial_success", "failed").
- Missing modalities are reported correctly.
- Errors are captured in errors or warnings.
- Risk scores are within [0.0, 1.0] when produced.
"""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import numpy as np
import pytest

from src.pipeline import ALL_MODALITIES, run_mpf_pipeline


def _make_valid_synthetic_inputs() -> Dict[str, Any]:
    """Helper returning a complete, valid synthetic multimodal payload."""
    return {
        "participant_id": "TEST-SYNTH-001",
        "age": 66.0,
        "sex": "female",
        "olfactory": {
            "available": True,
            "score": 26,
            "max_score": 40,
            "responses": [],
        },
        "rbd": {
            "available": True,
            "rbdsq_total": 6,
            "item_responses": [1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0],
        },
        "voice": {
            "available": True,
            "features": {
                "jitter_pct": 0.006,
                "shimmer": 0.045,
                "hnr": 18.0,
            },
        },
        "motor": {
            "available": True,
            "features": {
                "gait_speed_m_per_s": 1.05,
                "cadence_steps_per_min": 102.0,
            },
        },
        "retina": {
            "available": True,
            "features": {
                "vessel_density": 0.071,
                "mean_vessel_diameter_px": 3.1,
            },
        },
    }


def _assert_valid_output_schema(res: Dict[str, Any]):
    """Verify presence and structure of all required schema keys."""
    expected_top_keys = [
        "participant_id",
        "status",
        "experiment_type",
        "available_modalities",
        "missing_modalities",
        "modality_results",
        "fusion",
        "explanation",
        "metadata",
        "errors",
    ]
    for k in expected_top_keys:
        assert k in res, f"Missing required top-level key '{k}'"

    assert res["status"] in ["success", "partial_success", "failed"]
    assert isinstance(res["available_modalities"], list)
    assert isinstance(res["missing_modalities"], list)
    assert isinstance(res["modality_results"], dict)
    assert isinstance(res["fusion"], dict)
    assert isinstance(res["explanation"], dict)
    assert isinstance(res["metadata"], dict)
    assert isinstance(res["errors"], list)

    assert "pipeline_version" in res["metadata"]
    assert res["metadata"]["clinical_claim"] is False

    # Check each modality in modality_results
    for m in ALL_MODALITIES:
        assert m in res["modality_results"], f"Modality '{m}' not found in modality_results"
        m_res = res["modality_results"][m]
        assert "status" in m_res
        assert m_res["status"] in ["success", "missing", "failed_qc", "not_trained", "error"]
        assert "risk_score" in m_res
        assert "embedding" in m_res
        assert "features_used" in m_res
        assert "warnings" in m_res

    # Check fusion schema
    fusion = res["fusion"]
    assert "status" in fusion
    assert fusion["status"] in ["success", "failed", "not_trained", "missing"]
    assert "risk_score" in fusion
    assert "fused_embedding" in fusion
    assert "gate_weights" in fusion
    assert "warnings" in fusion

    # Check explanation schema
    exp = res["explanation"]
    assert "important_modalities" in exp
    assert "important_features" in exp
    assert "positive_contributors" in exp
    assert "negative_contributors" in exp
    assert "missing_modalities" in exp
    assert "warnings" in exp


# =============================================================================
# SCENARIO 1: All modalities present
# =============================================================================
def test_scenario_01_all_modalities_present():
    """Verify pipeline executes cleanly when all 5 modalities are present."""
    payload = _make_valid_synthetic_inputs()
    res = run_mpf_pipeline(payload)

    _assert_valid_output_schema(res)
    assert res["status"] == "success"
    assert res["fusion"]["status"] == "success"
    assert res["fusion"]["risk_score"] is not None
    assert 0.0 <= res["fusion"]["risk_score"] <= 1.0
    assert len(res["available_modalities"]) == 5
    assert len(res["missing_modalities"]) == 0
    assert len(res["errors"]) == 0
    for m in ALL_MODALITIES:
        assert res["modality_results"][m]["status"] == "success"


# =============================================================================
# SCENARIO 2: One modality missing
# =============================================================================
def test_scenario_02_one_modality_missing():
    """Verify pipeline handles a single missing optional modality gracefully."""
    payload = _make_valid_synthetic_inputs()
    payload["voice"] = {"available": False}

    res = run_mpf_pipeline(payload)

    _assert_valid_output_schema(res)
    assert res["status"] == "success"
    assert res["fusion"]["status"] == "success"
    assert 0.0 <= res["fusion"]["risk_score"] <= 1.0
    assert "voice" in res["missing_modalities"]
    assert "voice" not in res["available_modalities"]
    assert res["modality_results"]["voice"]["status"] == "missing"
    assert res["modality_results"]["voice"]["risk_score"] is None


# =============================================================================
# SCENARIO 3: Multiple modalities missing
# =============================================================================
def test_scenario_03_multiple_modalities_missing():
    """Verify pipeline executes with multiple modalities omitted."""
    payload = {
        "participant_id": "TEST-PARTIAL-003",
        "age": 70.0,
        "sex": "male",
        "olfactory": {"available": True, "score": 22, "max_score": 40},
        "rbd": {"available": True, "rbdsq_total": 8},
        "voice": {"available": False},
        "motor": {"available": False},
        "retina": {"available": False},
    }

    res = run_mpf_pipeline(payload)

    _assert_valid_output_schema(res)
    assert res["status"] == "success"
    assert res["fusion"]["status"] == "success"
    assert 0.0 <= res["fusion"]["risk_score"] <= 1.0
    assert set(res["missing_modalities"]) == {"voice", "motor", "retina"}
    assert set(res["available_modalities"]) == {"olfactory", "rbd"}


# =============================================================================
# SCENARIO 4: Invalid input structure
# =============================================================================
def test_scenario_04_invalid_input_structure():
    """Verify invalid participant inputs fail gracefully with status='failed'."""
    # 4a: Non-dict payload
    res_nondict = run_mpf_pipeline("not_a_valid_dict")
    _assert_valid_output_schema(res_nondict)
    assert res_nondict["status"] == "failed"
    assert len(res_nondict["errors"]) > 0
    assert res_nondict["fusion"]["status"] == "failed"

    # 4b: Missing required age
    res_noage = run_mpf_pipeline({"participant_id": "NO-AGE"})
    _assert_valid_output_schema(res_noage)
    assert res_noage["status"] == "failed"
    assert any("age" in err.lower() for err in res_noage["errors"])

    # 4c: Age out of screening range
    res_badage = run_mpf_pipeline({"participant_id": "BAD-AGE", "age": 145})
    _assert_valid_output_schema(res_badage)
    assert res_badage["status"] == "failed"
    assert any("age" in err.lower() for err in res_badage["errors"])


# =============================================================================
# SCENARIO 5: Corrupted image
# =============================================================================
def test_scenario_05_corrupted_image(tmp_path: Path):
    """Verify corrupted retinal image fails QC gracefully without crashing pipeline."""
    corrupt_file = tmp_path / "corrupt_fundus.png"
    corrupt_file.write_bytes(b"INVALID_CORRUPTED_NON_IMAGE_BYTES_1234567890")

    payload = _make_valid_synthetic_inputs()
    payload["retina"] = {
        "available": True,
        "file_path": str(corrupt_file),
    }

    res = run_mpf_pipeline(payload)

    _assert_valid_output_schema(res)
    assert res["status"] == "partial_success"
    assert res["modality_results"]["retina"]["status"] in ["failed_qc", "error"]
    assert "retina" in res["missing_modalities"]
    assert any("retin" in err.lower() or "image" in err.lower() for err in res["errors"])
    # Fusion continues with other 4 valid modalities
    assert res["fusion"]["status"] == "success"
    assert 0.0 <= res["fusion"]["risk_score"] <= 1.0


# =============================================================================
# SCENARIO 6: Invalid audio file
# =============================================================================
def test_scenario_06_invalid_audio_file(tmp_path: Path):
    """Verify corrupted or unreadable audio fails QC gracefully without pipeline crash."""
    corrupt_wav = tmp_path / "corrupt_audio.wav"
    corrupt_wav.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00NOT_VALID_AUDIO")

    payload = _make_valid_synthetic_inputs()
    payload["voice"] = {
        "available": True,
        "file_path": str(corrupt_wav),
    }

    res = run_mpf_pipeline(payload)

    _assert_valid_output_schema(res)
    assert res["status"] == "partial_success"
    assert res["modality_results"]["voice"]["status"] in ["failed_qc", "error"]
    assert "voice" in res["missing_modalities"]
    assert any("voice" in err.lower() or "audio" in err.lower() for err in res["errors"])
    # Pipeline fusion proceeds with remaining modalities
    assert res["fusion"]["status"] == "success"
    assert 0.0 <= res["fusion"]["risk_score"] <= 1.0


# =============================================================================
# SCENARIO 7: Malformed motor file
# =============================================================================
def test_scenario_07_malformed_motor_file(tmp_path: Path):
    """Verify malformed motor CSV fails QC gracefully without pipeline crash."""
    bad_csv = tmp_path / "malformed_motor.csv"
    bad_csv.write_text("random_unparseable_data\n;;;;;;,,\x00\xff")

    payload = _make_valid_synthetic_inputs()
    payload["motor"] = {
        "available": True,
        "file_path": str(bad_csv),
    }

    res = run_mpf_pipeline(payload)

    _assert_valid_output_schema(res)
    assert res["status"] == "partial_success"
    assert res["modality_results"]["motor"]["status"] in ["failed_qc", "error"]
    assert "motor" in res["missing_modalities"]
    assert any("motor" in err.lower() for err in res["errors"])
    assert res["fusion"]["status"] == "success"
    assert 0.0 <= res["fusion"]["risk_score"] <= 1.0


# =============================================================================
# SCENARIO 8: Olfactory score out of range
# =============================================================================
def test_scenario_08_olfactory_score_out_of_range():
    """Verify olfactory score exceeding max_score triggers failed_qc."""
    payload = _make_valid_synthetic_inputs()
    payload["olfactory"] = {
        "available": True,
        "score": 999,
        "max_score": 40,
    }

    res = run_mpf_pipeline(payload)

    _assert_valid_output_schema(res)
    assert res["status"] == "partial_success"
    assert res["modality_results"]["olfactory"]["status"] == "failed_qc"
    assert "olfactory" in res["missing_modalities"]
    assert any("olfactory" in err.lower() for err in res["errors"])
    assert res["fusion"]["status"] == "success"
    assert 0.0 <= res["fusion"]["risk_score"] <= 1.0


# =============================================================================
# SCENARIO 9: RBDSQ score out of range
# =============================================================================
def test_scenario_09_rbdsq_score_out_of_range():
    """Verify RBDSQ score outside [0, 13] triggers failed_qc."""
    payload = _make_valid_synthetic_inputs()
    payload["rbd"] = {
        "available": True,
        "rbdsq_total": -5,
    }

    res = run_mpf_pipeline(payload)

    _assert_valid_output_schema(res)
    assert res["status"] == "partial_success"
    assert res["modality_results"]["rbd"]["status"] == "failed_qc"
    assert "rbd" in res["missing_modalities"]
    assert any("rbd" in err.lower() for err in res["errors"])
    assert res["fusion"]["status"] == "success"
    assert 0.0 <= res["fusion"]["risk_score"] <= 1.0


# =============================================================================
# SCENARIO 10: Missing fusion model
# =============================================================================
def test_scenario_10_missing_fusion_model():
    """Verify pipeline degrades gracefully to partial_success when fusion artifact is missing."""
    payload = _make_valid_synthetic_inputs()

    with patch("src.pipeline.load_fusion_model") as mock_load:
        mock_load.return_value = {
            "status": "missing",
            "artifact_path": "models/fusion/classifier.joblib",
            "metadata": {},
            "model": None,
        }
        res = run_mpf_pipeline(payload)

    _assert_valid_output_schema(res)
    assert res["status"] == "partial_success"
    assert res["fusion"]["status"] == "missing"
    assert res["fusion"]["risk_score"] is None
    assert any("fusion" in err.lower() for err in res["errors"])
    # Modality-level results are still preserved
    for m in ALL_MODALITIES:
        assert res["modality_results"][m]["status"] == "success"


# =============================================================================
# SCENARIO 11: Missing SHAP explainer
# =============================================================================
def test_scenario_11_missing_shap_explainer():
    """Verify pipeline generates fallback explanation when SHAP explainer is missing."""
    payload = _make_valid_synthetic_inputs()

    with patch("src.pipeline.load_shap_explainer") as mock_shap:
        mock_shap.return_value = {
            "status": "missing",
            "artifact_path": "models/fusion/classifier.joblib",
            "metadata": {},
            "model": None,
        }
        res = run_mpf_pipeline(payload)

    _assert_valid_output_schema(res)
    assert res["status"] == "success"
    assert res["fusion"]["status"] == "success"
    assert 0.0 <= res["fusion"]["risk_score"] <= 1.0
    # Explanation fallback must exist and contain important_modalities
    assert "important_modalities" in res["explanation"]
    assert len(res["explanation"]["important_modalities"]) == 5
    assert any("shap" in w.lower() or "missing" in w.lower() for w in res["explanation"]["warnings"])
