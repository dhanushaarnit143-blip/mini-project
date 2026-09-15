"""
MPF-PD Phase 7 — XAI Test Suite.

Tests verify:
  1. SHAP explainer loads the actual fusion model artifacts.
  2. Explanation object contains all required keys.
  3. Risk score is bounded in [0, 1].
  4. Missing modalities are listed correctly.
  5. SHAP values are finite.
  6. Modality-level aggregation sums approximately match total contribution.
  7. Explainer does not crash when one or more modalities are missing.
  8. Synthetic fixtures are clearly labeled.
  9. Global importance JSON is valid and contains required fields.
 10. Feature mapping is correct and complete.
 11. SHAP base value is finite if available.
 12. All features in the mapping account for FUSED_DIM indices.

IMPORTANT: All test fixtures are synthetic and clearly labeled.
No clinical claims are made. No real participant data is used.
"""

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

# Ensure project root on path
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def explainer():
    """Load MPFSHAPExplainer once for the test module."""
    from src.explainability.shap_explainer import MPFSHAPExplainer
    return MPFSHAPExplainer()


def _make_full_input() -> Dict[str, Any]:
    """
    Synthetic test fixture — ALL modalities present.
    Clearly labeled: used ONLY for software testing.
    """
    return {
        "olfactory": {
            "total_score": 22.0,
            "pct_correct": 0.55,
            "response_time_mean": 5.1,
            "n_errors": 3,
            "error_pattern_flags": 1,
        },
        "rbd": {
            "rbdsq_total": 8.0,
            "above_cutoff_flag": 1.0,
            "high_weight_item_flags": 2.0,
            "item_1": 1, "item_2": 1, "item_3": 1, "item_4": 1,
            "item_5": 0, "item_6": 1, "item_7": 1, "item_8": 0,
            "item_9": 1, "item_10": 1, "item_11": 0, "item_12": 0, "item_13": 0,
        },
        "voice": {
            "jitter_pct": 0.0085, "jitter_abs": 0.00006,
            "jitter_rap": 0.004, "jitter_ppq5": 0.0039, "jitter_ddp": 0.012,
            "shimmer": 0.065, "shimmer_db": 0.61, "shimmer_apq3": 0.037,
            "shimmer_apq5": 0.040, "shimmer_apq11": 0.065, "shimmer_dda": 0.11,
            "nhr": 0.030, "hnr": 14.5, "rpde": 0.48, "dfa": 0.79, "ppe": 0.23,
        },
        "motor": {
            "gait_speed_m_per_s": 0.88, "cadence_steps_per_min": 93.0,
            "stride_interval_mean_s": 1.18, "stride_interval_cv_pct": 3.1,
            "step_regularity": 0.82, "symmetry_index_pct": 5.2,
            "accel_variance": 0.041, "stance_swing_ratio": 1.85,
        },
        "retina": {
            "vessel_density": 0.062,
            "mean_vessel_diameter_px": 2.88,
            "vessel_tortuosity_index": 1.15,
            "branch_count": 48,
            "branch_point_density": 0.012,
            "endpoint_count": 22,
            "peripapillary_vessel_density": 0.070,
            "peripapillary_branch_count": 20,
            "macular_vessel_density": 0.055,
            "foveal_avascular_zone_area_px": 310.0,
            "optic_disc_detected": 1,
            "macula_detected": 1,
        },
        "age": 71.0,
        "sex": "male",
    }


def _make_partial_input(missing_modalities: List[str]) -> Dict[str, Any]:
    """
    Synthetic test fixture — some modalities absent.
    Clearly labeled: used ONLY for software testing.
    """
    full = _make_full_input()
    for mod in missing_modalities:
        full[mod] = {}  # absent
    return full


# ---------------------------------------------------------------------------
# Test Group 1: Artifact loading
# ---------------------------------------------------------------------------

