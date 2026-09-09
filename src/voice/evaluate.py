"""
Voice Model Evaluation Metrics Module for MPF-PD (Phase 3).

Mirrors the evaluation pattern used in Phase 2 (rbd/evaluate.py) for
consistency across the MPF-PD pipeline.

Computes:
  - accuracy, precision, recall, F1, ROC-AUC
  - confusion matrix
  - number of participants, number of recordings, class balance

RESEARCH PROTOTYPE ONLY — NOT A CLINICAL TOOL.
"""

from typing import Dict, Any, Optional, List

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)


def compute_voice_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
    participant_ids: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Compute standard classification metrics for voice model evaluation.

    Args:
        y_true: Ground truth binary labels (0/1).
        y_pred: Predicted binary labels.
        y_prob: Predicted positive class probability [0.0, 1.0].
        participant_ids: List of participant IDs per sample (for counting).

    Returns:
        Dict[str, Any]: Dictionary of evaluation metrics.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    n_samples = int(len(y_true))
    n_participants = (
        int(len(set(participant_ids))) if participant_ids is not None else n_samples
    )
    n_recordings = n_samples  # Each row = one recording

    unique_classes, counts = np.unique(y_true, return_counts=True)
    class_balance = {
        f"class_{int(cls)}": int(cnt) for cls, cnt in zip(unique_classes, counts)
    }

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

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "confusion_matrix": cm.tolist(),
        "number_of_samples": n_samples,
        "number_of_recordings": n_recordings,
        "number_of_participants": n_participants,
        "class_balance": class_balance,
    }
