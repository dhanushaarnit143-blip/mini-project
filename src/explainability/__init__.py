"""
MPF-PD Phase 7 — Explainability Package.

Provides SHAP-based explanations for the Gated Multimodal Fusion classifier.

RESEARCH PROTOTYPE ONLY. No clinical claims are made.
Explanations are decision-support artefacts for research review only.
"""

from src.explainability.modality_mapping import get_feature_mapping, FUSED_FEATURE_NAMES
from src.explainability.shap_explainer import MPFSHAPExplainer
from src.explainability.local_explanation import explain_single
from src.explainability.global_importance import compute_global_importance

__all__ = [
    "MPFSHAPExplainer",
    "get_feature_mapping",
    "FUSED_FEATURE_NAMES",
    "explain_single",
    "compute_global_importance",
]
