"""
Motor/Gait Model Training Pipeline for MPF-PD (Phase 4).

Trains and compares Logistic Regression, Random Forest, and XGBoost on
motor/gait features from the PhysioNet physionet_gait dataset (Category B).

Pipeline steps:
  1. Load data (real VGRF or synthetic fixture fallback)
  2. Preprocess and quality-check
  3. Participant-level stratified split (prevents data leakage)
  4. Feature extraction (from raw VGRF or pass-through for derived/synthetic)
  5. Fit imputer and scaler on TRAINING set only
  6. Train Logistic Regression, Random Forest, XGBoost
  7. Evaluate on validation and test sets
  8. Save best model artifact (joblib) and metadata.json
  9. Save evaluation/motor_results.json

DATASET NOTE:
  - physionet_gait provides binary PD vs Control labels only.
  - No prodromal labels exist in this dataset.
  - Raw VGRF text files are not included in this repository (open access download
    required from https://doi.org/10.13026/C24H3N).
  - When real data is absent, the pipeline runs in SIMULATION MODE using a
    clearly-labelled synthetic fixture (Category E).

IMPORTANT: No clinical claims. All outputs are research prototype risk estimates.
"""

import datetime
import json
import warnings
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.seeds import set_global_seed
from src.config import load_config
from src.motor.preprocess import (
    load_motor_data,
    preprocess_motor_data,
    split_motor_data,
)
from src.motor.features import (
    extract_motor_features,
    get_feature_matrix,
    MOTOR_FEATURE_NAMES,
    LIMITATIONS,
)
from src.motor.quality import check_motor_quality
from src.motor.evaluate import compute_motor_metrics


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _generate_synthetic_motor_fixture(n_participants: int = 200, seed: int = 42) -> pd.DataFrame:
    """
    Alias to the preprocess-module synthetic generator, exposed for test imports.

    SYNTHETIC DATA — for unit tests and CI/CD only. Zero clinical validity.
    """
    from src.motor.preprocess import generate_synthetic_motor_fixture
    return generate_synthetic_motor_fixture(n_participants=n_participants, seed=seed)


