"""
MPF Mobile Extension — MPF Adapter Layer (Phase 12).

Integrates mobile longitudinal daily features with the existing MPF-PD
multimodal prodromal screening model.

NON-NEGOTIABLE INTEGRATION RULES:
1. NO DIAGNOSTIC CLAIMS:
   - "Elevated Parkinson's risk pattern detected" / "Standard risk pattern observed"
   - "Research screening result — not a clinical diagnosis"
   - "Progressive deviation from personal baseline" (never disease progression claims)
2. NO SENSOR OVERCLAIMING:
   - Smartphone front camera is strictly Ocular/Visual Behavior Module, NOT retinal imaging.
   - Retinal and olfactory modalities are strictly marked unavailable (available=False).
3. NO RETRAINING:
   - Model inference ONLY. Never retrain, fine-tune, or refit model weights or scalers.
4. EXACT PREPROCESSING:
   - Preprocessing re-uses models/fusion/preprocessor.joblib without modification.
5. PRESERVE MODEL OUTPUTS UNCHANGED:
   - Raw model predictions and risk scores are passed through faithfully.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.pipeline import run_mpf_pipeline, ALL_MODALITIES
from src.mobile.feature_mapper import (
    map_mobile_features,
    FEATURE_MAPPING_VERSION,
    PROXY_DISCLAIMER,
    OCULAR_DISCLAIMER,
)
from src.mobile.normalization_loader import (
    load_training_preprocessors,
    normalize_modality_features,
    normalize_demographics,
    get_modality_feature_columns,
    DEFAULT_PREPROCESSOR_PATH,
)
from src.mobile.prediction_logger import (
    format_mpf_prediction_response,
    log_prediction,
    RESEARCH_DISCLAIMER,
)

logger = logging.getLogger("mpf.mobile.mpf_adapter")

ADAPTER_VERSION = "1.0.0"


class MPFAdapter:
    """
    Adapter bridging Mobile Longitudinal Feature Ingestion and the MPF Pipeline.
    """

    def __init__(
        self,
        supabase_client: Optional[Any] = None,
        preprocessor_path: str = DEFAULT_PREPROCESSOR_PATH,
        log_file_path: Optional[str] = "logs/mobile_predictions.jsonl",
    ):
        """
        Initialize the MPF Adapter.

        Args:
            supabase_client: Optional Supabase Python client instance.
            preprocessor_path: Path to models/fusion/preprocessor.joblib.
            log_file_path: Path to JSONL audit log.
        """
        self.supabase_client = supabase_client
        self.preprocessor_path = preprocessor_path
        self.log_file_path = log_file_path
        # Verify preprocessors can be loaded (asserts artifact existence)
        self.preprocessors = load_training_preprocessors(self.preprocessor_path)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. LOAD DAILY FEATURES
    # ─────────────────────────────────────────────────────────────────────────
    def load_daily_features(
        self,
        participant_id: str,
        feature_date: str,
        local_cache_dir: Optional[Union[str, Path]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Load daily features for a participant and date from Supabase or local cache.

        Args:
            participant_id: UUID of participant.
            feature_date: Date (YYYY-MM-DD).
            local_cache_dir: Optional directory containing cached daily feature JSON files.

        Returns:
            Dict containing daily features, or None if not found.
        """
        # 1. Attempt Supabase lookup if client available
        if self.supabase_client is not None:
            try:
                res = (
                    self.supabase_client.table("daily_features")
                    .select("*")
                    .eq("participant_id", participant_id)
                    .eq("feature_date", feature_date)
                    .limit(1)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    logger.info(
                        f"Loaded daily features from Supabase for {participant_id} on {feature_date}"
                    )
                    return res.data[0]
            except Exception as e:
                logger.warning(f"Error querying Supabase daily_features: {e}")

        # 2. Fallback to local cache directory if provided
        if local_cache_dir:
            cache_p = Path(local_cache_dir)
            candidate_files = [
                cache_p / f"{participant_id}_{feature_date}.json",
                cache_p / f"{participant_id}" / f"{feature_date}.json",
                cache_p / f"daily_features_{participant_id}_{feature_date}.json",
            ]
            for c_file in candidate_files:
                if c_file.exists():
                    try:
                        with open(c_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        logger.info(f"Loaded daily features from local cache '{c_file}'")
                        return data
                    except Exception as err:
                        logger.warning(f"Failed to read local cache file '{c_file}': {err}")

        logger.info(f"No daily features found for {participant_id} on {feature_date}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # 2. VALIDATE FEATURE SCHEMA
    # ─────────────────────────────────────────────────────────────────────────
    def validate_feature_schema(
        self,
        features: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate incoming mobile features against schema and quality requirements.

        Returns:
            Dict with 'valid' (bool), 'errors' (list[str]), 'warnings' (list[str]).
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(features, dict):
            return {
                "valid": False,
                "errors": [f"Features payload must be a dict. Got {type(features).__name__}"],
                "warnings": warnings,
            }

        raw_feats = features.get("features", features)

        # Modality checks
        typing_f = raw_feats.get("typing")
        if typing_f is not None and not isinstance(typing_f, dict):
            errors.append("Modality 'typing' must be an object/dict.")

        voice_f = raw_feats.get("voice")
        if voice_f is not None and not isinstance(voice_f, dict):
            errors.append("Modality 'voice' must be an object/dict.")

        motor_f = raw_feats.get("motor")
        if motor_f is not None and not isinstance(motor_f, dict):
            errors.append("Modality 'motor' must be an object/dict.")

        visual_f = raw_feats.get("visual")
        if visual_f is not None and not isinstance(visual_f, dict):
            errors.append("Modality 'visual' must be an object/dict.")

        sleep_f = raw_feats.get("sleep")
        if sleep_f is not None and not isinstance(sleep_f, dict):
            errors.append("Modality 'sleep' must be an object/dict.")

        # Physiological range boundary checks
        if isinstance(voice_f, dict):
            jitter = voice_f.get("jitter") or voice_f.get("jitter_pct")
            if jitter is not None:
                try:
                    j_val = float(jitter)
                    if j_val < 0.0 or j_val > 0.5:
                        warnings.append(f"Voice jitter value {j_val} is outside standard range [0.0, 0.5].")
                except (ValueError, TypeError):
                    errors.append(f"Invalid non-numeric voice jitter value: {jitter}")

        if isinstance(motor_f, dict):
            cadence = motor_f.get("cadence") or motor_f.get("cadence_steps_per_min")
            if cadence is not None:
                try:
                    c_val = float(cadence)
                    if c_val < 20.0 or c_val > 250.0:
                        warnings.append(f"Motor cadence {c_val} steps/min is outside plausible range [20, 250].")
                except (ValueError, TypeError):
                    errors.append(f"Invalid non-numeric motor cadence: {cadence}")

        is_valid = len(errors) == 0
        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 3. RUN INFERENCE VIA MPF PIPELINE
    # ─────────────────────────────────────────────────────────────────────────
    def run_inference(
        self,
        mobile_daily_features: Dict[str, Any],
        baseline_deviation_context: Optional[Dict[str, Any]] = None,
        demographics: Optional[Dict[str, Any]] = None,
        feature_date: Optional[str] = None,
        log_to_db: bool = True,
        raw_feature_version: Optional[str] = None,
        processing_version: Optional[str] = "1.0.0",
        baseline_version: Optional[Union[str, int]] = None,
        app_version: Optional[str] = "1.0.0",
    ) -> Dict[str, Any]:
        """
        Execute end-to-end inference for a mobile observation:
        1. Validate schema
        2. Map features to MPF representation
        3. Pass to frozen MPF pipeline
        4. Return existing model's output unchanged in Section 5 format
        5. Log metadata for reproducibility (tracking all 5 version coordinates)

        Args:
            mobile_daily_features: Mobile features dictionary.
            baseline_deviation_context: Optional deviation metrics from personal baseline.
            demographics: Optional dict with 'age' and 'sex'.
            feature_date: Date string (YYYY-MM-DD).
            log_to_db: Whether to write audit record to Supabase/logs.
            raw_feature_version: Optional version of raw feature extractor.
            processing_version: Optional version of feature processing pipeline.
            baseline_version: Optional version of baseline calibration.
            app_version: Optional version of mobile application.

        Returns:
            Formatted response dict conforming to Section 5.
        """
        # Step 1: Validate feature schema
        val_res = self.validate_feature_schema(mobile_daily_features)
        if not val_res["valid"]:
            error_output = {
                "risk_score": None,
                "status": "failed_schema_validation",
                "available_modalities": [],
                "missing_modalities": ALL_MODALITIES,
                "model_version": "gated_multimodal_fusion_v1",
                "errors": val_res["errors"],
                "warnings": val_res["warnings"],
                "prediction_metadata": {
                    "source": "mobile_extension",
                    "feature_mapping_version": FEATURE_MAPPING_VERSION,
                    "baseline_deviation_context": baseline_deviation_context or {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "disclaimer": RESEARCH_DISCLAIMER,
                },
            }
            return error_output

        # Step 2: Map mobile features to MPF representation
        mapped_payload, mapping_meta = map_mobile_features(
            mobile_daily_features=mobile_daily_features,
            demographics=demographics,
        )

        p_id = mapped_payload.get("participant_id", "MOBILE_001")
        f_date = (
            feature_date
            or mobile_daily_features.get("feature_date")
            or mobile_daily_features.get("date")
            or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )

        # Check if all mobile modalities are absent
        active_modalities = [
            m for m in ["voice", "motor", "rbd"]
            if mapped_payload.get(m, {}).get("available")
        ]

        if len(active_modalities) == 0:
            logger.warning("No mobile modalities available for inference.")
            no_data_output = {
                "risk_score": None,
                "status": "skipped_no_modalities_available",
                "available_modalities": [],
                "missing_modalities": ALL_MODALITIES,
                "model_version": "gated_multimodal_fusion_v1",
                "warnings": [
                    "All mobile modalities are missing or failed quality control.",
                    "Inference was not performed to prevent data fabrication.",
                ],
                "prediction_metadata": {
                    "source": "mobile_extension",
                    "feature_mapping_version": FEATURE_MAPPING_VERSION,
                    "baseline_deviation_context": baseline_deviation_context or {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "disclaimer": RESEARCH_DISCLAIMER,
                },
            }
            return no_data_output

        # Step 3: Run existing MPF pipeline (FROZEN - INFERENCE ONLY)
        # Note: run_mpf_pipeline internally re-applies exact preprocessing via predict_fusion
        raw_mpf_result = run_mpf_pipeline(mapped_payload)

        # Step 4: Format output conforming to Section 5
        raw_feat_ver = (
            raw_feature_version
            or mobile_daily_features.get("raw_feature_version")
            or mobile_daily_features.get("feature_version")
        )
        base_ver = (
            baseline_version
            or (baseline_deviation_context or {}).get("baseline_version")
        )
        app_ver = (
            app_version
            or mobile_daily_features.get("app_version")
        )
        proc_ver = (
            processing_version
            or mobile_daily_features.get("processing_version")
            or "1.0.0"
        )

        formatted_response = format_mpf_prediction_response(
            raw_mpf_result=raw_mpf_result,
            feature_mapping_version=FEATURE_MAPPING_VERSION,
            baseline_deviation_context=baseline_deviation_context or {},
            raw_feature_version=raw_feat_ver,
            processing_version=proc_ver,
            baseline_version=base_ver,
            app_version=app_ver,
        )

        # Step 5: Log prediction metadata for reproducibility
        if log_to_db:
            try:
                log_prediction(
                    prediction_output=formatted_response,
                    participant_id=p_id,
                    feature_date=f_date,
                    daily_feature_id=mobile_daily_features.get("id"),
                    supabase_client=self.supabase_client,
                    log_file_path=self.log_file_path,
                )
            except Exception as log_err:
                logger.warning(f"Prediction logging encountered non-critical error: {log_err}")

        return formatted_response


def run_mobile_adapter(
    mobile_daily_features: Dict[str, Any],
    baseline_deviation_context: Optional[Dict[str, Any]] = None,
    demographics: Optional[Dict[str, Any]] = None,
    supabase_client: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Convenience function to run MPF adapter inference on a single observation.
    """
    adapter = MPFAdapter(supabase_client=supabase_client)
    return adapter.run_inference(
        mobile_daily_features=mobile_daily_features,
        baseline_deviation_context=baseline_deviation_context,
        demographics=demographics,
        **kwargs,
    )
