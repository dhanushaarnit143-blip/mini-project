"""
RBD Model Evaluation Metrics Module for MPF-PD.

Computes comprehensive validation and test metrics adhering to Phase 2 guidelines:
- accuracy, precision, recall, F1, ROC-AUC
- confusion matrix
- sample counts, participant counts, class balance
"""

from typing import Dict, Any, Optional, List
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


def compute_evaluation_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
    participant_ids: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Computes standard Phase 2 classification metrics for RBD models.

    Args:
        y_true: Ground truth binary labels.
        y_pred: Predicted binary labels (0 or 1).
        y_prob: Predicted class probabilities [0.0, 1.0].
        participant_ids: List of participant IDs corresponding to samples.

    Returns:
        Dict[str, Any]: Dictionary containing evaluation metrics.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    n_samples = int(len(y_true))
    n_participants = int(len(set(participant_ids))) if participant_ids is not None else n_samples

    unique_classes, counts = np.unique(y_true, return_counts=True)
    class_balance = {f"class_{int(cls)}": int(cnt) for cls, cnt in zip(unique_classes, counts)}

    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    roc_auc: Optional[float] = None
    if y_prob is not None and len(unique_classes) > 1:
        try:
            roc_auc = float(roc_auc_score(y_true, y_prob))
        except Exception:
            roc_auc = None
    else:
        roc_auc = None

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "confusion_matrix": cm.tolist(),
        "number_of_samples": n_samples,
        "number_of_participants": n_participants,
        "class_balance": class_balance,
    }
