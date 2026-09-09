"""
Synthetic Data Fixture Generator for MPF-PD.

Provides clearly labeled synthetic unit-test fixtures for Olfactory and RBD modalities
when real datasets (PPMI/PREDICT-PD) are not present locally.

MUST ONLY be used for unit testing, continuous integration, and software verification in simulation mode.
MUST NEVER be presented as real clinical or research results.
"""

import numpy as np
import pandas as pd
from typing import Tuple


def generate_synthetic_olfactory_data(
    n_participants: int = 200,
    seed: int = 42
) -> pd.DataFrame:
    """
    Generate synthetic Olfactory (UPSIT-like) tabular dataset.

    Args:
        n_participants: Number of synthetic participants.
        seed: Random seed for reproducibility.

    Returns:
        pd.DataFrame: Synthetic olfactory DataFrame with explicit diagnosis labels.
    """
    rng = np.random.RandomState(seed)

    participant_ids = [f"P{i+1:04d}" for i in range(n_participants)]
    
    # 50% controls (0), 50% prodromal/PD (1)
    diagnoses = rng.choice([0, 1], size=n_participants, p=[0.5, 0.5])
    
    ages = rng.uniform(45.0, 80.0, size=n_participants).round(1)

    # Controls score higher on UPSIT (e.g. 30-39), PD scores lower (e.g. 12-28)
    total_scores = np.where(
        diagnoses == 0,
        rng.normal(loc=34.0, scale=3.0, size=n_participants),
        rng.normal(loc=22.0, scale=4.5, size=n_participants)
    )
    total_scores = np.clip(total_scores.round(), 0, 40).astype(int)

    # Response times: PD subjects slightly slower
    response_times = np.where(
        diagnoses == 0,
        rng.normal(loc=3.2, scale=0.8, size=n_participants),
        rng.normal(loc=4.8, scale=1.2, size=n_participants)
    )
    response_times = np.clip(response_times.round(2), 1.0, 15.0)

    n_errors = 40 - total_scores

    # Error pattern flags (synthetic count of high-risk odor misidentifications out of 5 key items)
    error_pattern_flags = np.where(
        diagnoses == 0,
        rng.binomial(n=5, p=0.15, size=n_participants),
        rng.binomial(n=5, p=0.65, size=n_participants)
    )

    df = pd.DataFrame({
        "participant_id": participant_ids,
        "age": ages,
        "total_score": total_scores,
        "response_time_mean": response_times,
        "n_errors": n_errors,
        "error_pattern_flags": error_pattern_flags,
        "diagnosis": diagnoses
    })

    # Introduce controlled 5% missingness in non-critical columns to test honest missing handling
    mask_rt = rng.rand(n_participants) < 0.05
    df.loc[mask_rt, "response_time_mean"] = np.nan

    return df


def generate_synthetic_rbd_data(
    n_participants: int = 200,
    seed: int = 42
) -> pd.DataFrame:
    """
    Generate synthetic RBD (RBDSQ-like) tabular dataset.

    Args:
        n_participants: Number of synthetic participants.
        seed: Random seed for reproducibility.

    Returns:
        pd.DataFrame: Synthetic RBDSQ DataFrame with explicit diagnosis labels.
    """
    rng = np.random.RandomState(seed)

    participant_ids = [f"P{i+1:04d}" for i in range(n_participants)]
    diagnoses = rng.choice([0, 1], size=n_participants, p=[0.5, 0.5])
    ages = rng.uniform(45.0, 80.0, size=n_participants).round(1)

    # Item probabilities: Controls have lower chance of endorsement, RBD/PD higher
    p_ctrl = [0.1, 0.1, 0.15, 0.1, 0.1, 0.08, 0.1, 0.1, 0.12, 0.1, 0.1, 0.1, 0.1]
    p_case = [0.6, 0.5, 0.7, 0.65, 0.55, 0.75, 0.6, 0.5, 0.65, 0.6, 0.5, 0.55, 0.6]

    items_data = {}
    for item_idx in range(1, 14):
        item_col = f"item_{item_idx}"
        prob = np.where(diagnoses == 0, p_ctrl[item_idx - 1], p_case[item_idx - 1])
        items_data[item_col] = rng.binomial(n=1, p=prob, size=n_participants)

    df_items = pd.DataFrame(items_data)
    rbdsq_total = df_items.sum(axis=1).values

    df = pd.DataFrame({
        "participant_id": participant_ids,
        "age": ages,
        "rbdsq_total": rbdsq_total,
        "diagnosis": diagnoses
    })

    df = pd.concat([df, df_items], axis=1)

    # Insert 5% missingness in item_13 for missing data testing
    mask = rng.rand(n_participants) < 0.05
    df.loc[mask, "item_13"] = np.nan

    return df
