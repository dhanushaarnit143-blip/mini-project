"""
RBD Model Training and Artifact Generation Pipeline for MPF-PD.

Trains Logistic Regression, Random Forest, and XGBoost models on RBD features.
Enforces training-set fitting of scalers/imputers, zero data leakage,
saves model artifacts and metadata, and exports evaluation JSON results.

Experiment types:
  real_data  — trained on PPMI / PREDICT-PD RBDSQ data (requires local CSV).
  simulation — trained on clearly-labelled synthetic fixture; all outputs
               carry experiment_type='simulation' and not_trained=True in
               metadata to prevent accidental clinical use.

IMPORTANT: Models trained here predict RBD RISK from questionnaire data.
           They do NOT constitute and MUST NOT be interpreted as a clinical
           RBD diagnosis. PSG confirmation is required for diagnosis.
"""

import os
import json
import datetime
from pathlib import Path
from typing import Dict, Any
import joblib
import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score

from src.seeds import set_global_seed
from src.config import load_config
from src.rbd.preprocess import (
    load_rbd_data,
    preprocess_rbd_data,
    split_rbd_data,
)
from src.rbd.features import (
    extract_rbd_features,
    get_rbd_feature_names,
    FEATURE_SCHEMA,
    RBD_LIMITATIONS,
)
from src.rbd.evaluate import compute_evaluation_metrics


