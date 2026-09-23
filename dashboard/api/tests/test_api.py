"""
Unit & Integration Tests for MPF-PD FastAPI Backend (Phase 8).
"""

import json
import io
import pytest
from fastapi.testclient import TestClient

from dashboard.api.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify /api/health returns 200 and model status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "models_loaded" in data
    assert data["status"] in ["ok", "degraded"]


def test_analyze_json_endpoint():
    """Verify /api/analyze processes pure JSON requests with all modalities."""
    payload = {
        "participant_id": "TEST-SUB-01",
        "age": 68.0,
        "sex": "male",
        "olfactory": {"available": True, "total_score": 24.0, "response_time_mean": 4.5},
        "rbd": {"available": True, "rbdsq_total": 7.0, "above_cutoff_flag": 1.0},
        "voice": {"available": True, "features": {"jitter_pct": 0.007, "shimmer": 0.05, "hnr": 16.5}},
        "motor": {"available": True, "features": {"gait_speed_m_per_s": 0.95, "cadence_steps_per_min": 98.0}},
        "retina": {"available": True, "features": {"vessel_density": 0.065, "mean_vessel_diameter_px": 2.95}},
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["participant_id"] == "TEST-SUB-01"
    assert "fusion" in data
    assert "risk_score" in data["fusion"]
    assert 0.0 <= data["fusion"]["risk_score"] <= 1.0
    assert "explainability" in data
    assert "important_modalities" in data["explainability"]


def test_analyze_with_missing_modalities():
    """Verify /api/analyze handles missing modalities gracefully without crashing."""
    payload = {
        "participant_id": "TEST-MISSING-01",
        "age": 70.0,
        "sex": "female",
        "olfactory": {"available": True, "total_score": 18.0},
        "rbd": {"available": False},
        "voice": {"available": False},
        "motor": {"available": False},
        "retina": {"available": False},
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "rbd" in data["missing_modalities"]
    assert "voice" in data["missing_modalities"]
    assert "motor" in data["missing_modalities"]
    assert "retina" in data["missing_modalities"]
    assert data["individual_modalities"]["rbd"]["status"] == "missing"
    assert 0.0 <= data["fusion"]["risk_score"] <= 1.0


def test_analyze_multipart_form():
    """Verify /api/analyze handles multipart/form-data with uploaded files."""
    json_payload = {
        "participant_id": "TEST-FORM-01",
        "age": 62.0,
        "sex": "female",
        "olfactory": {"available": True, "total_score": 25.0},
        "rbd": {"available": True, "rbdsq_total": 4.0},
    }

    dummy_csv = io.BytesIO(b"gait_speed_m_per_s,cadence_steps_per_min\n1.1,102.0\n")
    response = client.post(
        "/api/analyze",
        data={"payload": json.dumps(json_payload)},
        files={"motor_file": ("test_gait.csv", dummy_csv, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["participant_id"] == "TEST-FORM-01"
    assert "fusion" in data


def test_analyze_invalid_json_returns_400():
    """Verify invalid JSON returns HTTP 400."""
    response = client.post(
        "/api/analyze",
        data={"payload": "invalid-json{{"},
    )
    assert response.status_code == 400


def test_mobile_analyze_endpoint():
    """Verify /api/mobile/analyze processes mobile features and returns valid risk score and metadata."""
    payload = {
        "participant_id": "TEST-MOBILE-01",
        "features": {
            "typing": {"typing_speed": 4.8, "interval_variability": 0.11, "correction_rate": 0.05},
            "voice": {"jitter": 0.008, "shimmer": 0.04, "hnr": 18.0, "pitch_mean": 140.0},
            "motor": {"cadence": 105.0, "stride_variability": 2.5, "tapping_rate": 5.0},
            "sleep": {"rbdsq_total": 3.0, "unusual_movement_self_report": 0.0},
        },
        "baseline_deviation_context": {
            "baseline_version": "1.0.0",
            "mahalanobis_distance": 1.15,
            "status": "within_baseline",
        },
        "demographics": {"age": 63.0, "sex": "male"},
        "log_to_db": False,
        "raw_feature_version": "1.0.0",
        "app_version": "1.0.0",
    }
    response = client.post("/api/mobile/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert data["risk_score"] is not None
    assert 0.0 <= data["risk_score"] <= 1.0
    assert "status" in data
    assert data["status"] == "success"
    assert "risk_pattern" in data
    assert "Elevated" in data["risk_pattern"] or "Standard" in data["risk_pattern"]
    assert "prediction_metadata" in data
    meta = data["prediction_metadata"]
    assert meta["source"] == "mobile_extension"
    assert meta["model_version"] is not None
    assert meta["baseline_version"] == "1.0.0"
    assert "disclaimer" in meta
    # Ensure retina and olfactory are missing
    assert "retina" in data["missing_modalities"]
    assert "olfactory" in data["missing_modalities"]

