"""
MPF-PD Phase 7 — Local (Individual) Prediction Explanation.

Generates a standardised explanation object for a single participant sample.
The explanation includes:
  - Risk score from the trained XGBoost classifier.
  - SHAP values for every fused feature.
  - Top positive and negative contributors.
  - Modality-level importance breakdown.
  - Explicit missing modality notes.
  - Uncertainty warnings for missing modalities.

RESEARCH PROTOTYPE ONLY. Not a diagnostic device. No clinical claims.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.explainability.shap_explainer import MPFSHAPExplainer
from src.explainability.modality_mapping import (
    FUSED_FEATURE_NAMES,
    MODALITIES,
    get_feature_group,
    get_modality_for_presence_flag,
    FUSED_PRESENCE_RANGE,
)

logger = logging.getLogger("mpf.explainability.local_explanation")

OUTPUT_PATH = "evaluation/xai_sample_explanation.json"
TOP_K_FEATURES = 15  # number of top features to include in explanation


def explain_single(
    inputs: Dict[str, Any],
    participant_id: str,
    explainer: Optional[MPFSHAPExplainer] = None,
    top_k: int = TOP_K_FEATURES,
    is_synthetic: bool = False,
) -> Dict[str, Any]:
    """
    Generate a standardised explanation for a single participant input.

    Args:
        inputs:         Input dict in predict_fusion() format.
        participant_id: Pseudonymous participant identifier.
        explainer:      Pre-loaded MPFSHAPExplainer. Loads defaults if None.
        top_k:          Number of top features to include.
        is_synthetic:   Set True if inputs are a clearly-labeled synthetic fixture.

    Returns:
        Standardised explanation dict conforming to Phase 7 schema.
    """
    if explainer is None:
        explainer = MPFSHAPExplainer()

    warnings: List[str] = [
        "RESEARCH PROTOTYPE: Risk score is an investigational estimate only.",
        "NOT FOR CLINICAL DIAGNOSIS: No clinical validity is claimed.",
    ]

    if explainer.experiment_type == "prototype_simulation":
        warnings.append(
            "MODEL TRAINED IN SIMULATION MODE: Explanations derived from "
            "synthetic fixture training. No clinical validity."
        )

    if is_synthetic:
        warnings.append(
            "SYNTHETIC INPUT: This explanation was generated from a clearly-labeled "
            "synthetic software test fixture, not real participant data."
        )

    # ------------------------------------------------------------------
    # 1. Build fused representation for this one sample
    # ------------------------------------------------------------------
    fused_matrix, gate_weights_list, presence_flags_list = (
        explainer._build_fused_repr_from_raw([inputs])
    )
    gate_weights = gate_weights_list[0]
    presence_flags = presence_flags_list[0]

    # ------------------------------------------------------------------
    # 2. Get risk score
    # ------------------------------------------------------------------
    clf = explainer.classifier
    if hasattr(clf, "predict_proba"):
        prob = float(clf.predict_proba(fused_matrix)[0, 1])
    else:
        prob = float(clf.predict(fused_matrix)[0])
    risk_score = round(float(np.clip(prob, 0.0, 1.0)), 4)

    # ------------------------------------------------------------------
    # 3. Compute SHAP values for this sample
    # ------------------------------------------------------------------
    shap_values = explainer.compute_shap_values(fused_matrix)  # (1, 45)
    sv = shap_values[0]  # (45,)

    # Validate finiteness
    if not np.all(np.isfinite(sv)):
        warnings.append(
            "Some SHAP values were non-finite and replaced with 0.0. "
            "Explanation reliability is reduced."
        )
        sv = np.where(np.isfinite(sv), sv, 0.0)

    # ------------------------------------------------------------------
    # 4. Build per-feature explanation list
    # ------------------------------------------------------------------
    feature_shap_list = []
    for idx, fname in enumerate(FUSED_FEATURE_NAMES):
        shap_val = float(sv[idx])
        feature_shap_list.append(
            {
                "feature_name": fname,
                "feature_index": idx,
                "modality_group": get_feature_group(idx),
                "shap_value": round(shap_val, 6),
                "feature_value": round(float(fused_matrix[0, idx]), 4),
                "direction": "positive" if shap_val > 0 else "negative",
            }
        )

    # Sort by absolute SHAP value
    feature_shap_sorted = sorted(feature_shap_list, key=lambda x: -abs(x["shap_value"]))
    important_features = feature_shap_sorted[:top_k]
    positive_contributors = [f for f in feature_shap_sorted if f["shap_value"] > 0][:top_k]
    negative_contributors = [f for f in feature_shap_sorted if f["shap_value"] < 0][:top_k]

    # ------------------------------------------------------------------
    # 5. Modality-level importance (using gate weights for gated part)
    # ------------------------------------------------------------------
    modality_importance_list = explainer.aggregate_modality_importance(
        shap_values, [gate_weights]
    )

    important_modalities = []
    for entry in modality_importance_list:
        mod_name = entry["modality"]
        # Determine if this modality was missing
        is_missing = False
        if mod_name in MODALITIES:
            is_missing = not presence_flags.get(mod_name, True)
        importance = entry["mean_abs_shap"]
        direction = _determine_direction(mod_name, sv, gate_weights, presence_flags)
        important_modalities.append(
            {
                "modality": mod_name,
                "importance": round(importance, 6),
                "percent_contribution": entry["percent_contribution"],
                "direction": direction,
                "missing": is_missing,
            }
        )

    # ------------------------------------------------------------------
    # 6. Missing modality notes
    # ------------------------------------------------------------------
    missing_modalities = [m for m in MODALITIES if not presence_flags.get(m, True)]
    missing_notes: List[str] = []
    for mod in missing_modalities:
        warnings.append(
            f"Modality '{mod}' was ABSENT: gating unit applied a learned missing token. "
            f"Uncertainty is increased. Requires clinician review if used in future clinical studies."
        )
        missing_notes.append(
            f"{mod.capitalize()} input missing; model relied more heavily on available modalities. "
            f"Missing modalities increase uncertainty in the research risk estimate."
        )

    if not missing_modalities:
        missing_notes.append("All modalities present. Missingness-related uncertainty is minimal.")

    # ------------------------------------------------------------------
    # 7. Presence flag SHAP notes
    # ------------------------------------------------------------------
    presence_shap_notes: List[str] = []
    for i, mod in enumerate(MODALITIES):
        pres_idx = FUSED_PRESENCE_RANGE[i]
        pres_sv = float(sv[pres_idx])
        if abs(pres_sv) > 0.001:
            direction_word = "increased" if pres_sv > 0 else "decreased"
            missing_word = "absent" if not presence_flags.get(mod, True) else "present"
            presence_shap_notes.append(
                f"Presence flag for '{mod}' (index {pres_idx}, value "
                f"{'0 — MISSING' if missing_word == 'absent' else '1 — present'}) "
                f"{direction_word} the risk estimate by SHAP={pres_sv:+.4f}."
            )

    if presence_shap_notes:
        warnings.extend(presence_shap_notes)

    # ------------------------------------------------------------------
    # 8. Assemble explanation object
    # ------------------------------------------------------------------
    explanation = {
        "participant_id": participant_id,
        "risk_score": risk_score,
        "experiment_type": explainer.experiment_type,
        "synthetic_example": is_synthetic,
        "explanation_method": explainer.explanation_method,
        "important_modalities": important_modalities,
        "important_features": important_features,
        "positive_contributors": positive_contributors,
        "negative_contributors": negative_contributors,
        "missing_modalities": missing_modalities,
        "missing_modality_notes": missing_notes,
        "modality_presence": {m: bool(presence_flags.get(m, True)) for m in MODALITIES},
        "gate_weights": {m: round(float(gate_weights.get(m, 0.2)), 4) for m in MODALITIES},
        "shap_base_value": (
            round(float(explainer._get_shap_explainer().expected_value), 6)
            if explainer.explanation_method == "shap_tree"
            else None
        ),
        "shap_sum": round(float(np.sum(sv)), 6),
        "warnings": warnings,
        "disclaimer": (
            "This explanation is a research prototype output only. "
            "It must not be used for clinical diagnosis. "
            "Requires clinician review if used in future clinical studies. "
            "All risk scores are research prototype estimates, not clinical findings."
        ),
    }

    return explanation


def _determine_direction(
    modality: str,
    sv: np.ndarray,
    gate_weights: Dict[str, float],
    presence_flags: Dict[str, bool],
) -> str:
    """
    Determine net SHAP direction for a modality group.

    For presence flags: direction from the corresponding flag SHAP value.
    For the gated representation: direction inferred from the gate-weighted
    sum of the gated vector SHAP values.
    For demographics: direction from the demo encoder SHAP values.
    """
    from src.explainability.modality_mapping import (
        FUSED_GATED_MODALITY_RANGE,
        FUSED_DEMO_RANGE,
    )

    if modality == "demographic_covariates":
        net = float(np.sum(sv[FUSED_DEMO_RANGE]))
    elif modality in MODALITIES:
        # Gate-weighted fraction of the gated representation
        total_gate = sum(gate_weights.values()) or 1.0
        norm_w = gate_weights.get(modality, 0.2) / total_gate
        gated_net = float(np.sum(sv[FUSED_GATED_MODALITY_RANGE]))
        # Plus the presence flag direct contribution
        idx = FUSED_PRESENCE_RANGE[MODALITIES.index(modality)]
        pres_net = float(sv[idx])
        net = norm_w * gated_net + pres_net
    else:
        net = 0.0

    if net > 1e-6:
        return "positive"
    elif net < -1e-6:
        return "negative"
    else:
        return "mixed"


def save_sample_explanation(
    explanation: Dict[str, Any],
    output_path: str = OUTPUT_PATH,
) -> None:
    """Write explanation dict to JSON file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(explanation, f, indent=2)
    logger.info("Sample explanation written to %s", output_path)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Synthetic test fixture — clearly labeled
    SYNTHETIC_SAMPLE = {
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
        # Retina intentionally ABSENT to demonstrate missing-modality behaviour
        "age": 71.0,
        "sex": "male",
    }

    exp = explain_single(
        inputs=SYNTHETIC_SAMPLE,
        participant_id="SYNTH-PD-001",
        is_synthetic=True,
    )
    save_sample_explanation(exp)

    print(f"\nParticipant: {exp['participant_id']}")
    print(f"Risk score:  {exp['risk_score']}")
    print(f"Missing:     {exp['missing_modalities']}")
    print(f"\nTop-5 features by |SHAP|:")
    for feat in exp["important_features"][:5]:
        print(
            f"  {feat['feature_name']:35s}  SHAP={feat['shap_value']:+.4f}  "
            f"({feat['direction']})"
        )
    print(f"\nModality-level importance:")
    for m in exp["important_modalities"][:6]:
        miss = " [MISSING]" if m["missing"] else ""
        print(
            f"  {m['modality']:30s}  {m['importance']:.4f}  "
            f"({m['percent_contribution']:.1f}%)  {m['direction']}{miss}"
        )
