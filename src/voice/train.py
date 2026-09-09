"""
Voice Model Training and Artifact Generation Pipeline for MPF-PD (Phase 3).

Dataset: UCI Parkinson's Telemonitoring Dataset (uci_voice)
  Category: B (Modality-Specific)
  Participants: 42 PD patients (NO healthy controls)
  Recordings: 5,875 (approx. 140-200 per patient over 6 months)
  Labels: Continuous motor_UPDRS and total_UPDRS

Label binarization strategy (documented):
  Because UCI uci_voice has NO healthy controls, we cannot train a PD vs. control
  classifier on this dataset alone. Instead we:
    Option A (used here): Binarize total_UPDRS at median to distinguish
                          HIGHER vs. LOWER disease severity.
                          This is a regression-to-binary proxy, NOT PD diagnosis.
    This is EXPLICITLY documented as a LIMITATION.

Participant-level split strategy (documented):
  The UCI dataset has multiple recordings per participant (subject#).
  Strategy: PARTICIPANT-LEVEL GROUP SPLIT.
    - Unique participant IDs are split into train/val/test.
    - ALL recordings from the same participant are in exactly ONE split.
    - This prevents audio leakage from longitudinal data.
  If only one recording per participant existed, standard split would suffice.

When real data is unavailable locally, falls back to a synthetic fixture
(Category E) and marks all metrics as experiment_type='simulation'.

RESEARCH PROTOTYPE ONLY — NOT A CLINICAL TOOL.
Do NOT interpret outputs as PD diagnosis or clinical risk estimates.
"""

import os
import json
import datetime
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import joblib
import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold, cross_val_score
from xgboost import XGBClassifier

from src.seeds import set_global_seed
from src.config import load_config
from src.voice.features import (
    extract_tabular_voice_features,
    TABULAR_FEATURE_NAMES,
    VOICE_LIMITATIONS,
)
from src.voice.evaluate import compute_voice_metrics

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
# Dataset constants and documentation
# ──────────────────────────────────────────────────────────────────

UCI_DATASET_CARD = {
    "dataset_id": "uci_voice",
    "dataset_category": "B",
    "name": "UCI Parkinson's Telemonitoring Dataset",
    "source": "https://archive.ics.uci.edu/dataset/189/parkinsons+telemonitoring",
    "license": "CC BY 4.0",
    "n_participants": 42,
    "n_recordings": 5875,
    "label_definition": (
        "motor_UPDRS and total_UPDRS (continuous, clinician-assessed). "
        "Binarized at median for prototype classification: "
        "0 = UPDRS <= median (lower severity), 1 = UPDRS > median (higher severity). "
        "There are NO healthy controls in this dataset."
    ),
    "recording_tasks": "Sustained phonation of /a/ vowel during telemonitoring home sessions",
    "sampling_rate": "NOT provided as raw audio — features are precomputed by original authors",
    "file_format": "CSV (precomputed dysphonia features)",
    "missing_data": "Low missingness within extracted feature table; unbalanced recording frequencies per participant",
    "access_restrictions": "None — Open Access (CC BY 4.0)",
    "same_participant_multimodal": False,
    "healthy_controls": False,
    "limitations": [
        "NO healthy controls — binarization is severity proxy, not PD vs. control.",
        "Small cohort (N=42 participants); generalization should not be assumed.",
        "Pre-extracted features: original audio unavailable for re-extraction.",
        "Labels (UPDRS) are regression targets binarized for prototype classification.",
    ],
}

SYNTHETIC_DATASET_CARD = {
    "dataset_id": "synthetic_fixture",
    "dataset_category": "E",
    "name": "MPF-PD Synthetic Voice Test Fixture",
    "n_participants": 200,
    "label_definition": "Binary diagnosis (0=control, 1=PD) — ENTIRELY SYNTHETIC",
    "limitations": [
        "Completely synthetic — ZERO physiological or clinical reality.",
        "Used ONLY for software testing and CI/CD.",
        "Results in simulation mode must NOT be reported as clinical findings.",
    ],
}


# ──────────────────────────────────────────────────────────────────
# UCI data loading
# ──────────────────────────────────────────────────────────────────

