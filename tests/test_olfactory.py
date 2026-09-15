"""
Unit and integration tests for the Olfactory ML Risk Pipeline (src/olfactory).

Coverage:
  - Data loading fallback (simulation mode)
  - Preprocessing range clipping
  - Feature schema completeness and required-column guard
  - Participant-level split disjointness (zero data leakage)
  - Cross-split leakage detection
  - Training pipeline: artifact creation, metadata fields, not_trained flag
  - Experiment type propagation to evaluation JSON
  - Prediction bounds and missing-feature safety
  - No age-adjustment claim in features or limitations
"""

import json
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from src.data.synthetic_fixture import generate_synthetic_olfactory_data
from src.olfactory.preprocess import (
    load_olfactory_data,
    preprocess_olfactory_data,
    split_olfactory_data,
)
from src.olfactory.features import (
    extract_olfactory_features,
    FEATURE_COLUMNS,
    FEATURE_SCHEMA,
    LIMITATIONS,
)
from src.olfactory.train import run_olfactory_pipeline
from src.olfactory.predict import predict_olfactory
from src.data.validators import validate_participant_split


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def test_olfactory_data_loading_fallback():
    """Verify loading falls back gracefully to synthetic fixture when real file missing."""
    df, exp_type = load_olfactory_data("non_existent_file.csv")
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert exp_type == "simulation"
    assert "participant_id" in df.columns
    assert "total_score" in df.columns
    assert "diagnosis" in df.columns


def test_olfactory_data_loading_returns_correct_tuple_types():
    """Verify return types from load_olfactory_data."""
    df, exp_type = load_olfactory_data("non_existent_file.csv")
    assert isinstance(df, pd.DataFrame)
    assert isinstance(exp_type, str)
    assert exp_type in ("simulation", "real_data")


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def test_olfactory_preprocessing_and_range():
    """Verify preprocessing validates columns and clips scores to valid UPSIT range [0, 40]."""
    raw_df = pd.DataFrame({
        "participant_id": ["P1", "P2", "P3"],
        "total_score": [-5, 25, 45],  # out-of-range scores
        "diagnosis": [0, 1, 0]
    })
    clean_df = preprocess_olfactory_data(raw_df)
    assert clean_df["total_score"].min() >= 0
    assert clean_df["total_score"].max() <= 40


def test_olfactory_preprocessing_missing_required_column_raises():
    """Verify preprocessing raises ValueError when required columns are missing."""
    bad_df = pd.DataFrame({"participant_id": ["P1"], "diagnosis": [0]})
    with pytest.raises((ValueError, KeyError)):
        preprocess_olfactory_data(bad_df)


def test_olfactory_preprocessing_invalid_label_raises():
    """Verify preprocessing raises ValueError for invalid label values."""
    bad_df = pd.DataFrame({
        "participant_id": ["P1"],
        "total_score": [20],
        "diagnosis": [99]  # invalid label
    })
    with pytest.raises(ValueError):
        preprocess_olfactory_data(bad_df)


# ---------------------------------------------------------------------------
# Feature Engineering
# ---------------------------------------------------------------------------

def test_olfactory_feature_engineering_keys():
    """Verify feature engineering produces exactly the expected FEATURE_COLUMNS."""
    df = generate_synthetic_olfactory_data(n_participants=10, seed=123)
    feat = extract_olfactory_features(df)
    assert list(feat.columns) == FEATURE_COLUMNS
    assert len(feat) == 10


def test_olfactory_feature_schema_coverage():
    """Verify FEATURE_SCHEMA documents every column in FEATURE_COLUMNS."""
    for col in FEATURE_COLUMNS:
        assert col in FEATURE_SCHEMA, f"FEATURE_SCHEMA missing entry for: {col}"
        assert "source" in FEATURE_SCHEMA[col]
        assert "missing_strategy" in FEATURE_SCHEMA[col]


def test_olfactory_feature_no_age_adjustment_fabricated():
    """Verify no age-adjusted score is silently added to features (per limitation)."""
    df = generate_synthetic_olfactory_data(n_participants=20, seed=42)
    feat = extract_olfactory_features(df)
    assert "age_adjusted_score" not in feat.columns, (
        "age_adjusted_score must NOT appear in features; no normative table available."
    )


