"""
Olfactory Feature Engineering Module for MPF-PD.

Extracts tabular olfactory features as specified in Phase 2 guidelines:
- total_score       : raw UPSIT/UPSIT-like score (0-40)
- pct_correct       : total_score / 40 (0.0-1.0)
- response_time_mean: mean per-item response time in seconds (optional)
- n_errors          : number of incorrect identifications (0-40)
- error_pattern_flags: count of high-risk odor misidentifications (0-5)

Age-adjusted normative score is intentionally OMITTED — see LIMITATIONS.
No age-adjustment table is invented or fabricated.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


# Ordered list of feature columns fed to the ML models
FEATURE_COLUMNS: List[str] = [
    "total_score",
    "pct_correct",
    "response_time_mean",
    "n_errors",
    "error_pattern_flags",
]

# Schema documentation for each feature: source, value range, and notes
FEATURE_SCHEMA: Dict[str, Dict[str, Any]] = {
    "total_score": {
        "source": "UPSIT raw score",
        "range": [0, 40],
        "missing_strategy": "required",
    },
    "pct_correct": {
        "source": "derived: total_score / 40",
        "range": [0.0, 1.0],
        "missing_strategy": "derived from total_score",
    },
    "response_time_mean": {
        "source": "per-item response time (seconds), if recorded",
        "range": [0.0, None],
        "missing_strategy": "imputed with training-set median",
    },
    "n_errors": {
        "source": "derived: 40 - total_score, or explicit column",
        "range": [0, 40],
        "missing_strategy": "derived from total_score",
    },
    "error_pattern_flags": {
        "source": "count of high-risk odor misidentifications (0-5)",
        "range": [0, 5],
        "missing_strategy": "defaults to 0 when column absent",
    },
}

LIMITATIONS: List[str] = [
    "Age-adjusted normative tables (e.g., Doty UPSIT age/sex percentiles) are not available "
    "in public tabular export without proprietary tables; age_adjusted_score omitted to prevent data fabrication.",
    "If raw item-level responses (1-40) are absent, error_pattern_flags represents a summary "
    "flag of high-risk odor errors.",
]


def extract_olfactory_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes olfactory feature variables from a raw or preprocessed DataFrame.

    Handles optional columns gracefully:
      - response_time_mean: set to NaN if absent (imputed downstream).
      - n_errors: derived from total_score if column is absent.
      - error_pattern_flags: defaults to 0.0 if column is absent.

    Age-adjusted score is intentionally NOT computed to avoid fabricating
    proprietary normative lookup tables.

    Args:
        df: Input DataFrame containing raw olfactory measurements.

    Returns:
        pd.DataFrame: DataFrame with exactly the columns in FEATURE_COLUMNS,
                      preserving the original index.
    """
    if "total_score" not in df.columns:
        raise ValueError(
            "Required column 'total_score' is missing from the input DataFrame."
        )

    feat = pd.DataFrame(index=df.index)

    # 1. Total score (0–40); already clipped in preprocess_olfactory_data
    feat["total_score"] = df["total_score"].astype(float)

    # 2. Percentage correct (deterministic, leak-free derivation)
    feat["pct_correct"] = (feat["total_score"] / 40.0).round(4)

    # 3. Mean response time — optional; NaN propagated for imputer
    if "response_time_mean" in df.columns:
        feat["response_time_mean"] = df["response_time_mean"].astype(float)
    else:
        feat["response_time_mean"] = np.nan

    # 4. Number of errors — prefer explicit column, else derive
    if "n_errors" in df.columns:
        feat["n_errors"] = df["n_errors"].astype(float)
    else:
        feat["n_errors"] = 40.0 - feat["total_score"]

    # 5. Error pattern flags — optional summary metric
    if "error_pattern_flags" in df.columns:
        feat["error_pattern_flags"] = df["error_pattern_flags"].astype(float)
    else:
        feat["error_pattern_flags"] = 0.0

    return feat[FEATURE_COLUMNS]
