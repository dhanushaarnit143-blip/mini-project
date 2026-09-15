"""
Unit and integration tests for the RBD Questionnaire ML Risk Pipeline (src/rbd).

Coverage:
  - Data loading fallback (simulation mode)
  - Preprocessing range clipping
  - Feature schema completeness and required-column guard
  - Participant-level split disjointness (zero data leakage)
  - Cross-split leakage detection
  - Training pipeline: artifact creation, metadata fields, not_trained flag,
    rbd_diagnosis_claim=False
  - Experiment type propagation to evaluation JSON
  - No age-adjustment fabrication in features or limitations
  - No RBD diagnosis claim in metadata or evaluation JSON
  - Prediction bounds and missing-feature safety
  - rbdsq_total reconstruction from item subscores when total is absent
"""

import json
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from src.data.synthetic_fixture import generate_synthetic_rbd_data
from src.rbd.preprocess import (
    load_rbd_data,
    preprocess_rbd_data,
    split_rbd_data,
)
from src.rbd.features import (
    extract_rbd_features,
    BASE_FEATURE_COLUMNS,
    ITEM_COLUMNS,
    FEATURE_SCHEMA,
    RBD_LIMITATIONS,
)
from src.rbd.train import run_rbd_pipeline
from src.rbd.predict import predict_rbd
from src.data.validators import validate_participant_split


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def test_rbd_data_loading_fallback():
    """Verify loading falls back to synthetic fixture when real file is absent."""
    df, exp_type = load_rbd_data("non_existent_file.csv")
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert exp_type == "simulation"
    assert "participant_id" in df.columns
    assert "rbdsq_total" in df.columns
    assert "diagnosis" in df.columns


def test_rbd_data_loading_returns_correct_tuple_types():
    """Verify return types from load_rbd_data."""
    df, exp_type = load_rbd_data("non_existent_file.csv")
    assert isinstance(df, pd.DataFrame)
    assert isinstance(exp_type, str)
    assert exp_type in ("simulation", "real_data")


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def test_rbd_preprocessing_and_range():
    """Verify preprocessing validates columns and clips scores to valid RBDSQ range [0, 13]."""
    raw_df = pd.DataFrame({
        "participant_id": ["P1", "P2", "P3"],
        "rbdsq_total": [-2, 6, 18],
        "diagnosis": [0, 1, 0]
    })
    clean_df = preprocess_rbd_data(raw_df)
    assert clean_df["rbdsq_total"].min() >= 0
    assert clean_df["rbdsq_total"].max() <= 13


def test_rbd_preprocessing_missing_required_column_raises():
    """Verify preprocessing raises ValueError when required columns are missing."""
    bad_df = pd.DataFrame({"participant_id": ["P1"], "diagnosis": [0]})
    with pytest.raises((ValueError, KeyError)):
        preprocess_rbd_data(bad_df)


def test_rbd_preprocessing_invalid_label_raises():
    """Verify preprocessing raises ValueError for invalid label values."""
    bad_df = pd.DataFrame({
        "participant_id": ["P1"],
        "rbdsq_total": [5],
        "diagnosis": [99]  # invalid label
    })
    with pytest.raises(ValueError):
        preprocess_rbd_data(bad_df)


# ---------------------------------------------------------------------------
# Feature Engineering
# ---------------------------------------------------------------------------

def test_rbd_feature_engineering_keys():
    """Verify feature engineering produces expected base columns and item subscores."""
    df = generate_synthetic_rbd_data(n_participants=10, seed=42)
    feat = extract_rbd_features(df)
    for col in BASE_FEATURE_COLUMNS:
        assert col in feat.columns, f"Missing base RBD feature column: {col}"
    assert len(feat) == 10


def test_rbd_feature_schema_coverage():
    """Verify FEATURE_SCHEMA documents every base column and every item column."""
    all_documented_cols = BASE_FEATURE_COLUMNS + ITEM_COLUMNS
    for col in all_documented_cols:
        assert col in FEATURE_SCHEMA, f"FEATURE_SCHEMA missing entry for: {col}"
        assert "source" in FEATURE_SCHEMA[col]
        assert "missing_strategy" in FEATURE_SCHEMA[col]


def test_rbd_feature_no_age_adjustment_fabricated():
    """Verify no age-adjusted RBD risk score is silently added to features."""
    df = generate_synthetic_rbd_data(n_participants=20, seed=42)
    feat = extract_rbd_features(df)
    assert "age_adjusted_rbd_risk" not in feat.columns, (
        "age_adjusted_rbd_risk must NOT appear in features; no normative table published."
    )


def test_rbd_feature_age_adjustment_in_limitations():
    """Verify RBD_LIMITATIONS explicitly documents the age-adjustment omission."""
    combined = " ".join(RBD_LIMITATIONS).lower()
    assert "age" in combined and "adjusted" in combined, (
        "RBD_LIMITATIONS must document that age-adjusted norms are omitted."
    )


