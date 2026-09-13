"""
Motor/Gait Model Evaluation Metrics Module for MPF-PD (Phase 4).

Computes comprehensive classification metrics for the motor pipeline:
  - accuracy, precision, recall, F1, ROC-AUC
  - confusion matrix
  - number of participants, number of trials/recordings
  - feature counts

Gracefully handles ROC-AUC computation failures (single class, small splits).

IMPORTANT: No clinical claims. Metrics apply to research prototype outputs only.
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


def compute_motor_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
    participant_ids: Optional[List[Any]] = None,
    n_recordings: Optional[int] = None,
    n_features: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compute all standard Phase 4 motor classification metrics.

    Args:
        y_true: Ground truth binary labels (0 = Control, 1 = PD).
        y_pred: Predicted binary labels.
        y_prob: Predicted class probabilities for positive class (optional).
        participant_ids: List of participant IDs (for counting unique participants).
        n_recordings: Total number of trial recordings included (if aggregated).
        n_features: Number of features used in the model.

    Returns:
        Dict[str, Any]: Dictionary containing all evaluation metrics.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    n_samples = int(len(y_true))
    n_participants = int(len(set(participant_ids))) if participant_ids is not None else n_samples
    n_rec = n_recordings if n_recordings is not None else n_samples

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

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    cm_list = cm.tolist()

    result: Dict[str, Any] = {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "confusion_matrix": cm_list,
        "number_of_samples": n_samples,
        "number_of_participants": n_participants,
        "number_of_recordings": n_rec,
        "class_balance": class_balance,
    }

    if n_features is not None:
        result["number_of_features"] = n_features

    return result