class TestArtifactLoading:
    """Verify that the SHAP explainer loads actual trained artifacts."""

    def test_explainer_loads_without_error(self, explainer):
        """SHAP explainer must load without raising FileNotFoundError."""
        assert explainer is not None

    def test_classifier_loaded(self, explainer):
        """Classifier must be loaded and have predict_proba."""
        assert hasattr(explainer.classifier, "predict_proba")

    def test_fusion_net_loaded(self, explainer):
        """Fusion encoder must be loaded."""
        import torch.nn as nn
        assert explainer.fusion_net is not None
        assert isinstance(explainer.fusion_net, nn.Module)

    def test_preprocessors_loaded(self, explainer):
        """Preprocessor bundle must contain expected keys."""
        preps = explainer.preprocessors
        assert "modality_imputers" in preps
        assert "modality_scalers" in preps
        assert "demo_imputer" in preps
        assert "demo_scaler" in preps
        assert "modality_feature_cols" in preps

    def test_explanation_method_is_shap_tree(self, explainer):
        """XGBoost classifier should use shap_tree."""
        assert explainer.explanation_method == "shap_tree", (
            f"Expected shap_tree, got {explainer.explanation_method}"
        )

    def test_missing_artifact_raises_file_not_found(self):
        """Explainer must raise FileNotFoundError if classifier is missing."""
        from src.explainability.shap_explainer import MPFSHAPExplainer
        with pytest.raises(FileNotFoundError, match="Phase 7 blocked"):
            MPFSHAPExplainer(clf_path="models/fusion/nonexistent.joblib")


# ---------------------------------------------------------------------------
# Test Group 2: Fused representation builder
# ---------------------------------------------------------------------------

class TestFusedRepresentationBuilder:
    """Verify that the encoder produces valid 45-dim representations."""

    def test_full_modalities_produces_correct_shape(self, explainer):
        inputs = _make_full_input()
        fused_matrix, _, _ = explainer._build_fused_repr_from_raw([inputs])
        assert fused_matrix.shape == (1, 45), f"Got shape {fused_matrix.shape}"

    def test_fused_values_are_finite(self, explainer):
        inputs = _make_full_input()
        fused_matrix, _, _ = explainer._build_fused_repr_from_raw([inputs])
        assert np.all(np.isfinite(fused_matrix)), "Fused representation contains non-finite values"

    def test_batch_of_inputs_produces_correct_shape(self, explainer):
        inputs_list = [_make_full_input(), _make_full_input()]
        fused_matrix, _, _ = explainer._build_fused_repr_from_raw(inputs_list)
        assert fused_matrix.shape == (2, 45)

    def test_presence_flags_correct_for_full_input(self, explainer):
        inputs = _make_full_input()
        _, _, presence_list = explainer._build_fused_repr_from_raw([inputs])
        presence = presence_list[0]
        from src.fusion.dataset import MODALITIES
        for mod in MODALITIES:
            assert presence[mod] is True, f"Expected {mod} to be present"

    def test_presence_flags_correct_for_missing_modality(self, explainer):
        inputs = _make_partial_input(["retina"])
        _, _, presence_list = explainer._build_fused_repr_from_raw([inputs])
        presence = presence_list[0]
        assert presence["retina"] is False
        assert presence["olfactory"] is True


# ---------------------------------------------------------------------------
# Test Group 3: SHAP value computation
# ---------------------------------------------------------------------------

