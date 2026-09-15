"""
MPF-PD Phase 10 Validation & Verification Automated Test Suite.

Verifies:
1. Phase 10 evaluation artifacts existence and JSON schema integrity.
2. Dataset validation categories and provenance.
3. Leakage detection report (zero participant overlap, strict training set fitting).
4. Missing modality analysis coverage and gate weight adaptation.
5. Figure generation completeness (ROC, calibration, confusion matrix, missing impact).
6. End-to-end pipeline robustness against corrupted/adversarial inputs.
7. Reproducibility across repeated seeded runs.
8. Dashboard API endpoints smoke testing.
"""

import json
from pathlib import Path
from typing import Dict, Any

import pytest
import numpy as np
from fastapi.testclient import TestClient

from src.config import load_config
from src.model_registry import load_all_models
from src.pipeline import run_mpf_pipeline, ALL_MODALITIES
from dashboard.api.main import app

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = PROJECT_ROOT / "evaluation"
FIGURES_DIR = EVAL_DIR / "figures"


# =============================================================================
# 1. ARTIFACT EXISTENCE & INTEGRITY TESTS
# =============================================================================

def test_phase10_artifacts_exist():
    """Verify all Phase 10 artifacts are generated and non-empty."""
    required_artifacts = [
        EVAL_DIR / "dataset_validation.json",
        EVAL_DIR / "leakage_report.json",
        EVAL_DIR / "missing_modality_analysis.json",
        EVAL_DIR / "FINAL_EVALUATION.md",
        FIGURES_DIR / "fusion_roc.png",
        FIGURES_DIR / "fusion_calibration.png",
        FIGURES_DIR / "fusion_confusion_matrix.png",
        FIGURES_DIR / "modality_comparison_roc.png",
        FIGURES_DIR / "gate_weights_distribution.png",
        FIGURES_DIR / "missing_modality_impact.png",
    ]
    for path in required_artifacts:
        assert path.exists(), f"Missing required Phase 10 artifact: {path}"
        assert path.stat().st_size > 0, f"Artifact {path} is unexpectedly empty."


# =============================================================================
# 2. DATASET VALIDATION SCHEMA TESTS
# =============================================================================

