"""
MPF-PD Phase 7 — Global Importance Computation.

Computes mean absolute SHAP values across a dataset of samples to produce
global feature importance and modality-level importance rankings.

Uses the synthetic multimodal fixture for computation because real same-participant
multimodal data is unavailable locally (prototype_simulation mode).

RESEARCH PROTOTYPE ONLY. Not a diagnostic device. No clinical claims.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.explainability.shap_explainer import MPFSHAPExplainer, SEED
from src.explainability.modality_mapping import FUSED_FEATURE_NAMES, FUSED_DIM
from src.fusion.dataset import generate_synthetic_multimodal_fixture, MODALITIES
from src.fusion.dataset import RBD_FEATURES
from src.olfactory.features import FEATURE_COLUMNS as OLFACTORY_FEATURES
from src.voice.features import TABULAR_FEATURE_NAMES as VOICE_FEATURES
from src.motor.features import MOTOR_FEATURE_NAMES
from src.retina.vessel_features import RETINA_FEATURE_NAMES

logger = logging.getLogger("mpf.explainability.global_importance")

OUTPUT_PATH = "evaluation/xai_global_importance.json"
N_BACKGROUND_SAMPLES = 100  # samples used for global SHAP computation


def build_inputs_from_df(df, n_samples: int = N_BACKGROUND_SAMPLES):
    """
    Convert the synthetic multimodal fixture DataFrame into a list of input dicts
    compatible with MPFSHAPExplainer._build_fused_repr_from_raw().

    Args:
        df:        Synthetic multimodal DataFrame from generate_synthetic_multimodal_fixture.
        n_samples: Max number of samples to use.

    Returns:
        List of input dicts.
    """
    retina_cols = RETINA_FEATURE_NAMES + [f"retina_emb_{d}" for d in range(16)]
    modality_feature_cols = {
        "olfactory": OLFACTORY_FEATURES,
        "rbd": RBD_FEATURES,
        "voice": VOICE_FEATURES,
        "motor": MOTOR_FEATURE_NAMES,
        "retina": retina_cols,
    }

    subset = df.sample(n=min(n_samples, len(df)), random_state=SEED)
    inputs_list = []

    for _, row in subset.iterrows():
        sample: Dict[str, Any] = {
            "age": float(row.get("age", 65.0)),
            "sex": float(row.get("sex_encoded", 0.0)),
        }
        for mod, cols in modality_feature_cols.items():
            pres_col = f"presence_{mod}"
            is_present = bool(row.get(pres_col, 1)) if pres_col in row else True
            if is_present:
                mod_dict = {}
                for col in cols:
                    if col in row:
                        v = row[col]
                        mod_dict[col] = float(v) if not (v != v) else np.nan  # NaN check
                    else:
                        mod_dict[col] = np.nan
                sample[mod] = mod_dict
            else:
                sample[mod] = {}  # absent
        inputs_list.append(sample)

    return inputs_list


def compute_global_importance(
    explainer: Optional[MPFSHAPExplainer] = None,
    n_samples: int = N_BACKGROUND_SAMPLES,
    output_path: str = OUTPUT_PATH,
) -> Dict[str, Any]:
    """
    Compute and save global SHAP feature importance.

    Args:
        explainer:   Pre-loaded MPFSHAPExplainer. If None, loads default artifacts.
        n_samples:   Number of samples from the synthetic fixture to use.
        output_path: Path to write the JSON output.

    Returns:
        Global importance dict (also written to JSON).
    """
    if explainer is None:
        explainer = MPFSHAPExplainer()

    logger.info(
        "Generating synthetic multimodal fixture (%d samples) for global SHAP computation.",
        n_samples,
    )
    df = generate_synthetic_multimodal_fixture(n_participants=max(n_samples + 50, 350), seed=SEED)

    inputs_list = build_inputs_from_df(df, n_samples=n_samples)
    logger.info("Built %d input dicts from fixture.", len(inputs_list))

    # Build fused representations
    fused_matrix, gate_weights_list, presence_flags_list = (
        explainer._build_fused_repr_from_raw(inputs_list)
    )
    logger.info("Fused matrix shape: %s", fused_matrix.shape)

    # Compute SHAP values
    logger.info("Computing SHAP values via %s ...", explainer.explanation_method)
    shap_values = explainer.compute_shap_values(fused_matrix)
    logger.info("SHAP values computed. Shape: %s", shap_values.shape)

    # Mean absolute SHAP per feature
    mean_abs_shap = np.mean(np.abs(shap_values), axis=0)

    # Build per-feature importance list (sorted descending)
    from src.explainability.modality_mapping import get_feature_group
    feature_importance: List[Dict[str, Any]] = []
    for idx, fname in enumerate(FUSED_FEATURE_NAMES):
        feature_importance.append(
            {
                "feature_name": fname,
                "feature_index": idx,
                "modality_group": get_feature_group(idx),
                "mean_abs_shap": round(float(mean_abs_shap[idx]), 6),
            }
        )
    feature_importance.sort(key=lambda x: -x["mean_abs_shap"])

    # Modality-level importance
    modality_importance = explainer.aggregate_modality_importance(
        shap_values, gate_weights_list
    )

    output: Dict[str, Any] = {
        "phase": 7,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "explanation_method": explainer.explanation_method,
        "model_type": explainer.clf_type,
        "dataset_used": "synthetic_fixture_prototype_simulation",
        "experiment_type": "prototype_simulation",
        "synthetic_example": True,
        "n_samples_used": len(inputs_list),
        "fused_dim": FUSED_DIM,
        "global_feature_importance": feature_importance,
        "modality_importance": modality_importance,
        "shap_base_value": (
            round(float(explainer._get_shap_explainer().expected_value), 6)
            if explainer.explanation_method == "shap_tree"
            else None
        ),
        "architecture_note": (
            "The 45-dim fused vector contains a 32-dim gated modality representation "
            "(post-attention over all modality embeddings), an 8-dim demographic encoder "
            "output, and 5 explicit modality presence flags. Modality-level importance "
            "for the gated representation is attributed proportionally to fusion gate weights."
        ),
        "limitations": [
            "PROTOTYPE SIMULATION MODE: Global importance computed on synthetic fixture data. "
            "Metrics have ZERO clinical validity.",
            "SHAP values reflect the 45-dim fused representation, not raw biomarker features. "
            "Individual feature-level importance (e.g., jitter_pct, vessel_density) is not "
            "directly recoverable from fused SHAP without additional attribution.",
            "Modality-level importance for the gated vector is estimated via gate weights, "
            "which are soft attention scores rather than exact SHAP decompositions.",
            "No clinical claims. All outputs are research prototype estimates only.",
            "Do not interpret these values as validated biomarker importance rankings.",
        ],
        "clinical_claim": False,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    logger.info("Global importance written to %s", output_path)

    return output


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    result = compute_global_importance()
    top5 = result["global_feature_importance"][:5]
    print("\n=== Top-5 Features by Mean |SHAP| ===")
    for feat in top5:
        print(
            f"  {feat['feature_name']:35s}  group={feat['modality_group']:30s}  "
            f"mean_abs_shap={feat['mean_abs_shap']:.4f}"
        )
    print("\n=== Modality-Level Importance ===")
    for m in result["modality_importance"]:
        print(
            f"  {m['modality']:30s}  {m['mean_abs_shap']:.4f}  ({m['percent_contribution']:.1f}%)"
        )
