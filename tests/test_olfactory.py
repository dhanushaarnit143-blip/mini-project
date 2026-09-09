"""
Unit tests for Olfactory ML Risk Pipeline (src/olfactory).
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
from src.olfactory.features import extract_olfactory_features, FEATURE_COLUMNS
from src.olfactory.train import run_olfactory_pipeline
from src.olfactory.predict import predict_olfactory
from src.data.validators import validate_participant_split


def test_olfactory_data_loading_fallback():
    """Verify loading falls back gracefully to synthetic fixture when real file missing."""
    df, exp_type = load_olfactory_data("non_existent_file.csv")
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert exp_type == "simulation"
    assert "participant_id" in df.columns
    assert "total_score" in df.columns


def test_olfactory_preprocessing_and_range():
    """Verify preprocessing validates columns and clips scores to valid UPSIT range."""
    raw_df = pd.DataFrame({
        "participant_id": ["P1", "P2", "P3"],
        "total_score": [-5, 25, 45],  # Out of range scores
        "diagnosis": [0, 1, 0]
    })
    clean_df = preprocess_olfactory_data(raw_df)
    assert clean_df["total_score"].min() >= 0
    assert clean_df["total_score"].max() <= 40


def test_olfactory_feature_engineering_keys():
    """Verify feature engineering produces expected columns."""
    df = generate_synthetic_olfactory_data(n_participants=10, seed=123)
    feat = extract_olfactory_features(df)
    for col in FEATURE_COLUMNS:
        assert col in feat.columns, f"Missing feature column: {col}"
    assert len(feat) == 10


def test_olfactory_participant_split_disjoint():
    """Verify train, validation, and test splits have zero participant ID overlap."""
    df = generate_synthetic_olfactory_data(n_participants=50, seed=42)
    df_clean = preprocess_olfactory_data(df)
    df_train, df_val, df_test = split_olfactory_data(df_clean, test_size=0.2, val_size=0.2, seed=42)

    train_ids = df_train["participant_id"].unique()
    val_ids = df_val["participant_id"].unique()
    test_ids = df_test["participant_id"].unique()

    # Enforce zero data leakage
    assert validate_participant_split(train_ids, val_ids, test_ids) is True
    assert len(train_ids) + len(val_ids) + len(test_ids) == len(df_clean["participant_id"].unique())


def test_olfactory_train_pipeline_and_artifacts():
    """Verify complete training pipeline execution and metadata structure."""
    result = run_olfactory_pipeline(data_path="non_existent_path.csv", seed=42)
    
    assert result["best_model"] in ["logistic_regression", "random_forest", "xgboost"]
    assert result["experiment_type"] == "simulation"

    # Verify model artifact files created
    model_path = Path("models/olfactory/model.joblib")
    metadata_path = Path("models/olfactory/metadata.json")
    eval_path = Path("evaluation/olfactory_results.json")

    assert model_path.exists()
    assert metadata_path.exists()
    assert eval_path.exists()

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Check mandatory metadata fields
    required_meta_keys = [
        "modality", "model_type", "dataset_id", "dataset_category",
        "features_used", "target_label", "training_samples",
        "validation_samples", "test_samples", "metrics", "seed",
        "timestamp", "limitations", "clinical_claim"
    ]
    for key in required_meta_keys:
        assert key in meta, f"Metadata missing required key: {key}"

    assert meta["modality"] == "olfactory"
    assert meta["clinical_claim"] is False


def test_olfactory_predict_bounds_and_missing_features():
    """Verify prediction function output range [0, 1] and graceful missing feature handling."""
    # Ensure model is trained
    run_olfactory_pipeline(seed=42)

    # Valid complete features
    input_features = {
        "total_score": 18.0,
        "response_time_mean": 4.5,
        "n_errors": 22.0,
        "error_pattern_flags": 3.0
    }
    pred_res = predict_olfactory(input_features)

    assert pred_res["modality"] == "olfactory"
    assert 0.0 <= pred_res["risk_score"] <= 1.0
    assert isinstance(pred_res["warnings"], list)

    # Missing critical feature test
    missing_features = {}
    pred_missing = predict_olfactory(missing_features)
    assert 0.0 <= pred_missing["risk_score"] <= 1.0
    assert len(pred_missing["warnings"]) > 0
    assert any("missing" in w.lower() for w in pred_missing["warnings"])
