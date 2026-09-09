"""
Voice Risk Prediction API for MPF-PD (Phase 3).

Provides the standardized `predict_voice(audio_file: str) -> dict` interface.

Input:
  - Path to an audio file (WAV, MP3, FLAC, etc.)
  - OR a pre-extracted feature dictionary (for UCI tabular data)

Output:
  {
    "modality": "voice",
    "risk_score": float,         # [0.0, 1.0] — research prototype estimate only
    "embedding": [...],          # Standardized feature vector for fusion
    "model_version": str,
    "features_used": [...],
    "quality": {
      "passed": bool,
      "issues": [...]
    },
    "warnings": [...]
  }

RESEARCH PROTOTYPE ONLY — NOT A CLINICAL DIAGNOSTIC TOOL.
Risk score is an investigational estimate with no clinical validation.
Do NOT use for medical decision-making.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import numpy as np
import pandas as pd
import joblib

from src.voice.quality import check_audio_quality
from src.voice.preprocess import load_audio, preprocess_audio, TARGET_SR
from src.voice.features import extract_tabular_voice_features, TABULAR_FEATURE_NAMES

logger = logging.getLogger(__name__)

MODEL_PATH_DEFAULT = "models/voice/model.joblib"


def predict_voice(
    audio_file: Optional[str] = None,
    tabular_features: Optional[Dict[str, float]] = None,
    model_path: str = MODEL_PATH_DEFAULT,
) -> Dict[str, Any]:
    """
    Predict voice-based PD risk score for a single audio recording or feature set.

    Two input modes:
      Mode A (audio_file): Loads and processes a raw audio file.
                           Quality checks run first. If quality fails, returns
                           risk_score=None and quality.passed=False.
      Mode B (tabular_features): Accepts a pre-extracted feature dict
                                 (e.g., from UCI Telemonitoring CSV).
                                 Quality checks are skipped (no audio to check).

    Args:
        audio_file: Path to audio file (optional).
        tabular_features: Pre-extracted feature dict (optional).
        model_path: Path to trained voice model artifact.

    Returns:
        Dict: Standardized prediction output schema.

    Raises:
        RuntimeError: If neither audio_file nor tabular_features is provided.
        FileNotFoundError: If model artifact is missing.
    """
    warnings: List[str] = []
    quality_result: Dict[str, Any] = {"passed": True, "issues": []}

    if audio_file is None and tabular_features is None:
        raise RuntimeError(
            "predict_voice() requires either 'audio_file' (path to audio) "
            "or 'tabular_features' (pre-extracted feature dict)."
        )

    # 1. Load model artifact
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Voice model artifact not found at '{model_path}'. "
            f"Run 'python -m src.voice.train' to train and save the model."
        )

    pipeline = joblib.load(path)
    model = pipeline["model"]
    imputer = pipeline["imputer"]
    scaler = pipeline["scaler"]
    model_name = pipeline.get("model_name", "unknown")
    features_used: List[str] = pipeline.get("features_used", TABULAR_FEATURE_NAMES)
    experiment_type = pipeline.get("experiment_type", "unknown")

    if experiment_type == "simulation":
        warnings.append(
            "Model was trained on SYNTHETIC FIXTURE data (simulation mode). "
            "This risk score has ZERO clinical validity."
        )

    # 2a. MODE A: Audio file input
    audio_array: Optional[np.ndarray] = None
    if audio_file is not None:
        audio_path = str(audio_file)
        audio_raw, sr = load_audio(audio_path, target_sr=TARGET_SR)

        # Quality check
        quality_result = check_audio_quality(
            audio=audio_raw, sr=sr if audio_raw is not None else 0,
            file_path=audio_path,
        )

        if not quality_result["passed"]:
            warnings.append(
                "Audio quality check FAILED. Risk score cannot be computed from this recording."
            )
            return {
                "modality": "voice",
                "risk_score": None,
                "embedding": None,
                "model_version": f"voice_{model_name}_v1",
                "features_used": features_used,
                "quality": quality_result,
                "warnings": warnings,
            }

        # Preprocess
        audio_array = preprocess_audio(audio_raw, sr=sr)

        # Extract spectral features from audio
        from src.voice.features import extract_spectral_features
        spectral = extract_spectral_features(audio_array, sr=sr)

        # Build feature row — fill NaN for missing tabular features
        feature_row: Dict[str, float] = {}
        for fname in features_used:
            feature_row[fname] = spectral.get(fname, np.nan)

        if all(np.isnan(v) for v in feature_row.values()):
            warnings.append(
                "All features are NaN for this audio input. "
                "The model was likely trained on UCI tabular features "
                "which are not extractable from raw audio. "
                "Use tabular_features= instead."
            )

    # 2b. MODE B: Pre-extracted tabular features
    else:
        feature_row = {}
        for fname in features_used:
            val = tabular_features.get(fname, np.nan)
            feature_row[fname] = float(val) if val is not None else np.nan
            if np.isnan(float(val if val is not None else float("nan"))):
                warnings.append(
                    f"Feature '{fname}' missing from input; will be imputed by training-set median."
                )

    # 3. Build feature array
    X_input = pd.DataFrame([feature_row])[features_used]

    # 4. Transform (impute → scale) using training-fit pipeline
    X_imp = imputer.transform(X_input)
    X_scaled = scaler.transform(X_imp)

    # 5. Inference
    if hasattr(model, "predict_proba"):
        prob = float(model.predict_proba(X_scaled)[0, 1])
    else:
        prob = float(model.predict(X_scaled)[0])

    risk_score = round(float(np.clip(prob, 0.0, 1.0)), 4)

    # 6. Embedding = standardized scaled feature vector
    embedding = X_scaled[0].tolist()

    warnings.append(
        "RESEARCH PROTOTYPE: This risk score is an investigational estimate. "
        "It is NOT a clinical diagnosis of Parkinson's disease."
    )

    return {
        "modality": "voice",
        "risk_score": risk_score,
        "embedding": embedding,
        "model_version": f"voice_{model_name}_v1",
        "features_used": features_used,
        "quality": quality_result,
        "warnings": warnings,
    }
