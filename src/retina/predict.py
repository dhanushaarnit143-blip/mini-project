"""
Retinal Inference and Feature Extraction API for MPF-PD (Phase 5).

Provides standardized prediction interface:
    predict_retina(image_path: str, model_version: str = "0.1.0") -> dict

Output Schema:
{
  "modality": "retina",
  "embedding": list[float],
  "quality": {
    "passed": bool,
    "issues": list[str]
  },
  "vessel_features": dict,
  "model_version": str,
  "pd_trained": bool,
  "warnings": list[str]
}

Safety & Honesty:
  - Outputs are research prototype representations, NOT a clinical diagnosis.
  - If image fails quality control (QC), downstream feature extraction is NOT forced.
  - Standardized fixed-length embeddings enable seamless downstream multimodal fusion (Phase 6).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from src.retina.quality import check_image_quality
from src.retina.preprocess import preprocess_retina, DEFAULT_IMAGE_SIZE
from src.retina.segmentation import segment_retinal_vessels
from src.retina.vessel_features import extract_vessel_features, RETINA_FEATURE_NAMES
from src.retina.encoder import RetinalCNNEncoder


logger = logging.getLogger("mpf.retina.predict")

# Singleton cached encoder instance to prevent redundant initialization overhead
_CACHED_ENCODER: Optional[RetinalCNNEncoder] = None
_DEFAULT_EMBEDDING_DIM = 128


def get_default_encoder(embedding_dim: int = _DEFAULT_EMBEDDING_DIM) -> RetinalCNNEncoder:
    """Load or retrieve the cached CNN feature encoder."""
    global _CACHED_ENCODER
    if _CACHED_ENCODER is None or _CACHED_ENCODER.embedding_dim != embedding_dim:
        # Check if saved metadata exists
        meta_file = Path("models/retina/metadata.json")
        pd_trained = False
        backbone = "resnet18"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    pd_trained = meta.get("pd_trained", False)
                    backbone = meta.get("backbone", "resnet18")
                    embedding_dim = meta.get("embedding_dim", embedding_dim)
            except Exception:
                pass

        _CACHED_ENCODER = RetinalCNNEncoder(
            backbone=backbone,
            embedding_dim=embedding_dim,
            pretrained=False,
            pd_trained=pd_trained,
        )
    return _CACHED_ENCODER


def predict_retina(
    image_path: Union[str, Path],
    model_version: str = "0.1.0",
    encoder: Optional[RetinalCNNEncoder] = None,
    embedding_dim: int = _DEFAULT_EMBEDDING_DIM,
    allow_qc_bypass: bool = False,
) -> Dict[str, Any]:
    """
    Run the end-to-end retinal analysis pipeline on a single fundus image.

    Pipeline Steps:
      1. Path validation.
      2. Image Quality Control (QC).
         -> If QC fails and allow_qc_bypass is False, feature extraction is aborted.
      3. Standardized Preprocessing (FOV crop, green channel CLAHE, ImageNet tensor).
      4. Vessel Segmentation (morphological baseline).
      5. Quantitative Vascular Biomarker Extraction.
      6. Deep CNN Feature Embedding Extraction (128-D).

    Args:
        image_path: Path to retinal fundus image file (or numpy array / PIL image).
        model_version: Pipeline model version string.
        encoder: Optional pre-instantiated RetinalCNNEncoder.
        embedding_dim: Target embedding dimensionality (default: 128).
        allow_qc_bypass: If True, attempts extraction even if QC flags warnings.

    Returns:
        Dict conforming to Phase 5 prediction schema.
    """
    warnings_list: List[str] = [
        "Research prototype representation only: not validated for clinical Parkinson's screening."
    ]

    # 1. Path validation
    p = Path(image_path) if isinstance(image_path, (str, Path)) else None
    if p is not None and not p.exists():
        return {
            "modality": "retina",
            "embedding": [0.0] * embedding_dim,
            "quality": {
                "passed": False,
                "issues": [f"Image file not found: {image_path}"],
            },
            "vessel_features": {},
            "model_version": model_version,
            "pd_trained": False,
            "warnings": warnings_list + [f"Execution aborted: image file does not exist at '{image_path}'"],
        }

    # 2. Image Quality Control
    qc = check_image_quality(image_path)
    quality_summary = {
        "passed": bool(qc["passed"]),
        "issues": list(qc.get("issues", [])),
    }

    if not qc["passed"]:
        warnings_list.append(
            f"Image failed Quality Control checks ({len(qc['issues'])} issue(s) flagged)."
        )

        if not allow_qc_bypass:
            warnings_list.append(
                "Feature extraction aborted due to QC failure to prevent spurious biomarkers."
            )
            return {
                "modality": "retina",
                "embedding": [0.0] * embedding_dim,
                "quality": quality_summary,
                "vessel_features": {},
                "model_version": model_version,
                "pd_trained": False,
                "warnings": warnings_list,
            }
        else:
            warnings_list.append("QC bypass requested: proceeding with extraction despite QC failure.")

    # 3. Preprocessing
    try:
        preprocessed = preprocess_retina(image_path, target_size=DEFAULT_IMAGE_SIZE)
    except Exception as e:
        warnings_list.append(f"Preprocessing error: {e}")
        return {
            "modality": "retina",
            "embedding": [0.0] * embedding_dim,
            "quality": quality_summary,
            "vessel_features": {},
            "model_version": model_version,
            "pd_trained": False,
            "warnings": warnings_list,
        }

    # 4. Vessel Segmentation
    seg_result = segment_retinal_vessels(
        image=preprocessed["rgb_image"],
        method="classical",
        fov_mask=preprocessed["fov_mask"],
    )

    # 5. Vessel Biomarkers
    vessel_features = extract_vessel_features(
        vessel_mask=seg_result["vessel_mask"],
        fov_mask=seg_result["fov_mask"],
        rgb_image=preprocessed["rgb_image"],
    )

    # 6. CNN Feature Embedding
    active_encoder = encoder if encoder is not None else get_default_encoder(embedding_dim=embedding_dim)
    try:
        emb_arr = active_encoder.extract_embedding(preprocessed["tensor"])
        embedding = [round(float(v), 6) for v in emb_arr]
    except Exception as e:
        warnings_list.append(f"Encoder inference error: {e}")
        embedding = [0.0] * embedding_dim

    # Non-clinical notice
    disclaimer = "Research prototype representation only: not validated for clinical Parkinson's screening."
    if disclaimer not in warnings_list:
        warnings_list.append(disclaimer)

    return {
        "modality": "retina",
        "embedding": embedding,
        "quality": quality_summary,
        "vessel_features": vessel_features,
        "model_version": model_version,
        "pd_trained": bool(active_encoder.pd_trained),
        "warnings": warnings_list,
    }