class TestSHAPValueComputation:
    """Verify SHAP value properties."""

    def test_shap_values_have_correct_shape(self, explainer):
        inputs = _make_full_input()
        fused_matrix, _, _ = explainer._build_fused_repr_from_raw([inputs])
        shap_vals = explainer.compute_shap_values(fused_matrix)
        assert shap_vals.shape == (1, 45), f"Expected (1, 45), got {shap_vals.shape}"

    def test_shap_values_are_finite(self, explainer):
        inputs = _make_full_input()
        fused_matrix, _, _ = explainer._build_fused_repr_from_raw([inputs])
        shap_vals = explainer.compute_shap_values(fused_matrix)
        assert np.all(np.isfinite(shap_vals)), "SHAP values contain non-finite values"

    def test_shap_values_for_batch(self, explainer):
        inputs_list = [_make_full_input(), _make_partial_input(["voice"])]
        fused_matrix, _, _ = explainer._build_fused_repr_from_raw(inputs_list)
        shap_vals = explainer.compute_shap_values(fused_matrix)
        assert shap_vals.shape == (2, 45)
        assert np.all(np.isfinite(shap_vals))

    def test_shap_sum_approximates_risk_score_shift(self, explainer):
        """
        XGBoost TreeExplainer SHAP consistency check.

        XGBoost's TreeExplainer computes SHAP values in **log-odds (margin) space**.
        The consistency property is:
            sigmoid(base_value_logit + sum(shap_values)) ≈ predict_proba(x)

        The base_value from TreeExplainer is the mean logit prediction on training data.
        shap_values sum to the per-sample contribution in logit space.
        """
        import scipy.special
        inputs = _make_full_input()
        fused_matrix, _, _ = explainer._build_fused_repr_from_raw([inputs])
        shap_vals = explainer.compute_shap_values(fused_matrix)
        base_val = float(explainer._get_shap_explainer().expected_value)
        prob = float(explainer.classifier.predict_proba(fused_matrix)[0, 1])
        shap_sum = float(np.sum(shap_vals[0]))

        # XGBoost SHAP is in logit space; apply sigmoid to reconstruct probability
        reconstructed_prob = float(scipy.special.expit(base_val + shap_sum))
        assert abs(reconstructed_prob - prob) < 0.05, (
            f"sigmoid(base + SHAP_sum)={reconstructed_prob:.4f} far from "
            f"predict_proba={prob:.4f} (tolerance 0.05)"
        )

    def test_wrong_input_shape_raises(self, explainer):
        """compute_shap_values should raise ValueError for wrong shape."""
        with pytest.raises(ValueError, match="Expected fused_matrix"):
            bad_input = np.zeros((3, 20))  # wrong dim
            explainer.compute_shap_values(bad_input)


# ---------------------------------------------------------------------------
# Test Group 4: Risk score bounds
# ---------------------------------------------------------------------------

class TestRiskScoreBounds:
    """Risk score must always be in [0, 1]."""

    @pytest.mark.parametrize("missing", [
        [],
        ["retina"],
        ["voice", "motor"],
        ["olfactory", "rbd", "voice"],
        ["olfactory", "rbd", "voice", "motor"],  # only retina present
    ])
    def test_risk_score_in_unit_interval(self, explainer, missing):
        from src.explainability.local_explanation import explain_single
        inputs = _make_partial_input(missing)
        exp = explain_single(inputs, participant_id="TEST-001", explainer=explainer, is_synthetic=True)
        score = exp["risk_score"]
        assert 0.0 <= score <= 1.0, f"Risk score {score} outside [0, 1]"


# ---------------------------------------------------------------------------
# Test Group 5: Local explanation schema
# ---------------------------------------------------------------------------

REQUIRED_EXPLANATION_KEYS = {
    "participant_id",
    "risk_score",
    "experiment_type",
    "synthetic_example",
    "explanation_method",
    "important_modalities",
    "important_features",
    "positive_contributors",
    "negative_contributors",
    "missing_modalities",
    "missing_modality_notes",
    "modality_presence",
    "gate_weights",
    "shap_base_value",
    "shap_sum",
    "warnings",
    "disclaimer",
}