def load_uci_voice_data(
    data_path: str = "data/raw/uci_voice/parkinsons_updrs.csv",
) -> Tuple[pd.DataFrame, str]:
    """
    Load the UCI Parkinson's Telemonitoring tabular feature dataset.

    Falls back to synthetic fixture when the real file is absent.

    Args:
        data_path: Path to UCI CSV file.

    Returns:
        Tuple (DataFrame, experiment_type):
          experiment_type is 'real_data' or 'simulation'.
    """
    path = Path(data_path)
    if path.exists() and path.is_file():
        df = pd.read_csv(path)
        df = _normalize_uci_columns(df)
        experiment_type = "real_data"
        logger.info(
            "Loaded real UCI voice data from '%s': %d records.", data_path, len(df)
        )
    else:
        logger.warning(
            "UCI voice file not found at '%s'. "
            "Falling back to SYNTHETIC FIXTURE (simulation mode). "
            "All metrics will be marked as simulation.", data_path
        )
        df = _generate_synthetic_voice_fixture(n_participants=200, seed=42)
        experiment_type = "simulation"

    return df, experiment_type


def _normalize_uci_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names for UCI dataset variants.

    The UCI dataset has two naming conventions in different downloads:
      - 'subject#' or 'subject_id'
      - 'motor_UPDRS' or 'motor_updrs'
    This function normalises them to a common schema.
    """
    col_map = {}
    for col in df.columns:
        lower = col.lower().strip()
        if lower in ("subject#", "subject_id", "subject"):
            col_map[col] = "participant_id"
        elif lower == "motor_updrs":
            col_map[col] = "motor_UPDRS"
        elif lower == "total_updrs":
            col_map[col] = "total_UPDRS"
        elif lower == "test_time":
            col_map[col] = "test_time"
        elif lower == "age":
            col_map[col] = "age"
        elif lower == "sex":
            col_map[col] = "sex"
    df = df.rename(columns=col_map)
    return df


def _generate_synthetic_voice_fixture(
    n_participants: int = 200,
    seed: int = 42,
    n_recordings_per_participant: int = 5,
) -> pd.DataFrame:
    """
    Generate synthetic voice feature table for unit testing ONLY.

    SYNTHETIC DATA — Category E (Test Fixture).
    Do NOT use for clinical evaluation or reporting.

    This simulates the UCI Telemonitoring structure:
      - Multiple recordings per participant
      - Continuous UPDRS-like targets (binarized for classification)
      - Pre-extracted dysphonia features (jitter, shimmer, HNR, etc.)
    """
    rng = np.random.RandomState(seed)

    rows = []
    for pid in range(1, n_participants + 1):
        # Each participant has n_recordings_per_participant recordings
        diag = rng.choice([0, 1])  # 0=lower severity, 1=higher severity
        for _ in range(n_recordings_per_participant):
            if diag == 0:
                # Lower severity → lower jitter, lower shimmer, higher HNR
                jitter_pct = rng.uniform(0.001, 0.006)
                shimmer = rng.uniform(0.02, 0.08)
                hnr = rng.uniform(20.0, 30.0)
                rpde = rng.uniform(0.35, 0.55)
                dfa = rng.uniform(0.7, 0.85)
                ppe = rng.uniform(0.08, 0.18)
                total_updrs = rng.uniform(15.0, 25.0)
            else:
                # Higher severity → higher jitter, shimmer, lower HNR
                jitter_pct = rng.uniform(0.005, 0.035)
                shimmer = rng.uniform(0.07, 0.25)
                hnr = rng.uniform(10.0, 22.0)
                rpde = rng.uniform(0.45, 0.75)
                dfa = rng.uniform(0.6, 0.78)
                ppe = rng.uniform(0.15, 0.40)
                total_updrs = rng.uniform(25.0, 50.0)

            rows.append({
                "participant_id": pid,
                "age": rng.uniform(45, 80),
                "sex": rng.choice([0, 1]),
                "test_time": rng.uniform(0, 180),
                "motor_UPDRS": total_updrs * 0.7 + rng.uniform(-2, 2),
                "total_UPDRS": total_updrs,
                "Jitter(%)": jitter_pct,
                "Jitter(Abs)": jitter_pct * 1e-4,
                "Jitter:RAP": jitter_pct * 0.55,
                "Jitter:PPQ5": jitter_pct * 0.57,
                "Jitter:DDP": jitter_pct * 1.65,
                "Shimmer": shimmer,
                "Shimmer(dB)": shimmer * 8.0,
                "Shimmer:APQ3": shimmer * 0.6,
                "Shimmer:APQ5": shimmer * 0.7,
                "Shimmer:APQ11": shimmer * 0.85,
                "Shimmer:DDA": shimmer * 1.8,
                "NHR": 1.0 / (hnr + 1e-6),
                "HNR": hnr,
                "RPDE": rpde,
                "DFA": dfa,
                "PPE": ppe,
                "_synthetic_label": diag,  # Pre-assigned synthetic label
            })

    df = pd.DataFrame(rows)

    # Insert controlled 5% missingness in Shimmer:APQ11 for missing-data testing
    mask = rng.rand(len(df)) < 0.05
    df.loc[mask, "Shimmer:APQ11"] = np.nan

    return df


# ──────────────────────────────────────────────────────────────────
# Label creation
# ──────────────────────────────────────────────────────────────────

def create_binary_label(
    df: pd.DataFrame,
    experiment_type: str,
    updrs_column: str = "total_UPDRS",
) -> pd.DataFrame:
    """
    Create binary classification label from the dataframe.

    For real UCI data:
      - Binarize total_UPDRS at the TRAINING-SET median.
      - This is NOT PD vs. control. It is HIGHER vs. LOWER UPDRS severity.
      - The median is computed ONLY on training data; applied to val/test.
      - This method is documented as a limitation.

    For synthetic fixture:
      - Uses pre-assigned '_synthetic_label' column.

    Args:
        df: Input DataFrame.
        experiment_type: 'real_data' or 'simulation'.
        updrs_column: Column to binarize (for real data only).

    Returns:
        DataFrame with added 'diagnosis' column (0 or 1).
    """
    df = df.copy()

    if experiment_type == "simulation" and "_synthetic_label" in df.columns:
        df["diagnosis"] = df["_synthetic_label"].astype(int)
    elif updrs_column in df.columns:
        # Median binarization — median MUST be fit on training data only
        # Here we compute it for reference; train.py recomputes on training split
        median_val = df[updrs_column].median()
        df["diagnosis"] = (df[updrs_column] > median_val).astype(int)
        logger.info(
            "Binarized '%s' at median %.2f: %d low-severity (0), %d high-severity (1).",
            updrs_column,
            median_val,
            int((df["diagnosis"] == 0).sum()),
            int((df["diagnosis"] == 1).sum()),
        )
    else:
        raise ValueError(
            f"Cannot create binary label: column '{updrs_column}' not found "
            f"and '_synthetic_label' not present (experiment_type='{experiment_type}')."
        )

    return df


# ──────────────────────────────────────────────────────────────────
# Participant-level split
# ──────────────────────────────────────────────────────────────────

def split_voice_data(
    df: pd.DataFrame,
    test_size: float = 0.15,
    val_size: float = 0.15,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Participant-level stratified train/validation/test split.

    Strategy: GROUP SPLIT.
      All recordings from the same participant_id are assigned to exactly one split.
      This prevents any audio leakage from the same person across splits.

    For the UCI dataset with multiple recordings per participant (~140-200 each),
    this is critical: without it, the same participant's voice could appear in both
    training and test, inflating apparent performance.

    Args:
        df: DataFrame with 'participant_id' and 'diagnosis' columns.
        test_size: Fraction of participants for test.
        val_size: Fraction of participants for validation.
        seed: Random seed.

    Returns:
        Tuple (df_train, df_val, df_test).
    """
    from sklearn.model_selection import train_test_split
    from src.data.validators import validate_participant_split

    # Get per-participant label (majority vote if multiple recordings have different labels)
    participant_labels = (
        df.groupby("participant_id")["diagnosis"]
        .agg(lambda x: int(x.mode()[0]))
        .reset_index()
    )

    train_val_participants, test_participants = train_test_split(
        participant_labels,
        test_size=test_size,
        stratify=participant_labels["diagnosis"],
        random_state=seed,
    )

    adjusted_val_size = val_size / (1.0 - test_size)
    train_participants, val_participants = train_test_split(
        train_val_participants,
        test_size=adjusted_val_size,
        stratify=train_val_participants["diagnosis"],
        random_state=seed,
    )

    train_ids = train_participants["participant_id"].tolist()
    val_ids = val_participants["participant_id"].tolist()
    test_ids = test_participants["participant_id"].tolist()

    validate_participant_split(train_ids, val_ids, test_ids)

    df_train = df[df["participant_id"].isin(train_ids)].copy()
    df_val = df[df["participant_id"].isin(val_ids)].copy()
    df_test = df[df["participant_id"].isin(test_ids)].copy()

    logger.info(
        "Split: train=%d recordings (%d participants), val=%d recordings (%d participants), "
        "test=%d recordings (%d participants).",
        len(df_train), len(train_ids),
        len(df_val), len(val_ids),
        len(df_test), len(test_ids),
    )

    return df_train, df_val, df_test


