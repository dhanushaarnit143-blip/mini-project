"""
Motor/Gait Pipeline Module for MPF-PD (Phase 4).

Provides preprocessing, quality checking, feature extraction, training,
evaluation, and prediction for motor/gait biomarkers.

Supported dataset: physionet_gait (Category B — Modality-Specific)
  - 166 participants (93 PD, 73 control)
  - 16-channel vertical ground reaction force (VGRF) at 100 Hz
  - 2-minute steady-state walking trial
  - No prodromal labels; binary PD vs Control classification only

IMPORTANT: This is a research prototype. Outputs are risk estimates only.
No clinical claims are made.
"""

from src.motor.preprocess import (
    load_motor_data,
    preprocess_motor_data,
    split_motor_data,
)
from src.motor.features import (
    extract_motor_features,
    GAIT_FEATURE_NAMES,
    MOTOR_FEATURE_NAMES,
    LIMITATIONS,
)
from src.motor.quality import check_motor_quality
from src.motor.train import run_motor_pipeline
from src.motor.evaluate import compute_motor_metrics
from src.motor.predict import predict_motor

__all__ = [
    "load_motor_data",
    "preprocess_motor_data",
    "split_motor_data",
    "extract_motor_features",
    "GAIT_FEATURE_NAMES",
    "MOTOR_FEATURE_NAMES",
    "LIMITATIONS",
    "check_motor_quality",
    "run_motor_pipeline",
    "compute_motor_metrics",
    "predict_motor",
]
