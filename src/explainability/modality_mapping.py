"""
MPF-PD Phase 7 — Fused Feature Mapping.

Maps each index in the 45-dimensional fused representation vector back to its
semantic group (modality, demographic, presence flag).

Fused vector layout (derived from GatedMultimodalFusion.extract_fused_representation):
  [0..31]  — gated modality fusion vector (32 dims, post-attention over 5 modality embeddings)
  [32..39] — demographic encoder output  (8 dims)
  [40..44] — modality presence flags     (5 dims, one per modality)

The 32-dim fused modality vector is a gated weighted sum over 5 modality-specific
32-dim embeddings; it cannot be exactly decomposed back to individual modality
dimensions in the fused space. SHAP values are therefore computed on the full
45-dim fused representation and then *attributed* to modalities using:
  1. Gate weights  — model-internal attention weights per modality.
  2. Presence flags — explicit missingness indicators (indices 40–44).

This module provides the canonical index→group mapping used by the SHAP explainer
and report generators.

RESEARCH PROTOTYPE ONLY. Not a diagnostic device.
"""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Modality definitions (must match src.fusion.dataset.MODALITIES ordering)
# ---------------------------------------------------------------------------
MODALITIES = ["olfactory", "rbd", "voice", "motor", "retina"]

# ---------------------------------------------------------------------------
# Fused vector index ranges
# ---------------------------------------------------------------------------
#  Fused dim = embedding_dim (32) + demo_dim (8) + n_modalities (5) = 45
FUSED_DIM = 45
EMBEDDING_DIM = 32   # gated modality fusion vector
DEMO_DIM = 8         # demographic encoder output
PRESENCE_DIM = 5     # one flag per modality

FUSED_GATED_MODALITY_RANGE = list(range(0, EMBEDDING_DIM))         # 0..31
FUSED_DEMO_RANGE = list(range(EMBEDDING_DIM, EMBEDDING_DIM + DEMO_DIM))  # 32..39
FUSED_PRESENCE_RANGE = list(
    range(EMBEDDING_DIM + DEMO_DIM, EMBEDDING_DIM + DEMO_DIM + PRESENCE_DIM)
)  # 40..44

# Named feature list (used as column names for SHAP DataFrame)
FUSED_FEATURE_NAMES: List[str] = (
    [f"fused_gated_{i}" for i in range(EMBEDDING_DIM)]
    + [f"demo_enc_{i}" for i in range(DEMO_DIM)]
    + [f"presence_{m}" for m in MODALITIES]
)

assert len(FUSED_FEATURE_NAMES) == FUSED_DIM, (
    f"Feature name count mismatch: {len(FUSED_FEATURE_NAMES)} != {FUSED_DIM}"
)

# ---------------------------------------------------------------------------
# Index → modality group mapping
# ---------------------------------------------------------------------------
# The gated modality vector [0..31] is attributable to the *ensemble* of
# present modalities as a group ("fused_gated_representation"). We label it
# separately and attribute modality-level importance via gate weights.
def get_feature_mapping() -> Dict[str, List[int]]:
    """
    Return the canonical mapping from semantic group → list of fused feature indices.

    Groups:
      "fused_gated_representation" : indices 0–31 (post-gating modality vector)
      "demographic_covariates"     : indices 32–39 (age/sex encoder output)
      "presence_olfactory"         : index 40
      "presence_rbd"               : index 41
      "presence_voice"             : index 42
      "presence_motor"             : index 43
      "presence_retina"            : index 44

    Returns:
        Dict mapping group name → list of integer indices.
    """
    mapping: Dict[str, List[int]] = {
        "fused_gated_representation": FUSED_GATED_MODALITY_RANGE,
        "demographic_covariates": FUSED_DEMO_RANGE,
    }
    for i, mod in enumerate(MODALITIES):
        mapping[f"presence_{mod}"] = [FUSED_PRESENCE_RANGE[i]]
    return mapping


def get_feature_group(feature_idx: int) -> str:
    """
    Return the semantic group name for a given fused feature index.

    Args:
        feature_idx: Integer index into the 45-dim fused vector.

    Returns:
        Group name string.
    """
    if feature_idx < 0 or feature_idx >= FUSED_DIM:
        return "unknown"
    if feature_idx in FUSED_GATED_MODALITY_RANGE:
        return "fused_gated_representation"
    if feature_idx in FUSED_DEMO_RANGE:
        return "demographic_covariates"
    for i, mod in enumerate(MODALITIES):
        if feature_idx == FUSED_PRESENCE_RANGE[i]:
            return f"presence_{mod}"
    return "unknown"


def get_modality_for_presence_flag(feature_idx: int) -> str:
    """
    If feature_idx corresponds to a presence flag, return the modality name.

    Returns empty string if not a presence flag index.
    """
    for i, mod in enumerate(MODALITIES):
        if feature_idx == FUSED_PRESENCE_RANGE[i]:
            return mod
    return ""
