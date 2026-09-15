"""
MPF-PD Central Inference Service (Phase 9).

Coordinates the complete end-to-end multimodal screening pipeline:
Input
  ↓
Data validation & participant demographics
  ↓
Preprocessing & Modality QC
  ↓
Olfactory model (UPSIT / Sniffin' Sticks)
  ↓
RBD model (RBDSQ questionnaire)
  ↓
Voice model (Acoustic audio .wav / spectral features)
  ↓
Motor model (Gait / Tapping CSV / tabular features)
  ↓
Retinal model (Fundus image analysis / CNN embeddings & vessel morphology)
  ↓
MPF gated multimodal neural fusion
  ↓
Final XGBoost classifier
  ↓
SHAP explanation
  ↓
Standardized structured result

RESEARCH PROTOTYPE ONLY — NOT A CLINICAL DIAGNOSTIC DEVICE.
No clinical claims: estimates prodromal risk patterns for research screening only.
"""

import argparse
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Union

# Ensure project root is on sys.path
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import numpy as np
import pandas as pd
from PIL import Image

from src.fusion.dataset import MODALITIES
from src.model_registry import (
    load_olfactory_model,
    load_rbd_model,
    load_voice_model,
    load_motor_model,
    load_retina_model,
    load_fusion_model,
    load_shap_explainer,
)
from src.olfactory.predict import predict_olfactory
from src.rbd.predict import predict_rbd
from src.voice.predict import predict_voice
from src.motor.predict import predict_motor
from src.retina.predict import predict_retina
from src.fusion.predict import predict_fusion
from src.explainability.local_explanation import explain_single

logger = logging.getLogger("mpf.pipeline")

PIPELINE_VERSION = "0.9.0"

DISCLAIMER_WARNINGS = [
    "RESEARCH PROTOTYPE: Risk score is an investigational estimate only.",
    "NOT FOR CLINICAL DIAGNOSIS: No clinical validity is claimed.",
    "Requires clinician review if used in future clinical studies.",
]

ALL_MODALITIES = ["olfactory", "rbd", "voice", "motor", "retina"]


def _make_fallback_explanation(
    participant_id: str,
    missing_modalities: List[str],
    gate_weights: Optional[Dict[str, float]] = None,
    risk_score: Optional[float] = None,
    warning_msg: str = "SHAP explanation was not computed.",
) -> Dict[str, Any]:
    """Construct a schema-compliant fallback explanation object."""
    gw = gate_weights or {m: 0.2 for m in ALL_MODALITIES}
    important_modalities = [
        {
            "modality": m,
            "importance": round(float(gw.get(m, 0.2)), 4),
            "percent_contribution": round(float(gw.get(m, 0.2)) * 100.0, 2),
            "direction": "positive" if (risk_score or 0.0) >= 0.5 else "negative",
            "missing": m in missing_modalities,
        }
        for m in ALL_MODALITIES
    ]
    return {
        "participant_id": participant_id,
        "risk_score": risk_score,
        "important_modalities": important_modalities,
        "important_features": [],
        "positive_contributors": [],
        "negative_contributors": [],
        "missing_modalities": missing_modalities,
        "warnings": [warning_msg],
    }


def _fail_pipeline(
    participant_id: str,
    errors: List[str],
    demographics: Optional[Dict[str, Any]] = None,
    experiment_type: str = "prototype_simulation",
) -> Dict[str, Any]:
    """Construct a schema-compliant failed pipeline result."""
    empty_modalities = {
        m: {
            "status": "missing",
            "risk_score": None,
            "embedding": [],
            "features_used": [],
            "warnings": [f"Pipeline failed before processing modality '{m}'."],
        }
        for m in ALL_MODALITIES
    }
    explanation = _make_fallback_explanation(
        participant_id=participant_id,
        missing_modalities=ALL_MODALITIES,
        warning_msg="Pipeline failed; explanation not generated.",
    )
    metadata = {
        "pipeline_version": PIPELINE_VERSION,
        "model_versions": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "clinical_claim": False,
    }
    demo = demographics or {"age": None, "sex": "unknown"}

    return {
        "participant_id": participant_id,
        "status": "failed",
        "experiment_type": experiment_type,
        "available_modalities": [],
        "missing_modalities": ALL_MODALITIES,
        "modality_results": empty_modalities,
        "fusion": {
            "status": "failed",
            "risk_score": None,
            "fused_embedding": [],
            "gate_weights": {},
            "warnings": ["Fusion was not performed due to pipeline failure."],
        },
        "explanation": explanation,
        "metadata": metadata,
        "errors": errors,
        # Backward-compatible fields
        "demographics": demo,
        "individual_modalities": empty_modalities,
        "explainability": explanation,
        "warnings": DISCLAIMER_WARNINGS + errors,
    }


