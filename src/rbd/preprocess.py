"""
RBD Questionnaire Data Preprocessing and Partitioning Module.

Handles loading, validation, cleaning, and participant-level splitting for RBDSQ data.
Prevents data leakage across train/validation/test splits.
"""

from pathlib import Path
from typing import Tuple, Dict, Any
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

from src.data.validators import (
    validate_required_columns,
    validate_label_column,
    validate_participant_split,
)
from src.data.synthetic_fixture import generate_synthetic_rbd_data


def load_rbd_data(
    data_path: str = "data/raw/ppmi/RBDSQ.csv"
) -> Tuple[pd.DataFrame, str]:
    """
    Loads raw RBDSQ dataset if present locally; otherwise falls back to labeled synthetic unit-test fixture.

    Args:
        data_path: Path to real RBDSQ CSV dataset.

    Returns:
        Tuple[pd.DataFrame, str]: (DataFrame, experiment_type) where experiment_type is 'real_data' or 'simulation'.
    """
    path = Path(data_path)
    if path.exists() and path.is_file():
        df = pd.read_csv(path)
        experiment_type = "real_data"
    else:
        df = generate_synthetic_rbd_data(n_participants=300, seed=42)
        experiment_type = "simulation"

    return df, experiment_type


def preprocess_rbd_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess raw RBDSQ dataframe: enforce column checking and range validation.

    Args:
        df: Raw RBDSQ DataFrame.

    Returns:
        pd.DataFrame: Cleaned DataFrame.
    """
    validate_required_columns(df, ["participant_id", "rbdsq_total", "diagnosis"])
    validate_label_column(df, "diagnosis", [0, 1])

    cleaned_df = df.copy()
    cleaned_df["rbdsq_total"] = np.clip(cleaned_df["rbdsq_total"], 0, 13)

    return cleaned_df


def split_rbd_data(
    df: pd.DataFrame,
    test_size: float = 0.15,
    val_size: float = 0.15,
    seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Participant-level stratified train/validation/test split for RBD questionnaire data.
    Ensures zero participant overlap between splits.

    Args:
        df: Preprocessed RBD DataFrame.
        test_size: Fraction of participants for test set.
        val_size: Fraction of participants for validation set.
        seed: Random seed.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: (df_train, df_val, df_test).
    """
    unique_participants = df.groupby("participant_id")["diagnosis"].first().reset_index()

    train_val_participants, test_participants = train_test_split(
        unique_participants,
        test_size=test_size,
        stratify=unique_participants["diagnosis"],
        random_state=seed
    )

    adjusted_val_size = val_size / (1.0 - test_size)
    train_participants, val_participants = train_test_split(
        train_val_participants,
        test_size=adjusted_val_size,
        stratify=train_val_participants["diagnosis"],
        random_state=seed
    )

    train_ids = train_participants["participant_id"].tolist()
    val_ids = val_participants["participant_id"].tolist()
    test_ids = test_participants["participant_id"].tolist()

    validate_participant_split(train_ids, val_ids, test_ids)

    df_train = df[df["participant_id"].isin(train_ids)].copy()
    df_val = df[df["participant_id"].isin(val_ids)].copy()
    df_test = df[df["participant_id"].isin(test_ids)].copy()

    return df_train, df_val, df_test