class TestLocalExplanationSchema:
    """Explanation objects must conform to Phase 7 schema."""

    @pytest.fixture(scope="class")
    def full_explanation(self, explainer):
        from src.explainability.local_explanation import explain_single
        return explain_single(
            _make_full_input(),
            participant_id="SYNTH-FULL-001",
            explainer=explainer,
            is_synthetic=True,
        )

    @pytest.fixture(scope="class")
    def missing_retina_explanation(self, explainer):
        from src.explainability.local_explanation import explain_single
        return explain_single(
            _make_partial_input(["retina"]),
            participant_id="SYNTH-NORET-001",
            explainer=explainer,
            is_synthetic=True,
        )

    def test_required_keys_present(self, full_explanation):
        missing_keys = REQUIRED_EXPLANATION_KEYS - set(full_explanation.keys())
        assert not missing_keys, f"Missing required keys: {missing_keys}"

    def test_risk_score_type(self, full_explanation):
        assert isinstance(full_explanation["risk_score"], float)

    def test_risk_score_bounded(self, full_explanation):
        assert 0.0 <= full_explanation["risk_score"] <= 1.0

    def test_synthetic_example_flag(self, full_explanation):
        assert full_explanation["synthetic_example"] is True

    def test_experiment_type_is_prototype(self, full_explanation):
        assert full_explanation["experiment_type"] == "prototype_simulation"

    def test_missing_modalities_empty_for_full_input(self, full_explanation):
        assert full_explanation["missing_modalities"] == []

    def test_missing_modalities_listed_correctly(self, missing_retina_explanation):
        assert "retina" in missing_retina_explanation["missing_modalities"]

    def test_missing_modality_notes_present(self, missing_retina_explanation):
        notes = missing_retina_explanation["missing_modality_notes"]
        assert any("retina" in note.lower() for note in notes), (
            "Missing modality note for 'retina' not found"
        )

    def test_modality_presence_correct(self, missing_retina_explanation):
        presence = missing_retina_explanation["modality_presence"]
        assert presence["retina"] is False
        assert presence["olfactory"] is True

    def test_important_features_list(self, full_explanation):
        feats = full_explanation["important_features"]
        assert isinstance(feats, list)
        assert len(feats) > 0
        # Each feature must have required sub-keys
        for feat in feats:
            assert "feature_name" in feat
            assert "shap_value" in feat
            assert "direction" in feat
            assert math.isfinite(feat["shap_value"])

    def test_important_modalities_list(self, full_explanation):
        mods = full_explanation["important_modalities"]
        assert isinstance(mods, list)
        assert len(mods) > 0
        for m in mods:
            assert "modality" in m
            assert "importance" in m
            assert "direction" in m
            assert "missing" in m

    def test_positive_contributors_direction(self, full_explanation):
        for feat in full_explanation["positive_contributors"]:
            assert feat["shap_value"] > 0, (
                f"Positive contributor has non-positive SHAP: {feat['shap_value']}"
            )

    def test_negative_contributors_direction(self, full_explanation):
        for feat in full_explanation["negative_contributors"]:
            assert feat["shap_value"] < 0, (
                f"Negative contributor has non-negative SHAP: {feat['shap_value']}"
            )

    def test_warnings_are_non_empty(self, full_explanation):
        assert len(full_explanation["warnings"]) >= 2

    def test_disclaimer_present(self, full_explanation):
        assert "clinical" in full_explanation["disclaimer"].lower()

    def test_gate_weights_sum_approximately_one(self, full_explanation):
        gw = full_explanation["gate_weights"]
        total = sum(gw.values())
        assert abs(total - 1.0) < 0.05, (
            f"Gate weights sum {total:.4f} not close to 1.0"
        )


# ---------------------------------------------------------------------------
# Test Group 6: Missing modality robustness
# ---------------------------------------------------------------------------

