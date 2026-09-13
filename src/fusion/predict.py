"""
Inference Pipeline for Multimodal Prodromal Fusion (MPF-PD Phase 6).

Provides standardized inference function:
    predict_fusion(inputs: dict) -> dict

Supports missing modalities gracefully without crashing:
- Zero vector / learnable missing tokens substituted for absent modalities.
- Modality presence indicators explicitly passed to the neural gating layer.
- Returns research prototype risk score, fused embedding, presence flags, and gate weights.

RESEARCH PROTOTYPE ONLY — NO CLINICAL VALIDITY CLAIMED.
NOT A DIAGNOSTIC DEVICE.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Ensure project root is in sys.path when executed directly
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import numpy as np
import pandas as pd
import joblib
import torch

from src.fusion.dataset import MODALITIES
from src.fusion.gated_fusion import GatedMultimodalFusion

logger = logging.getLogger("mpf.fusion.predict")

DEFAULT_MODEL_PATH = "models/fusion/classifier.joblib"
DEFAULT_ENCODER_PATH = "models/fusion/fusion_encoder.pt"
DEFAULT_PREPROCESSOR_PATH = "models/fusion/preprocessor.joblib"
DEFAULT_METADATA_PATH = "models/fusion/metadata.json"


def _parse_sex_feature(sex_input: Any) -> float:
    """Parse sex input into numeric value (0=female, 1=male)."""
    if isinstance(sex_input, (int, float)):
        return 1.0 if sex_input >= 0.5 else 0.0
    if isinstance(sex_input, str):
        s = sex_input.strip().lower()
        if s in ["m", "male", "1"]:
            return 1.0
        elif s in ["f", "female", "0"]:
            return 0.0
    return 0.5  # Neutral default


def predict_fusion(
    inputs: Dict[str, Any],
    model_path: str = DEFAULT_MODEL_PATH,
    encoder_path: str = DEFAULT_ENCODER_PATH,
    preprocessor_path: str = DEFAULT_PREPROCESSOR_PATH,
    metadata_path: str = DEFAULT_METADATA_PATH,
) -> Dict[str, Any]:
    """
    Predict multimodal Parkinson's risk score from available modalities.

    Args:
        inputs: Dictionary containing any subset of:
            - 'olfactory': dict of olfactory features / sub-dict
            - 'rbd': dict of RBDSQ features / sub-dict
            - 'voice': dict of voice acoustic features / sub-dict
            - 'motor': dict of motor/gait features / sub-dict
            - 'retina': dict of retinal vessel features / sub-dict
            - 'age': participant age in years (float/int)
            - 'sex': participant sex ("female", "male", 0, 1)
        model_path: Path to trained classifier joblib file.
        encoder_path: Path to trained PyTorch fusion encoder weights.
        preprocessor_path: Path to preprocessor joblib file.
        metadata_path: Path to model metadata JSON.

    Returns:
        Dict conforming to Phase 6 inference schema:
        {
            "risk_score": float,
            "fused_embedding": list[float],
            "modality_presence": dict[str, bool],
            "gate_weights": dict[str, float],
            "model_version": str,
            "experiment_type": str,
            "warnings": list[str]
        }
    """
    warnings: List[str] = [
        "RESEARCH PROTOTYPE: Risk score is an investigational estimate only.",
        "NOT FOR CLINICAL DIAGNOSIS: No clinical validity is claimed.",
    ]

    if not isinstance(inputs, dict):
        raise TypeError(f"Input 'inputs' must be a dictionary. Got {type(inputs).__name__}.")

    # Load artifacts
    p_clf = Path(model_path)
    p_enc = Path(encoder_path)
    p_prep = Path(preprocessor_path)

    if not p_clf.exists() or not p_enc.exists() or not p_prep.exists():
        raise FileNotFoundError(
            "Fusion model artifacts not found. Please run 'python -m src.fusion.train' first."
        )

    classifier = joblib.load(p_clf)
    preprocessors = joblib.load(p_prep)
    
    modality_imputers = preprocessors["modality_imputers"]
    modality_scalers = preprocessors["modality_scalers"]
    demo_imp = preprocessors["demo_imputer"]
    demo_scaler = preprocessors["demo_scaler"]
    modality_feature_cols = preprocessors["modality_feature_cols"]

    # Metadata & experiment type
    experiment_type = "prototype_simulation"
    model_version = "gated_multimodal_fusion_v1"
    if Path(metadata_path).exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                experiment_type = meta.get("experiment_type", experiment_type)
        except Exception:
            pass

    if experiment_type == "prototype_simulation":
        warnings.append(
            "MODEL TRAINED IN SIMULATION MODE: Metrics derived from synthetic test fixtures."
        )

    # 1. Determine modality presence and parse features
    modality_presence: Dict[str, bool] = {}
    modality_tensors: Dict[str, torch.Tensor] = {}

    for mod in MODALITIES:
        mod_input = inputs.get(mod)
        is_present = False
        cols = modality_feature_cols[mod]

        if mod_input is not None and isinstance(mod_input, dict) and len(mod_input) > 0:
            # Check if there is at least one non-null feature or non-zero value
            valid_keys = [k for k, v in mod_input.items() if v is not None]
            if len(valid_keys) > 0:
                is_present = True

        modality_presence[mod] = is_present

        if is_present:
            # Build single-row DataFrame
            row_dict = {}
            for col in cols:
                val = mod_input.get(col, np.nan)
                try:
                    row_dict[col] = float(val) if val is not None else np.nan
                except (ValueError, TypeError):
                    row_dict[col] = np.nan

            df_mod = pd.DataFrame([row_dict])[cols]
            # Impute and scale
            X_imp = modality_imputers[mod].transform(df_mod.values)
            X_scaled = modality_scalers[mod].transform(X_imp)
            modality_tensors[mod] = torch.tensor(X_scaled, dtype=torch.float32)
        else:
            # Zero vector for absent modality
            dim = len(cols)
            modality_tensors[mod] = torch.zeros((1, dim), dtype=torch.float32)
            warnings.append(f"Modality '{mod}' is ABSENT. Gating unit will mask this modality.")

    # 2. Check if all modalities are missing
    total_present = sum(1 for v in modality_presence.values() if v)
    if total_present == 0:
        warnings.append("ALL modalities are missing. Returning uninformative baseline risk score 0.5.")
        return {
            "risk_score": 0.5,
            "fused_embedding": [0.0] * 45,
            "modality_presence": modality_presence,
            "gate_weights": {m: 0.2 for m in MODALITIES},
            "model_version": model_version,
            "experiment_type": experiment_type,
            "warnings": warnings,
        }

    # 3. Demographics
    age_raw = inputs.get("age", 65.0)
    if "age" not in inputs:
        warnings.append("Age not provided; defaulting to reference screening age 65.0.")
    try:
        age_val = float(age_raw)
    except (ValueError, TypeError):
        age_val = 65.0

    sex_raw = inputs.get("sex", "female")
    if "sex" not in inputs:
        warnings.append("Sex not provided; defaulting to neutral reference.")
    sex_val = _parse_sex_feature(sex_raw)

    demo_row = np.array([[age_val, sex_val, 1.0]], dtype=float)
    demo_scaled = demo_scaler.transform(demo_imp.transform(demo_row))
    t_demo = torch.tensor(demo_scaled, dtype=torch.float32)

    # Presence flags tensor: (1, 5)
    pres_row = np.array([[float(modality_presence[m]) for m in MODALITIES]], dtype=float)
    t_pres = torch.tensor(pres_row, dtype=torch.float32)

    # 4. Instantiate and load neural fusion encoder
    modality_dims = {m: len(modality_feature_cols[m]) for m in MODALITIES}
    fusion_net = GatedMultimodalFusion(
        modality_dims=modality_dims,
        embedding_dim=32,
        demo_dim=3,
        fusion_mechanism="gated_attention",
        missing_modality_strategy="learnable_token",
        mask_dropout_rate=0.0,  # Eval mode
        seed=42,
    )
    fusion_net.load_state_dict(torch.load(p_enc, map_location="cpu"))
    fusion_net.eval()

    # 5. Extract fused representation and gate weights
    with torch.no_grad():
        fused_repr, gate_tensor = fusion_net.extract_fused_representation(
            modality_tensors=modality_tensors,
            presence_flags=t_pres,
            demo_tensor=t_demo,
        )

    fused_embedding_np = fused_repr.numpy()
    gate_weights_np = gate_tensor.numpy()[0]

    # 6. Final classification with trained XGBoost classifier
    if hasattr(classifier, "predict_proba"):
        prob = float(classifier.predict_proba(fused_embedding_np)[0, 1])
    else:
        prob = float(classifier.predict(fused_embedding_np)[0])

    risk_score = round(float(np.clip(prob, 0.0, 1.0)), 4)
    fused_embedding_list = [round(float(x), 4) for x in fused_embedding_np[0]]
    clean_gate_weights = {
        m: round(float(gate_weights_np[i]), 4)
        for i, m in enumerate(MODALITIES)
    }

    return {
        "risk_score": risk_score,
        "fused_embedding": fused_embedding_list,
        "modality_presence": modality_presence,
        "gate_weights": clean_gate_weights,
        "model_version": model_version,
        "experiment_type": experiment_type,
        "warnings": warnings,
    }


if __name__ == "__main__":
    # Smoke test inference example
    sample_inputs = {
        "olfactory": {"total_score": 24.0, "response_time_mean": 4.5},
        "rbd": {"rbdsq_total": 7.0, "above_cutoff_flag": 1.0},
        "voice": {"jitter_pct": 0.007, "shimmer": 0.05, "hnr": 16.5},
        "motor": {"gait_speed_m_per_s": 0.95, "cadence_steps_per_min": 98.0},
        "retina": {"vessel_density": 0.065, "mean_vessel_diameter_px": 2.95},
        "age": 68.0,
        "sex": "male",
    }
    result = predict_fusion(sample_inputs)
    print("Inference Result Sample:")
    print(json.dumps(result, indent=2))
