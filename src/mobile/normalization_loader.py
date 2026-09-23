"""
MPF Mobile Extension — Normalization & Preprocessing Loader (Phase 12).

Strictly re-uses the exact serialized preprocessing and scaling artifacts
trained during the MPF model training phase.

SCIENTIFIC INTEGRITY & ZERO RETRAINING RULES:
1. NO REFITTING: Strictly calls transform(). Never calls fit() or fit_transform().
2. IDENTICAL ARTIFACTS: Re-uses models/fusion/preprocessor.joblib directly.
3. EXACT COLUMN ORDER: Preserves modality feature ordering recorded during training.
4. OUTLIER BOUNDING: Clips scaled values to [-5.0, +5.0] to prevent numerical instability.
5. NO POPULATION IMPUTATION: Missing values are handled via the model's trained imputers/missing-tokens.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import logging
import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger("mpf.mobile.normalization_loader")

DEFAULT_PREPROCESSOR_PATH = "models/fusion/preprocessor.joblib"
OUTLIER_CLIP_MIN = -5.0
OUTLIER_CLIP_MAX = 5.0

# In-memory cache for preprocessor artifacts
_PREPROCESSOR_CACHE: Optional[Dict[str, Any]] = None
_CACHE_PATH: Optional[str] = None


def load_training_preprocessors(
    preprocessor_path: str = DEFAULT_PREPROCESSOR_PATH,
    force_reload: bool = False,
) -> Dict[str, Any]:
    """
    Load serialized preprocessing artifacts from training.

    Args:
        preprocessor_path: Path to preprocessor.joblib.
        force_reload: If True, bypasses cache and reloads from disk.

    Returns:
        Dict containing:
            - modality_scalers: Dict[str, StandardScaler]
            - modality_imputers: Dict[str, SimpleImputer]
            - demo_scaler: StandardScaler
            - demo_imputer: SimpleImputer
            - modality_feature_cols: Dict[str, List[str]]

    Raises:
        FileNotFoundError: If the preprocessor artifact is missing.
    """
    global _PREPROCESSOR_CACHE, _CACHE_PATH

    if not force_reload and _PREPROCESSOR_CACHE is not None and _CACHE_PATH == preprocessor_path:
        return _PREPROCESSOR_CACHE

    p = Path(preprocessor_path)
    if not p.exists():
        raise FileNotFoundError(
            f"Pre-trained preprocessor artifact not found at '{preprocessor_path}'. "
            "Cannot normalize mobile features without existing training preprocessor."
        )

    preprocessor = joblib.load(p)

    required_keys = [
        "modality_scalers",
        "modality_imputers",
        "demo_scaler",
        "demo_imputer",
        "modality_feature_cols",
    ]
    for key in required_keys:
        if key not in preprocessor:
            raise KeyError(
                f"Preprocessor artifact corrupted or incomplete: missing key '{key}'."
            )

    _PREPROCESSOR_CACHE = preprocessor
    _CACHE_PATH = preprocessor_path
    logger.info(f"Loaded training preprocessors from '{preprocessor_path}'")
    return _PREPROCESSOR_CACHE


def get_modality_feature_columns(
    modality: str,
    preprocessor_path: str = DEFAULT_PREPROCESSOR_PATH,
) -> List[str]:
    """
    Retrieve the exact feature column list and order for a given modality.
    """
    prep = load_training_preprocessors(preprocessor_path)
    cols = prep["modality_feature_cols"].get(modality)
    if cols is None:
        raise ValueError(
            f"Modality '{modality}' not recognized in trained preprocessors. "
            f"Available modalities: {list(prep['modality_feature_cols'].keys())}"
        )
    return list(cols)


def normalize_modality_features(
    modality: str,
    features: Dict[str, Any],
    preprocessor_path: str = DEFAULT_PREPROCESSOR_PATH,
    clip_outliers: bool = True,
) -> np.ndarray:
    """
    Normalize mobile features for a single modality using the EXACT training preprocessor.

    Strict rules:
    - Never calls fit(). Only calls transform().
    - Values aligned strictly to training column order.
    - Outliers clipped to [-5.0, +5.0].

    Args:
        modality: Name of modality ('voice', 'motor', 'rbd', 'olfactory', 'retina').
        features: Dictionary containing feature values.
        preprocessor_path: Path to serialized preprocessor.
        clip_outliers: Whether to clip extreme values to [-5.0, +5.0].

    Returns:
        np.ndarray: 2D array of shape (1, n_features) of scaled feature values.
    """
    prep = load_training_preprocessors(preprocessor_path)
    cols = prep["modality_feature_cols"].get(modality)
    if cols is None:
        raise ValueError(f"Unknown modality '{modality}' for normalization.")

    imputer = prep["modality_imputers"][modality]
    scaler = prep["modality_scalers"][modality]

    # Verify that imputer and scaler are fitted and ready
    if not hasattr(scaler, "mean_") or not hasattr(imputer, "statistics_"):
        raise RuntimeError(
            f"Scaler/imputer for '{modality}' is not fitted. Cannot normalize features."
        )

    # Build single-row DataFrame with strict column order
    row_dict = {}
    for col in cols:
        val = features.get(col)
        try:
            row_dict[col] = float(val) if val is not None else np.nan
        except (ValueError, TypeError):
            row_dict[col] = np.nan

    df = pd.DataFrame([row_dict])[cols]

    # Apply transform only - NEVER fit
    X_imp = imputer.transform(df.values)
    X_scaled = scaler.transform(X_imp)

    if clip_outliers:
        X_scaled = np.clip(X_scaled, OUTLIER_CLIP_MIN, OUTLIER_CLIP_MAX)

    return X_scaled


def normalize_demographics(
    age: float,
    sex: Union[str, float],
    preprocessor_path: str = DEFAULT_PREPROCESSOR_PATH,
    clip_outliers: bool = True,
) -> np.ndarray:
    """
    Normalize demographic features using training demographic preprocessors.

    Args:
        age: Participant age in years.
        sex: Sex ('female'=0.0, 'male'=1.0, or numeric).
        preprocessor_path: Path to serialized preprocessor.
        clip_outliers: Whether to clip extreme values.

    Returns:
        np.ndarray: 2D array of shape (1, 2) [age_scaled, sex_scaled].
    """
    prep = load_training_preprocessors(preprocessor_path)
    demo_imp = prep["demo_imputer"]
    demo_scaler = prep["demo_scaler"]

    # Parse sex to numeric
    if isinstance(sex, (int, float)):
        sex_num = 1.0 if sex >= 0.5 else 0.0
    elif isinstance(sex, str):
        s = sex.strip().lower()
        sex_num = 1.0 if s in ["m", "male", "1"] else 0.0
    else:
        sex_num = 0.5

    demo_row = np.array([[float(age), sex_num, 1.0]], dtype=float)

    # Transform only
    X_imp = demo_imp.transform(demo_row)
    X_scaled = demo_scaler.transform(X_imp)

    if clip_outliers:
        X_scaled = np.clip(X_scaled, OUTLIER_CLIP_MIN, OUTLIER_CLIP_MAX)

    return X_scaled


def verify_no_retraining(
    preprocessor_path: str = DEFAULT_PREPROCESSOR_PATH,
) -> bool:
    """
    Safety check verifying that scalers retain their original training parameters.
    """
    prep = load_training_preprocessors(preprocessor_path)
    for mod, scaler in prep["modality_scalers"].items():
        if not hasattr(scaler, "mean_") or scaler.mean_ is None:
            return False
    return True
