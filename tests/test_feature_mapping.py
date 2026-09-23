"""
Phase 12 Tests: Feature Mapping Layer.

Verifies:
1. Typing features map to fine-motor digital representation proxies.
2. Voice features map to acoustic voice representation.
3. Movement/gait features map to motor representation.
4. Visual behavior features map to ocular/visual representation (NOT retinal).
5. Sleep survey features map to RBD questionnaire proxies.
6. Olfactory and retinal modalities are strictly marked unavailable.
7. Proxy disclaimers and mapping documentation are present and complete.
"""

import pytest
from src.mobile.feature_mapper import (
    map_mobile_features,
    FEATURE_MAPPING_DOCUMENTATION,
    FEATURE_MAPPING_VERSION,
    PROXY_DISCLAIMER,
    OCULAR_DISCLAIMER,
)


def test_feature_mapping_documentation_completeness():
    """Verify that all required proxy mappings are thoroughly documented."""
    required_mappings = [
        "typing.typing_speed",
        "typing.interval_variability",
        "typing.correction_rate",
        "voice.jitter",
        "voice.shimmer",
        "voice.hnr",
        "voice.pitch_mean",
        "motor.cadence",
        "motor.stride_variability",
        "motor.tapping_rate",
        "motor.tremor_frequency",
        "visual.blink_rate",
        "visual.gaze_stability",
        "visual.reaction_time",
        "sleep.unusual_movement_self_report",
        "sleep.sleep_quality",
    ]
    for key in required_mappings:
        assert key in FEATURE_MAPPING_DOCUMENTATION, f"Missing documentation for {key}"
        doc = FEATURE_MAPPING_DOCUMENTATION[key]
        assert "target" in doc
        assert "modality" in doc
        assert "is_proxy" in doc
        assert "description" in doc


def test_typing_to_motor_proxy_mapping():
    """Verify typing features map to motor proxies."""
    mobile_data = {
        "participant_id": "TEST_P001",
        "typing": {
            "typing_speed": 4.5,
            "interval_variability": 0.22,
            "correction_rate": 0.08,
        },
    }

    mapped, meta = map_mobile_features(mobile_data)

    assert mapped["motor"]["available"] is True
    motor_feats = mapped["motor"]["features"]
    assert motor_feats["tapping_rate"] == 4.5
    assert motor_feats["tapping_interval_variability"] == 0.22
    assert motor_feats["fine_motor_indicator"] == 0.08

    # Verify proxies are documented in metadata
    assert any("typing.typing_speed" in p for p in meta["activated_proxies"])
    assert any("typing.interval_variability" in p for p in meta["activated_proxies"])
    assert any("typing.correction_rate" in p for p in meta["activated_proxies"])


def test_voice_features_mapping():
    """Verify acoustic voice features map correctly."""
    mobile_data = {
        "participant_id": "TEST_P002",
        "voice": {
            "jitter": 0.0075,
            "shimmer": 0.042,
            "hnr": 19.5,
            "pitch_mean": 185.0,
        },
    }

    mapped, meta = map_mobile_features(mobile_data)

    assert mapped["voice"]["available"] is True
    vf = mapped["voice"]["features"]
    assert vf["jitter_pct"] == 0.0075
    assert vf["shimmer"] == 0.042
    assert vf["hnr"] == 19.5
    assert vf["pitch_mean"] == 185.0
    assert vf["f0_mean_hz"] == 185.0
    assert "voice" in meta["available_modalities"]


def test_motor_gait_and_tremor_mapping():
    """Verify movement and motor features map correctly."""
    mobile_data = {
        "participant_id": "TEST_P003",
        "motor": {
            "cadence": 104.0,
            "stride_variability": 3.8,
            "tapping_rate": 5.2,
            "tremor_frequency": 5.1,
            "gait_speed_m_per_s": 1.15,
        },
    }

    mapped, meta = map_mobile_features(mobile_data)

    assert mapped["motor"]["available"] is True
    mf = mapped["motor"]["features"]
    assert mf["cadence_steps_per_min"] == 104.0
    assert mf["gait_cadence"] == 104.0
    assert mf["stride_interval_cv_pct"] == 3.8
    assert mf["stride_variability"] == 3.8
    assert mf["tapping_rate"] == 5.2
    assert mf["tremor_frequency"] == 5.1
    assert mf["gait_speed_m_per_s"] == 1.15


def test_visual_behavior_no_retinal_claim():
    """Verify visual behavior maps to ocular proxies and NEVER claims retinal imaging."""
    mobile_data = {
        "participant_id": "TEST_P004",
        "visual": {
            "blink_rate": 14.5,
            "gaze_stability": 0.88,
            "reaction_time": 320.0,
        },
    }

    mapped, meta = map_mobile_features(mobile_data)

    # Retinal modality MUST remain strictly unavailable
    assert mapped["retina"]["available"] is False
    assert "retina" in meta["missing_modalities"]
    assert meta["is_retinal_claimed"] is False

    # Ocular behavior extension present
    ocular = mapped["ocular_visual"]
    assert ocular["available"] is True
    assert ocular["is_retinal_imaging"] is False
    assert ocular["features"]["blink_rate"] == 14.5
    assert ocular["features"]["gaze_stability"] == 0.88
    assert ocular["features"]["reaction_time"] == 320.0

    # Visual reaction time maps into motor reaction time
    assert mapped["motor"]["features"]["reaction_time"] == 320.0
    assert any("visual.reaction_time" in p for p in meta["activated_proxies"])


def test_sleep_questionnaire_to_rbd_proxy_mapping():
    """Verify sleep self-reports map to RBD cutoff and item subscores."""
    mobile_data = {
        "participant_id": "TEST_P005",
        "sleep": {
            "unusual_movement_self_report": 1.0,
            "sleep_quality": 8.0,
        },
    }

    mapped, meta = map_mobile_features(mobile_data)

    assert mapped["rbd"]["available"] is True
    assert mapped["rbd"]["rbdsq_total"] >= 5.0
    assert len(mapped["rbd"]["item_responses"]) == 13
    assert any("sleep.unusual_movement_self_report" in p for p in meta["activated_proxies"])
    assert any("sleep.sleep_quality" in p for p in meta["activated_proxies"])


def test_sensor_limitations_and_disclaimers():
    """Verify olfactory absent and required ethical disclaimers attached."""
    mobile_data = {"participant_id": "TEST_P006"}
    mapped, meta = map_mobile_features(mobile_data)

    assert mapped["olfactory"]["available"] is False
    assert mapped["retina"]["available"] is False
    assert meta["proxy_disclaimer"] == PROXY_DISCLAIMER
    assert meta["ocular_disclaimer"] == OCULAR_DISCLAIMER
    assert "not a clinical diagnosis" in meta["proxy_disclaimer"].lower()
    assert "not a retinal camera" in meta["ocular_disclaimer"].lower()
