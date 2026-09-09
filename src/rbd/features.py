"""
RBD Feature Engineering Module for MPF-PD.

Extracts tabular RBD questionnaire features as specified in Phase 2 guidelines:
- rbdsq_total
- item_subscores (item_1 to item_13 when available)
- above_cutoff_flag (rbdsq_total >= 5 clinical cutoff)
- age_adjusted_rbd_risk (documented limitation if unavailable)
- high_weight_item_flags (acting out dreams item 6, dream enactment)
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


BASE_FEATURE_COLUMNS = [
    "rbdsq_total",
    "above_cutoff_flag",
    "high_weight_item_flags"
]

ITEM_COLUMNS = [f"item_{i}" for i in range(1, 14)]

RBD_LIMITATIONS = [
    "Age-adjusted RBD risk norms are not published for standard RBDSQ scale; age_adjusted_rbd_risk omitted to avoid fabrication.",
    "If only a subset of RBDSQ items (1-13) is available, item_subscores uses available items and documents missingness."
]


def extract_rbd_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes RBD feature variables from raw or preprocessed dataframe.

    Args:
        df: Input DataFrame containing RBDSQ questionnaire responses.

    Returns:
        pd.DataFrame: DataFrame containing engineered feature columns.
    """
    feat = pd.DataFrame(index=df.index)

    # 1. RBDSQ Total score
    feat["rbdsq_total"] = df["rbdsq_total"].astype(float)

    # 2. Above cutoff flag (standard clinical threshold RBDSQ >= 5 or 6)
    feat["above_cutoff_flag"] = (feat["rbdsq_total"] >= 5.0).astype(float)

    # 3. Item subscores (item_1 to item_13 if available in df)
    for col in ITEM_COLUMNS:
        if col in df.columns:
            feat[col] = df[col].astype(float)
        else:
            feat[col] = np.nan

    # 4. High weight item flags (item_6: acting out vivid/violent dreams, item_5: muscle twitches)
    if "item_6" in df.columns:
        feat["high_weight_item_flags"] = df["item_6"].fillna(0).astype(float)
    else:
        feat["high_weight_item_flags"] = 0.0

    feature_cols = BASE_FEATURE_COLUMNS + [col for col in ITEM_COLUMNS if col in feat.columns]
    return feat[feature_cols]


def get_rbd_feature_names(df: Optional[pd.DataFrame] = None) -> List[str]:
    """Returns list of feature column names."""
    if df is not None:
        return list(extract_rbd_features(df).columns)
    return BASE_FEATURE_COLUMNS + ITEM_COLUMNS