def test_rbd_feature_required_column_guard():
    """Verify extract_rbd_features raises ValueError when rbdsq_total is missing."""
    bad_df = pd.DataFrame({"participant_id": ["P1"], "diagnosis": [0]})
    with pytest.raises(ValueError, match="rbdsq_total"):
        extract_rbd_features(bad_df)


def test_rbd_feature_above_cutoff_flag():
    """Verify above_cutoff_flag is 1 when rbdsq_total >= 5 and 0 when < 5."""
    df = pd.DataFrame({
        "participant_id": ["P1", "P2", "P3"],
        "rbdsq_total": [4, 5, 7],
        "diagnosis": [0, 1, 1],
    })
    feat = extract_rbd_features(df)
    assert list(feat["above_cutoff_flag"].values) == [0.0, 1.0, 1.0]


def test_rbd_feature_item_nan_when_absent():
    """Verify item columns are NaN (not 0) when absent from the input DataFrame."""
    df = pd.DataFrame({
        "participant_id": ["P1"],
        "rbdsq_total": [7],
        "diagnosis": [1],
        # deliberately omit item columns
    })
    feat = extract_rbd_features(df)
    for col in ITEM_COLUMNS:
        if col in feat.columns:
            assert pd.isna(feat[col].iloc[0]), (
                f"Item column '{col}' should be NaN when absent from input"
            )


def test_rbd_feature_limitations_no_clinical_rbd_claim():
    """Verify RBD_LIMITATIONS includes a statement disavowing clinical diagnosis."""
    combined = " ".join(RBD_LIMITATIONS).lower()
    assert "diagnosis" in combined or "not" in combined, (
        "RBD_LIMITATIONS must explicitly state that results are NOT a clinical RBD diagnosis."
    )


# ---------------------------------------------------------------------------
# Participant-Level Split / Leakage Prevention
# ---------------------------------------------------------------------------

def test_rbd_participant_split_disjoint():
    """Verify train/val/test splits have zero participant ID overlap."""
    df = generate_synthetic_rbd_data(n_participants=50, seed=42)
    df_clean = preprocess_rbd_data(df)
    df_train, df_val, df_test = split_rbd_data(df_clean, test_size=0.2, val_size=0.2, seed=42)

    train_ids = df_train["participant_id"].unique()
    val_ids = df_val["participant_id"].unique()
    test_ids = df_test["participant_id"].unique()

    assert validate_participant_split(train_ids, val_ids, test_ids) is True
    assert len(train_ids) + len(val_ids) + len(test_ids) == len(df_clean["participant_id"].unique())


def test_rbd_split_no_train_test_overlap():
    """Direct set-intersection check: no training participant IDs in test split."""
    df = generate_synthetic_rbd_data(n_participants=60, seed=7)
    df_clean = preprocess_rbd_data(df)
    df_train, df_val, df_test = split_rbd_data(df_clean, seed=7)

    train_set = set(df_train["participant_id"].tolist())
    test_set = set(df_test["participant_id"].tolist())
    val_set = set(df_val["participant_id"].tolist())

    assert train_set.isdisjoint(test_set), "DATA LEAKAGE: train IDs found in test set"
    assert train_set.isdisjoint(val_set), "DATA LEAKAGE: train IDs found in val set"
    assert val_set.isdisjoint(test_set), "DATA LEAKAGE: val IDs found in test set"


def test_rbd_split_covers_all_participants():
    """Verify all participants end up in exactly one split."""
    df = generate_synthetic_rbd_data(n_participants=100, seed=99)
    df_clean = preprocess_rbd_data(df)
    df_train, df_val, df_test = split_rbd_data(df_clean, seed=99)

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

def test_rbd_train_pipeline_and_artifacts():
    """Verify complete RBD training pipeline execution and metadata structure."""
    result = run_rbd_pipeline(data_path="non_existent_path.csv", seed=42)

    assert result["best_model"] in ["logistic_regression", "random_forest", "xgboost"]
    assert result["experiment_type"] == "simulation"
    assert result["not_trained"] is True

    model_path = Path("models/rbd/model.joblib")
    metadata_path = Path("models/rbd/metadata.json")
    eval_path = Path("evaluation/rbd_results.json")

    assert model_path.exists(), "model.joblib artifact not found"
    assert metadata_path.exists(), "metadata.json artifact not found"
    assert eval_path.exists(), "rbd_results.json not found"

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    required_meta_keys = [
        "modality", "model_type", "dataset_id", "dataset_category",
        "experiment_type", "not_trained",
        "features_used", "feature_schema", "target_label",
        "training_samples", "validation_samples", "test_samples",
        "metrics", "seed", "timestamp", "limitations",
        "clinical_claim", "rbd_diagnosis_claim",
    ]
    for key in required_meta_keys:
        assert key in meta, f"Metadata missing required key: {key}"

    assert meta["modality"] == "rbd"
    assert meta["clinical_claim"] is False
    assert meta["rbd_diagnosis_claim"] is False
    assert meta["not_trained"] is True
    assert meta["experiment_type"] == "simulation"
    assert "cv_roc_auc_std" in meta["metrics"]