# ──────────────────────────────────────────────────────────────────
# Aggregate per-participant features
# ──────────────────────────────────────────────────────────────────

def aggregate_participant_features(
    X: pd.DataFrame,
    participant_ids: pd.Series,
    labels: pd.Series,
    strategy: str = "mean",
) -> Tuple[pd.DataFrame, pd.Series, List[Any]]:
    """
    Aggregate multiple recordings per participant into a single feature vector.

    Strategy options:
      - 'mean': Average all recording features per participant.
        Used here as the primary strategy.
      - 'median': Median across recordings.

    This is an alternative to group-split (we use group-split in split_voice_data
    but also aggregate for the classifier so each participant = one row).
    Both approaches are documented.

    Args:
        X: Feature DataFrame (rows = recordings).
        participant_ids: Series of participant IDs matching X rows.
        labels: Binary label Series matching X rows.
        strategy: Aggregation strategy ('mean' or 'median').

    Returns:
        Tuple (X_agg, y_agg, participant_id_list).
    """
    df_agg = X.copy()
    df_agg["_pid"] = participant_ids.values
    df_agg["_label"] = labels.values

    if strategy == "mean":
        feat_agg = df_agg.groupby("_pid")[list(X.columns)].mean()
    elif strategy == "median":
        feat_agg = df_agg.groupby("_pid")[list(X.columns)].median()
    else:
        raise ValueError(f"Unknown aggregation strategy: '{strategy}'")

    label_agg = df_agg.groupby("_pid")["_label"].agg(lambda x: int(x.mode()[0]))
    pids = feat_agg.index.tolist()

    return feat_agg.reset_index(drop=True), label_agg.reset_index(drop=True), pids