def run_rbd_pipeline(
    data_path: str = "data/raw/ppmi/RBDSQ.csv",
    seed: int = 42
) -> Dict[str, Any]:
    """
    Executes the complete RBD ML training, evaluation, and artifact saving pipeline.

    When real data is not available locally the pipeline falls back to a
    clearly-labelled synthetic fixture.  All artifacts produced in this mode
    carry ``experiment_type='simulation'`` and ``not_trained=True`` so they
    cannot be mistaken for results on real clinical data.

    Models predict RBD screening risk from RBDSQ questionnaire scores.
    They do NOT constitute a clinical RBD diagnosis.

    Args:
        data_path: Path to real dataset CSV file (PPMI RBDSQ export).
        seed: Random seed for reproducibility.

    Returns:
        Dict[str, Any]: Complete training pipeline result dictionary.
    """
    set_global_seed(seed)
    config = load_config()

    # 1. Load data
    df_raw, experiment_type = load_rbd_data(data_path)
    dataset_id = "ppmi" if experiment_type == "real_data" else "synthetic_fixture"
    dataset_category = "A" if experiment_type == "real_data" else "E"
    # not_trained: outputs should not be used as trained model claims without real data
    not_trained: bool = experiment_type != "real_data"

    # 2. Preprocess & validate schema
    df_clean = preprocess_rbd_data(df_raw)

    # 3. Participant-level split (zero leakage enforced inside)
    df_train, df_val, df_test = split_rbd_data(
        df_clean, test_size=0.15, val_size=0.15, seed=seed
    )

    # 4. Feature engineering
    X_train_raw = extract_rbd_features(df_train)
    X_val_raw = extract_rbd_features(df_val)
    X_test_raw = extract_rbd_features(df_test)

    features_used = list(X_train_raw.columns)

    y_train = df_train["diagnosis"].values
    y_val = df_val["diagnosis"].values
    y_test = df_test["diagnosis"].values

    # 5. Fit imputer and scaler strictly on TRAINING set — no leakage
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()

    X_train_imp = imputer.fit_transform(X_train_raw)
    X_train = scaler.fit_transform(X_train_imp)

    X_val_imp = imputer.transform(X_val_raw)
    X_val = scaler.transform(X_val_imp)

    X_test_imp = imputer.transform(X_test_raw)
    X_test = scaler.transform(X_test_imp)

    # 6. Define models
    models = {
        "logistic_regression": LogisticRegression(
            C=1.0, random_state=seed, max_iter=1000
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=100, max_depth=5, random_state=seed
        ),
        "xgboost": XGBClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.05,
            eval_metric="logloss", random_state=seed
        ),
    }

    results: Dict[str, Any] = {}
    best_model_name: str | None = None
    best_val_score: float = -1.0
    best_pipeline: Dict[str, Any] | None = None

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)

    for name, model in models.items():
        # Cross-validation strictly within training set
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="roc_auc")

        # Fit model on full training set
        model.fit(X_train, y_train)

        # Validation set evaluation
        val_pred = model.predict(X_val)
        val_prob = model.predict_proba(X_val)[:, 1]
        val_metrics = compute_evaluation_metrics(
            y_val, val_pred, val_prob, df_val["participant_id"].tolist()
        )

        # Test set evaluation
        test_pred = model.predict(X_test)
        test_prob = model.predict_proba(X_test)[:, 1]
        test_metrics = compute_evaluation_metrics(
            y_test, test_pred, test_prob, df_test["participant_id"].tolist()
        )

        results[name] = {
            "cv_roc_auc_mean": round(float(np.mean(cv_scores)), 4),
            "cv_roc_auc_std": round(float(np.std(cv_scores)), 4),
            "validation_metrics": val_metrics,
            "test_metrics": test_metrics,
            "model_object": model,
        }

        # Model selection: validation ROC-AUC (or F1 fallback)
        score = val_metrics["roc_auc"] if val_metrics["roc_auc"] is not None else val_metrics["f1"]
        if score > best_val_score:
            best_val_score = score
            best_model_name = name
            best_pipeline = {
                "imputer": imputer,
                "scaler": scaler,
                "model": model,
                "model_name": name,
                "features_used": features_used,
            }

    # 7. Save model artifacts
    models_dir = Path("models/rbd")
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / "model.joblib"
    joblib.dump(best_pipeline, model_path)

    limitations = RBD_LIMITATIONS + (
        [
            "Real RBD data unavailable locally; evaluation generated using "
            "synthetic fixture in simulation mode."
        ]
        if not_trained else []
    )

    metadata: Dict[str, Any] = {
        "modality": "rbd",
        "model_type": best_model_name,
        "dataset_id": dataset_id,
        "dataset_category": dataset_category,
        "experiment_type": experiment_type,
        "not_trained": not_trained,
        "features_used": features_used,
        "feature_schema": {k: v for k, v in FEATURE_SCHEMA.items() if k in features_used},
        "target_label": "diagnosis",
        "training_samples": int(len(df_train)),
        "validation_samples": int(len(df_val)),
        "test_samples": int(len(df_test)),
        "metrics": {
            "validation": results[best_model_name]["validation_metrics"],
            "test": results[best_model_name]["test_metrics"],
            "cv_roc_auc_mean": results[best_model_name]["cv_roc_auc_mean"],
            "cv_roc_auc_std": results[best_model_name]["cv_roc_auc_std"],
        },
        "seed": seed,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "limitations": limitations,
        "clinical_claim": False,
        "rbd_diagnosis_claim": False,
    }

    metadata_path = models_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # 8. Save evaluation results
    eval_dir = Path("evaluation")
    eval_dir.mkdir(parents=True, exist_ok=True)
    eval_path = eval_dir / "rbd_results.json"

    eval_output: Dict[str, Any] = {
        "phase": 2,
        "modality": "rbd",
        "dataset_id": dataset_id,
        "experiment_type": experiment_type,
        "not_trained": not_trained,
        "models_compared": list(models.keys()),
        "best_model": best_model_name,
        "metrics": {
            model_name: {
                "validation": res["validation_metrics"],
                "test": res["test_metrics"],
                "cv_roc_auc_mean": res["cv_roc_auc_mean"],
                "cv_roc_auc_std": res["cv_roc_auc_std"],
            }
            for model_name, res in results.items()
        },
        "features_used": features_used,
        "feature_schema": {k: v for k, v in FEATURE_SCHEMA.items() if k in features_used},
        "limitations": limitations,
        "clinical_claim": False,
        "rbd_diagnosis_claim": False,
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
        "not_trained": not_trained,
        "metadata": metadata,
        "evaluation": eval_output,
    }


if __name__ == "__main__":
    res = run_rbd_pipeline()
    print("RBD pipeline completed successfully!")
    print(f"Experiment Type: {res['experiment_type']}")
    print(f"Not Trained (simulation mode): {res['not_trained']}")
    print(f"Best Model: {res['best_model']} (Val Score: {res['best_val_score']})")
