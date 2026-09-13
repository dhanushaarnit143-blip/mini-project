"""
Evaluation Module for Multimodal Prodromal Fusion (MPF-PD Phase 6).

Computes standardized classification metrics:
- Accuracy, Precision, Recall, F1, ROC-AUC, Confusion Matrix
- Subset evaluations (complete vs missing modality cases)
- Baseline comparisons and bootstrap statistical significance of AUC differences.

SCIENTIFIC HONESTY:
- Metrics reflect research prototype performance on simulation data.
- No clinical validity is claimed.
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)


def compute_binary_metrics(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Compute comprehensive binary classification evaluation metrics.

    Args:
        y_true: Ground truth binary labels (0 or 1).
        y_pred_proba: Predicted risk probabilities in [0.0, 1.0].
        threshold: Decision threshold for discrete classification.

    Returns:
        Dict containing accuracy, precision, recall, f1, roc_auc, confusion_matrix, etc.
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred_proba = np.asarray(y_pred_proba).astype(float)
    y_pred = (y_pred_proba >= threshold).astype(int)

    acc = float(np.round(accuracy_score(y_true, y_pred), 4))
    prec = float(np.round(precision_score(y_true, y_pred, zero_division=0), 4))
    rec = float(np.round(recall_score(y_true, y_pred, zero_division=0), 4))
    f1 = float(np.round(f1_score(y_true, y_pred, zero_division=0), 4))

    try:
        auc = float(np.round(roc_auc_score(y_true, y_pred_proba), 4))
    except Exception:
        auc = 0.5

    cm = confusion_matrix(y_true, y_pred).tolist()

    return {
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "roc_auc": auc,
        "confusion_matrix": cm,
        "number_of_samples": int(len(y_true)),
        "class_balance": {
            "class_0": int(np.sum(y_true == 0)),
            "class_1": int(np.sum(y_true == 1)),
        },
    }


def compare_auc_significance(
    y_true: np.ndarray,
    y_prob_a: np.ndarray,
    y_prob_b: np.ndarray,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Compute bootstrap difference in ROC-AUC between two models to determine
    whether the performance gain is statistically meaningful or likely due to variance.

    Args:
        y_true: Ground truth labels.
        y_prob_a: Predicted probabilities for Model A (e.g. Gated Fusion).
        y_prob_b: Predicted probabilities for Model B (e.g. Concatenation or best single).
        n_bootstraps: Number of bootstrap iterations.
        seed: Random seed.

    Returns:
        Dict: auc_diff_mean, ci_lower, ci_upper, p_value, statistically_significant.
    """
    rng = np.random.RandomState(seed)
    n = len(y_true)
    diffs = []

    for _ in range(n_bootstraps):
        idx = rng.randint(0, n, size=n)
        sample_y = y_true[idx]
        if len(np.unique(sample_y)) < 2:
            continue
        try:
            auc_a = roc_auc_score(sample_y, y_prob_a[idx])
            auc_b = roc_auc_score(sample_y, y_prob_b[idx])
            diffs.append(auc_a - auc_b)
        except Exception:
            continue

    if not diffs:
        return {
            "auc_diff_mean": 0.0,
            "ci_95": [0.0, 0.0],
            "statistically_meaningful": False,
            "interpretation": "Insufficient bootstrap variation to compute confidence interval.",
        }

    diffs = np.array(diffs)
    mean_diff = float(np.round(np.mean(diffs), 4))
    ci_lower = float(np.round(np.percentile(diffs, 2.5), 4))
    ci_upper = float(np.round(np.percentile(diffs, 97.5), 4))

    # Statistically significant if 95% CI does not include 0 and mean_diff > 0
    stat_sig = bool(ci_lower > 0.0)

    interpretation = (
        "Statistically meaningful improvement (95% CI excludes 0)."
        if stat_sig
        else "Difference is not statistically significant and likely within random variance."
    )

    return {
        "auc_diff_mean": mean_diff,
        "ci_95": [ci_lower, ci_upper],
        "statistically_meaningful": stat_sig,
        "interpretation": interpretation,
    }