def split_motor_data_wrapper(
    df: pd.DataFrame,
    test_size: float = 0.15,
    val_size: float = 0.15,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Thin wrapper for split_motor_data (exposed for test imports)."""
    return split_motor_data(df, test_size=test_size, val_size=val_size, seed=seed)


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_motor_pipeline(
    data_dir: str = "data/raw/physionet_gait",
    precomputed_csv: Optional[str] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Execute the complete motor/gait ML training, evaluation, and artifact pipeline.

    Args:
        data_dir: Directory containing PhysioNet VGRF .txt files.
        precomputed_csv: Optional path to precomputed participant-level feature CSV.
        seed: Random seed for reproducibility.

    Returns:
        Dict[str, Any]: Pipeline result dictionary containing model metadata,
                        evaluation metrics, and artifact paths.
    """
    set_global_seed(seed)
    config = load_config()

    # ── 1. Load data ──────────────────────────────────────────────────────────
    df_raw, experiment_type, raw_sensor_available = load_motor_data(
        data_dir=data_dir,
        precomputed_csv=precomputed_csv,
    )

    dataset_id = "physionet_gait" if experiment_type in ("real_data", "derived_only") else "synthetic_fixture"
    dataset_category = "B" if experiment_type in ("real_data", "derived_only") else "E"

    # ── 2. Preprocess ─────────────────────────────────────────────────────────
    df_clean = preprocess_motor_data(
        df_raw,
        raw_sensor_available=raw_sensor_available,
        experiment_type=experiment_type,
    )

    # ── 3. Quality check ──────────────────────────────────────────────────────
    quality_report = check_motor_quality(
        df_clean,
        raw_sensor_available=raw_sensor_available,
    )
    if not quality_report["passed"]:
        n_issues = len(quality_report.get("issues", []))
        warnings.warn(
            f"Motor quality check flagged {n_issues} issue(s). "
            "Check motor quality report for details. Proceeding with pipeline.",
            UserWarning,
            stacklevel=2,
        )

    # ── 4. Feature extraction ─────────────────────────────────────────────────
    # When raw sensor is available, feature extraction runs per-participant VGRF analysis.
    # When not available (derived/synthetic), features are read directly from the table.
    df_features = extract_motor_features(
        df_clean,
        raw_sensor_available=raw_sensor_available,
    )

    # ── 5. Participant-level split ────────────────────────────────────────────
    df_train, df_val, df_test = split_motor_data(df_features, seed=seed)

    # ── 6. Prepare feature matrices ───────────────────────────────────────────
    X_train_raw, y_train, feature_names = get_feature_matrix(df_train)
    X_val_raw, y_val, _ = get_feature_matrix(df_val)
    X_test_raw, y_test, _ = get_feature_matrix(df_test)

    # ── 7. Fit imputer and scaler on TRAINING set only (zero leakage) ─────────
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()

    X_train_imp = imputer.fit_transform(X_train_raw)
    X_train = scaler.fit_transform(X_train_imp)

    X_val_imp = imputer.transform(X_val_raw)
    X_val = scaler.transform(X_val_imp)

    X_test_imp = imputer.transform(X_test_raw)
    X_test = scaler.transform(X_test_imp)

    # ── 8. Define models ──────────────────────────────────────────────────────
    models = {
        "logistic_regression": LogisticRegression(
            C=1.0, random_state=seed, max_iter=1000
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=100, max_depth=5, random_state=seed
        ),
        "xgboost": XGBClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.05,
            eval_metric="logloss", random_state=seed,
            verbosity=0,
        ),
    }

    results: Dict[str, Any] = {}
    best_model_name: Optional[str] = None
    best_val_score: float = -1.0
    best_pipeline: Optional[Dict[str, Any]] = None

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)

    n_recordings_train = len(df_train)
    n_recordings_val = len(df_val)
    n_recordings_test = len(df_test)

    # ── 9. Train and evaluate each model ─────────────────────────────────────
    for name, model in models.items():
        # Cross-validation strictly within training set
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="roc_auc")

        # Fit on full training set
        model.fit(X_train, y_train)

        # Validation evaluation
        val_pred = model.predict(X_val)
        val_prob = model.predict_proba(X_val)[:, 1]
        val_metrics = compute_motor_metrics(
            y_val, val_pred, val_prob,
            participant_ids=df_val["participant_id"].tolist(),
            n_recordings=n_recordings_val,
            n_features=len(feature_names),
        )

        # Test evaluation
        test_pred = model.predict(X_test)
        test_prob = model.predict_proba(X_test)[:, 1]
        test_metrics = compute_motor_metrics(
            y_test, test_pred, test_prob,
            participant_ids=df_test["participant_id"].tolist(),
            n_recordings=n_recordings_test,
            n_features=len(feature_names),
        )

        results[name] = {
            "cv_roc_auc_mean": round(float(np.mean(cv_scores)), 4),
            "cv_roc_auc_std": round(float(np.std(cv_scores)), 4),
            "validation": val_metrics,
            "test": test_metrics,
            "model_object": model,
        }

        # Model selection: use validation ROC-AUC (F1 fallback)
        score = val_metrics["roc_auc"] if val_metrics["roc_auc"] is not None else val_metrics["f1"]
        if score > best_val_score:
            best_val_score = score
            best_model_name = name
            best_pipeline = {
                "imputer": imputer,
                "scaler": scaler,
                "model": model,
                "model_name": name,
                "features_used": feature_names,
                "raw_sensor_used": raw_sensor_available,
                "tasks_used": ["walking_gait"],
                "dataset_id": dataset_id,
                "experiment_type": experiment_type,
            }

    # ── 10. Save model artifact ───────────────────────────────────────────────
    models_dir = Path("models/motor")
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / "model.joblib"
    joblib.dump(best_pipeline, model_path)

    # ── 11. Save metadata ─────────────────────────────────────────────────────
    limitations = LIMITATIONS.copy()
    if experiment_type == "simulation":
        limitations = [
            "SIMULATION MODE: Real PhysioNet physionet_gait data not found locally. "
            "All metrics computed on SYNTHETIC FIXTURE data (Category E). "
            "These metrics have ZERO clinical validity.",
        ] + limitations

    metadata = {
        "modality": "motor",
        "model_type": best_model_name,
        "dataset_id": dataset_id,
        "dataset_category": dataset_category,
        "experiment_type": experiment_type,
        "raw_sensor_processing_used": raw_sensor_available,
        "tasks_used": ["walking_gait"],
        "features_used": feature_names,
        "target_label": "diagnosis",
        "label_mapping": {"0": "Control", "1": "PD"},
        "training_participants": int(df_train["participant_id"].nunique()),
        "validation_participants": int(df_val["participant_id"].nunique()),
        "test_participants": int(df_test["participant_id"].nunique()),
        "training_recordings": n_recordings_train,
        "validation_recordings": n_recordings_val,
        "test_recordings": n_recordings_test,
        "metrics": {
            "validation": results[best_model_name]["validation"],
            "test": results[best_model_name]["test"],
            "cv_roc_auc_mean": results[best_model_name]["cv_roc_auc_mean"],
        },
        "seed": seed,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "limitations": limitations,
        "clinical_claim": False,
    }

    metadata_path = models_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # ── 12. Save evaluation results ───────────────────────────────────────────
    eval_dir = Path("evaluation")
    eval_dir.mkdir(parents=True, exist_ok=True)
    eval_path = eval_dir / "motor_results.json"

    eval_output = {
        "phase": 4,
        "modality": "motor",
        "dataset_id": dataset_id,
        "dataset_category": dataset_category,
        "experiment_type": experiment_type,
        "raw_sensor_processing_used": raw_sensor_available,
        "tasks_used": ["walking_gait"],
        "models_compared": list(models.keys()),
        "best_model": best_model_name,
        "metrics": {
            model_name: {
                "validation": res["validation"],
                "test": res["test"],
                "cv_roc_auc_mean": res["cv_roc_auc_mean"],
                "cv_roc_auc_std": res["cv_roc_auc_std"],
            }
            for model_name, res in results.items()
        },
        "features_used": feature_names,
        "limitations": limitations,
        "artifact_paths": {
            "model_path": str(model_path),
            "metadata_path": str(metadata_path),
        },
    }

    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(eval_output, f, indent=2)

    return {
        "best_model": best_model_name,
        "best_val_score": best_val_score,
        "experiment_type": experiment_type,
        "raw_sensor_processing_used": raw_sensor_available,
        "metadata": metadata,
        "evaluation": eval_output,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    res = run_motor_pipeline()
    print("Motor pipeline completed successfully!")
    print(f"Experiment Type : {res['experiment_type']}")
    print(f"Best Model      : {res['best_model']} (Val Score: {res['best_val_score']:.4f})")
    print(f"Raw Sensor Used : {res['raw_sensor_processing_used']}")
