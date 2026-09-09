"""
Olfactory Risk Prediction API Entry Point for MPF-PD.

Provides standardized inference function `predict_olfactory(features: dict) -> dict`.
Validates input feature dictionaries, handles missing features safely without inventing data,
and returns structured risk probability and warning flags.
"""

from pathlib import Path
from typing import Dict, Any, List
import joblib
import pandas as pd
import numpy as np

from src.olfactory.features import FEATURE_COLUMNS, extract_olfactory_features


def predict_olfactory(
    features: Dict[str, Any],
    model_path: str = "models/olfactory/model.joblib"
) -> Dict[str, Any]:
    """
    Predict olfactory Parkinson's risk probability for a single participant or observation.

    Args:
        features: Dictionary containing olfactory measurement keys (e.g. total_score).
        model_path: Path to trained joblib model artifact.

    Returns:
        Dict[str, Any]: Standardized prediction output dictionary:
            - modality: 'olfactory'
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
            f"Olfactory model artifact not found at '{model_path}'. "
            f"Please run 'python -m src.olfactory.train' to train and save the model."
        )

    pipeline = joblib.load(path)
    model = pipeline["model"]
    imputer = pipeline["imputer"]
    scaler = pipeline["scaler"]
    model_name = pipeline.get("model_name", "unknown")

    # 2. Check input features
    if not isinstance(features, dict):
        raise TypeError("Input 'features' must be a dictionary.")

    # Primary key requirement check
    if "total_score" not in features or features["total_score"] is None:
        warnings.append("Critical feature 'total_score' missing. Defaulting risk calculation to neutral uninformative state.")
        return {
            "modality": "olfactory",
            "risk_score": 0.5,
            "model_version": f"olfactory_{model_name}_v1",
            "features_used": FEATURE_COLUMNS,
            "warnings": warnings + ["Inference performed with incomplete primary features."]
        }

    # 3. Create single-row DataFrame and compute features
    df_raw = pd.DataFrame([features])
    
    # Fill defaults for secondary optional columns if not provided
    if "response_time_mean" not in df_raw.columns:
        warnings.append("Optional feature 'response_time_mean' not provided; handled via training-set imputer median.")
    if "n_errors" not in df_raw.columns and "total_score" in df_raw.columns:
        df_raw["n_errors"] = 40.0 - float(df_raw["total_score"].iloc[0])
    if "error_pattern_flags" not in df_raw.columns:
        df_raw["error_pattern_flags"] = 0.0

    X_raw = extract_olfactory_features(df_raw)

    # 4. Impute and scale using saved pipeline fit on training data
    X_imp = imputer.transform(X_raw)
    X_scaled = scaler.transform(X_imp)

    # 5. Model probability prediction
    if hasattr(model, "predict_proba"):
        prob = float(model.predict_proba(X_scaled)[0, 1])
    else:
        prob = float(model.predict(X_scaled)[0])

    # Bound risk score between 0.0 and 1.0
    risk_score = round(float(np.clip(prob, 0.0, 1.0)), 4)

    return {
        "modality": "olfactory",
        "risk_score": risk_score,
        "model_version": f"olfactory_{model_name}_v1",
        "features_used": FEATURE_COLUMNS,
        "warnings": warnings
    }