class TestMissingModalityRobustness:
    """Explainer must not crash with any combination of missing modalities."""

    @pytest.mark.parametrize("missing", [
        ["olfactory"],
        ["rbd"],
        ["voice"],
        ["motor"],
        ["retina"],
        ["olfactory", "retina"],
        ["voice", "motor", "retina"],
        ["rbd", "voice", "motor"],
        ["olfactory", "rbd", "motor", "retina"],  # only voice present
    ])
    def test_no_crash_with_missing_modalities(self, explainer, missing):
        from src.explainability.local_explanation import explain_single
        inputs = _make_partial_input(missing)
        # Must not raise
        exp = explain_single(inputs, participant_id="TEST-MISS-001", explainer=explainer, is_synthetic=True)
        assert exp is not None
        for mod in missing:
            assert mod in exp["missing_modalities"], (
                f"'{mod}' should be in missing_modalities"
            )

    def test_all_modalities_missing_returns_safe_response(self, explainer):
        """When all modalities are missing, explainer should handle gracefully."""
        from src.explainability.local_explanation import explain_single
        inputs = {"age": 65.0, "sex": "female"}
        for mod in ["olfactory", "rbd", "voice", "motor", "retina"]:
            inputs[mod] = {}
        exp = explain_single(inputs, participant_id="TEST-ALL-MISS", explainer=explainer, is_synthetic=True)
        assert exp is not None
        assert 0.0 <= exp["risk_score"] <= 1.0


# ---------------------------------------------------------------------------
# Test Group 7: Modality-level aggregation
# ---------------------------------------------------------------------------

class TestModalityAggregation:
    """Modality importance percentages must sum to ~100%."""

    def test_modality_percent_contributions_sum_to_100(self, explainer):
        inputs = _make_full_input()
        fused_matrix, gate_weights_list, _ = explainer._build_fused_repr_from_raw([inputs])
        shap_vals = explainer.compute_shap_values(fused_matrix)
        modality_importance = explainer.aggregate_modality_importance(
            shap_vals, gate_weights_list
        )
        total_pct = sum(m["percent_contribution"] for m in modality_importance)
        assert abs(total_pct - 100.0) < 1.0, (
            f"Modality % contributions sum to {total_pct:.2f}%, expected ~100%"
        )

    def test_modality_mean_abs_shap_non_negative(self, explainer):
        inputs = _make_full_input()
        fused_matrix, gate_weights_list, _ = explainer._build_fused_repr_from_raw([inputs])
        shap_vals = explainer.compute_shap_values(fused_matrix)
        modality_importance = explainer.aggregate_modality_importance(shap_vals, gate_weights_list)
        for entry in modality_importance:
            assert entry["mean_abs_shap"] >= 0.0, (
                f"Negative mean_abs_shap for {entry['modality']}: {entry['mean_abs_shap']}"
            )

    def test_all_five_modalities_represented(self, explainer):
        from src.fusion.dataset import MODALITIES as MODS
        inputs = _make_full_input()
        fused_matrix, gate_weights_list, _ = explainer._build_fused_repr_from_raw([inputs])
        shap_vals = explainer.compute_shap_values(fused_matrix)
        modality_importance = explainer.aggregate_modality_importance(shap_vals, gate_weights_list)
        reported_modalities = {m["modality"] for m in modality_importance}
        for mod in MODS:
            assert mod in reported_modalities, f"Modality '{mod}' missing from importance list"


# ---------------------------------------------------------------------------
# Test Group 8: Feature mapping correctness
# ---------------------------------------------------------------------------

class TestFeatureMapping:
    """Feature mapping must cover all 45 indices exactly."""

    def test_feature_names_count(self):
        from src.explainability.modality_mapping import FUSED_FEATURE_NAMES, FUSED_DIM
        assert len(FUSED_FEATURE_NAMES) == FUSED_DIM, (
            f"Expected {FUSED_DIM} feature names, got {len(FUSED_FEATURE_NAMES)}"
        )

    def test_feature_mapping_covers_all_indices(self):
        from src.explainability.modality_mapping import get_feature_mapping, FUSED_DIM
        mapping = get_feature_mapping()
        all_indices = set()
        for indices in mapping.values():
            all_indices.update(indices)
        expected = set(range(FUSED_DIM))
        assert all_indices == expected, (
            f"Mapping missing indices: {expected - all_indices}; "
            f"extra indices: {all_indices - expected}"
        )

    def test_get_feature_group_gated_range(self):
        from src.explainability.modality_mapping import get_feature_group
        for i in range(32):
            assert get_feature_group(i) == "fused_gated_representation"

    def test_get_feature_group_demo_range(self):
        from src.explainability.modality_mapping import get_feature_group
        for i in range(32, 40):
            assert get_feature_group(i) == "demographic_covariates"

    def test_get_feature_group_presence_flags(self):
        from src.explainability.modality_mapping import get_feature_group, MODALITIES
        expected_groups = [f"presence_{m}" for m in MODALITIES]
        for i, idx in enumerate(range(40, 45)):
            assert get_feature_group(idx) == expected_groups[i]

    def test_out_of_range_index_returns_unknown(self):
        from src.explainability.modality_mapping import get_feature_group
        assert get_feature_group(99) == "unknown"
        assert get_feature_group(-1) == "unknown"


