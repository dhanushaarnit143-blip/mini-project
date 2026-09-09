"""
Olfactory Feature Engineering Module for MPF-PD.

Extracts tabular olfactory features as specified in Phase 2 guidelines:
- total_score
- pct_correct
- age_adjusted_score (documented limitation if unavailable)
- response_time_mean
- n_errors
- error_pattern_flags
"""

from typing import Tuple, List, Dict, Any, Optional
import pandas as pd
import numpy as np


FEATURE_COLUMNS = [
    "total_score",
    "pct_correct",
    "response_time_mean",
    "n_errors",
    "error_pattern_flags"
]

LIMITATIONS = [
    "Age-adjusted normative tables (e.g., Doty UPSIT age/sex percentiles) are not available in public tabular export without proprietary tables; age_adjusted_score omitted to prevent data fabrication.",
    "If raw item-level responses (1-40) are absent, error_pattern_flags represents a summary flag of high-risk odor errors."
]


def extract_olfactory_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes olfactory feature variables from raw or preprocessed dataframe.

    Args:
        df: Input DataFrame containing raw olfactory measurements.

    Returns:
        pd.DataFrame: DataFrame containing engineered feature columns.
    """
    feat = pd.DataFrame(index=df.index)

    # 1. Total score (0 - 40)
    feat["total_score"] = df["total_score"].astype(float)

    # 2. Percentage correct
    feat["pct_correct"] = (feat["total_score"] / 40.0).round(4)

    # 3. Mean response time (if available in df)
    if "response_time_mean" in df.columns:
        feat["response_time_mean"] = df["response_time_mean"].astype(float)
    else:
        feat["response_time_mean"] = np.nan

    # 4. Number of errors (40 - total_score)
    if "n_errors" in df.columns:
        feat["n_errors"] = df["n_errors"].astype(float)
    else:
        feat["n_errors"] = 40.0 - feat["total_score"]

    # 5. Error pattern flags
    if "error_pattern_flags" in df.columns:
        feat["error_pattern_flags"] = df["error_pattern_flags"].astype(float)
    else:
        feat["error_pattern_flags"] = 0.0

    return feat[FEATURE_COLUMNS]