def test_olfactory_feature_age_adjustment_in_limitations():
    """Verify LIMITATIONS explicitly documents the age-adjustment omission."""
    combined = " ".join(LIMITATIONS).lower()
    assert "age" in combined and "adjusted" in combined, (
        "LIMITATIONS must explicitly document that age-adjusted score is omitted."
    )


def test_olfactory_feature_required_column_guard():
    """Verify extract_olfactory_features raises ValueError when total_score is missing."""
    bad_df = pd.DataFrame({"participant_id": ["P1"], "diagnosis": [0]})
    with pytest.raises(ValueError, match="total_score"):
        extract_olfactory_features(bad_df)


def test_olfactory_features_pct_correct_derivation():
    """Verify pct_correct equals total_score / 40 (no leakage, deterministic)."""
    df = pd.DataFrame({
        "participant_id": ["P1", "P2"],
        "total_score": [20, 40],
        "diagnosis": [1, 0]
    })
    feat = extract_olfactory_features(df)
    np.testing.assert_allclose(feat["pct_correct"].values, [0.5, 1.0], atol=1e-4)


# ---------------------------------------------------------------------------
# Participant-Level Split / Leakage Prevention
# ---------------------------------------------------------------------------

def test_olfactory_participant_split_disjoint():
    """Verify train/val/test splits have zero participant ID overlap."""
    df = generate_synthetic_olfactory_data(n_participants=50, seed=42)
    df_clean = preprocess_olfactory_data(df)
    df_train, df_val, df_test = split_olfactory_data(df_clean, test_size=0.2, val_size=0.2, seed=42)

    train_ids = df_train["participant_id"].unique()
    val_ids = df_val["participant_id"].unique()
    test_ids = df_test["participant_id"].unique()

    assert validate_participant_split(train_ids, val_ids, test_ids) is True
    assert len(train_ids) + len(val_ids) + len(test_ids) == len(df_clean["participant_id"].unique())


def test_olfactory_split_no_train_test_overlap():
    """Direct set-intersection check: training IDs must not appear in test set."""
    df = generate_synthetic_olfactory_data(n_participants=60, seed=7)
    df_clean = preprocess_olfactory_data(df)
    df_train, df_val, df_test = split_olfactory_data(df_clean, seed=7)

    train_set = set(df_train["participant_id"].tolist())
    test_set = set(df_test["participant_id"].tolist())
    val_set = set(df_val["participant_id"].tolist())

    assert train_set.isdisjoint(test_set), "DATA LEAKAGE: train IDs found in test set"
    assert train_set.isdisjoint(val_set), "DATA LEAKAGE: train IDs found in val set"
    assert val_set.isdisjoint(test_set), "DATA LEAKAGE: val IDs found in test set"


def test_olfactory_split_covers_all_participants():
    """Verify all participants end up in exactly one split."""
    df = generate_synthetic_olfactory_data(n_participants=100, seed=99)
    df_clean = preprocess_olfactory_data(df)
    df_train, df_val, df_test = split_olfactory_data(df_clean, seed=99)

    all_ids = set(df_clean["participant_id"].tolist())
    combined = (
        set(df_train["participant_id"].tolist())
        | set(df_val["participant_id"].tolist())
        | set(df_test["participant_id"].tolist())
    )
    assert combined == all_ids, "Some participants were lost during splitting"


# ---------------------------------------------------------------------------
# Training Pipeline & Artifacts
# ---------------------------------------------------------------------------

def test_olfactory_train_pipeline_and_artifacts():
    """Verify complete training pipeline execution and metadata structure."""
    result = run_olfactory_pipeline(data_path="non_existent_path.csv", seed=42)

    assert result["best_model"] in ["logistic_regression", "random_forest", "xgboost"]
    assert result["experiment_type"] == "simulation"
    assert result["not_trained"] is True

    model_path = Path("models/olfactory/model.joblib")
    metadata_path = Path("models/olfactory/metadata.json")
    eval_path = Path("evaluation/olfactory_results.json")

    assert model_path.exists(), "model.joblib artifact not found"
    assert metadata_path.exists(), "metadata.json artifact not found"
    assert eval_path.exists(), "olfactory_results.json not found"

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    required_meta_keys = [
        "modality", "model_type", "dataset_id", "dataset_category",
        "experiment_type", "not_trained",
        "features_used", "feature_schema", "target_label",
        "training_samples", "validation_samples", "test_samples",
        "metrics", "seed", "timestamp", "limitations", "clinical_claim",
    ]
    for key in required_meta_keys:
        assert key in meta, f"Metadata missing required key: {key}"

    assert meta["modality"] == "olfactory"
    assert meta["clinical_claim"] is False
    assert meta["not_trained"] is True
    assert meta["experiment_type"] == "simulation"
    assert "cv_roc_auc_std" in meta["metrics"]


