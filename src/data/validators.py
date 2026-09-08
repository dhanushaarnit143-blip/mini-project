"""
Data Validation Utilities Module for MPF-PD.

Enforces dataset integrity rules:
- Verifies required columns exist.
- Detects duplicate participant IDs in tabular datasets.
- Validates label column value constraints.
- Analyzes and reports missing data proportions against threshold without silent imputation.
- Enforces strict subject-level train/val/test split disjointness (zero data leakage).
- Verifies modality coverage against metadata requirements.
"""

from typing import List, Set, Union, Dict, Any
import pandas as pd


def validate_required_columns(df: pd.DataFrame, required_columns: List[str]) -> bool:
    """
    Verify that all required columns exist in the DataFrame.

    Args:
        df: Input pandas DataFrame.
        required_columns: List of column names that must be present.

    Returns:
        bool: True if all required columns exist.

    Raises:
        ValueError: If any required columns are missing.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input 'df' must be a pandas DataFrame.")

    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"DataFrame is missing required columns: {missing_cols}")

    return True


def validate_no_duplicate_participants(df: pd.DataFrame, participant_id_column: str) -> bool:
    """
    Ensure that each participant ID appears only once in single-record datasets.

    Args:
        df: Input pandas DataFrame.
        participant_id_column: Name of the column containing participant identifiers.

    Returns:
        bool: True if all participant IDs are unique.

    Raises:
        ValueError: If duplicate participant IDs are detected.
    """
    validate_required_columns(df, [participant_id_column])

    duplicates = df[df.duplicated(subset=[participant_id_column], keep=False)][
        participant_id_column
    ].unique()

    if len(duplicates) > 0:
        raise ValueError(
            f"Found {len(duplicates)} duplicate participant ID(s) in column '{participant_id_column}': "
            f"{list(duplicates)[:5]}"
        )

    return True


def validate_label_column(
    df: pd.DataFrame, label_column: str, allowed_values: List[Union[int, str]]
) -> bool:
    """
    Verify that values in a label column adhere strictly to allowed discrete values or classes.

    Args:
        df: Input pandas DataFrame.
        label_column: Column containing label values.
        allowed_values: List of valid allowed label values.

    Returns:
        bool: True if all label values are valid.

    Raises:
        ValueError: If invalid or unallowed label values are detected.
    """
    validate_required_columns(df, [label_column])

    actual_values = set(df[label_column].dropna().unique())
    allowed_set = set(allowed_values)
    invalid_values = actual_values - allowed_set

    if invalid_values:
        raise ValueError(
            f"Label column '{label_column}' contains invalid value(s): {list(invalid_values)}. "
            f"Allowed values are: {allowed_values}"
        )

    return True


def validate_missingness(df: pd.DataFrame, threshold: float = 0.5) -> Dict[str, Any]:
    """
    Analyze missing data ratios per column and report columns exceeding the threshold.
    Does NOT silently impute missing data.

    Args:
        df: Input pandas DataFrame.
        threshold: Maximum allowed missing data fraction (0.0 to 1.0).

    Returns:
        dict: Missingness report containing missing_ratios and flagged_columns.

    Raises:
        ValueError: If threshold is invalid or if flagged columns exceed threshold.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input 'df' must be a pandas DataFrame.")
    if not (0.0 <= threshold <= 1.0):
        raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}.")

    missing_counts = df.isnull().sum()
    total_rows = len(df)
    missing_ratios = (missing_counts / total_rows).to_dict() if total_rows > 0 else {}

    flagged_columns = {
        col: ratio for col, ratio in missing_ratios.items() if ratio > threshold
    }

    report = {
        "total_rows": total_rows,
        "missing_ratios": missing_ratios,
        "flagged_columns": flagged_columns,
        "passed": len(flagged_columns) == 0,
    }

    if flagged_columns:
        raise ValueError(
            f"Columns exceed maximum allowed missingness threshold ({threshold}): {flagged_columns}"
        )

    return report


def validate_participant_split(
    train_ids: Union[List[Any], Set[Any]],
    val_ids: Union[List[Any], Set[Any]],
    test_ids: Union[List[Any], Set[Any]],
) -> bool:
    """
    Enforce zero participant-level data leakage across train, val, and test splits.

    Args:
        train_ids: Subject IDs in train set.
        val_ids: Subject IDs in validation set.
        test_ids: Subject IDs in test set.

    Returns:
        bool: True if sets are completely disjoint.

    Raises:
        ValueError: If overlapping participant IDs are detected between any splits.
    """
    set_train = set(train_ids)
    set_val = set(val_ids)
    set_test = set(test_ids)

    train_val_overlap = set_train.intersection(set_val)
    train_test_overlap = set_train.intersection(set_test)
    val_test_overlap = set_val.intersection(set_test)

    overlaps = {}
    if train_val_overlap:
        overlaps["train-val"] = list(train_val_overlap)
    if train_test_overlap:
        overlaps["train-test"] = list(train_test_overlap)
    if val_test_overlap:
        overlaps["val-test"] = list(val_test_overlap)

    if overlaps:
        raise ValueError(
            f"Data leakage detected! Overlapping participant IDs found across splits: {overlaps}"
        )

    return True


def validate_modality_presence(metadata: Dict[str, Any], required_modalities: List[str]) -> bool:
    """
    Check if a dataset's metadata lists all required modalities.

    Args:
        metadata: Dataset metadata dictionary.
        required_modalities: List of modality names required by pipeline.

    Returns:
        bool: True if all required modalities are present in metadata.

    Raises:
        ValueError: If required modalities are missing.
    """
    available_modalities = set(metadata.get("modalities", []))
    missing = [mod for mod in required_modalities if mod not in available_modalities]

    if missing:
        raise ValueError(
            f"Dataset '{metadata.get('dataset_id')}' is missing required modalities: {missing}. "
            f"Available modalities: {list(available_modalities)}"
        )

    return True
