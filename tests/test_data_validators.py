"""
Unit tests for src/data/validators.py using tiny synthetic DataFrames.
"""

import pytest
import pandas as pd
from src.data.validators import (
    validate_required_columns,
    validate_no_duplicate_participants,
    validate_label_column,
    validate_missingness,
    validate_participant_split,
    validate_modality_presence,
)


def test_validate_required_columns_success():
    """Test validate_required_columns passes when all required columns are present."""
    df = pd.DataFrame({"participant_id": [1, 2], "upsit_score": [30, 35]})
    assert validate_required_columns(df, ["participant_id", "upsit_score"]) is True


def test_validate_required_columns_failure():
    """Test validate_required_columns raises ValueError when columns are missing."""
    df = pd.DataFrame({"participant_id": [1, 2]})
    with pytest.raises(ValueError, match="missing required columns"):
        validate_required_columns(df, ["participant_id", "rbd_score"])


def test_validate_no_duplicate_participants_success():
    """Test validate_no_duplicate_participants passes for unique IDs."""
    df = pd.DataFrame({"participant_id": ["P001", "P002", "P003"]})
    assert validate_no_duplicate_participants(df, "participant_id") is True


def test_validate_no_duplicate_participants_failure():
    """Test validate_no_duplicate_participants detects duplicate participant IDs."""
    df = pd.DataFrame({"participant_id": ["P001", "P002", "P001"]})
    with pytest.raises(ValueError, match="duplicate participant ID"):
        validate_no_duplicate_participants(df, "participant_id")


def test_validate_label_column_success():
    """Test validate_label_column passes for allowed label values."""
    df = pd.DataFrame({"diagnosis": [0, 1, 2, 0, 1]})
    assert validate_label_column(df, "diagnosis", [0, 1, 2]) is True


def test_validate_label_column_failure():
    """Test validate_label_column raises ValueError when invalid label is present."""
    df = pd.DataFrame({"diagnosis": [0, 1, 99]})
    with pytest.raises(ValueError, match="invalid value"):
        validate_label_column(df, "diagnosis", [0, 1, 2])


def test_validate_missingness_success():
    """Test validate_missingness passes when missingness is below threshold."""
    df = pd.DataFrame({
        "col_a": [1.0, 2.0, None, 4.0, 5.0],  # 20% missing
        "col_b": [1.0, 2.0, 3.0, 4.0, 5.0],   # 0% missing
    })
    report = validate_missingness(df, threshold=0.3)
    assert report["passed"] is True
    assert report["missing_ratios"]["col_a"] == 0.2


def test_validate_missingness_failure():
    """Test validate_missingness raises ValueError when missingness exceeds threshold."""
    df = pd.DataFrame({
        "col_a": [1.0, None, None, None, 5.0],  # 60% missing
    })
    with pytest.raises(ValueError, match="exceed maximum allowed missingness"):
        validate_missingness(df, threshold=0.5)


def test_validate_participant_split_success():
    """Test validate_participant_split passes for disjoint sets."""
    train_ids = ["P1", "P2", "P3"]
    val_ids = ["P4", "P5"]
    test_ids = ["P6", "P7"]
    assert validate_participant_split(train_ids, val_ids, test_ids) is True


def test_validate_participant_split_leakage():
    """Test validate_participant_split detects train/test participant ID leakage."""
    train_ids = ["P1", "P2", "P3"]
    val_ids = ["P4", "P5"]
    test_ids = ["P3", "P6"]  # P3 is in both train and test!
    with pytest.raises(ValueError, match="Data leakage detected"):
        validate_participant_split(train_ids, val_ids, test_ids)


def test_validate_modality_presence():
    """Test validate_modality_presence verifies required modalities in metadata."""
    metadata = {
        "dataset_id": "ppmi",
        "modalities": ["olfactory", "rbd_sleep", "motor_gait"],
    }
    assert validate_modality_presence(metadata, ["olfactory", "rbd_sleep"]) is True

    with pytest.raises(ValueError, match="missing required modalities"):
        validate_modality_presence(metadata, ["olfactory", "retina_fundus"])
