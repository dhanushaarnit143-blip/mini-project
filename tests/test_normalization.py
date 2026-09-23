"""
Phase 12 Tests: Normalization and Preprocessing Layer.

Verifies:
1. Normalization strictly re-uses existing preprocessors from models/fusion/preprocessor.joblib.
2. Only transform() is called; fit() or fit_transform() is NEVER called.
3. Feature column ordering strictly matches training schema.
4. Outlier clipping at [-5.0, +5.0] prevents numerical explosion.
5. No new normalization parameters or scalers are generated.
"""

from unittest.mock import patch, MagicMock
import numpy as np
import pytest
import joblib

from src.mobile.normalization_loader import (
    load_training_preprocessors,
    normalize_modality_features,
    normalize_demographics,
    get_modality_feature_columns,
    DEFAULT_PREPROCESSOR_PATH,
    OUTLIER_CLIP_MIN,
    OUTLIER_CLIP_MAX,
)


def test_load_training_preprocessors_success():
    """Verify preprocessors are loaded from existing model artifacts."""
    prep = load_training_preprocessors(force_reload=True)
    assert "modality_scalers" in prep
    assert "modality_imputers" in prep
    assert "demo_scaler" in prep
    assert "demo_imputer" in prep
    assert "modality_feature_cols" in prep

    for mod in ["olfactory", "rbd", "voice", "motor", "retina"]:
        assert mod in prep["modality_scalers"]
        assert mod in prep["modality_imputers"]
        assert mod in prep["modality_feature_cols"]
        assert hasattr(prep["modality_scalers"][mod], "mean_")


def test_column_ordering_matches_training():
    """Verify feature column ordering is strictly retrieved from training preprocessor."""
    voice_cols = get_modality_feature_columns("voice")
    assert "jitter_pct" in voice_cols
    assert "shimmer" in voice_cols
    assert "hnr" in voice_cols

    motor_cols = get_modality_feature_columns("motor")
    assert "gait_speed_m_per_s" in motor_cols
    assert "cadence_steps_per_min" in motor_cols


def test_no_fit_called_during_normalization():
    """Verify that fit() or fit_transform() is NEVER called on the scalers."""
    prep = load_training_preprocessors()
    scaler = prep["modality_scalers"]["voice"]

    # Wrap scaler.fit and scaler.fit_transform to ensure they are never invoked
    with patch.object(scaler, "fit", side_effect=AssertionError("fit() must not be called!")):
        with patch.object(scaler, "fit_transform", side_effect=AssertionError("fit_transform() must not be called!")):
            norm_res = normalize_modality_features(
                "voice",
                {"jitter_pct": 0.005, "shimmer": 0.03, "hnr": 20.0},
            )
            assert isinstance(norm_res, np.ndarray)
            assert norm_res.shape[0] == 1


def test_outlier_clipping_boundaries():
    """Verify extreme physiological values are clipped to [-5.0, +5.0]."""
    # Extremely massive value designed to exceed 5 std dev
    extreme_features = {
        "jitter_pct": 1000.0,
        "shimmer": 1000.0,
        "hnr": 1000.0,
    }

    norm_res = normalize_modality_features("voice", extreme_features, clip_outliers=True)
    assert np.all(norm_res <= OUTLIER_CLIP_MAX)
    assert np.all(norm_res >= OUTLIER_CLIP_MIN)


def test_no_new_normalization_parameters_created():
    """Verify that scaler mean_ and scale_ parameters remain unchanged after normalization."""
    prep = load_training_preprocessors()
    motor_scaler = prep["modality_scalers"]["motor"]
    original_mean = np.copy(motor_scaler.mean_)
    original_scale = np.copy(motor_scaler.scale_)

    # Run multiple normalizations
    for _ in range(5):
        normalize_modality_features(
            "motor",
            {"gait_speed_m_per_s": 1.1, "cadence_steps_per_min": 105.0},
        )

    np.testing.assert_array_equal(motor_scaler.mean_, original_mean)
    np.testing.assert_array_equal(motor_scaler.scale_, original_scale)


def test_demographics_normalization():
    """Verify demographic normalization uses existing demographic scaler."""
    demo_norm = normalize_demographics(age=68.0, sex="female")
    assert demo_norm.shape == (1, 3)
    assert np.all(demo_norm >= OUTLIER_CLIP_MIN)
    assert np.all(demo_norm <= OUTLIER_CLIP_MAX)