# ──────────────────────────────────────────────────────────────────
# Main training pipeline
# ──────────────────────────────────────────────────────────────────

def run_voice_pipeline(
    data_path: str = "data/raw/uci_voice/parkinsons_updrs.csv",
    seed: int = 42,
    aggregate: bool = True,
) -> Dict[str, Any]:
    """
    Execute the complete voice ML training, evaluation, and artifact saving pipeline.

    Steps:
      1. Load UCI feature data (real or synthetic fallback).
      2. Binarize UPDRS label (median split on training data only).
      3. Participant-level group split (train/val/test).
      4. Feature extraction (tabular — PATH A).
      5. Aggregate per-participant features (mean of recordings).
      6. Fit imputer + scaler STRICTLY on training data.
      7. Train 4 models: LR, SVM, RF, XGBoost.
      8. Select best by val ROC-AUC.
      9. Save model artifact + metadata.
      10. Save evaluation JSON.

    Args:
        data_path: Path to UCI CSV file.
        seed: Random seed for reproducibility.
        aggregate: If True, aggregate multi-recording features per participant.

    Returns:
        Dict[str, Any]: Pipeline results.
    """
    set_global_seed(seed)
    config = load_config()

    # 1. Load data
    df_raw, experiment_type = load_uci_voice_data(data_path)
    dataset_id = UCI_DATASET_CARD["dataset_id"] if experiment_type == "real_data" else "synthetic_fixture"
    dataset_category = "B" if experiment_type == "real_data" else "E"

    # 2. Participant-level split (BEFORE label binarization to avoid leakage)
    #    We need a provisional diagnosis column for stratification.
    #    For UCI real data: binarize total_UPDRS using FULL dataset median first
    #    (provisional split), then re-compute median on TRAINING set only.
    df_provisional = create_binary_label(df_raw, experiment_type)
    df_train_raw, df_val_raw, df_test_raw = split_voice_data(
        df_provisional, test_size=0.15, val_size=0.15, seed=seed
    )

    # 3. Re-binarize using TRAINING-SET median only (prevent leakage)
    if experiment_type == "real_data":
        train_median = df_train_raw["total_UPDRS"].median()
        logger.info(
            "UPDRS binarization: using training-set median %.2f "
            "(prevents leakage from val/test into label creation).",
            train_median,
        )
        df_train_raw = df_train_raw.copy()
        df_val_raw = df_val_raw.copy()
        df_test_raw = df_test_raw.copy()

        df_train_raw["diagnosis"] = (df_train_raw["total_UPDRS"] > train_median).astype(int)
        df_val_raw["diagnosis"] = (df_val_raw["total_UPDRS"] > train_median).astype(int)
        df_test_raw["diagnosis"] = (df_test_raw["total_UPDRS"] > train_median).astype(int)

    # 4. Feature extraction
    X_train_raw = extract_tabular_voice_features(df_train_raw)
    X_val_raw = extract_tabular_voice_features(df_val_raw)
    X_test_raw = extract_tabular_voice_features(df_test_raw)
    features_used = TABULAR_FEATURE_NAMES

    y_train_raw = df_train_raw["diagnosis"]
    y_val_raw = df_val_raw["diagnosis"]
    y_test_raw = df_test_raw["diagnosis"]

    # 5. Aggregate per-participant features (mean of recordings)
    #    This ensures each participant is one row in the model input.
    if aggregate:
        X_train_agg, y_train, train_pids = aggregate_participant_features(
            X_train_raw, df_train_raw["participant_id"], y_train_raw
        )
        X_val_agg, y_val, val_pids = aggregate_participant_features(
            X_val_raw, df_val_raw["participant_id"], y_val_raw
        )
        X_test_agg, y_test, test_pids = aggregate_participant_features(
            X_test_raw, df_test_raw["participant_id"], y_test_raw
        )
        aggregation_strategy = "mean_per_participant"
    else:
        X_train_agg = X_train_raw
        y_train = y_train_raw
        train_pids = df_train_raw["participant_id"].tolist()
        X_val_agg = X_val_raw
        y_val = y_val_raw
        val_pids = df_val_raw["participant_id"].tolist()
        X_test_agg = X_test_raw
        y_test = y_test_raw
        test_pids = df_test_raw["participant_id"].tolist()
        aggregation_strategy = "none_group_split_only"

    y_train = np.asarray(y_train)
    y_val = np.asarray(y_val)
    y_test = np.asarray(y_test)

    # 6. Fit imputer + scaler STRICTLY on training data
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()

    X_train_imp = imputer.fit_transform(X_train_agg)
    X_train = scaler.fit_transform(X_train_imp)

    X_val_imp = imputer.transform(X_val_agg)
    X_val = scaler.transform(X_val_imp)

    X_test_imp = imputer.transform(X_test_agg)
    X_test = scaler.transform(X_test_imp)

    # 7. Define models
    models = {
        "logistic_regression": LogisticRegression(
            C=1.0, random_state=seed, max_iter=2000
        ),
        "svm": SVC(
            C=1.0, kernel="rbf", probability=True, random_state=seed
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=100, max_depth=5, random_state=seed
        ),
        "xgboost": XGBClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.05,
            eval_metric="logloss", random_state=seed, verbosity=0
        ),
    }

    results = {}
    best_model_name = None
    best_val_score = -1.0
    best_pipeline = None

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)

    for name, model in models.items():
        # Cross-validation within training set
        if len(np.unique(y_train)) > 1:
            cv_scores = cross_val_score(
                model, X_train, y_train, cv=cv, scoring="roc_auc"
            )
        else:
            cv_scores = np.array([float("nan")] * 5)
            logger.warning("Only one class in training set; CV scores are NaN.")

        model.fit(X_train, y_train)

        val_pred = model.predict(X_val)
        val_prob = model.predict_proba(X_val)[:, 1] if hasattr(model, "predict_proba") else None
        val_metrics = compute_voice_metrics(y_val, val_pred, val_prob, val_pids)

        test_pred = model.predict(X_test)
        test_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else None
        test_metrics = compute_voice_metrics(y_test, test_pred, test_prob, test_pids)

        cv_mean = float(np.nanmean(cv_scores))
        cv_std = float(np.nanstd(cv_scores))

        results[name] = {
            "cv_roc_auc_mean": round(cv_mean, 4),
            "cv_roc_auc_std": round(cv_std, 4),
            "validation_metrics": val_metrics,
            "test_metrics": test_metrics,
            "model_object": model,
        }

        score = val_metrics.get("roc_auc") or val_metrics.get("f1") or 0.0
        if score > best_val_score:
            best_val_score = score
            best_model_name = name
            best_pipeline = {
                "imputer": imputer,
                "scaler": scaler,
                "model": model,
                "model_name": name,
                "features_used": features_used,
                "aggregation_strategy": aggregation_strategy,
                "experiment_type": experiment_type,
            }

    # 8. Save model artifacts
    models_dir = Path("models/voice")
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / "model.joblib"
    joblib.dump(best_pipeline, model_path)

    all_limitations = list(VOICE_LIMITATIONS) + (
        UCI_DATASET_CARD["limitations"] if experiment_type == "real_data"
        else SYNTHETIC_DATASET_CARD["limitations"]
    )
    if experiment_type == "simulation":
        all_limitations.insert(0, (
            "SIMULATION MODE: Real UCI voice data not found locally. "
            "All metrics computed on SYNTHETIC FIXTURE data (Category E). "
            "These metrics have ZERO clinical validity."
        ))

    metadata = {
        "modality": "voice",
        "model_type": best_model_name,
        "dataset_id": dataset_id,
        "dataset_category": dataset_category,
        "features_used": features_used,
        "feature_extraction_path": "tabular_uci",
        "aggregation_strategy": aggregation_strategy,
        "label_definition": UCI_DATASET_CARD["label_definition"],
        "target_label": "diagnosis (binarized UPDRS)",
        "training_participants": len(set(train_pids)),
        "validation_participants": len(set(val_pids)),
        "test_participants": len(set(test_pids)),
        "training_recordings": int(len(df_train_raw)),
        "validation_recordings": int(len(df_val_raw)),
        "test_recordings": int(len(df_test_raw)),
        "metrics": {
            "validation": results[best_model_name]["validation_metrics"],
            "test": results[best_model_name]["test_metrics"],
            "cv_roc_auc_mean": results[best_model_name]["cv_roc_auc_mean"],
        },
        "seed": seed,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "limitations": all_limitations,
        "clinical_claim": False,
        "experiment_type": experiment_type,
        "dataset_card": UCI_DATASET_CARD if experiment_type == "real_data" else SYNTHETIC_DATASET_CARD,
    }

    metadata_path = models_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # 9. Save quality check summary
    quality_summary = {
        "note": (
            "Audio quality checks apply to raw audio files. "
            "UCI uci_voice provides pre-extracted features (no raw audio). "
            "Quality checks for tabular data: missing value ratios checked per feature."
        ),
        "missing_value_ratios": {
            col: round(float(X_train_agg[col].isna().mean()), 4)
            for col in features_used
            if col in X_train_agg.columns
        },
    }

    # 10. Save evaluation results
    eval_dir = Path("evaluation")
    eval_dir.mkdir(parents=True, exist_ok=True)
    eval_path = eval_dir / "voice_results.json"

    eval_output = {
        "phase": 3,
        "modality": "voice",
        "dataset_id": dataset_id,
        "dataset_category": dataset_category,
        "experiment_type": experiment_type,
        "models_compared": list(models.keys()),
        "best_model": best_model_name,
        "metrics": {
            model_name: {
                "validation": res["validation_metrics"],
                "test": res["test_metrics"],
                "cv_roc_auc_mean": res["cv_roc_auc_mean"],
            }
            for model_name, res in results.items()
        },
        "features_used": features_used,
        "quality_checks": quality_summary,
        "limitations": all_limitations,
        "artifact_paths": {
            "model_path": str(model_path),
            "metadata_path": str(metadata_path),
        },
    }

    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(eval_output, f, indent=2)

    logger.info(
        "Voice pipeline complete. Best model: %s (val score: %.4f). experiment_type: %s.",
        best_model_name, best_val_score, experiment_type,
    )

    return {
        "best_model": best_model_name,
        "best_val_score": best_val_score,
        "experiment_type": experiment_type,
        "metadata": metadata,
        "evaluation": eval_output,
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    data_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/uci_voice/parkinsons_updrs.csv"
    res = run_voice_pipeline(data_path=data_path)
    print(f"\nVoice pipeline completed!")
    print(f"Experiment Type : {res['experiment_type']}")
    print(f"Best Model      : {res['best_model']}")
    print(f"Best Val Score  : {res['best_val_score']:.4f}")
