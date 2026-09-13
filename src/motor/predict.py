"""
Motor/Gait Risk Prediction API for MPF-PD (Phase 4).

Provides standardized inference function:
    predict_motor(data: dict | pandas.DataFrame | str) -> dict

The returned dictionary is suitable for downstream multimodal fusion (Phase 6).

IMPORTANT:
  - Outputs are research prototype risk estimates only.
  - No clinical claims are made.
  - The risk score is NOT a diagnosis of Parkinson's disease.
  - Missing motor modality produces warnings but NOT a crash.
"""

import warnings
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple

import joblib
import numpy as np
import pandas as pd

from src.motor.features import MOTOR_FEATURE_NAMES, GAIT_FEATURE_NAMES


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_pipeline(model_path: str) -> Dict[str, Any]:
    """
    Load the saved motor model pipeline from disk.

    Args:
        model_path: Path to the joblib artifact.

    Returns:
        Dict with 'model', 'imputer', 'scaler', 'features_used', 'model_name'.

    Raises:
        FileNotFoundError: If the model artifact does not exist.
    """
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Motor model artifact not found at '{model_path}'. "
            "Please run 'python -m src.motor.train' to train and save the model."
        )
    return joblib.load(path)


def _normalise_input(
    data: Union[Dict[str, Any], pd.DataFrame, str],
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Normalise various input formats to a single-row (or multi-row) DataFrame.

    Accepts:
      - dict: Single participant feature dict.
      - pd.DataFrame: Pre-built feature DataFrame (one or more rows).
      - str: Path to a CSV file with feature columns.

    Returns:
        Tuple[pd.DataFrame, List[str]]: (feature DataFrame, warnings list).
    """
    input_warnings: List[str] = []

    if isinstance(data, dict):
        df = pd.DataFrame([data])
    elif isinstance(data, pd.DataFrame):
        df = data.copy()
    elif isinstance(data, str):
        p = Path(data)
        if not p.exists():
            raise FileNotFoundError(f"Input CSV not found: '{data}'")
        df = pd.read_csv(p)
        input_warnings.append(f"Input loaded from CSV file: {data}")
    else:
        raise TypeError(
            f"Input 'data' must be a dict, pd.DataFrame, or str (CSV path). "
            f"Got {type(data).__name__}."
        )

    return df, input_warnings


# ─────────────────────────────────────────────────────────────────────────────
# Public prediction API
# ─────────────────────────────────────────────────────────────────────────────

def predict_motor(
    data: Union[Dict[str, Any], pd.DataFrame, str],
    model_path: str = "models/motor/model.joblib",
) -> Dict[str, Any]:
    """
    Predict motor Parkinson's risk probability for one or more participants.

    Input Formats:
      - dict: Single participant feature dictionary with any subset of:
              gait_speed_m_per_s, cadence_steps_per_min,
              stride_interval_mean_s, stride_interval_cv_pct,
              step_regularity, symmetry_index_pct,
              accel_variance, stance_swing_ratio
      - pd.DataFrame: Feature DataFrame (one row per participant).
      - str: Path to CSV file with feature columns.

    Output Schema (JSON-serialisable):
        {
            "modality": "motor",
            "risk_score": float,           # [0.0, 1.0] — research prototype estimate
            "embedding": list[float],       # model probability + scaled features
            "model_version": str,
            "features_used": list[str],
            "tasks_used": list[str],
            "quality": {
                "passed": bool,
                "issues": list[str]
            },
            "warnings": list[str]
        }

    IMPORTANT: risk_score is a research prototype estimate. Not a clinical diagnosis.

    Args:
        data: Input features as dict, DataFrame, or CSV path.
        model_path: Path to trained motor model artifact.

    Returns:
        Dict[str, Any]: Standardised prediction output dictionary.
    """
    pred_warnings: List[str] = []
    quality_issues: List[str] = []

    # ── Load model pipeline ───────────────────────────────────────────────────
    try:
        pipeline = _load_pipeline(model_path)
    except FileNotFoundError as e:
        pred_warnings.append(str(e))
        return {
            "modality": "motor",
            "risk_score": 0.5,
            "embedding": [],
            "model_version": "motor_unavailable_v1",
            "features_used": MOTOR_FEATURE_NAMES,
            "tasks_used": ["walking_gait"],
            "quality": {"passed": False, "issues": [str(e)]},
            "warnings": pred_warnings,
        }

    model = pipeline["model"]
    imputer = pipeline["imputer"]
    scaler = pipeline["scaler"]
    feature_names: List[str] = pipeline.get("features_used", MOTOR_FEATURE_NAMES)
    model_name: str = pipeline.get("model_name", "unknown")
    tasks_used: List[str] = pipeline.get("tasks_used", ["walking_gait"])
    experiment_type: str = pipeline.get("experiment_type", "unknown")

    if experiment_type == "simulation":
        pred_warnings.append(
            "MODEL TRAINED ON SYNTHETIC FIXTURE (simulation mode). "
            "Risk score has ZERO clinical validity."
        )

    # ── Normalise input ───────────────────────────────────────────────────────
    try:
        df_input, input_warnings = _normalise_input(data)
        pred_warnings.extend(input_warnings)
    except (FileNotFoundError, TypeError) as e:
        pred_warnings.append(str(e))
        return {
            "modality": "motor",
            "risk_score": 0.5,
            "embedding": [],
            "model_version": f"motor_{model_name}_v1",
            "features_used": feature_names,
            "tasks_used": tasks_used,
            "quality": {"passed": False, "issues": [str(e)]},
            "warnings": pred_warnings,
        }

    # ── Feature presence check ────────────────────────────────────────────────
    provided_features = set(df_input.columns)
    expected_features = set(feature_names)
    missing_in_input = expected_features - provided_features
    extra_in_input = provided_features - expected_features

    if missing_in_input:
        pred_warnings.append(
            f"Missing feature columns in input: {sorted(missing_in_input)}. "
            "These will be imputed with training-set medians."
        )

    if extra_in_input:
        pred_warnings.append(
            f"Extra columns in input not used by model: {sorted(extra_in_input)}. Ignored."
        )

    # ── Check if ALL motor features are completely absent ─────────────────────
    n_available = sum(1 for f in feature_names if f in df_input.columns)
    if n_available == 0:
        pred_warnings.append(
            "No motor feature columns found in input. "
            "Motor modality is effectively absent. Returning uninformative risk score 0.5."
        )
        quality_issues.append(
            "Zero motor features provided. Motor modality cannot contribute to fusion."
        )
        return {
            "modality": "motor",
            "risk_score": 0.5,
            "embedding": [0.5] * len(feature_names),
            "model_version": f"motor_{model_name}_v1",
            "features_used": feature_names,
            "tasks_used": tasks_used,
            "quality": {"passed": False, "issues": quality_issues},
            "warnings": pred_warnings,
        }

    # ── Build feature matrix ──────────────────────────────────────────────────
    # Create empty DataFrame with all expected features, fill from input
    df_model = pd.DataFrame(
        np.nan,
        index=range(len(df_input)),
        columns=feature_names,
    )
    for feat in feature_names:
        if feat in df_input.columns:
            df_model[feat] = pd.to_numeric(df_input[feat], errors="coerce").values

    X_raw = df_model.values.astype(np.float64)

    # Check for all-NaN rows
    all_nan_rows = np.all(np.isnan(X_raw), axis=1)
    if np.any(all_nan_rows):
        quality_issues.append(
            f"{int(np.sum(all_nan_rows))} input row(s) have all-NaN features. "
            "Predictions for these rows will be unreliable."
        )

    # ── Impute and scale (using TRAINING statistics) ──────────────────────────
    X_imp = imputer.transform(X_raw)
    X_scaled = scaler.transform(X_imp)

    # ── Model inference ───────────────────────────────────────────────────────
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X_scaled)[:, 1]
    else:
        probs = model.predict(X_scaled).astype(float)

    probs = np.clip(probs, 0.0, 1.0)

    # ── Aggregate to single risk score (mean across rows if multi-row input) ──
    if len(probs) > 1:
        risk_score = float(np.mean(probs))
        pred_warnings.append(
            f"Input contains {len(probs)} rows. Risk score is the mean across rows."
        )
    else:
        risk_score = float(probs[0])

    risk_score = round(risk_score, 4)

    # ── Embedding for fusion ──────────────────────────────────────────────────
    # Embedding: [risk_score] + per-feature mean scaled values
    # Shape: (1 + n_features,) — compact embedding for Phase 6 fusion.
    embedding = [risk_score] + list(np.nanmean(X_scaled, axis=0).round(4))

    quality_passed = len(quality_issues) == 0

    return {
        "modality": "motor",
        "risk_score": risk_score,
        "embedding": embedding,
        "model_version": f"motor_{model_name}_v1",
        "features_used": feature_names,
        "tasks_used": tasks_used,
        "quality": {
            "passed": quality_passed,
            "issues": quality_issues,
        },
        "warnings": pred_warnings,
    }
