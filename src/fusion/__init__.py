"""
Multimodal Prodromal Fusion (MPF-PD) Module.

Combines olfactory, RBD, voice, motor/gait, and retinal biomarkers
with non-specialist deployment covariates into a research prototype risk estimate.

DISCLAIMER:
Outputs are research prototype risk estimates only.
No clinical claims are made. Not for clinical diagnosis.
"""

from src.fusion.predict import predict_fusion
from src.fusion.gated_fusion import GatedMultimodalFusion
from src.fusion.dataset import build_multimodal_dataset, check_true_multimodal_data_availability

__all__ = [
    "predict_fusion",
    "GatedMultimodalFusion",
    "build_multimodal_dataset",
    "check_true_multimodal_data_availability",
]
