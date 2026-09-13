"""
Retinal Analysis Pipeline for MPF-PD (Phase 5).

Integrates:
  - Image quality control (QC)
  - Color fundus preprocessing (FOV segmentation, green channel CLAHE, ImageNet normalization)
  - Vessel segmentation (U-Net deep learning & classical morphological baseline)
  - Quantitative vascular biomarker extraction (density, tortuosity, branching, caliber)
  - Deep CNN feature encoder (ResNet/EfficientNet fixed-length embeddings)
  - Unified inference interface: `predict_retina(image_path)`
"""

from src.retina.quality import check_image_quality
from src.retina.preprocess import preprocess_retina, load_retinal_image
from src.retina.segmentation import segment_retinal_vessels, UNetVesselSegmentation
from src.retina.vessel_features import extract_vessel_features, RETINA_FEATURE_NAMES
from src.retina.encoder import RetinalCNNEncoder
from src.retina.predict import predict_retina

__all__ = [
    "check_image_quality",
    "preprocess_retina",
    "load_retinal_image",
    "segment_retinal_vessels",
    "UNetVesselSegmentation",
    "extract_vessel_features",
    "RETINA_FEATURE_NAMES",
    "RetinalCNNEncoder",
    "predict_retina",
]
