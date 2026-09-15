"""
MPF-PD Model Registry (Phase 9).

Provides standardized model inspection and loader utilities for:
- Olfactory model
- RBD model
- Voice model
- Motor model
- Retina encoder/model
- Gated Multimodal Fusion model
- SHAP TreeExplainer

Each loader returns a standardized dictionary:
{
    "status": "loaded" | "not_trained" | "missing",
    "artifact_path": str,
    "metadata": dict,
    "model": Any (or None if status != "loaded")
}

SAFETY & INTEGRITY RULES:
- Never invents a model if artifacts are missing.
- No clinical claims or diagnoses.
- Prototype research estimate only.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import joblib
import torch

logger = logging.getLogger("mpf.model_registry")

# Default artifact paths
DEFAULT_PATHS = {
    "olfactory": {
        "model": "models/olfactory/model.joblib",
        "metadata": "models/olfactory/metadata.json",
    },
    "rbd": {
        "model": "models/rbd/model.joblib",
        "metadata": "models/rbd/metadata.json",
    },
    "voice": {
        "model": "models/voice/model.joblib",
        "metadata": "models/voice/metadata.json",
    },
    "motor": {
        "model": "models/motor/model.joblib",
        "metadata": "models/motor/metadata.json",
    },
    "retina": {
        "model": "models/retina/model.pt",
        "metadata": "models/retina/metadata.json",
    },
    "fusion": {
        "classifier": "models/fusion/classifier.joblib",
        "encoder": "models/fusion/fusion_encoder.pt",
        "preprocessor": "models/fusion/preprocessor.joblib",
        "metadata": "models/fusion/metadata.json",
    },
}


def _load_metadata(meta_path: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    """Helper to safely load a metadata.json file."""
    if meta_path is None:
        return {}
    p = Path(meta_path)
    if p.exists() and p.is_file():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read metadata at {meta_path}: {e}")
    return {}


def load_olfactory_model(
    model_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Load the trained olfactory risk model artifact and metadata."""
    m_path = Path(model_path or DEFAULT_PATHS["olfactory"]["model"])
    meta_p = Path(metadata_path or DEFAULT_PATHS["olfactory"]["metadata"])
    metadata = _load_metadata(meta_p)

    if not m_path.exists():
        return {
            "status": "missing",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": None,
        }

    try:
        pipeline = joblib.load(m_path)
        return {
            "status": "loaded",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": pipeline,
        }
    except Exception as e:
        logger.error(f"Error loading olfactory model from {m_path}: {e}")
        return {
            "status": "missing",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": None,
            "error": str(e),
        }


