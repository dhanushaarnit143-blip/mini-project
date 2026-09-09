"""
RBD Risk Prediction API Entry Point for MPF-PD.

Provides standardized inference function `predict_rbd(features: dict) -> dict`.
Validates input feature dictionaries, handles missing features safely without inventing data,
and returns structured risk probability and warning flags.
"""

from pathlib import Path
from typing import Dict, Any, List
import joblib
import pandas as pd
import numpy as np

from src.rbd.features import extract_rbd_features, BASE_FEATURE_COLUMNS, ITEM_COLUMNS


def predict_rbd(
    features: Dict[str, Any],
    model_path: str = "models/rbd/model.joblib"
) -> Dict[str, Any]:
    """
    Predict RBD Parkinson's risk probability for a single participant or questionnaire submission.

    Args:
        features: Dictionary containing RBDSQ questionnaire responses (e.g. rbdsq_total, item_1..13).
        model_path: Path to trained joblib model artifact.

    Returns:
        Dict[str, Any]: Standardized prediction output dictionary:
            - modality: 'rbd'
            - risk_score: float [0.0, 1.0]
            - model_version: str
            - features_used: list
            - warnings: list
    """
    warnings: List[str] = []

    # 1. Load model artifact
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(
            f"RBD model artifact not found at '{model_path}'. "
            f"Please run 'python -m src.rbd.train' to train and save the model."
        )

    pipeline = joblib.load(path)
    model = pipeline["model"]
    imputer = pipeline["imputer"]
    scaler = pipeline["scaler"]
    model_name = pipeline.get("model_name", "unknown")
    features_used = pipeline.get("features_used", BASE_FEATURE_COLUMNS + ITEM_COLUMNS)

    # 2. Input validation
    if not isinstance(features, dict):
        raise TypeError("Input 'features' must be a dictionary.")

    if "rbdsq_total" not in features or features["rbdsq_total"] is None:
        # Check if individual items can sum to rbdsq_total
        provided_items = [features.get(col) for col in ITEM_COLUMNS if col in features and features[col] is not None]
        if provided_items:
            features["rbdsq_total"] = float(sum(provided_items))
            warnings.append("rbdsq_total was missing; computed sum from available item subscores.")
        else:
            warnings.append("Critical feature 'rbdsq_total' missing. Returning neutral risk probability.")
            return {
                "modality": "rbd",
                "risk_score": 0.5,
                "model_version": f"rbd_{model_name}_v1",
                "features_used": features_used,
                "warnings": warnings + ["Inference performed with incomplete primary features."]
            }

    # 3. Build single row dataframe
    df_raw = pd.DataFrame([features])

    if "above_cutoff_flag" not in df_raw.columns:
        df_raw["above_cutoff_flag"] = (float(df_raw["rbdsq_total"].iloc[0]) >= 5.0)

    X_raw = extract_rbd_features(df_raw)

    # Align columns with trained features_used
    for col in features_used:
        if col not in X_raw.columns:
            X_raw[col] = np.nan
            warnings.append(f"Feature '{col}' missing from input; imputed using training set median.")
    X_raw = X_raw[features_used]

    # 4. Transform using training-fit pipeline
    X_imp = imputer.transform(X_raw)
    X_scaled = scaler.transform(X_imp)

    # 5. Inference
    if hasattr(model, "predict_proba"):
        prob = float(model.predict_proba(X_scaled)[0, 1])
    else:
        prob = float(model.predict(X_scaled)[0])

    risk_score = round(float(np.clip(prob, 0.0, 1.0)), 4)

    return {
        "modality": "rbd",
        "risk_score": risk_score,
        "model_version": f"rbd_{model_name}_v1",
        "features_used": features_used,
        "warnings": warnings
    }
