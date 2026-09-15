"""
MPF-PD End-to-End Analysis Pipeline.

Coordinates:
  1. Input validation & participant pseudonymisation.
  2. Individual modality feature extraction, QC, and risk estimation:
     - Olfactory (UPSIT / Sniffin' Sticks)
     - RBD (RBDSQ questionnaire)
     - Voice (Acoustic audio .wav analysis / tabular features)
     - Motor (Gait / Tapping CSV/JSON sensor records / tabular features)
     - Retina (Fundus image analysis / vessel morphology & deep embedding)
  3. Gated multimodal neural fusion (predict_fusion).
  4. Local explainability & SHAP attribution (explain_single).
  5. Missing modality handling with uncertainty reporting.

RESEARCH PROTOTYPE ONLY — NOT A CLINICAL DIAGNOSTIC DEVICE.
No clinical claims: estimates prodromal risk patterns for research screening.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure project root is on sys.path
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import numpy as np

from src.olfactory.predict import predict_olfactory
from src.rbd.predict import predict_rbd
from src.voice.predict import predict_voice
from src.motor.predict import predict_motor
from src.retina.predict import predict_retina
from src.fusion.dataset import MODALITIES
from src.fusion.predict import predict_fusion
from src.explainability.local_explanation import explain_single

logger = logging.getLogger("mpf.pipeline")

# Standard research prototype notices
DISCLAIMER_WARNINGS = [
    "RESEARCH PROTOTYPE: Risk score is an investigational estimate only.",
    "NOT FOR CLINICAL DIAGNOSIS: No clinical validity is claimed.",
    "Requires clinician review if used in future clinical studies.",
]


def run_mpf_pipeline(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the full MPF-PD multimodal prodromal screening pipeline.

    Args:
        inputs: Dictionary containing:
            - participant_id: Pseudonymous identifier (str)
            - age: Participant age in years (float, 40-90)
            - sex: "female" | "male" | 0 | 1
            - olfactory: Optional dict (available: bool, total_score: float, ...)
            - rbd: Optional dict (available: bool, rbdsq_total: float, items: list/dict, ...)
            - voice: Optional dict (available: bool, audio_file: str, features: dict, ...)
            - motor: Optional dict (available: bool, file_path: str, features: dict, ...)
            - retina: Optional dict (available: bool, image_path: str, features: dict, ...)

    Returns:
        Structured dictionary matching Phase 8 API specification:
            - participant_id: str
            - demographics: dict
            - individual_modalities: dict of per-modality status, risk, and features
            - fusion: dict of fused risk_score, risk_pattern, gate_weights, embeddings
            - explainability: dict of SHAP values, feature importance, and narrative
            - missing_modalities: list of absent modalities
            - warnings: list of research disclaimers and notes
    """
    warnings: List[str] = list(DISCLAIMER_WARNINGS)

    # 1. Demographics & Participant ID
    participant_id = str(inputs.get("participant_id") or "PAR-PROTOTYPE-001").strip()
    try:
        age_val = float(inputs.get("age", 65.0))
        if age_val < 18 or age_val > 120:
            warnings.append(f"Age {age_val} is outside standard screening reference (40-90).")
    except (ValueError, TypeError):
        age_val = 65.0
        warnings.append("Invalid age specified; using reference screening age 65.0.")

    sex_raw = inputs.get("sex", "female")
    demographics = {
        "age": age_val,
        "sex": "male" if str(sex_raw).strip().lower() in ["m", "male", "1"] else "female",
    }

    # 2. Individual Modality Processing
    individual_results: Dict[str, Any] = {}
    fusion_features: Dict[str, Any] = {
        "age": age_val,
        "sex": demographics["sex"],
    }
    missing_modalities: List[str] = []

    # --- Olfactory ---
    olf_input = inputs.get("olfactory")
    if isinstance(olf_input, dict) and olf_input.get("available", True):
        olf_data = {k: v for k, v in olf_input.items() if k != "available"}
        try:
            res = predict_olfactory(olf_data)
            individual_results["olfactory"] = {
                "available": True,
                "status": "success",
                "risk_score": res.get("risk_score"),
                "features": olf_data,
                "quality": {"passed": True, "issues": []},
                "warnings": res.get("warnings", []),
            }
            fusion_features["olfactory"] = olf_data
        except Exception as e:
            logger.warning(f"Olfactory analysis failed: {e}")
            individual_results["olfactory"] = {
                "available": True,
                "status": "error",
                "risk_score": None,
                "features": {},
                "quality": {"passed": False, "issues": [str(e)]},
                "warnings": [f"Olfactory processing error: {e}"],
            }
            missing_modalities.append("olfactory")
    else:
        individual_results["olfactory"] = {
            "available": False,
            "status": "missing",
            "risk_score": None,
            "features": {},
            "quality": {"passed": False, "issues": ["Modality marked as missing or not provided."]},
            "warnings": ["Modality 'olfactory' was omitted from this analysis session."],
        }
        missing_modalities.append("olfactory")

    # --- RBD ---
    rbd_input = inputs.get("rbd")
    if isinstance(rbd_input, dict) and rbd_input.get("available", True):
        rbd_data = {k: v for k, v in rbd_input.items() if k != "available"}
        # Check if items list or individual item_1..13 provided
        if "items" in rbd_data and isinstance(rbd_data["items"], (list, dict)):
            items_raw = rbd_data["items"]
            if isinstance(items_raw, list):
                for i, val in enumerate(items_raw):
                    rbd_data[f"item_{i+1}"] = int(bool(val))
            elif isinstance(items_raw, dict):
                for k, v in items_raw.items():
                    rbd_data[k] = int(bool(v))
            if "rbdsq_total" not in rbd_data:
                rbd_data["rbdsq_total"] = sum(
                    int(bool(rbd_data.get(f"item_{i}", 0))) for i in range(1, 14)
                )

        try:
            res = predict_rbd(rbd_data)
            individual_results["rbd"] = {
                "available": True,
                "status": "success",
                "risk_score": res.get("risk_score"),
                "features": rbd_data,
                "quality": {"passed": True, "issues": []},
                "warnings": res.get("warnings", []),
            }
            fusion_features["rbd"] = rbd_data
        except Exception as e:
            logger.warning(f"RBD analysis failed: {e}")
            individual_results["rbd"] = {
                "available": True,
                "status": "error",
                "risk_score": None,
                "features": {},
                "quality": {"passed": False, "issues": [str(e)]},
                "warnings": [f"RBD processing error: {e}"],
            }
            missing_modalities.append("rbd")
    else:
        individual_results["rbd"] = {
            "available": False,
            "status": "missing",
            "risk_score": None,
            "features": {},
            "quality": {"passed": False, "issues": ["Modality marked as missing or not provided."]},
            "warnings": ["Modality 'rbd' was omitted from this analysis session."],
        }
        missing_modalities.append("rbd")

    # --- Voice ---
    voice_input = inputs.get("voice")
    if isinstance(voice_input, dict) and voice_input.get("available", True):
        audio_file = voice_input.get("audio_file")
        tabular_feats = voice_input.get("features")
        try:
            if audio_file and Path(audio_file).exists():
                res = predict_voice(audio_file=audio_file)
            elif tabular_feats and isinstance(tabular_feats, dict):
                res = predict_voice(tabular_features=tabular_feats)
            else:
                direct_feats = {
                    k: v for k, v in voice_input.items()
                    if k not in ["available", "audio_file", "features"]
                }
                if direct_feats:
                    res = predict_voice(tabular_features=direct_feats)
                else:
                    raise ValueError("Neither valid audio_file nor voice features provided.")

            quality = res.get("quality", {"passed": True, "issues": []})
            is_passed = quality.get("passed", True)
            status = "success" if is_passed else "failed_qc"

            features_used = {}
            if tabular_feats and isinstance(tabular_feats, dict):
                features_used = tabular_feats
            elif "direct_feats" in locals() and direct_feats:
                features_used = direct_feats

            individual_results["voice"] = {
                "available": True,
                "status": status,
                "risk_score": res.get("risk_score"),
                "features": features_used,
                "quality": quality,
                "warnings": res.get("warnings", []),
            }

            if is_passed and features_used:
                fusion_features["voice"] = features_used
            elif not is_passed:
                missing_modalities.append("voice")
        except Exception as e:
            logger.warning(f"Voice analysis failed: {e}")
            individual_results["voice"] = {
                "available": True,
                "status": "error",
                "risk_score": None,
                "features": {},
                "quality": {"passed": False, "issues": [str(e)]},
                "warnings": [f"Voice processing error: {e}"],
            }
            missing_modalities.append("voice")
    else:
        individual_results["voice"] = {
            "available": False,
            "status": "missing",
            "risk_score": None,
            "features": {},
            "quality": {"passed": False, "issues": ["Modality marked as missing or not provided."]},
            "warnings": ["Modality 'voice' was omitted from this analysis session."],
        }
        missing_modalities.append("voice")

    # --- Motor ---
    motor_input = inputs.get("motor")
    if isinstance(motor_input, dict) and motor_input.get("available", True):
        file_path = motor_input.get("file_path")
        tabular_feats = motor_input.get("features")
        try:
            if file_path and Path(file_path).exists():
                res = predict_motor(data=file_path)
                feats = {}
            elif tabular_feats and isinstance(tabular_feats, dict):
                res = predict_motor(data=tabular_feats)
                feats = tabular_feats
            else:
                direct_feats = {
                    k: v for k, v in motor_input.items()
                    if k not in ["available", "file_path", "features"]
                }
                if direct_feats:
                    res = predict_motor(data=direct_feats)
                    feats = direct_feats
                else:
                    raise ValueError("Neither valid motor file_path nor motor features provided.")

            individual_results["motor"] = {
                "available": True,
                "status": "success",
                "risk_score": res.get("risk_score"),
                "features": feats,
                "quality": res.get("quality", {"passed": True, "issues": []}),
                "warnings": res.get("warnings", []),
            }
            fusion_features["motor"] = feats
        except Exception as e:
            logger.warning(f"Motor analysis failed: {e}")
            individual_results["motor"] = {
                "available": True,
                "status": "error",
                "risk_score": None,
                "features": {},
                "quality": {"passed": False, "issues": [str(e)]},
                "warnings": [f"Motor processing error: {e}"],
            }
            missing_modalities.append("motor")
    else:
        individual_results["motor"] = {
            "available": False,
            "status": "missing",
            "risk_score": None,
            "features": {},
            "quality": {"passed": False, "issues": ["Modality marked as missing or not provided."]},
            "warnings": ["Modality 'motor' was omitted from this analysis session."],
        }
        missing_modalities.append("motor")

    # --- Retina ---
    retina_input = inputs.get("retina")
    if isinstance(retina_input, dict) and retina_input.get("available", True):
        image_path = retina_input.get("image_path")
        tabular_feats = retina_input.get("features")
        try:
            if image_path and Path(image_path).exists():
                res = predict_retina(image_path=image_path)
                quality = res.get("quality", {"passed": True, "issues": []})
                is_passed = quality.get("passed", True)
                status = "success" if is_passed else "failed_qc"
                vessel_feats = res.get("vessel_features", {})

                # Also add 16-D embedding components if available
                emb = res.get("embedding", [])
                for i in range(min(16, len(emb))):
                    vessel_feats[f"retina_emb_{i}"] = emb[i]

                individual_results["retina"] = {
                    "available": True,
                    "status": status,
                    "risk_score": None,  # Retina module outputs representations/vessel morphology
                    "features": vessel_feats,
                    "quality": quality,
                    "warnings": res.get("warnings", []),
                }

                if is_passed and vessel_feats:
                    fusion_features["retina"] = vessel_feats
                elif not is_passed:
                    missing_modalities.append("retina")
            elif tabular_feats and isinstance(tabular_feats, dict):
                individual_results["retina"] = {
                    "available": True,
                    "status": "success",
                    "risk_score": None,
                    "features": tabular_feats,
                    "quality": {"passed": True, "issues": []},
                    "warnings": [],
                }
                fusion_features["retina"] = tabular_feats
            else:
                direct_feats = {
                    k: v for k, v in retina_input.items()
                    if k not in ["available", "image_path", "features"]
                }
                if direct_feats:
                    individual_results["retina"] = {
                        "available": True,
                        "status": "success",
                        "risk_score": None,
                        "features": direct_feats,
                        "quality": {"passed": True, "issues": []},
                        "warnings": [],
                    }
                    fusion_features["retina"] = direct_feats
                else:
                    raise ValueError("Neither valid image_path nor retina features provided.")
        except Exception as e:
            logger.warning(f"Retina analysis failed: {e}")
            individual_results["retina"] = {
                "available": True,
                "status": "error",
                "risk_score": None,
                "features": {},
                "quality": {"passed": False, "issues": [str(e)]},
                "warnings": [f"Retina processing error: {e}"],
            }
            missing_modalities.append("retina")
    else:
        individual_results["retina"] = {
            "available": False,
            "status": "missing",
            "risk_score": None,
            "features": {},
            "quality": {"passed": False, "issues": ["Modality marked as missing or not provided."]},
            "warnings": ["Modality 'retina' was omitted from this analysis session."],
        }
        missing_modalities.append("retina")

    # 3. Multimodal Fusion
    fusion_prediction = predict_fusion(fusion_features)
    risk_score = fusion_prediction["risk_score"]
    fused_embedding = fusion_prediction["fused_embedding"]
    gate_weights = fusion_prediction["gate_weights"]
    modality_presence = fusion_prediction["modality_presence"]
    fusion_warnings = fusion_prediction.get("warnings", [])

    risk_pattern = (
        "Elevated Parkinson's risk pattern detected"
        if risk_score >= 0.5
        else "Standard risk pattern observed"
    )

    fusion_summary = {
        "risk_score": risk_score,
        "risk_pattern": risk_pattern,
        "fused_embedding": fused_embedding,
        "modality_presence": modality_presence,
        "gate_weights": gate_weights,
        "model_version": fusion_prediction.get("model_version", "gated_multimodal_fusion_v1"),
        "experiment_type": fusion_prediction.get("experiment_type", "prototype_simulation"),
        "warnings": fusion_warnings,
    }

    # 4. Explainability (SHAP attribution)
    try:
        explanation = explain_single(
            inputs=fusion_features,
            participant_id=participant_id,
            is_synthetic=False,
        )
    except Exception as e:
        logger.warning(f"SHAP explanation computation failed: {e}")
        explanation = {
            "participant_id": participant_id,
            "risk_score": risk_score,
            "important_modalities": [
                {
                    "modality": m,
                    "importance": round(gate_weights.get(m, 0.2), 4),
                    "percent_contribution": round(gate_weights.get(m, 0.2) * 100, 2),
                    "direction": "positive" if risk_score >= 0.5 else "negative",
                    "missing": m in missing_modalities,
                }
                for m in MODALITIES
            ],
            "important_features": [],
            "positive_contributors": [],
            "negative_contributors": [],
            "missing_modalities": missing_modalities,
            "missing_modality_notes": [
                f"Modality '{m}' absent: gating unit masked this modality."
                for m in missing_modalities
            ],
            "modality_presence": modality_presence,
            "gate_weights": gate_weights,
            "shap_base_value": 0.5,
            "warnings": [f"Local explanation fallback active: {e}"],
        }

    # Aggregate warnings
    all_warnings = list(dict.fromkeys(warnings + fusion_warnings + explanation.get("warnings", [])))

    return {
        "participant_id": participant_id,
        "demographics": demographics,
        "individual_modalities": individual_results,
        "fusion": fusion_summary,
        "explainability": explanation,
        "missing_modalities": missing_modalities,
        "warnings": all_warnings,
    }