def test_dataset_validation_schema():
    """Verify evaluation/dataset_validation.json conforms to project specifications."""
    ds_path = EVAL_DIR / "dataset_validation.json"
    with open(ds_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["phase"] == 10
    assert data["clinical_claim"] is False
    assert data["experiment_type"] == "prototype_simulation"
    assert "datasets" in data

    datasets = data["datasets"]
    expected_ids = [
        "ppmi", "predict_pd", "uci_voice", "physionet_gait",
        "mpower", "retinal_fundus_pretraining", "oct500", "synthetic_fixture"
    ]
    for ds_id in expected_ids:
        assert ds_id in datasets, f"Dataset '{ds_id}' missing from dataset_validation.json"
        meta = datasets[ds_id]
        assert "category" in meta
        assert "label_definition" in meta
        assert "participant_count" in meta
        assert "missingness" in meta
        assert "license" in meta
        assert "verified" in meta
        assert meta["verified"] is True

        valid_categories = [
            "same_participant_multimodal",
            "modality_specific",
            "pretraining",
            "external_validation",
            "synthetic_fixture",
        ]
        assert meta["category"] in valid_categories, f"Invalid category for {ds_id}: {meta['category']}"


# =============================================================================
# 3. LEAKAGE DETECTION & SPLIT VERIFICATION TESTS
# =============================================================================

def test_leakage_detection_status():
    """Verify evaluation/leakage_report.json reports zero leakage across all checks."""
    leak_path = EVAL_DIR / "leakage_report.json"
    with open(leak_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["phase"] == 10
    assert data["leakage_status"] == "PASSED_ZERO_LEAKAGE"
    assert data["leakage_detected"] is False
    assert len(data["leakage_findings"]) == 0

    checks = data["checks_conducted"]
    assert checks["participant_overlap_across_splits"] == "VERIFIED_DISJOINT"
    assert checks["audio_recording_duplication_across_splits"] == "VERIFIED_DISJOINT"
    assert checks["retinal_image_duplication_across_splits"] == "VERIFIED_DISJOINT"
    assert checks["preprocessors_fitted_on_training_set_only"] == "VERIFIED_STRICT_TRAIN_ONLY"
    assert checks["feature_selection_without_test_data"] == "VERIFIED_NO_TEST_LEAKAGE"
    assert checks["target_leakage_from_future_outcomes"] == "VERIFIED_CROSS_SECTIONAL_ONLY"

    # Verify per-modality disjointness
    for mod, summary in data["participant_splits"].items():
        assert summary["participant_disjoint"] is True, f"Participant overlap in {mod}!"
        assert summary["train_participants"] > 0
        assert summary["val_participants"] > 0
        assert summary["test_participants"] > 0


# =============================================================================
# 4. MISSING MODALITY ANALYSIS TESTS
# =============================================================================

def test_missing_modality_analysis_schema():
    """Verify evaluation/missing_modality_analysis.json covers all scenarios and gate adaptation."""
    path = EVAL_DIR / "missing_modality_analysis.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["phase"] == 10
    assert data["clinical_claim"] is False
    assert "baseline_auc" in data
    assert "scenarios" in data
    assert "recommendations" in data

    scenarios = data["scenarios"]
    # Check baseline
    assert "all_5_modalities" in scenarios

    # Check 1-missing scenarios
    for m in ALL_MODALITIES:
        key = f"missing_{m}"
        assert key in scenarios, f"Missing scenario '{key}' in missing_modality_analysis.json"
        res = scenarios[key]
        assert "auc_drop" in res
        assert "mean_gate_weights" in res
        # Absent modality should receive zero attention gate weight
        assert np.isclose(res["mean_gate_weights"][m], 0.0, atol=1e-3)

    # Check minimum required modalities recommendation
    rec = data["recommendations"]
    assert rec["minimum_required_modalities"] >= 2
    assert "uncertainty_policy" in rec


# =============================================================================
# 5. ROBUSTNESS TESTS
# =============================================================================

def test_pipeline_robustness_out_of_range_inputs():
    """Verify pipeline degrades gracefully on physiological out-of-range inputs."""
    payload = {
        "participant_id": "TEST-ROB-001",
        "age": 65.0,
        "olfactory": {"available": True, "score": 999, "max_score": 40},
        "rbd": {"available": True, "rbdsq_total": -20},
        "motor": {"available": True, "features": {"gait_speed_m_per_s": 1.05}},
    }
    res = run_mpf_pipeline(payload)
    assert res["status"] in ["partial_success", "success"]
    assert res["modality_results"]["olfactory"]["status"] == "failed_qc"
    assert res["modality_results"]["rbd"]["status"] == "failed_qc"
    assert res["fusion"]["risk_score"] is not None
    assert 0.0 <= res["fusion"]["risk_score"] <= 1.0


def test_pipeline_robustness_missing_files():
    """Verify pipeline does not crash when audio or retinal files do not exist."""
    payload = {
        "participant_id": "TEST-ROB-002",
        "voice": {"available": True, "audio_file": "missing_audio_test.wav"},
        "retina": {"available": True, "image_path": "missing_image_test.png"},
    }
    res = run_mpf_pipeline(payload)
    assert res["status"] in ["partial_success", "success", "failed"]
    # Modalities should report error or missing, not raise uncaught exception
    assert res["modality_results"]["voice"]["status"] in ["error", "missing", "failed_qc"]
    assert res["modality_results"]["retina"]["status"] in ["error", "missing", "failed_qc"]


def test_pipeline_robustness_empty_input():
    """Verify empty dictionary input fails cleanly with errors captured."""
    res = run_mpf_pipeline({})
    assert res["status"] == "failed"
    assert len(res["errors"]) > 0


# =============================================================================
# 6. REPRODUCIBILITY TESTS
# =============================================================================

def test_reproducibility_deterministic_outputs():
    """Verify identical risk scores and gate weights across repeated runs with seed=42."""
    payload = {
        "participant_id": "TEST-REPRO-001",
        "age": 70.0,
        "sex": "male",
        "olfactory": {"available": True, "score": 22},
        "rbd": {"available": True, "rbdsq_total": 8},
        "motor": {"available": True, "features": {"gait_speed_m_per_s": 0.95}},
    }

    res1 = run_mpf_pipeline(payload)
    res2 = run_mpf_pipeline(payload)

    score1 = res1["fusion"]["risk_score"]
    score2 = res2["fusion"]["risk_score"]
    assert score1 is not None and score2 is not None
    assert np.isclose(score1, score2, atol=1e-5), f"Non-deterministic scores: {score1} vs {score2}"

    w1 = res1["fusion"]["gate_weights"]
    w2 = res2["fusion"]["gate_weights"]
    for m in ALL_MODALITIES:
        assert np.isclose(w1[m], w2[m], atol=1e-5), f"Non-deterministic gate weights for {m}: {w1[m]} vs {w2[m]}"


# =============================================================================
# 7. FINAL EVALUATION DOCUMENT TESTS
# =============================================================================

def test_final_evaluation_markdown_sections():
    """Verify evaluation/FINAL_EVALUATION.md contains all 14 required sections."""
    md_path = EVAL_DIR / "FINAL_EVALUATION.md"
    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")

    required_sections = [
        "## 1. Executive Summary",
        "## 2. Datasets Used",
        "## 3. Experiment Type",
        "## 4. Modality Performance",
        "## 5. Fusion Performance Comparison",
        "## 6. Missing-Modality Analysis",
        "## 7. Leakage Report",
        "## 8. Robustness Report",
        "## 9. Reproducibility Report",
        "## 10. Explainability & Interpretability Summary",
        "## 11. Major Limitations",
        "## 12. What Claims Are Supported",
        "## 13. What Claims Are NOT Supported",
        "## 14. Future Validation Requirements",
    ]
    for sec in required_sections:
        assert sec in content, f"Missing section '{sec}' in FINAL_EVALUATION.md"

    assert "prototype_simulation" in content
    assert "ZERO clinical validity" in content


# =============================================================================
# 8. DASHBOARD API SMOKE TESTS
# =============================================================================

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_dashboard_api_health_endpoint(client):
    """Smoke test /api/health."""
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ["ok", "degraded"]
    assert "models_loaded" in data


def test_dashboard_api_analyze_smoke(client):
    """Smoke test /api/analyze with synthetic payload."""
    payload = {
        "participant_id": "SMOKE-TEST-001",
        "age": 67.0,
        "sex": "female",
        "olfactory": {"available": True, "score": 24, "max_score": 40},
        "rbd": {"available": True, "rbdsq_total": 5},
    }
    resp = client.post("/api/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "participant_id" in data
    assert "individual_modalities" in data
    assert "fusion" in data
    assert "explainability" in data
    assert "risk_score" in data["fusion"]