def load_rbd_model(
    model_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Load the trained RBD questionnaire risk model artifact and metadata."""
    m_path = Path(model_path or DEFAULT_PATHS["rbd"]["model"])
    meta_p = Path(metadata_path or DEFAULT_PATHS["rbd"]["metadata"])
    metadata = _load_metadata(meta_p)

    if not m_path.exists():
        return {
            "status": "missing",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": None,
        }

    try:
        pipeline = joblib.load(m_path)
        return {
            "status": "loaded",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": pipeline,
        }
    except Exception as e:
        logger.error(f"Error loading RBD model from {m_path}: {e}")
        return {
            "status": "missing",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": None,
            "error": str(e),
        }


def load_voice_model(
    model_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Load the trained voice acoustic risk model artifact and metadata."""
    m_path = Path(model_path or DEFAULT_PATHS["voice"]["model"])
    meta_p = Path(metadata_path or DEFAULT_PATHS["voice"]["metadata"])
    metadata = _load_metadata(meta_p)

    if not m_path.exists():
        return {
            "status": "missing",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": None,
        }

    try:
        pipeline = joblib.load(m_path)
        return {
            "status": "loaded",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": pipeline,
        }
    except Exception as e:
        logger.error(f"Error loading voice model from {m_path}: {e}")
        return {
            "status": "missing",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": None,
            "error": str(e),
        }


def load_motor_model(
    model_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Load the trained motor/gait risk model artifact and metadata."""
    m_path = Path(model_path or DEFAULT_PATHS["motor"]["model"])
    meta_p = Path(metadata_path or DEFAULT_PATHS["motor"]["metadata"])
    metadata = _load_metadata(meta_p)

    if not m_path.exists():
        return {
            "status": "missing",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": None,
        }

    try:
        pipeline = joblib.load(m_path)
        return {
            "status": "loaded",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": pipeline,
        }
    except Exception as e:
        logger.error(f"Error loading motor model from {m_path}: {e}")
        return {
            "status": "missing",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": None,
            "error": str(e),
        }


def load_retina_model(
    model_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
    require_pd_trained: bool = False,
) -> Dict[str, Any]:
    """
    Load retinal model encoder and metadata.

    If require_pd_trained is True and metadata reports pd_trained=False,
    returns status='not_trained'.
    """
    meta_p = Path(metadata_path or DEFAULT_PATHS["retina"]["metadata"])
    metadata = _load_metadata(meta_p)

    m_path = Path(model_path or DEFAULT_PATHS["retina"]["model"])
    if model_path is not None and not m_path.exists():
        return {
            "status": "missing",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": None,
        }

    if not meta_p.exists():
        return {
            "status": "missing",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": None,
        }

    if require_pd_trained and not metadata.get("pd_trained", False):
        return {
            "status": "not_trained",
            "artifact_path": str(m_path),
            "metadata": metadata,
            "model": None,
        }

    try:
        from src.retina.predict import get_default_encoder
        encoder = get_default_encoder()
        return {
            "status": "loaded",
            "artifact_path": str(meta_p),
            "metadata": metadata,
            "model": encoder,
        }
    except Exception as e:
        logger.error(f"Error loading retinal encoder: {e}")
        return {
            "status": "missing",
            "artifact_path": str(meta_p),
            "metadata": metadata,
            "model": None,
            "error": str(e),
        }


def load_fusion_model(
    classifier_path: Optional[str] = None,
    encoder_path: Optional[str] = None,
    preprocessor_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Load multimodal gated fusion encoder, classifier, and preprocessor."""
    c_path = Path(classifier_path or DEFAULT_PATHS["fusion"]["classifier"])
    e_path = Path(encoder_path or DEFAULT_PATHS["fusion"]["encoder"])
    p_path = Path(preprocessor_path or DEFAULT_PATHS["fusion"]["preprocessor"])
    meta_p = Path(metadata_path or DEFAULT_PATHS["fusion"]["metadata"])
    metadata = _load_metadata(meta_p)

    missing_artifacts = []
    if not c_path.exists():
        missing_artifacts.append(str(c_path))
    if not e_path.exists():
        missing_artifacts.append(str(e_path))
    if not p_path.exists():
        missing_artifacts.append(str(p_path))

    if missing_artifacts:
        return {
            "status": "missing",
            "artifact_path": str(c_path),
            "metadata": metadata,
            "model": None,
            "missing_artifacts": missing_artifacts,
        }

    try:
        clf = joblib.load(c_path)
        preprocessor = joblib.load(p_path)
        from src.fusion.dataset import MODALITIES
        from src.fusion.gated_fusion import GatedMultimodalFusion
        modality_feature_cols = preprocessor["modality_feature_cols"]
        modality_dims = {m: len(modality_feature_cols[m]) for m in MODALITIES}
        state_dict = torch.load(e_path, map_location="cpu", weights_only=True)
        encoder = GatedMultimodalFusion(modality_dims=modality_dims)
        encoder.load_state_dict(state_dict)
        encoder.eval()

        return {
            "status": "loaded",
            "artifact_path": str(c_path),
            "metadata": metadata,
            "model": {
                "classifier": clf,
                "encoder": encoder,
                "preprocessor": preprocessor,
            },
        }
    except Exception as e:
        logger.error(f"Error loading fusion model artifacts: {e}")
        return {
            "status": "missing",
            "artifact_path": str(c_path),
            "metadata": metadata,
            "model": None,
            "error": str(e),
        }


def load_shap_explainer(
    classifier_path: Optional[str] = None,
    encoder_path: Optional[str] = None,
    preprocessor_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Load or initialize the MPF SHAP explainer."""
    c_path = Path(classifier_path or DEFAULT_PATHS["fusion"]["classifier"])
    e_path = Path(encoder_path or DEFAULT_PATHS["fusion"]["encoder"])
    p_path = Path(preprocessor_path or DEFAULT_PATHS["fusion"]["preprocessor"])
    meta_p = Path(metadata_path or DEFAULT_PATHS["fusion"]["metadata"])
    metadata = _load_metadata(meta_p)

    if not c_path.exists() or not e_path.exists() or not p_path.exists():
        return {
            "status": "missing",
            "artifact_path": str(c_path),
            "metadata": metadata,
            "model": None,
        }

    try:
        from src.explainability.shap_explainer import MPFSHAPExplainer
        explainer = MPFSHAPExplainer(
            clf_path=str(c_path),
            enc_path=str(e_path),
            prep_path=str(p_path),
            meta_path=str(meta_p),
        )
        return {
            "status": "loaded",
            "artifact_path": str(c_path),
            "metadata": metadata,
            "model": explainer,
        }
    except Exception as e:
        logger.error(f"Error initializing SHAP explainer: {e}")
        return {
            "status": "missing",
            "artifact_path": str(c_path),
            "metadata": metadata,
            "model": None,
            "error": str(e),
        }


def load_all_models() -> Dict[str, Dict[str, Any]]:
    """Load all models and return the complete registry dictionary."""
    return {
        "olfactory": load_olfactory_model(),
        "rbd": load_rbd_model(),
        "voice": load_voice_model(),
        "motor": load_motor_model(),
        "retina": load_retina_model(),
        "fusion": load_fusion_model(),
        "shap_explainer": load_shap_explainer(),
    }


def get_model_registry() -> Dict[str, Dict[str, Any]]:
    """Alias for load_all_models()."""
    return load_all_models()
