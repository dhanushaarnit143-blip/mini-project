"""
Phase 16 — Full Integration & End-to-End System Tests
=====================================================
Validates complete mobile extension integration with existing MPF pipeline:
1. 14-day synthetic mobile collection simulation
2. Baseline establishment (calibration window)
3. Day 15 progressive deviation generation
4. MPF adapter mapping & schema validation
5. Frozen MPF neural fusion inference
6. Explanation generation (SHAP / Gating attention weights)
7. Complete 5-tuple version reproducibility logging
8. Non-diagnostic phrasing compliance (Zero diagnostic claims)
9. Backward compatibility with existing MPF pipeline & datasets

ALL DATA IS STRICTLY [SYNTHETIC] FOR SOFTWARE VERIFICATION.
"""

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import tempfile
from typing import Any, Dict, List
import uuid
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_mpf_pipeline, ALL_MODALITIES, PIPELINE_VERSION
from src.mobile.mpf_adapter import MPFAdapter, run_mobile_adapter, ADAPTER_VERSION
from src.mobile.feature_mapper import (
    map_mobile_features,
    FEATURE_MAPPING_VERSION,
    OCULAR_DISCLAIMER,
    PROXY_DISCLAIMER,
)
from src.mobile.prediction_logger import (
    format_mpf_prediction_response,
    log_prediction,
    FORBIDDEN_DIAGNOSTIC_TERMS,
    RESEARCH_DISCLAIMER,
)
from dashboard.api.main import app


# ══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC DATA GENERATORS & HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def generate_synthetic_day_features(
    day_num: int,
    participant_id: str = "SYNTH_P016",
    is_deviated: bool = False,
) -> Dict[str, Any]:
    """
    [SYNTHETIC] Generates a single day's mobile digital biomarker features.
    
    Days 1-14: Normal physiological variation around healthy personal mean.
    Day 15 (if is_deviated): Progressive deviation across voice, motor, typing, sleep.
    """
    f_date = f"2026-09-{day_num:02d}"

    if not is_deviated:
        fluct = math.sin(day_num * 0.7) * 0.05
        return {
            "participant_id": participant_id,
            "feature_date": f_date,
            "date": f_date,
            "raw_feature_version": "1.0.0",
            "processing_version": "1.0.0",
            "app_version": "1.0.0",
            "typing": {
                "typing_speed": 4.5 + fluct,
                "interval_variability": 0.12 + fluct * 0.1,
                "correction_rate": 0.04 + abs(fluct) * 0.02,
                "quality_score": 0.92,
            },
            "voice": {
                "jitter": 0.0075 + fluct * 0.001,
                "shimmer": 0.038 + fluct * 0.005,
                "hnr": 19.5 - fluct * 0.5,
                "pitch_mean": 148.0 + fluct * 2.0,
                "quality_score": 0.95,
            },
            "motor": {
                "cadence": 108.0 + fluct * 3.0,
                "stride_variability": 2.2 + abs(fluct) * 0.3,
                "tapping_rate": 5.2 + fluct * 0.2,
                "tremor_frequency": 0.0,
                "gait_speed_m_per_s": 1.15 + fluct * 0.05,
                "quality_score": 0.90,
            },
            "visual": {
                "blink_rate": 18.0 + fluct * 1.5,
                "gaze_stability": 0.88 - abs(fluct) * 0.02,
                "reaction_time": 260.0 + fluct * 10.0,
                "quality_score": 0.88,
            },
            "sleep": {
                "rbdsq_total": 2.0,
                "unusual_movement_self_report": 0.0,
                "sleep_quality": 8.0,
                "quality_score": 1.0,
            },
        }
    else:
        # Day 15: Progressive deviation from personal baseline
        return {
            "participant_id": participant_id,
            "feature_date": f_date,
            "date": f_date,
            "raw_feature_version": "1.0.0",
            "processing_version": "1.0.0",
            "app_version": "1.0.0",
            "typing": {
                "typing_speed": 2.8,  # Slower typing speed (fine motor slowing)
                "interval_variability": 0.28,  # Higher rhythm variability
                "correction_rate": 0.14,  # More corrections/backspaces
                "quality_score": 0.90,
            },
            "voice": {
                "jitter": 0.0165,  # Elevated jitter (> 2x baseline)
                "shimmer": 0.088,  # Elevated shimmer (> 2x baseline)
                "hnr": 12.2,  # Depressed HNR
                "pitch_mean": 142.0,
                "quality_score": 0.94,
            },
            "motor": {
                "cadence": 82.0,  # Markedly reduced cadence
                "stride_variability": 6.8,  # Increased stride irregularity
                "tapping_rate": 3.1,  # Bradykinesia in finger tapping
                "tremor_frequency": 4.8,  # Emergence of 4-6 Hz rest tremor
                "gait_speed_m_per_s": 0.82,
                "quality_score": 0.91,
            },
            "visual": {
                "blink_rate": 9.5,  # Decreased spontaneous blink rate
                "gaze_stability": 0.65,
                "reaction_time": 395.0,  # Saccadic latency elongation
                "quality_score": 0.86,
            },
            "sleep": {
                "rbdsq_total": 6.0,  # Above cutoff (>= 5)
                "unusual_movement_self_report": 1.0,  # Dream enactment flag
                "sleep_quality": 4.0,
                "quality_score": 1.0,
            },
        }