def test_olfactory_experiment_type_propagated_to_eval_json():
    """Verify experiment_type and not_trained flags are propagated to evaluation JSON."""
    run_olfactory_pipeline(data_path="non_existent_path.csv", seed=42)
    with open("evaluation/olfactory_results.json", "r", encoding="utf-8") as f:
        ev = json.load(f)

    assert ev["experiment_type"] == "simulation"
    assert ev["not_trained"] is True
    assert ev["modality"] == "olfactory"


def test_olfactory_eval_json_has_cv_roc_auc_std():
    """Verify evaluation JSON includes cv_roc_auc_std for each model."""
    run_olfactory_pipeline(data_path="non_existent_path.csv", seed=42)
    with open("evaluation/olfactory_results.json", "r", encoding="utf-8") as f:
        ev = json.load(f)
    for model_name, model_res in ev["metrics"].items():
        assert "cv_roc_auc_std" in model_res, (
            f"cv_roc_auc_std missing from eval JSON for model: {model_name}"
        )


def test_olfactory_eval_json_has_feature_schema():
    """Verify evaluation JSON includes feature_schema."""
    run_olfactory_pipeline(data_path="non_existent_path.csv", seed=42)
    with open("evaluation/olfactory_results.json", "r", encoding="utf-8") as f:
        ev = json.load(f)
    assert "feature_schema" in ev
    for col in FEATURE_COLUMNS:
        assert col in ev["feature_schema"], f"feature_schema missing entry for: {col}"


def test_olfactory_metadata_no_age_adjustment_fabrication():
    """Verify limitations in metadata explicitly document age-adjustment omission."""
    run_olfactory_pipeline(data_path="non_existent_path.csv", seed=42)
    with open("models/olfactory/metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    combined = " ".join(meta["limitations"]).lower()
    assert "age" in combined and "adjusted" in combined and "omit" in combined


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

def test_olfactory_predict_bounds_and_missing_features():
    """Verify prediction output range [0, 1] and graceful missing feature handling."""
    run_olfactory_pipeline(seed=42)

    input_features = {
        "total_score": 18.0,
        "response_time_mean": 4.5,
        "n_errors": 22.0,
        "error_pattern_flags": 3.0,
    }
    pred_res = predict_olfactory(input_features)

    assert pred_res["modality"] == "olfactory"
    assert 0.0 <= pred_res["risk_score"] <= 1.0
    assert isinstance(pred_res["warnings"], list)


def test_olfactory_predict_missing_critical_feature():
    """Verify prediction returns neutral score and warning when total_score is absent."""
    run_olfactory_pipeline(seed=42)
    pred_missing = predict_olfactory({})
    assert 0.0 <= pred_missing["risk_score"] <= 1.0
    assert len(pred_missing["warnings"]) > 0
    assert any("missing" in w.lower() for w in pred_missing["warnings"])


def test_olfactory_predict_high_score_lower_risk():
    """Verify a high UPSIT score (control-like) produces lower risk than a low score (PD-like)."""
    run_olfactory_pipeline(seed=42)
    high_score_pred = predict_olfactory({"total_score": 38.0, "n_errors": 2.0, "error_pattern_flags": 0.0})
    low_score_pred = predict_olfactory({"total_score": 10.0, "n_errors": 30.0, "error_pattern_flags": 5.0})
    # High UPSIT score → lower PD risk
    assert high_score_pred["risk_score"] < low_score_pred["risk_score"]


def test_olfactory_predict_invalid_input_type_raises():
    """Verify predict_olfactory raises TypeError for non-dict input."""
    run_olfactory_pipeline(seed=42)
    with pytest.raises(TypeError):
        predict_olfactory("not_a_dict")
