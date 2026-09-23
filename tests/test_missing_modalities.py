"""
Phase 12 Tests: Missing Modality Handling.

Verifies:
1. Missing modalities are detected and included in missing_modalities list.
2. Missing flags are passed to MPF fusion layer.
3. No population average imputation or data fabrication is performed.
4. Single missing modality behaves correctly.
5. Multiple missing modalities behave correctly.
6. All mobile modalities missing returns a graceful skip response without crashing.
7. Olfactory and retina are ALWAYS marked missing on mobile devices.
"""

import pytest
from src.mobile.mpf_adapter import MPFAdapter, run_mobile_adapter
from src.mobile.feature_mapper import map_mobile_features


def test_retina_and_olfactory_always_missing_on_mobile():
    """Verify olfactory and retina are always absent on mobile devices."""
    mobile_data = {
        "participant_id": "TEST_P010",
        "voice": {"jitter": 0.006, "shimmer": 0.035, "hnr": 18.0},
        "motor": {"cadence": 100.0, "tapping_rate": 4.8},
        "sleep": {"unusual_movement_self_report": 0.0, "sleep_quality": 7.0},
    }

    mapped, meta = map_mobile_features(mobile_data)
    assert mapped["olfactory"]["available"] is False
    assert mapped["retina"]["available"] is False
    assert "olfactory" in meta["missing_modalities"]
    assert "retina" in meta["missing_modalities"]


def test_single_modality_missing_inference():
    """Verify inference runs gracefully when one mobile modality is absent (e.g. sleep missing)."""
    adapter = MPFAdapter(log_file_path=None)
    mobile_data = {
        "participant_id": "TEST_P011",
        "date": "2026-09-23",
        "voice": {"jitter": 0.007, "shimmer": 0.04, "hnr": 17.5, "pitch_mean": 170.0},
        "motor": {"cadence": 98.0, "stride_variability": 3.2, "tapping_rate": 5.0},
        # sleep omitted
    }

    res = adapter.run_inference(mobile_data, log_to_db=False)
    assert res["risk_score"] is not None
    assert 0.0 <= res["risk_score"] <= 1.0
    assert "voice" in res["available_modalities"]
    assert "motor" in res["available_modalities"]
    assert "rbd" in res["missing_modalities"]
    assert "olfactory" in res["missing_modalities"]
    assert "retina" in res["missing_modalities"]


def test_multiple_modalities_missing_inference():
    """Verify inference works when only a single modality (e.g., voice) is available."""
    adapter = MPFAdapter(log_file_path=None)
    mobile_data = {
        "participant_id": "TEST_P012",
        "date": "2026-09-23",
        "voice": {"jitter": 0.008, "shimmer": 0.05, "hnr": 16.0, "pitch_mean": 165.0},
        # motor omitted, sleep omitted
    }

    res = adapter.run_inference(mobile_data, log_to_db=False)
    assert res["risk_score"] is not None
    assert 0.0 <= res["risk_score"] <= 1.0
    assert "voice" in res["available_modalities"]
    assert "motor" in res["missing_modalities"]
    assert "rbd" in res["missing_modalities"]


def test_all_mobile_modalities_missing():
    """Verify that when no mobile modalities are available, inference is skipped gracefully without crashing."""
    adapter = MPFAdapter(log_file_path=None)
    empty_mobile_data = {
        "participant_id": "TEST_P013",
        "date": "2026-09-23",
        "voice": {},
        "motor": {},
        "sleep": {},
    }

    res = adapter.run_inference(empty_mobile_data, log_to_db=False)
    assert res["status"] == "skipped_no_modalities_available"
    assert res["risk_score"] is None
    assert len(res["available_modalities"]) == 0
    assert any("missing or failed quality control" in w for w in res["warnings"])


def test_no_data_fabrication_on_missing_values():
    """Verify missing features are not populated with synthetic numbers or population means."""
    mobile_data = {
        "participant_id": "TEST_P014",
        "voice": {"jitter": 0.005},  # shimmer and hnr not provided
    }

    mapped, _ = map_mobile_features(mobile_data)
    vf = mapped["voice"]["features"]
    assert "shimmer" not in vf
    assert "hnr" not in vf
    assert mapped["motor"]["features"] == {}
    assert mapped["rbd"]["rbdsq_total"] is None