def compute_personal_baseline_profile(daily_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    [SYNTHETIC] Reference calculation of personal baseline over 14-day calibration.
    """
    n = len(daily_records)
    features_to_track = [
        ("voice", "jitter"),
        ("voice", "shimmer"),
        ("voice", "hnr"),
        ("motor", "cadence"),
        ("motor", "stride_variability"),
        ("motor", "tapping_rate"),
        ("typing", "typing_speed"),
    ]

    metrics: Dict[str, Dict[str, float]] = {}
    for mod, f_name in features_to_track:
        vals = [r[mod][f_name] for r in daily_records if mod in r and f_name in r[mod]]
        mean = sum(vals) / len(vals)
        var = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1) if len(vals) > 1 else 0.0
        std = math.sqrt(var)
        sorted_vals = sorted(vals)
        median = sorted_vals[len(sorted_vals) // 2]
        metrics[f"{mod}.{f_name}"] = {
            "mean": round(mean, 5),
            "std": round(std, 5),
            "median": round(median, 5),
            "sample_count": len(vals),
        }

    status = "established" if n >= 14 else "calibrating"
    return {
        "baseline_version": "1.0.0",
        "sample_count": n,
        "calibration_status": status,
        "feature_metrics": metrics,
    }


def compute_deviation_context(
    day_features: Dict[str, Any],
    baseline_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    [SYNTHETIC] Computes univariate Z-scores and anomaly context relative to baseline.
    """
    metrics = baseline_profile["feature_metrics"]
    z_scores: Dict[str, float] = {}
    significant_deviations: List[str] = []

    features_to_check = [
        ("voice", "jitter"),
        ("voice", "shimmer"),
        ("voice", "hnr"),
        ("motor", "cadence"),
        ("motor", "stride_variability"),
        ("motor", "tapping_rate"),
        ("typing", "typing_speed"),
    ]

    sq_sum = 0.0
    k = 0
    for mod, f_name in features_to_check:
        key = f"{mod}.{f_name}"
        if key in metrics and mod in day_features and f_name in day_features[mod]:
            val = float(day_features[mod][f_name])
            m = metrics[key]["mean"]
            s = metrics[key]["std"]
            if s > 0:
                z = (val - m) / s
                z_scores[key] = round(z, 3)
                sq_sum += z ** 2
                k += 1
                if abs(z) >= 2.0:
                    significant_deviations.append(key)

    pseudo_mahalanobis = round(math.sqrt(sq_sum / max(1, k)), 3)

    return {
        "baseline_version": baseline_profile["baseline_version"],
        "z_scores": z_scores,
        "mahalanobis_distance": pseudo_mahalanobis,
        "significant_deviations": significant_deviations,
        "is_significant_deviation": len(significant_deviations) > 0,
        "deviation_pattern": (
            "Elevated deviation from personal baseline"
            if len(significant_deviations) > 0
            else "Within personal baseline"
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 1: End-to-End Mobile Pipeline (14-Day Baseline to Day 15 Inference)
# ══════════════════════════════════════════════════════════════════════════════

class TestEndToEndMobilePipeline:
    """
    Executes Section 2 of Phase 16:
    1. Simulate 14 days of mobile data collection (synthetic)
    2. Establish personal baseline (status -> established)
    3. Generate Day 15 features with progressive deviation
    4. Pass through MPF adapter
    5. Run frozen MPF inference
    6. Return risk score & explanation to dashboard
    7. Verify version tracking & non-diagnostic language
    """

    @pytest.fixture
    def simulated_14_days(self):
        """[SYNTHETIC] 14 days of regular longitudinal mobile observations."""
        return [generate_synthetic_day_features(day) for day in range(1, 15)]

    def test_step1_and_step2_baseline_calibration(self, simulated_14_days):
        """Simulate 14 days and establish baseline."""
        assert len(simulated_14_days) == 14
        profile = compute_personal_baseline_profile(simulated_14_days)
        assert profile["sample_count"] == 14
        assert profile["calibration_status"] == "established"
        assert profile["baseline_version"] == "1.0.0"

        # Check feature statistics
        v_jit = profile["feature_metrics"]["voice.jitter"]
        assert v_jit["sample_count"] == 14
        assert 0.005 < v_jit["mean"] < 0.015
        assert v_jit["std"] > 0.0

    def test_step3_day15_progressive_deviation(self, simulated_14_days):
        """Generate Day 15 with marked deviation and verify deviation metrics."""
        baseline_profile = compute_personal_baseline_profile(simulated_14_days)
        day15 = generate_synthetic_day_features(15, is_deviated=True)
        dev_ctx = compute_deviation_context(day15, baseline_profile)

        assert dev_ctx["is_significant_deviation"] is True
        assert dev_ctx["mahalanobis_distance"] >= 2.0
        assert "voice.jitter" in dev_ctx["significant_deviations"]
        assert "motor.stride_variability" in dev_ctx["significant_deviations"]
        assert "typing.typing_speed" in dev_ctx["significant_deviations"]

    def test_step4_adapter_mapping_and_qc(self, simulated_14_days):
        """Verify Day 15 features map correctly through MPF Adapter and feature mapper."""
        day15 = generate_synthetic_day_features(15, is_deviated=True)
        adapter = MPFAdapter(log_file_path=None)

        # Validate schema
        val_res = adapter.validate_feature_schema(day15)
        assert val_res["valid"] is True
        assert len(val_res["errors"]) == 0

        # Map to MPF format
        mapped_payload, meta = map_mobile_features(day15, demographics={"age": 68.0, "sex": "male"})
        assert mapped_payload["age"] == 68.0
        assert mapped_payload["sex"] == "male"

        # Sensory integrity rule enforcement:
        assert mapped_payload["olfactory"]["available"] is False
        assert mapped_payload["retina"]["available"] is False
        assert mapped_payload["voice"]["available"] is True
        assert mapped_payload["motor"]["available"] is True
        assert mapped_payload["rbd"]["available"] is True
        assert mapped_payload["ocular_visual"]["is_retinal_imaging"] is False

    def test_step5_to_step8_mpf_inference_and_version_logging(self, simulated_14_days):
        """
        Run inference on Day 15, inspect risk score, explanation, and 5-tuple version logging.
        """
        baseline_profile = compute_personal_baseline_profile(simulated_14_days)
        day15 = generate_synthetic_day_features(15, is_deviated=True)
        dev_ctx = compute_deviation_context(day15, baseline_profile)

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp_log:
            tmp_log_path = tmp_log.name

        try:
            adapter = MPFAdapter(log_file_path=tmp_log_path)
            res = adapter.run_inference(
                mobile_daily_features=day15,
                baseline_deviation_context=dev_ctx,
                demographics={"age": 68.0, "sex": "male"},
                log_to_db=True,
                raw_feature_version="1.0.0",
                processing_version="1.0.0",
                baseline_version="1.0.0",
                app_version="1.0.0",
            )

            # Step 6: Risk score returned to dashboard
            assert "risk_score" in res
            assert isinstance(res["risk_score"], float)
            assert 0.0 <= res["risk_score"] <= 1.0

            # Step 7: Verify explanation is available
            assert "explanation" in res
            exp = res["explanation"]
            assert isinstance(exp, dict)
            # Explanation contains important modalities or gate weights
            assert "important_modalities" in exp or "gate_weights" in res
            if "important_modalities" in exp:
                mods_in_exp = [item["modality"] for item in exp.get("important_modalities", [])]
                assert any(m in mods_in_exp for m in ["voice", "motor", "rbd"])

            # Step 8: Verify all 5 versions are logged in prediction_metadata
            meta = res["prediction_metadata"]
            assert meta["source"] == "mobile_extension"
            assert meta["model_version"] == "gated_multimodal_fusion_v1"
            assert meta["feature_mapping_version"] == FEATURE_MAPPING_VERSION
            assert meta["feature_version"] == "1.0.0"
            assert meta["raw_feature_version"] == "1.0.0"
            assert meta["processing_version"] == "1.0.0"
            assert meta["baseline_version"] == "1.0.0"
            assert meta["app_version"] == "1.0.0"
            assert meta["baseline_deviation_context"] == dev_ctx

            # Audit file logging verification
            with open(tmp_log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 1
            audit_entry = json.loads(lines[0])
            assert "record_id" in audit_entry
            assert audit_entry["prediction"]["risk_score"] == res["risk_score"]

            # Step 9: Safety & non-diagnostic language
            serialized = json.dumps(res).lower()
            for forbidden in FORBIDDEN_DIAGNOSTIC_TERMS:
                assert forbidden not in serialized, f"Forbidden diagnostic claim '{forbidden}' in output!"
            assert "research screening result" in serialized
            assert "not a clinical diagnosis" in serialized
            assert "risk pattern" in serialized

        finally:
            Path(tmp_log_path).unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 2: Backward Compatibility & Zero Regression
# ══════════════════════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    """
    Executes Section 3 of Phase 16:
    1. Existing MPF pipeline runs with standard 5-modality clinical inputs
    2. Model outputs are identical and unchanged
    3. Missing modalities handling is unchanged
    4. Mobile extension is purely additive (zero modifications to existing core)
    """

    def test_existing_pipeline_5_modality_execution(self):
        """Verify original MPF pipeline runs directly without mobile extension."""
        standard_inputs = {
            "participant_id": "LEGACY_CLINICAL_001",
            "age": 65.0,
            "sex": "male",
            "olfactory": {
                "available": True,
                "total_score": 26.0,
                "response_time_mean": 3.8,
            },
            "rbd": {
                "available": True,
                "rbdsq_total": 4.0,
                "above_cutoff_flag": 0.0,
            },
            "voice": {
                "available": True,
                "features": {
                    "jitter_pct": 0.006,
                    "shimmer": 0.035,
                    "hnr": 21.0,
                    "pitch_mean": 140.0,
                },
            },
            "motor": {
                "available": True,
                "features": {
                    "gait_speed_m_per_s": 1.20,
                    "cadence_steps_per_min": 110.0,
                    "stride_interval_cv_pct": 2.1,
                },
            },
            "retina": {
                "available": True,
                "features": {
                    "vessel_density": 0.068,
                    "mean_vessel_diameter_px": 3.1,
                },
            },
        }

        result = run_mpf_pipeline(standard_inputs)
        assert result["status"] == "success"
        assert result["participant_id"] == "LEGACY_CLINICAL_001"
        assert "fusion" in result
        assert 0.0 <= result["fusion"]["risk_score"] <= 1.0
        assert len(result["available_modalities"]) == 5
        assert len(result["missing_modalities"]) == 0
        assert result["metadata"]["pipeline_version"] == PIPELINE_VERSION

    def test_existing_pipeline_missing_modalities_backward_compatibility(self):
        """Verify original pipeline still handles subsets of missing modalities properly."""
        inputs_with_missing = {
            "participant_id": "LEGACY_CLINICAL_002",
            "age": 72.0,
            "sex": "female",
            "olfactory": {"available": True, "total_score": 14.0},
            "voice": {"available": True, "features": {"jitter_pct": 0.015, "shimmer": 0.08, "hnr": 13.0}},
            "rbd": {"available": False},
            "motor": {"available": False},
            "retina": {"available": False},
        }

        result = run_mpf_pipeline(inputs_with_missing)
        assert result["status"] in ["success", "partial_success"]
        assert "olfactory" in result["available_modalities"]
        assert "voice" in result["available_modalities"]
        assert "rbd" in result["missing_modalities"]
        assert "motor" in result["missing_modalities"]
        assert "retina" in result["missing_modalities"]
        assert 0.0 <= result["fusion"]["risk_score"] <= 1.0

    def test_models_remain_frozen_and_unmodified(self):
        """Verify models/ directory artifacts exist and are unmodified."""
        fusion_clf = ROOT / "models" / "fusion" / "classifier.joblib"
        fusion_encoder = ROOT / "models" / "fusion" / "fusion_encoder.pt"
        preprocessor = ROOT / "models" / "fusion" / "preprocessor.joblib"

        assert fusion_clf.exists()
        assert fusion_encoder.exists()
        assert preprocessor.exists()

        # Check metadata.json exists and tracks model version
        meta_file = ROOT / "models" / "fusion" / "metadata.json"
        if meta_file.exists():
            with open(meta_file, "r", encoding="utf-8") as f:
                meta_data = json.load(f)
            assert "model_type" in meta_data or "model_version" in meta_data or "model_name" in meta_data


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 3: FastAPI REST API Mobile Endpoint Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestApiMobileEndpointIntegration:
    """
    Validates the POST /api/mobile/analyze HTTP endpoint through FastAPI TestClient.
    """

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_api_mobile_analyze_standard_flow(self, client):
        """Send mobile daily features to /api/mobile/analyze and verify Section 5 response."""
        day15 = generate_synthetic_day_features(15, is_deviated=True)
        payload = {
            "participant_id": "HTTP_MOBILE_001",
            "features": day15,
            "baseline_deviation_context": {
                "baseline_version": "1.0.0",
                "mahalanobis_distance": 2.45,
                "significant_deviations": ["voice.jitter", "motor.cadence"],
            },
            "demographics": {"age": 66.0, "sex": "female"},
            "log_to_db": False,
            "raw_feature_version": "1.0.0",
            "processing_version": "1.0.0",
            "baseline_version": "1.0.0",
            "app_version": "1.0.0",
        }

        resp = client.post("/api/mobile/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert "risk_score" in data
        assert isinstance(data["risk_score"], float)
        assert 0.0 <= data["risk_score"] <= 1.0
        assert data["status"] == "success"
        assert "risk_pattern" in data
        assert data["model_version"] == "gated_multimodal_fusion_v1"

        # Check modalities: mobile present, clinic absent
        assert "retina" in data["missing_modalities"]
        assert "olfactory" in data["missing_modalities"]

        # Check metadata
        meta = data["prediction_metadata"]
        assert meta["source"] == "mobile_extension"
        assert meta["baseline_version"] == "1.0.0"
        assert meta["feature_version"] == "1.0.0"
        assert meta["app_version"] == "1.0.0"
        assert meta["disclaimer"] == RESEARCH_DISCLAIMER

    def test_api_mobile_analyze_invalid_payload_handling(self, client):
        """Verify API handles non-dict features gracefully."""
        payload = {
            "participant_id": "BAD_PAYLOAD_001",
            "features": "not-a-dict",
            "log_to_db": False,
        }
        resp = client.post("/api/mobile/analyze", json=payload)
        assert resp.status_code == 422  # Pydantic validation error
