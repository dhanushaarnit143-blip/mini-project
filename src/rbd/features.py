"""
RBD Feature Engineering Module for MPF-PD.

Extracts tabular RBD questionnaire features as specified in Phase 2 guidelines:
- rbdsq_total           : sum of RBDSQ items 1-13 (0-13)
- above_cutoff_flag     : 1 if rbdsq_total >= 5 (clinical screening threshold)
- high_weight_item_flags: item_6 endorsement (acting out vivid/violent dreams)
- item_1 … item_13      : individual binary RBDSQ item scores (when available)

Age-adjusted RBD risk norms are intentionally OMITTED — see RBD_LIMITATIONS.
"above_cutoff_flag" reflects a published screening threshold (RBDSQ >= 5),
NOT a clinically confirmed RBD diagnosis.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


# Base features always present after feature extraction
BASE_FEATURE_COLUMNS: List[str] = [
    "rbdsq_total",
    "above_cutoff_flag",
    "high_weight_item_flags",
]

# Optional item-level columns (item_1 to item_13)
ITEM_COLUMNS: List[str] = [f"item_{i}" for i in range(1, 14)]

# Schema documentation for transparency / downstream auditing
FEATURE_SCHEMA: Dict[str, Dict[str, Any]] = {
    "rbdsq_total": {
        "source": "Sum of RBDSQ binary items 1-13",
        "range": [0, 13],
        "missing_strategy": "required",
    },
    "above_cutoff_flag": {
        "source": "derived: 1 if rbdsq_total >= 5",
        "range": [0, 1],
        "missing_strategy": "derived from rbdsq_total",
        "note": (
            "Reflects published RBDSQ screening cutoff. "
            "NOT equivalent to clinically confirmed RBD diagnosis."
        ),
    },
    "high_weight_item_flags": {
        "source": "item_6 (acting out vivid/violent dreams)",
        "range": [0, 1],
        "missing_strategy": "defaults to 0 when item_6 absent",
    },
    **{
        col: {
            "source": f"RBDSQ binary item {i+1}",
            "range": [0, 1],
            "missing_strategy": "NaN propagated; imputed with training-set median",
        }
        for i, col in enumerate(ITEM_COLUMNS)
    },
}

RBD_LIMITATIONS: List[str] = [
    "Age-adjusted RBD risk norms are not published for standard RBDSQ scale; "
    "age_adjusted_rbd_risk omitted to avoid fabrication.",
    "If only a subset of RBDSQ items (1-13) is available, item_subscores uses "
    "available items and documents missingness.",
    "above_cutoff_flag uses the RBDSQ >= 5 published screening threshold and "
    "does NOT constitute or imply a clinically confirmed RBD diagnosis.",
]


def extract_rbd_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes RBD feature variables from a raw or preprocessed DataFrame.

    All item columns (item_1 to item_13) that are missing from ``df`` are
    represented as NaN so they can be imputed downstream using training-set
    statistics without leaking information.

    Age-adjusted RBD risk is intentionally NOT computed — no published normative
    table exists for the standard RBDSQ; fabricating one would be misleading.

    Args:
        df: Input DataFrame containing RBDSQ questionnaire responses.
            Must contain 'rbdsq_total' column.

    Returns:
        pd.DataFrame: DataFrame with BASE_FEATURE_COLUMNS plus any available
                      ITEM_COLUMNS, preserving the original index.

    Raises:
        ValueError: If 'rbdsq_total' column is absent.
    """
    if "rbdsq_total" not in df.columns:
        raise ValueError(
            "Required column 'rbdsq_total' is missing from the input DataFrame."
        )

    feat = pd.DataFrame(index=df.index)

    # 1. RBDSQ Total score (0-13)
    feat["rbdsq_total"] = df["rbdsq_total"].astype(float)

    # 2. Above-cutoff screening flag (NOT a diagnostic claim)
    feat["above_cutoff_flag"] = (feat["rbdsq_total"] >= 5.0).astype(float)

    # 3. Individual item subscores (item_1 to item_13); NaN when absent
    for col in ITEM_COLUMNS:
        if col in df.columns:
            feat[col] = df[col].astype(float)
        else:
            feat[col] = np.nan

    # 4. High-weight item flag: item_6 — acting out vivid/violent dreams
    if "item_6" in df.columns:
        feat["high_weight_item_flags"] = df["item_6"].fillna(0).astype(float)
    else:
        feat["high_weight_item_flags"] = 0.0

    feature_cols = BASE_FEATURE_COLUMNS + [
        col for col in ITEM_COLUMNS if col in feat.columns
    ]
    return feat[feature_cols]


def get_rbd_feature_names(df: Optional[pd.DataFrame] = None) -> List[str]:
    """
    Returns the ordered list of feature column names.

    Args:
        df: Optional DataFrame; if provided, returns the actual columns that
            would be generated for that DataFrame.

    Returns:
        List[str]: Feature column names.
    """
    if df is not None:
        return list(extract_rbd_features(df).columns)
    return BASE_FEATURE_COLUMNS + ITEM_COLUMNS
