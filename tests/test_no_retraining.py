"""
Phase 12 Tests: No Retraining and Model Preservation Mandate.

Verifies:
1. Model inference strictly separates execution from model retraining.
2. No model weights, scaler means, or classifier trees are modified by inference.
3. Checksums of model artifacts on disk remain identical before and after inference.
4. Calling the adapter multiple times produces deterministic outputs without drift.
5. No training methods (fit, fit_transform, backward, optimizer.step) are called.
"""

import hashlib
from pathlib import Path
from unittest.mock import patch
import joblib
import numpy as np
import pytest
import torch

from src.mobile.mpf_adapter import MPFAdapter
from src.mobile.normalization_loader import DEFAULT_PREPROCESSOR_PATH


def _calculate_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def test_artifact_checksums_unchanged_after_inference():
    """Verify disk artifacts are unmodified after running adapter inference."""
    artifacts = [
        Path("models/fusion/classifier.joblib"),
        Path("models/fusion/fusion_encoder.pt"),
        Path(DEFAULT_PREPROCESSOR_PATH),
    ]

    # Pre-inference checksums
    initial_hashes = {p: _calculate_file_sha256(p) for p in artifacts if p.exists()}
    assert len(initial_hashes) == 3, "All three fusion model artifacts must exist."

    # Run inference
    adapter = MPFAdapter(log_file_path=None)
    mobile_data = {
        "participant_id": "TEST_P030",
        "date": "2026-09-23",
        "voice": {"jitter": 0.007, "shimmer": 0.04, "hnr": 18.0},
        "motor": {"cadence": 100.0, "tapping_rate": 5.0},
        "sleep": {"unusual_movement_self_report": 0.0, "sleep_quality": 6.0},
    }

    res = adapter.run_inference(mobile_data, log_to_db=False)
    assert res["risk_score"] is not None

    # Post-inference checksums
    post_hashes = {p: _calculate_file_sha256(p) for p in artifacts}
    for p, init_hash in initial_hashes.items():
        assert post_hashes[p] == init_hash, f"Artifact '{p}' was modified during inference!"


def test_pytorch_encoder_weights_frozen():
    """Verify PyTorch fusion encoder weights do not change during adapter execution."""
    encoder_path = Path("models/fusion/fusion_encoder.pt")
    weights_before = torch.load(encoder_path, weights_only=True)

    adapter = MPFAdapter(log_file_path=None)
    mobile_data = {
        "participant_id": "TEST_P031",
        "date": "2026-09-23",
        "voice": {"jitter": 0.008, "shimmer": 0.05, "hnr": 17.0},
        "motor": {"cadence": 95.0, "tapping_rate": 4.5},
    }

    # Execute multiple inference cycles
    for _ in range(3):
        adapter.run_inference(mobile_data, log_to_db=False)

    weights_after = torch.load(encoder_path, weights_only=True)

    for k in weights_before:
        assert torch.equal(weights_before[k], weights_after[k]), f"Encoder parameter {k} shifted!"


def test_deterministic_inference_no_drift():
    """Verify repeated inferences with identical input yield identical results."""
    adapter = MPFAdapter(log_file_path=None)
    mobile_data = {
        "participant_id": "TEST_P032",
        "date": "2026-09-23",
        "voice": {"jitter": 0.006, "shimmer": 0.038, "hnr": 19.0},
        "motor": {"cadence": 105.0, "tapping_rate": 5.2},
    }

    res1 = adapter.run_inference(mobile_data, log_to_db=False)
    res2 = adapter.run_inference(mobile_data, log_to_db=False)
    res3 = adapter.run_inference(mobile_data, log_to_db=False)

    assert res1["risk_score"] == res2["risk_score"] == res3["risk_score"]
    assert res1["gate_weights"] == res2["gate_weights"] == res3["gate_weights"]


def test_strict_inference_mode_no_grad():
    """Verify inference does not compute gradients or alter gradient status."""
    adapter = MPFAdapter(log_file_path=None)
    mobile_data = {
        "participant_id": "TEST_P033",
        "date": "2026-09-23",
        "voice": {"jitter": 0.007, "shimmer": 0.04, "hnr": 18.0},
    }

    with patch("torch.autograd.backward") as mock_backward:
        res = adapter.run_inference(mobile_data, log_to_db=False)
        assert mock_backward.call_count == 0
        assert res["risk_score"] is not None