def run_mpf_pipeline(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the full MPF-PD multimodal prodromal screening pipeline.

    Single entry point used by dashboard, integration tests, and CLI.

    Args:
        inputs: Input dictionary conforming to Section 3 specification.

    Returns:
        Structured result conforming to Section 4 standardized schema.
    """
    errors: List[str] = []
    warnings: List[str] = list(DISCLAIMER_WARNINGS)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. PARTICIPANT-LEVEL INPUT VALIDATION
    # ─────────────────────────────────────────────────────────────────────────
    if not isinstance(inputs, dict):
        return _fail_pipeline(
            participant_id="UNKNOWN",
            errors=["Input payload must be a dictionary."],
        )

    participant_id = str(inputs.get("participant_id") or "PSEUDO-001").strip()

    # Participant age validation
    if "age" not in inputs or inputs["age"] is None:
        errors.append("Participant-level error: 'age' is required.")
        return _fail_pipeline(participant_id=participant_id, errors=errors)

    try:
        age_val = float(inputs["age"])
        if np.isnan(age_val) or age_val < 18 or age_val > 120:
            errors.append(
                f"Participant-level error: Age {age_val} is invalid. Age must be between 18 and 120 years."
            )
            return _fail_pipeline(participant_id=participant_id, errors=errors)
    except (ValueError, TypeError):
        errors.append(
            f"Participant-level error: Could not parse age '{inputs.get('age')}' as a numeric value."
        )
        return _fail_pipeline(participant_id=participant_id, errors=errors)

    # Participant sex validation
    sex_raw = inputs.get("sex", "female")
    sex_str = "male" if str(sex_raw).strip().lower() in ["m", "male", "1"] else "female"
    demographics = {"age": age_val, "sex": sex_str}

    # ─────────────────────────────────────────────────────────────────────────
    # 2. DETECT MODALITIES & MODEL ARTIFACT CHECKS
    # ─────────────────────────────────────────────────────────────────────────
    available_modalities: List[str] = []
    missing_modalities: List[str] = []
    modality_results: Dict[str, Any] = {}
    fusion_features: Dict[str, Any] = {
        "age": age_val,
        "sex": sex_str,
    }
    model_versions: Dict[str, str] = {}
    experiment_type = "prototype_simulation"

    # ─────────────────────────────────────────────────────────────────────────
    # 3. INDIVIDUAL MODALITY PROCESSING & QC
    # ─────────────────────────────────────────────────────────────────────────

    # --- A. Olfactory ---
    olf_in = inputs.get("olfactory")
    if isinstance(olf_in, dict) and olf_in.get("available", True):
        # Extract score and max_score
        score = olf_in.get("score") if "score" in olf_in else olf_in.get("total_score")
        max_score = olf_in.get("max_score", 40)

        # Range and type validation
        if score is None:
            # Check if other features provided
            other_feats = {k: v for k, v in olf_in.items() if k not in ["available", "responses", "max_score"]}
            if not other_feats:
                modality_results["olfactory"] = {
                    "status": "failed_qc",
                    "risk_score": None,
                    "embedding": [],
                    "features_used": [],
                    "warnings": ["Olfactory score was not provided."],
                }
                errors.append("Olfactory validation failed: score is missing.")
                missing_modalities.append("olfactory")
                score = None
        elif not isinstance(score, (int, float)) or score < 0 or score > max_score:
            modality_results["olfactory"] = {
                "status": "failed_qc",
                "risk_score": None,
                "embedding": [],
                "features_used": [],
                "warnings": [f"Olfactory score {score} is out of valid range [0, {max_score}]."],
            }
            errors.append(f"Olfactory validation failed: score {score} out of range [0, {max_score}].")
            missing_modalities.append("olfactory")
            score = None

        if score is not None:
            olf_loader = load_olfactory_model()
            if olf_loader["status"] != "loaded":
                modality_results["olfactory"] = {
                    "status": olf_loader["status"],
                    "risk_score": None,
                    "embedding": [],
                    "features_used": [],
                    "warnings": ["Olfactory model artifact missing or not trained."],
                }
                errors.append("Olfactory model artifact missing.")
                missing_modalities.append("olfactory")
            else:
                model_versions["olfactory"] = olf_loader.get("metadata", {}).get("model_name", "xgboost")
                pct_correct = (float(score) / float(max_score)) * 100.0 if max_score > 0 else 0.0
                olf_data = {
                    "total_score": float(score),
                    "pct_correct": pct_correct,
                    "n_errors": float(max_score - score),
                    "error_pattern_flags": 1.0 if (float(score) / float(max_score)) < 0.7 else 0.0,
                    "response_time_mean": float(olf_in.get("response_time_mean", 4.0)),
                }
                try:
                    res = predict_olfactory(olf_data)
                    risk_sc = res.get("risk_score")
                    modality_results["olfactory"] = {
                        "status": "success",
                        "risk_score": risk_sc,
                        "embedding": [risk_sc] if risk_sc is not None else [],
                        "features_used": res.get("features_used", list(olf_data.keys())),
                        "warnings": res.get("warnings", []),
                    }
                    available_modalities.append("olfactory")
                    fusion_features["olfactory"] = olf_data
                except Exception as e:
                    logger.warning(f"Olfactory prediction error: {e}")
                    modality_results["olfactory"] = {
                        "status": "error",
                        "risk_score": None,
                        "embedding": [],
                        "features_used": [],
                        "warnings": [f"Olfactory inference failed: {str(e)}"],
                    }
                    errors.append(f"Olfactory processing error: {str(e)}")
                    missing_modalities.append("olfactory")
    else:
        modality_results["olfactory"] = {
            "status": "missing",
            "risk_score": None,
            "embedding": [],
            "features_used": [],
            "warnings": ["Modality 'olfactory' was omitted or marked unavailable."],
        }
        missing_modalities.append("olfactory")

    # --- B. RBD ---
    rbd_in = inputs.get("rbd")
    if isinstance(rbd_in, dict) and rbd_in.get("available", True):
        item_responses = rbd_in.get("item_responses") or rbd_in.get("items")
        rbdsq_total = rbd_in.get("rbdsq_total")

        if rbdsq_total is None and item_responses and isinstance(item_responses, (list, dict)):
            if isinstance(item_responses, list):
                rbdsq_total = sum(int(bool(x)) for x in item_responses)
            elif isinstance(item_responses, dict):
                rbdsq_total = sum(int(bool(v)) for v in item_responses.values())

        # Range and type validation
        if rbdsq_total is None:
            modality_results["rbd"] = {
                "status": "failed_qc",
                "risk_score": None,
                "embedding": [],
                "features_used": [],
                "warnings": ["RBDSQ total score was not provided."],
            }
            errors.append("RBD validation failed: rbdsq_total is missing.")
            missing_modalities.append("rbd")
        elif not isinstance(rbdsq_total, (int, float)) or rbdsq_total < 0 or rbdsq_total > 13:
            modality_results["rbd"] = {
                "status": "failed_qc",
                "risk_score": None,
                "embedding": [],
                "features_used": [],
                "warnings": [f"RBDSQ score {rbdsq_total} is out of valid range [0, 13]."],
            }
            errors.append(f"RBD validation failed: RBDSQ score {rbdsq_total} out of range [0, 13].")
            missing_modalities.append("rbd")
        else:
            rbd_loader = load_rbd_model()
            if rbd_loader["status"] != "loaded":
                modality_results["rbd"] = {
                    "status": rbd_loader["status"],
                    "risk_score": None,
                    "embedding": [],
                    "features_used": [],
                    "warnings": ["RBD model artifact missing or not trained."],
                }
                errors.append("RBD model artifact missing.")
                missing_modalities.append("rbd")
            else:
                model_versions["rbd"] = rbd_loader.get("metadata", {}).get("model_name", "logistic_regression")
                rbd_data = {
                    "rbdsq_total": float(rbdsq_total),
                    "above_cutoff_flag": 1.0 if float(rbdsq_total) >= 5.0 else 0.0,
                    "high_weight_item_flags": 1.0 if float(rbdsq_total) >= 5.0 else 0.0,
                }
                if isinstance(item_responses, list):
                    for idx, val in enumerate(item_responses[:13]):
                        rbd_data[f"item_{idx+1}"] = float(int(bool(val)))
                elif isinstance(item_responses, dict):
                    for k, v in item_responses.items():
                        rbd_data[k] = float(int(bool(v)))

                try:
                    res = predict_rbd(rbd_data)
                    risk_sc = res.get("risk_score")
                    modality_results["rbd"] = {
                        "status": "success",
                        "risk_score": risk_sc,
                        "embedding": [risk_sc] if risk_sc is not None else [],
                        "features_used": res.get("features_used", list(rbd_data.keys())),
                        "warnings": res.get("warnings", []),
                    }
                    available_modalities.append("rbd")
                    fusion_features["rbd"] = rbd_data
                except Exception as e:
                    logger.warning(f"RBD prediction error: {e}")
                    modality_results["rbd"] = {
                        "status": "error",
                        "risk_score": None,
                        "embedding": [],
                        "features_used": [],
                        "warnings": [f"RBD inference failed: {str(e)}"],
                    }
                    errors.append(f"RBD processing error: {str(e)}")
                    missing_modalities.append("rbd")
    else:
        modality_results["rbd"] = {
            "status": "missing",
            "risk_score": None,
            "embedding": [],
            "features_used": [],
            "warnings": ["Modality 'rbd' was omitted or marked unavailable."],
        }
        missing_modalities.append("rbd")

    # --- C. Voice ---
    voice_in = inputs.get("voice")
    if isinstance(voice_in, dict) and voice_in.get("available", True):
        file_path = voice_in.get("file_path") or voice_in.get("audio_file")
        tabular_feats = voice_in.get("features")
        direct_feats = {
            k: v for k, v in voice_in.items()
            if k not in ["available", "file_path", "audio_file", "features"]
        }

        v_loader = load_voice_model()
        if v_loader["status"] != "loaded":
            modality_results["voice"] = {
                "status": v_loader["status"],
                "risk_score": None,
                "embedding": [],
                "features_used": [],
                "warnings": ["Voice model artifact missing or not trained."],
            }
            errors.append("Voice model artifact missing.")
            missing_modalities.append("voice")
        elif file_path:
            fpath = Path(file_path)
            if not fpath.exists() or not fpath.is_file():
                modality_results["voice"] = {
                    "status": "error",
                    "risk_score": None,
                    "embedding": [],
                    "features_used": [],
                    "warnings": [f"Audio file not found: '{file_path}'"],
                }
                errors.append(f"Voice file not found: '{file_path}'")
                missing_modalities.append("voice")
            elif fpath.suffix.lower() not in [".wav", ".mp3", ".flac", ".ogg", ".m4a"]:
                modality_results["voice"] = {
                    "status": "failed_qc",
                    "risk_score": None,
                    "embedding": [],
                    "features_used": [],
                    "warnings": [f"Unsupported audio file extension '{fpath.suffix}'. Expected .wav, .mp3, .flac."],
                }
                errors.append(f"Voice format error: unsupported extension '{fpath.suffix}'.")
                missing_modalities.append("voice")
            else:
                try:
                    res = predict_voice(audio_file=str(fpath))
                    quality = res.get("quality", {"passed": True, "issues": []})
                    is_passed = quality.get("passed", True) and res.get("risk_score") is not None
                    if not is_passed:
                        issues = quality.get("issues", ["Audio quality check failed."])
                        modality_results["voice"] = {
                            "status": "failed_qc",
                            "risk_score": None,
                            "embedding": [],
                            "features_used": res.get("features_used", []),
                            "warnings": res.get("warnings", []) + issues,
                        }
                        errors.append(f"Voice QC failed: {issues}")
                        missing_modalities.append("voice")
                    else:
                        modality_results["voice"] = {
                            "status": "success",
                            "risk_score": res["risk_score"],
                            "embedding": res.get("embedding") or [],
                            "features_used": res.get("features_used", []),
                            "warnings": res.get("warnings", []),
                        }
                        available_modalities.append("voice")
                        model_versions["voice"] = v_loader.get("metadata", {}).get("model_name", "xgboost")
                        if tabular_feats and isinstance(tabular_feats, dict):
                            fusion_features["voice"] = tabular_feats
                except Exception as e:
                    logger.warning(f"Voice processing error: {e}")
                    modality_results["voice"] = {
                        "status": "failed_qc",
                        "risk_score": None,
                        "embedding": [],
                        "features_used": [],
                        "warnings": [f"Invalid or corrupted audio file: {str(e)}"],
                    }
                    errors.append(f"Voice audio invalid or corrupted: {str(e)}")
                    missing_modalities.append("voice")
        elif tabular_feats or direct_feats:
            feats_to_use = tabular_feats if isinstance(tabular_feats, dict) else direct_feats
            try:
                res = predict_voice(tabular_features=feats_to_use)
                modality_results["voice"] = {
                    "status": "success",
                    "risk_score": res["risk_score"],
                    "embedding": res.get("embedding") or [],
                    "features_used": res.get("features_used", list(feats_to_use.keys())),
                    "warnings": res.get("warnings", []),
                }
                available_modalities.append("voice")
                fusion_features["voice"] = feats_to_use
                model_versions["voice"] = v_loader.get("metadata", {}).get("model_name", "xgboost")
            except Exception as e:
                logger.warning(f"Voice tabular error: {e}")
                modality_results["voice"] = {
                    "status": "error",
                    "risk_score": None,
                    "embedding": [],
                    "features_used": [],
                    "warnings": [f"Voice tabular inference failed: {str(e)}"],
                }
                errors.append(f"Voice inference error: {str(e)}")
                missing_modalities.append("voice")
        else:
            modality_results["voice"] = {
                "status": "failed_qc",
                "risk_score": None,
                "embedding": [],
                "features_used": [],
                "warnings": ["Voice input provided without valid audio file_path or tabular features."],
            }
            errors.append("Voice validation failed: neither file_path nor features provided.")
            missing_modalities.append("voice")
    else:
        modality_results["voice"] = {
            "status": "missing",
            "risk_score": None,
            "embedding": [],
            "features_used": [],
            "warnings": ["Modality 'voice' was omitted or marked unavailable."],
        }
        missing_modalities.append("voice")

    # --- D. Motor ---
    motor_in = inputs.get("motor")
    if isinstance(motor_in, dict) and motor_in.get("available", True):
        file_path = motor_in.get("file_path")
        tabular_feats = motor_in.get("features")
        direct_feats = {
            k: v for k, v in motor_in.items()
            if k not in ["available", "file_path", "features"]
        }

        m_loader = load_motor_model()
        if m_loader["status"] != "loaded":
            modality_results["motor"] = {
                "status": m_loader["status"],
                "risk_score": None,
                "embedding": [],
                "features_used": [],
                "warnings": ["Motor model artifact missing or not trained."],
            }
            errors.append("Motor model artifact missing.")
            missing_modalities.append("motor")
        elif file_path:
            fpath = Path(file_path)
            if not fpath.exists() or not fpath.is_file():
                modality_results["motor"] = {
                    "status": "error",
                    "risk_score": None,
                    "embedding": [],
                    "features_used": [],
                    "warnings": [f"Motor data file not found: '{file_path}'"],
                }
                errors.append(f"Motor file not found: '{file_path}'")
                missing_modalities.append("motor")
            elif fpath.suffix.lower() not in [".csv", ".tsv", ".txt", ".json"]:
                modality_results["motor"] = {
                    "status": "failed_qc",
                    "risk_score": None,
                    "embedding": [],
                    "features_used": [],
                    "warnings": [f"Unsupported motor file extension '{fpath.suffix}'. Expected .csv, .tsv."],
                }
                errors.append(f"Motor format error: unsupported extension '{fpath.suffix}'.")
                missing_modalities.append("motor")
            else:
                try:
                    res = predict_motor(data=str(fpath))
                    quality = res.get("quality", {"passed": True, "issues": []})
                    is_passed = quality.get("passed", True) and res.get("risk_score") is not None
                    if not is_passed:
                        issues = quality.get("issues", ["Motor quality check failed."])
                        modality_results["motor"] = {
                            "status": "failed_qc",
                            "risk_score": None,
                            "embedding": [],
                            "features_used": res.get("features_used", []),
                            "warnings": res.get("warnings", []) + issues,
                        }
                        errors.append(f"Motor QC check failed: {issues}")
                        missing_modalities.append("motor")
                    else:
                        modality_results["motor"] = {
                            "status": "success",
                            "risk_score": res["risk_score"],
                            "embedding": res.get("embedding") or [],
                            "features_used": res.get("features_used", []),
                            "warnings": res.get("warnings", []),
                        }
                        available_modalities.append("motor")
                        model_versions["motor"] = m_loader.get("metadata", {}).get("model_name", "random_forest")
                        try:
                            df_motor = pd.read_csv(fpath)
                            fusion_features["motor"] = df_motor.iloc[0].to_dict()
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(f"Motor file processing error: {e}")
                    modality_results["motor"] = {
                        "status": "failed_qc",
                        "risk_score": None,
                        "embedding": [],
                        "features_used": [],
                        "warnings": [f"Malformed motor file: {str(e)}"],
                    }
                    errors.append(f"Motor file malformed: {str(e)}")
                    missing_modalities.append("motor")
        elif tabular_feats or direct_feats:
            feats_to_use = tabular_feats if isinstance(tabular_feats, dict) else direct_feats
            try:
                res = predict_motor(data=feats_to_use)
                modality_results["motor"] = {
                    "status": "success",
                    "risk_score": res["risk_score"],
                    "embedding": res.get("embedding") or [],
                    "features_used": res.get("features_used", list(feats_to_use.keys())),
                    "warnings": res.get("warnings", []),
                }
                available_modalities.append("motor")
                fusion_features["motor"] = feats_to_use
                model_versions["motor"] = m_loader.get("metadata", {}).get("model_name", "random_forest")
            except Exception as e:
                logger.warning(f"Motor tabular error: {e}")
                modality_results["motor"] = {
                    "status": "error",
                    "risk_score": None,
                    "embedding": [],
                    "features_used": [],
                    "warnings": [f"Motor tabular inference failed: {str(e)}"],
                }
                errors.append(f"Motor inference error: {str(e)}")
                missing_modalities.append("motor")
        else:
            modality_results["motor"] = {
                "status": "failed_qc",
                "risk_score": None,
                "embedding": [],
                "features_used": [],
                "warnings": ["Motor input provided without valid file_path or tabular features."],
            }
            errors.append("Motor validation failed: neither file_path nor features provided.")
            missing_modalities.append("motor")
    else:
        modality_results["motor"] = {
            "status": "missing",
            "risk_score": None,
            "embedding": [],
            "features_used": [],
            "warnings": ["Modality 'motor' was omitted or marked unavailable."],
        }
        missing_modalities.append("motor")

    # --- E. Retina ---
    retina_in = inputs.get("retina")
    if isinstance(retina_in, dict) and retina_in.get("available", True):
        file_path = retina_in.get("file_path") or retina_in.get("image_path")
        tabular_feats = retina_in.get("features")
        direct_feats = {
            k: v for k, v in retina_in.items()
            if k not in ["available", "file_path", "image_path", "features"]
        }

        r_loader = load_retina_model()
        if r_loader["status"] != "loaded":
            modality_results["retina"] = {
                "status": r_loader["status"],
                "risk_score": None,
                "embedding": [],
                "features_used": [],
                "warnings": ["Retinal encoder artifact missing."],
            }
            errors.append("Retinal encoder artifact missing.")
            missing_modalities.append("retina")
        elif file_path:
            fpath = Path(file_path)
            if not fpath.exists() or not fpath.is_file():
                modality_results["retina"] = {
                    "status": "error",
                    "risk_score": None,
                    "embedding": [],
                    "features_used": [],
                    "warnings": [f"Retinal image file not found: '{file_path}'"],
                }
                errors.append(f"Retinal image file not found: '{file_path}'")
                missing_modalities.append("retina")
            elif fpath.suffix.lower() not in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
                modality_results["retina"] = {
                    "status": "failed_qc",
                    "risk_score": None,
                    "embedding": [],
                    "features_used": [],
                    "warnings": [f"Unsupported image extension '{fpath.suffix}'. Expected .png, .jpg."],
                }
                errors.append(f"Retina format error: unsupported extension '{fpath.suffix}'.")
                missing_modalities.append("retina")
            else:
                # Validate image integrity (catch corrupt images)
                is_corrupted = False
                try:
                    with Image.open(fpath) as img:
                        img.verify()
                except Exception as img_err:
                    is_corrupted = True
                    modality_results["retina"] = {
                        "status": "failed_qc",
                        "risk_score": None,
                        "embedding": [],
                        "features_used": [],
                        "warnings": [f"Corrupted or invalid retinal image file: {str(img_err)}"],
                    }
                    errors.append(f"Retinal image corrupted: {str(img_err)}")
                    missing_modalities.append("retina")

                if not is_corrupted:
                    try:
                        res = predict_retina(image_path=str(fpath))
                        quality = res.get("quality", {"passed": True, "issues": []})
                        is_passed = quality.get("passed", True)
                        if not is_passed:
                            issues = quality.get("issues", ["Retinal image quality check failed."])
                            modality_results["retina"] = {
                                "status": "failed_qc",
                                "risk_score": None,
                                "embedding": res.get("embedding", []),
                                "features_used": list(res.get("vessel_features", {}).keys()),
                                "warnings": res.get("warnings", []) + issues,
                            }
                            errors.append(f"Retina QC check failed: {issues}")
                            missing_modalities.append("retina")
                        else:
                            vessel_feats = res.get("vessel_features", {})
                            emb = res.get("embedding", [])
                            for idx in range(min(16, len(emb))):
                                vessel_feats[f"retina_emb_{idx}"] = emb[idx]

                            modality_results["retina"] = {
                                "status": "success",
                                "risk_score": None,  # Prototype representation module
                                "embedding": emb,
                                "features_used": list(vessel_feats.keys()),
                                "warnings": res.get("warnings", []),
                            }
                            available_modalities.append("retina")
                            fusion_features["retina"] = vessel_feats
                            model_versions["retina"] = "resnet18_vessel_morphometry"
                    except Exception as e:
                        logger.warning(f"Retina processing error: {e}")
                        modality_results["retina"] = {
                            "status": "failed_qc",
                            "risk_score": None,
                            "embedding": [],
                            "features_used": [],
                            "warnings": [f"Retinal image processing failed: {str(e)}"],
                        }
                        errors.append(f"Retinal processing error: {str(e)}")
                        missing_modalities.append("retina")
        elif tabular_feats or direct_feats:
            feats_to_use = tabular_feats if isinstance(tabular_feats, dict) else direct_feats
            modality_results["retina"] = {
                "status": "success",
                "risk_score": None,
                "embedding": [],
                "features_used": list(feats_to_use.keys()),
                "warnings": [],
            }
            available_modalities.append("retina")
            fusion_features["retina"] = feats_to_use
            model_versions["retina"] = "tabular_features"
        else:
            modality_results["retina"] = {
                "status": "failed_qc",
                "risk_score": None,
                "embedding": [],
                "features_used": [],
                "warnings": ["Retina input provided without valid image file_path or tabular features."],
            }
            errors.append("Retina validation failed: neither file_path nor features provided.")
            missing_modalities.append("retina")
    else:
        modality_results["retina"] = {
            "status": "missing",
            "risk_score": None,
            "embedding": [],
            "features_used": [],
            "warnings": ["Modality 'retina' was omitted or marked unavailable."],
        }
        missing_modalities.append("retina")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. MULTIMODAL GATED FUSION & CLASSIFICATION
    # ─────────────────────────────────────────────────────────────────────────
    fusion_loader = load_fusion_model()
    fusion_result: Dict[str, Any] = {}
    overall_status = "success"

    if fusion_loader["status"] != "loaded":
        fusion_status = "not_trained" if fusion_loader["status"] == "not_trained" else "missing"
        fusion_result = {
            "status": fusion_status,
            "risk_score": None,
            "fused_embedding": [],
            "gate_weights": {},
            "warnings": ["Multimodal fusion model artifact is missing or not trained."],
        }
        errors.append("Fusion model artifact missing; multimodal risk could not be computed.")
        overall_status = "partial_success" if len(available_modalities) > 0 else "failed"
        explanation = _make_fallback_explanation(
            participant_id=participant_id,
            missing_modalities=missing_modalities,
            warning_msg="Fusion model is unavailable; explanation not computed.",
        )
    elif len(available_modalities) == 0:
        # All modalities are missing or failed QC
        fusion_result = {
            "status": "failed",
            "risk_score": None,
            "fused_embedding": [],
            "gate_weights": {},
            "warnings": ["Fusion was not performed: all modalities are absent or failed quality control."],
        }
        errors.append("No available modalities for fusion.")
        overall_status = "partial_success"
        explanation = _make_fallback_explanation(
            participant_id=participant_id,
            missing_modalities=missing_modalities,
            warning_msg="All modalities are absent; explanation not computed.",
        )
    else:
        # Run Gated Fusion Inference
        try:
            pred_res = predict_fusion(fusion_features)
            risk_score = round(float(pred_res["risk_score"]), 4)
            fused_emb = pred_res.get("fused_embedding", [])
            gate_weights = pred_res.get("gate_weights", {})
            fusion_warnings = pred_res.get("warnings", [])

            fusion_result = {
                "status": "success",
                "risk_score": risk_score,
                "fused_embedding": fused_emb,
                "gate_weights": gate_weights,
                "warnings": fusion_warnings,
            }
            model_versions["fusion"] = pred_res.get("model_version", "gated_multimodal_fusion_v1")
            experiment_type = pred_res.get("experiment_type", "prototype_simulation")

            # Overall status: success if fusion succeeded, or partial_success if errors occurred
            if len(errors) > 0:
                overall_status = "partial_success"
            else:
                overall_status = "success"

            # ─────────────────────────────────────────────────────────────────
            # 5. SHAP ATTRIBUTION & EXPLAINABILITY
            # ─────────────────────────────────────────────────────────────────
            shap_loader = load_shap_explainer()
            if shap_loader["status"] != "loaded":
                explanation = _make_fallback_explanation(
                    participant_id=participant_id,
                    missing_modalities=missing_modalities,
                    gate_weights=gate_weights,
                    risk_score=risk_score,
                    warning_msg="SHAP explainer artifacts missing; using gate weight attribution.",
                )
            else:
                try:
                    exp_obj = explain_single(
                        inputs=fusion_features,
                        participant_id=participant_id,
                        explainer=shap_loader["model"],
                        is_synthetic=False,
                    )
                    explanation = {
                        "participant_id": participant_id,
                        "risk_score": risk_score,
                        "important_modalities": exp_obj.get("important_modalities", []),
                        "important_features": exp_obj.get("important_features", []),
                        "positive_contributors": exp_obj.get("positive_contributors", []),
                        "negative_contributors": exp_obj.get("negative_contributors", []),
                        "missing_modalities": missing_modalities,
                        "warnings": exp_obj.get("warnings", []),
                    }
                except Exception as shap_err:
                    logger.warning(f"SHAP explanation computation error: {shap_err}")
                    explanation = _make_fallback_explanation(
                        participant_id=participant_id,
                        missing_modalities=missing_modalities,
                        gate_weights=gate_weights,
                        risk_score=risk_score,
                        warning_msg=f"SHAP explanation fallback active: {str(shap_err)}",
                    )
        except Exception as fuse_err:
            logger.error(f"Multimodal fusion inference failed: {fuse_err}")
            fusion_result = {
                "status": "failed",
                "risk_score": None,
                "fused_embedding": [],
                "gate_weights": {},
                "warnings": [f"Fusion execution error: {str(fuse_err)}"],
            }
            errors.append(f"Fusion execution error: {str(fuse_err)}")
            overall_status = "partial_success"
            explanation = _make_fallback_explanation(
                participant_id=participant_id,
                missing_modalities=missing_modalities,
                warning_msg="Fusion failed; explanation not generated.",
            )

    # Ensure all modality_results have available, features, and quality for complete schema compatibility
    for m in ALL_MODALITIES:
        if m in modality_results:
            st = modality_results[m].get("status", "missing")
            modality_results[m].setdefault("available", st not in ["missing"])
            modality_results[m].setdefault("features", {})
            modality_results[m].setdefault(
                "quality",
                {"passed": st == "success", "issues": [] if st == "success" else modality_results[m].get("warnings", [])}
            )

    # ─────────────────────────────────────────────────────────────────────────
    # 6. ASSEMBLE STANDARDIZED RESULT
    # ─────────────────────────────────────────────────────────────────────────
    metadata = {
        "pipeline_version": PIPELINE_VERSION,
        "model_versions": model_versions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "clinical_claim": False,
    }

    # Enrich fusion_result with modality_presence, model_version, and risk_pattern
    fusion_result["risk_pattern"] = (
        "Elevated Parkinson's risk pattern detected"
        if (fusion_result.get("risk_score") is not None and fusion_result["risk_score"] >= 0.5)
        else "Standard risk pattern observed"
    )
    fusion_result["modality_presence"] = {m: m in available_modalities for m in ALL_MODALITIES}
    fusion_result["model_version"] = model_versions.get("fusion", "gated_multimodal_fusion_v1")
    fusion_result["experiment_type"] = experiment_type
    # Aggregate warnings
    all_warnings = list(dict.fromkeys(
        warnings + fusion_result.get("warnings", []) + explanation.get("warnings", [])
    ))

    return {
        "participant_id": participant_id,
        "status": overall_status,
        "experiment_type": experiment_type,
        "available_modalities": available_modalities,
        "missing_modalities": missing_modalities,
        "modality_results": modality_results,
        "fusion": fusion_result,
        "explanation": explanation,
        "metadata": metadata,
        "errors": errors,
        # Backward-compatible keys:
        "demographics": demographics,
        "individual_modalities": modality_results,
        "explainability": explanation,
        "warnings": all_warnings,
    }


def self_test() -> bool:
    """
    Run small synthetic end-to-end self-test to verify pipeline functionality.

    Returns True if pass, False if fail.
    """
    print("Executing MPF-PD pipeline self-test...")
    try:
        # 1. Test case: all modalities present via synthetic inputs
        synthetic_input = {
            "participant_id": "SELF-TEST-001",
            "age": 65.0,
            "sex": "female",
            "olfactory": {
                "available": True,
                "score": 28,
                "max_score": 40,
                "responses": [],
            },
            "rbd": {
                "available": True,
                "rbdsq_total": 7,
                "item_responses": [1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0],
            },
            "voice": {
                "available": True,
                "features": {
                    "jitter_pct": 0.007,
                    "shimmer": 0.05,
                    "hnr": 16.5,
                },
            },
            "motor": {
                "available": True,
                "features": {
                    "gait_speed_m_per_s": 0.95,
                    "cadence_steps_per_min": 98.0,
                },
            },
            "retina": {
                "available": True,
                "features": {
                    "vessel_density": 0.065,
                    "mean_vessel_diameter_px": 2.95,
                },
            },
        }

        res = run_mpf_pipeline(synthetic_input)

        # Schema checks
        required_keys = [
            "participant_id",
            "status",
            "experiment_type",
            "available_modalities",
            "missing_modalities",
            "modality_results",
            "fusion",
            "explanation",
            "metadata",
            "errors",
        ]
        for k in required_keys:
            if k not in res:
                print(f"PIPELINE SELF-TEST FAIL: Missing required key '{k}' in result.")
                return False

        if res["status"] not in ["success", "partial_success"]:
            print(f"PIPELINE SELF-TEST FAIL: Expected status success or partial_success, got {res['status']}.")
            return False

        if res["fusion"]["status"] != "success":
            print(f"PIPELINE SELF-TEST FAIL: Fusion status expected 'success', got {res['fusion']['status']}.")
            return False

        risk = res["fusion"]["risk_score"]
        if risk is None or not (0.0 <= risk <= 1.0):
            print(f"PIPELINE SELF-TEST FAIL: Risk score {risk} is out of bounds [0.0, 1.0].")
            return False

        if res["metadata"].get("clinical_claim") is not False:
            print("PIPELINE SELF-TEST FAIL: metadata.clinical_claim must be False.")
            return False

        # 2. Test case: partial modalities (missing olfactory and retina)
        partial_input = {
            "participant_id": "SELF-TEST-002",
            "age": 60.0,
            "sex": "male",
            "olfactory": {"available": False},
            "rbd": {"available": True, "rbdsq_total": 3},
            "voice": {"available": True, "features": {"jitter_pct": 0.005}},
            "motor": {"available": False},
            "retina": {"available": False},
        }
        res_partial = run_mpf_pipeline(partial_input)
        if "olfactory" not in res_partial["missing_modalities"]:
            print("PIPELINE SELF-TEST FAIL: Missing olfactory not reported in missing_modalities.")
            return False
        if res_partial["fusion"]["status"] != "success":
            print(f"PIPELINE SELF-TEST FAIL: Fusion should succeed with missing modalities, got {res_partial['fusion']['status']}.")
            return False

        print("PIPELINE SELF-TEST PASS")
        return True

    except Exception as e:
        print(f"PIPELINE SELF-TEST FAIL: Exception encountered during self-test: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MPF-PD Central Inference Pipeline")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run end-to-end synthetic self-test",
    )
    args = parser.parse_args()

    if args.self_test:
        passed = self_test()
        sys.exit(0 if passed else 1)
    else:
        parser.print_help()
