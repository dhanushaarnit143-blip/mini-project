"""
Unit tests for RBD Questionnaire ML Risk Pipeline (src/rbd).
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
from src.rbd.features import extract_rbd_features, BASE_FEATURE_COLUMNS
from src.rbd.train import run_rbd_pipeline
from src.rbd.predict import predict_rbd
from src.data.validators import validate_participant_split


def test_rbd_data_loading_fallback():
    """Verify loading falls back to synthetic fixture when real file is absent."""
    df, exp_type = load_rbd_data("non_existent_file.csv")
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert exp_type == "simulation"
    assert "participant_id" in df.columns
    assert "rbdsq_total" in df.columns


def test_rbd_preprocessing_and_range():
    """Verify preprocessing validates columns and clips scores to valid RBDSQ range."""
    raw_df = pd.DataFrame({
        "participant_id": ["P1", "P2", "P3"],
        "rbdsq_total": [-2, 6, 18],
        "diagnosis": [0, 1, 0]
    })
    clean_df = preprocess_rbd_data(raw_df)
    assert clean_df["rbdsq_total"].min() >= 0
    assert clean_df["rbdsq_total"].max() <= 13


def test_rbd_feature_engineering_keys():
    """Verify feature engineering produces expected base columns and item subscores."""
    df = generate_synthetic_rbd_data(n_participants=10, seed=42)
    feat = extract_rbd_features(df)
    for col in BASE_FEATURE_COLUMNS:
        assert col in feat.columns, f"Missing base RBD feature column: {col}"
    assert len(feat) == 10


def test_rbd_participant_split_disjoint():
    """Verify train, validation, and test splits have zero participant ID overlap."""
    df = generate_synthetic_rbd_data(n_participants=50, seed=42)
    df_clean = preprocess_rbd_data(df)
    df_train, df_val, df_test = split_rbd_data(df_clean, test_size=0.2, val_size=0.2, seed=42)

    train_ids = df_train["participant_id"].unique()
    val_ids = df_val["participant_id"].unique()
    test_ids = df_test["participant_id"].unique()

    assert validate_participant_split(train_ids, val_ids, test_ids) is True
    assert len(train_ids) + len(val_ids) + len(test_ids) == len(df_clean["participant_id"].unique())


def test_rbd_train_pipeline_and_artifacts():
    """Verify complete RBD training pipeline execution and metadata structure."""
    result = run_rbd_pipeline(data_path="non_existent_path.csv", seed=42)

    assert result["best_model"] in ["logistic_regression", "random_forest", "xgboost"]
    assert result["experiment_type"] == "simulation"

    model_path = Path("models/rbd/model.joblib")
    metadata_path = Path("models/rbd/metadata.json")
    eval_path = Path("evaluation/rbd_results.json")

    assert model_path.exists()
    assert metadata_path.exists()
    assert eval_path.exists()

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    required_meta_keys = [
        "modality", "model_type", "dataset_id", "dataset_category",
        "features_used", "target_label", "training_samples",
        "validation_samples", "test_samples", "metrics", "seed",
        "timestamp", "limitations", "clinical_claim"
    ]
    for key in required_meta_keys:
        assert key in meta, f"Metadata missing required key: {key}"

    assert meta["modality"] == "rbd"
    assert meta["clinical_claim"] is False


def test_rbd_predict_bounds_and_missing_features():
    """Verify prediction function output range [0, 1] and missing feature safety warnings."""
    run_rbd_pipeline(seed=42)

    input_features = {
        "rbdsq_total": 7.0,
        "item_6": 1.0,
        "item_1": 1.0,
        "item_2": 0.0
    }
    pred_res = predict_rbd(input_features)

    assert pred_res["modality"] == "rbd"
    assert 0.0 <= pred_res["risk_score"] <= 1.0
    assert isinstance(pred_res["warnings"], list)

    missing_features = {}
    pred_missing = predict_rbd(missing_features)
    assert 0.0 <= pred_missing["risk_score"] <= 1.0
    assert len(pred_missing["warnings"]) > 0
    assert any("missing" in w.lower() for w in pred_missing["warnings"])
