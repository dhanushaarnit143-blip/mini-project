"""
MPF Mobile Extension — Prediction Logger & Metadata Audit Service (Phase 12).

Records model predictions, explainability attributions, gate weights,
and full versioned provenance in Supabase `mpf_predictions` and local logs.

VERSIONED REPRODUCIBILITY MANDATE:
Every prediction records:
- source: 'mobile_extension'
- feature_mapping_version
- baseline_deviation_context
- model_version
- pipeline_version
- ISO timestamp

NON-DIAGNOSTIC COMMUNICATION RULE:
- Never say: "You have Parkinson's"
- Never say: "Parkinson's progression"
- Always say: "Elevated Parkinson's risk pattern detected" / "Standard risk pattern observed"
- Always say: "Research screening result — not a clinical diagnosis."
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("mpf.mobile.prediction_logger")

RESEARCH_DISCLAIMER = "Research screening result — not a clinical diagnosis."
FORBIDDEN_DIAGNOSTIC_TERMS = [
    "you have parkinson's",
    "parkinson's progression",
    "confirmed parkinson",
    "clinical diagnosis of parkinson",
]


def format_mpf_prediction_response(
    raw_mpf_result: Dict[str, Any],
    feature_mapping_version: str = "1.0.0",
    baseline_deviation_context: Optional[Dict[str, Any]] = None,
    custom_timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Format MPF model output according to Section 5 specification:
    {
      "risk_score": 0.0-1.0,
      "available_modalities": [...],
      "missing_modalities": [...],
      "model_version": "...",
      "prediction_metadata": {
        "source": "mobile_extension",
        "feature_mapping_version": "...",
        "baseline_deviation_context": {...},
        "timestamp": "..."
      }
    }
    """
    fusion_dict = raw_mpf_result.get("fusion") or {}
    risk_score = raw_mpf_result.get("risk_score")
    if risk_score is None:
        risk_score = fusion_dict.get("risk_score")

    if risk_score is not None:
        try:
            risk_score = round(float(risk_score), 4)
            risk_score = max(0.0, min(1.0, risk_score))
        except (ValueError, TypeError):
            risk_score = None

    avail_mods = list(raw_mpf_result.get("available_modalities") or [])
    missing_mods = list(raw_mpf_result.get("missing_modalities") or [])

    model_ver = (
        raw_mpf_result.get("model_version")
        or fusion_dict.get("model_version")
        or raw_mpf_result.get("metadata", {}).get("model_versions", {}).get("fusion")
        or "gated_multimodal_fusion_v1"
    )

    now_iso = custom_timestamp or datetime.now(timezone.utc).isoformat()
    baseline_ctx = baseline_deviation_context or {}

    # Determine standardized non-diagnostic risk pattern
    if risk_score is not None:
        risk_pattern = (
            "Elevated Parkinson's risk pattern detected"
            if risk_score >= 0.5
            else "Standard risk pattern observed"
        )
    else:
        risk_pattern = "Assessment incomplete — insufficient modality data"

    prediction_metadata = {
        "source": "mobile_extension",
        "feature_mapping_version": feature_mapping_version,
        "baseline_deviation_context": baseline_ctx,
        "timestamp": now_iso,
        "disclaimer": RESEARCH_DISCLAIMER,
        "risk_pattern": risk_pattern,
    }

    # Pass through gate weights, explainability, and embeddings faithfully
    formatted = {
        "risk_score": risk_score,
        "available_modalities": avail_mods,
        "missing_modalities": missing_mods,
        "model_version": model_ver,
        "prediction_metadata": prediction_metadata,
        # Preserve additional details from existing MPF pipeline
        "status": raw_mpf_result.get("status", "success"),
        "risk_pattern": risk_pattern,
        "gate_weights": fusion_dict.get("gate_weights", {}),
        "fused_embedding": fusion_dict.get("fused_embedding", []),
        "explanation": raw_mpf_result.get("explanation") or raw_mpf_result.get("explainability") or {},
        "warnings": raw_mpf_result.get("warnings", []),
    }

    # Verify no disallowed diagnostic statements in serialized text
    serialized_repr = json.dumps(formatted).lower()
    for term in FORBIDDEN_DIAGNOSTIC_TERMS:
        if term in serialized_repr:
            raise ValueError(f"Disallowed diagnostic language '{term}' detected in prediction output.")

    return formatted


def log_prediction(
    prediction_output: Dict[str, Any],
    participant_id: str,
    feature_date: str,
    daily_feature_id: Optional[str] = None,
    supabase_client: Optional[Any] = None,
    log_file_path: Optional[str] = "logs/mobile_predictions.jsonl",
) -> Dict[str, Any]:
    """
    Log prediction record to Supabase mpf_predictions and/or local audit file.

    Args:
        prediction_output: Formatted prediction response.
        participant_id: UUID of participant.
        feature_date: Date (YYYY-MM-DD).
        daily_feature_id: Optional UUID of daily_features record.
        supabase_client: Optional Supabase Python client.
        log_file_path: Optional local JSONL audit path.

    Returns:
        Dict with logging status and recorded IDs.
    """
    record_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    risk_score = prediction_output.get("risk_score")
    if risk_score is None:
        risk_score = 0.5  # Neutral default for missing calculation

    # Build database row conforming to migration 011 (mpf_predictions)
    db_record = {
        "id": record_id,
        "participant_id": participant_id,
        "timestamp": now_iso,
        "model_version": prediction_output.get("model_version", "gated_multimodal_fusion_v1"),
        "input_feature_version": prediction_output.get("prediction_metadata", {}).get(
            "feature_mapping_version", "1.0.0"
        ),
        "available_modalities": prediction_output.get("available_modalities", []),
        "missing_modalities": prediction_output.get("missing_modalities", []),
        "risk_score": float(risk_score),
        "prediction_metadata": {
            **prediction_output.get("prediction_metadata", {}),
            "gate_weights": prediction_output.get("gate_weights", {}),
            "fused_embedding": prediction_output.get("fused_embedding", []),
            "explanation": prediction_output.get("explanation", {}),
            "status": prediction_output.get("status", "success"),
            "daily_feature_id": daily_feature_id,
            "feature_date": feature_date,
        },
        "created_at": now_iso,
    }

    supabase_logged = False
    supabase_error = None

    if supabase_client is not None:
        try:
            res = supabase_client.table("mpf_predictions").insert(db_record).execute()
            if res.data:
                supabase_logged = True
                logger.info(f"Logged prediction to Supabase for participant {participant_id}")
        except Exception as e:
            supabase_error = str(e)
            logger.warning(f"Could not log to Supabase mpf_predictions table: {e}")

    # Local fallback file logging for audit reproducibility
    local_logged = False
    if log_file_path:
        try:
            log_path = Path(log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                log_entry = {
                    "logged_at": now_iso,
                    "record_id": record_id,
                    "prediction": prediction_output,
                    "db_record": db_record,
                }
                f.write(json.dumps(log_entry) + "\n")
            local_logged = True
        except Exception as log_err:
            logger.warning(f"Could not write to local audit log '{log_file_path}': {log_err}")

    return {
        "record_id": record_id,
        "supabase_logged": supabase_logged,
        "supabase_error": supabase_error,
        "local_logged": local_logged,
        "db_record": db_record,
    }