# ---------------------------------------------------------------------------
# Test Group 9: Global importance JSON
# ---------------------------------------------------------------------------

class TestGlobalImportanceJSON:
    """Global importance output JSON must be valid and complete."""

    @pytest.fixture(scope="class")
    def global_data(self, explainer):
        from src.explainability.global_importance import compute_global_importance
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            tmp_path = f.name
        try:
            data = compute_global_importance(explainer=explainer, n_samples=30, output_path=tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        return data

    def test_required_keys(self, global_data):
        required = {
            "phase", "explanation_method", "dataset_used", "experiment_type",
            "global_feature_importance", "modality_importance", "limitations",
            "clinical_claim", "n_samples_used"
        }
        missing = required - set(global_data.keys())
        assert not missing, f"Missing keys in global importance: {missing}"

    def test_phase_is_7(self, global_data):
        assert global_data["phase"] == 7

    def test_experiment_type_is_prototype(self, global_data):
        assert global_data["experiment_type"] == "prototype_simulation"

    def test_clinical_claim_is_false(self, global_data):
        assert global_data["clinical_claim"] is False

    def test_global_feature_importance_has_45_entries(self, global_data):
        assert len(global_data["global_feature_importance"]) == 45

    def test_feature_importance_values_non_negative(self, global_data):
        for feat in global_data["global_feature_importance"]:
            assert feat["mean_abs_shap"] >= 0.0

    def test_feature_importance_values_finite(self, global_data):
        for feat in global_data["global_feature_importance"]:
            assert math.isfinite(feat["mean_abs_shap"])

    def test_limitations_present(self, global_data):
        assert isinstance(global_data["limitations"], list)
        assert len(global_data["limitations"]) > 0

    def test_synthetic_flag_set(self, global_data):
        assert global_data["synthetic_example"] is True


# ---------------------------------------------------------------------------
# Test Group 10: Synthetic fixture labeling
# ---------------------------------------------------------------------------

class TestSyntheticFixtureLabeling:
    """Synthetic fixtures must be explicitly labeled as such."""

    def test_local_explanation_synthetic_flag(self, explainer):
        from src.explainability.local_explanation import explain_single
        exp = explain_single(
            _make_full_input(),
            participant_id="SYNTH-TEST",
            explainer=explainer,
            is_synthetic=True,
        )
        assert exp["synthetic_example"] is True

    def test_synthetic_warning_in_warnings(self, explainer):
        from src.explainability.local_explanation import explain_single
        exp = explain_single(
            _make_full_input(),
            participant_id="SYNTH-WARN",
            explainer=explainer,
            is_synthetic=True,
        )
        synthetic_warned = any("synthetic" in w.lower() for w in exp["warnings"])
        assert synthetic_warned, "Synthetic fixture warning not present in explanation warnings"

    def test_non_synthetic_flag_respected(self, explainer):
        from src.explainability.local_explanation import explain_single
        exp = explain_single(
            _make_full_input(),
            participant_id="NOTSYNTH-001",
            explainer=explainer,
            is_synthetic=False,
        )
        assert exp["synthetic_example"] is False