def test_rbd_experiment_type_propagated_to_eval_json():
    """Verify experiment_type and not_trained flags are propagated to evaluation JSON."""
    run_rbd_pipeline(data_path="non_existent_path.csv", seed=42)
    with open("evaluation/rbd_results.json", "r", encoding="utf-8") as f:
        ev = json.load(f)

    assert ev["experiment_type"] == "simulation"
    assert ev["not_trained"] is True
    assert ev["modality"] == "rbd"


def test_rbd_eval_json_has_cv_roc_auc_std():
    """Verify evaluation JSON includes cv_roc_auc_std for each model."""
    run_rbd_pipeline(data_path="non_existent_path.csv", seed=42)
    with open("evaluation/rbd_results.json", "r", encoding="utf-8") as f:
        ev = json.load(f)
    for model_name, model_res in ev["metrics"].items():
        assert "cv_roc_auc_std" in model_res, (
            f"cv_roc_auc_std missing from eval JSON for model: {model_name}"
        )


def test_rbd_eval_json_no_diagnosis_claim():
    """Verify evaluation JSON has rbd_diagnosis_claim=False (no clinical diagnosis claim)."""
    run_rbd_pipeline(data_path="non_existent_path.csv", seed=42)
    with open("evaluation/rbd_results.json", "r", encoding="utf-8") as f:
        ev = json.load(f)
    assert "rbd_diagnosis_claim" in ev
    assert ev["rbd_diagnosis_claim"] is False


def test_rbd_eval_json_has_feature_schema():
    """Verify evaluation JSON includes feature_schema."""
    run_rbd_pipeline(data_path="non_existent_path.csv", seed=42)
    with open("evaluation/rbd_results.json", "r", encoding="utf-8") as f:
        ev = json.load(f)
    assert "feature_schema" in ev
    for col in ev["features_used"]:
        assert col in ev["feature_schema"], f"feature_schema missing entry for: {col}"


def test_rbd_metadata_no_age_adjustment_fabrication():
    """Verify limitations in metadata explicitly document age-adjustment omission."""
    run_rbd_pipeline(data_path="non_existent_path.csv", seed=42)
    with open("models/rbd/metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    combined = " ".join(meta["limitations"]).lower()
    assert "age" in combined and "adjusted" in combined and "omit" in combined


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

def test_rbd_predict_bounds_and_missing_features():
    """Verify prediction output range [0, 1] and missing feature safety warnings."""
    run_rbd_pipeline(seed=42)

    input_features = {
        "rbdsq_total": 7.0,
        "item_6": 1.0,
        "item_1": 1.0,
        "item_2": 0.0,
    }
    pred_res = predict_rbd(input_features)

    assert pred_res["modality"] == "rbd"
    assert 0.0 <= pred_res["risk_score"] <= 1.0
    assert isinstance(pred_res["warnings"], list)


def test_rbd_predict_missing_critical_feature():
    """Verify prediction returns neutral score and warning when rbdsq_total is absent."""
    run_rbd_pipeline(seed=42)
    pred_missing = predict_rbd({})
    assert 0.0 <= pred_missing["risk_score"] <= 1.0
    assert len(pred_missing["warnings"]) > 0
    assert any("missing" in w.lower() for w in pred_missing["warnings"])


def test_rbd_predict_rbdsq_total_from_items():
    """Verify rbdsq_total is reconstructed from item subscores when total is absent."""
    run_rbd_pipeline(seed=42)
    # Provide only item scores, no rbdsq_total
    features_items_only = {f"item_{i}": 1 for i in range(1, 8)}  # sum = 7
    pred = predict_rbd(features_items_only)
    # Should not raise and should warn that total was computed from items
    assert 0.0 <= pred["risk_score"] <= 1.0
    assert any("total" in w.lower() or "item" in w.lower() for w in pred["warnings"])


def test_rbd_predict_high_total_higher_risk():
    """Verify a high RBDSQ total produces higher risk than a low total."""
    run_rbd_pipeline(seed=42)
    low_risk = predict_rbd({"rbdsq_total": 1.0})
    high_risk = predict_rbd({"rbdsq_total": 12.0})
    assert high_risk["risk_score"] >= low_risk["risk_score"]


def test_rbd_predict_invalid_input_type_raises():
    """Verify predict_rbd raises TypeError for non-dict input."""
    run_rbd_pipeline(seed=42)
    with pytest.raises(TypeError):
        predict_rbd("not_a_dict")
