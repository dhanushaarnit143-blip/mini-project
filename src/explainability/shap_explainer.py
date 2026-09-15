"""
MPF-PD Phase 7 — SHAP Explainer.

Wraps the trained XGBoost fusion classifier with a SHAP TreeExplainer.
Computes SHAP values on the actual 45-dimensional fused representation produced
by the GatedMultimodalFusion encoder.

Architecture note:
  The final classifier is an XGBoost model operating on a 45-dim vector:
    [0..31]  gated modality fusion vector   (post-attention, all modalities)
    [32..39] demographic encoder output      (age, sex projection)
    [40..44] modality presence flags         (one per modality, binary 0/1)

  SHAP TreeExplainer is exact for tree models; no surrogate approximation is used.

IMPORTANT:
  - SHAP values reflect the fused representation, NOT raw feature importance
    of the original biomarkers (jitter, RBDSQ score, vessel density, etc.).
  - Modality-level attribution is inferred from:
      (a) SHAP magnitude on the presence flags (indices 40–44) — direct.
      (b) Gate weights from the fusion encoder — soft attribution of the
          gated representation to individual modalities.
  - Missing modalities receive a presence flag of 0; their SHAP contribution
    on the presence flag index directly quantifies the missingness effect.

RESEARCH PROTOTYPE ONLY. Not a diagnostic device. No clinical claims.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure project root on path when run as module
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import joblib
import torch
import shap

from src.fusion.dataset import MODALITIES, generate_synthetic_multimodal_fixture
from src.fusion.gated_fusion import GatedMultimodalFusion
from src.fusion.predict import predict_fusion
from src.explainability.modality_mapping import (
    FUSED_FEATURE_NAMES,
    FUSED_DIM,
    FUSED_GATED_MODALITY_RANGE,
    FUSED_DEMO_RANGE,
    FUSED_PRESENCE_RANGE,
    get_feature_group,
    get_modality_for_presence_flag,
)

logger = logging.getLogger("mpf.explainability.shap_explainer")

DEFAULT_CLF_PATH = "models/fusion/classifier.joblib"
DEFAULT_ENC_PATH = "models/fusion/fusion_encoder.pt"
DEFAULT_PREP_PATH = "models/fusion/preprocessor.joblib"
DEFAULT_META_PATH = "models/fusion/metadata.json"

SEED = 42


class MPFSHAPExplainer:
    """
    SHAP-based explainer for the MPF-PD gated multimodal fusion pipeline.

    Computes exact SHAP values via shap.TreeExplainer on the XGBoost classifier.
    Provides:
      - compute_shap_values()        → raw SHAP arrays for a fused representation matrix
      - explain_single()             → standardised explanation dict for one sample
      - aggregate_modality_importance() → modality-level importance from gate weights + SHAP
    """

    def __init__(
        self,
        clf_path: str = DEFAULT_CLF_PATH,
        enc_path: str = DEFAULT_ENC_PATH,
        prep_path: str = DEFAULT_PREP_PATH,
        meta_path: str = DEFAULT_META_PATH,
        seed: int = SEED,
    ):
        """
        Load the trained XGBoost classifier and fusion encoder.

        Args:
            clf_path:  Path to classifier.joblib (XGBoost).
            enc_path:  Path to fusion_encoder.pt (PyTorch weights).
            prep_path: Path to preprocessor.joblib (imputers + scalers).
            meta_path: Path to metadata.json.
            seed:      Random seed for reproducibility.

        Raises:
            FileNotFoundError: If any required artifact is missing.
        """
        self.seed = seed
        np.random.seed(seed)

        # Validate artifact existence before loading
        for path_str, label in [
            (clf_path, "classifier"),
            (enc_path, "fusion_encoder"),
            (prep_path, "preprocessor"),
        ]:
            p = Path(path_str)
            if not p.exists():
                raise FileNotFoundError(
                    f"Phase 7 blocked: fusion model artifact missing — {label}: {path_str}"
                )

        self.clf_path = clf_path
        self.enc_path = enc_path
        self.prep_path = prep_path
        self.meta_path = meta_path

        # Load classifier
        logger.info("Loading XGBoost classifier from %s", clf_path)
        self.classifier = joblib.load(clf_path)
        self.clf_type = type(self.classifier).__name__

        # Load preprocessor bundle
        logger.info("Loading preprocessor bundle from %s", prep_path)
        self.preprocessors = joblib.load(prep_path)
        self.modality_imputers = self.preprocessors["modality_imputers"]
        self.modality_scalers = self.preprocessors["modality_scalers"]
        self.demo_imp = self.preprocessors["demo_imputer"]
        self.demo_scaler = self.preprocessors["demo_scaler"]
        self.modality_feature_cols = self.preprocessors["modality_feature_cols"]

        # Load metadata
        self.metadata: Dict[str, Any] = {}
        if Path(meta_path).exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        self.experiment_type = self.metadata.get("experiment_type", "prototype_simulation")
        self.average_gate_weights: Dict[str, float] = self.metadata.get(
            "average_gate_weights", {m: 0.2 for m in MODALITIES}
        )

        # Load fusion encoder
        logger.info("Loading fusion encoder from %s", enc_path)
        modality_dims = {m: len(self.modality_feature_cols[m]) for m in MODALITIES}
        self.fusion_net = GatedMultimodalFusion(
            modality_dims=modality_dims,
            embedding_dim=32,
            demo_dim=3,
            fusion_mechanism="gated_attention",
            missing_modality_strategy="learnable_token",
            mask_dropout_rate=0.0,
            seed=seed,
        )
        self.fusion_net.load_state_dict(
            torch.load(enc_path, map_location="cpu")
        )
        self.fusion_net.eval()

        # Determine explanation method
        if hasattr(self.classifier, "get_booster"):
            self.explanation_method = "shap_tree"
            logger.info("Using shap.TreeExplainer (XGBoost detected).")
        elif hasattr(self.classifier, "coef_"):
            self.explanation_method = "shap_linear"
            logger.info("Using shap.LinearExplainer (linear model detected).")
        else:
            self.explanation_method = "shap_kernel"
            logger.warning(
                "Classifier type '%s' requires KernelExplainer — slow for large datasets.",
                self.clf_type,
            )

        self._shap_explainer: Optional[shap.Explainer] = None

    # ------------------------------------------------------------------
    # Internal: build encoder → fused representation for a batch of inputs
    # ------------------------------------------------------------------

    def _build_fused_repr_from_raw(
        self,
        inputs_list: List[Dict[str, Any]],
    ) -> Tuple[np.ndarray, List[Dict[str, float]], List[Dict[str, bool]]]:
        """
        Convert a list of raw input dicts to the 45-dim fused representation matrix.

        Args:
            inputs_list: List of input dicts (same format as predict_fusion).

        Returns:
            Tuple of:
              fused_matrix  : np.ndarray of shape (N, 45)
              gate_weights  : list of dict per sample {modality: gate_weight}
              presence_flags: list of dict per sample {modality: bool}
        """
        import pandas as pd

        all_fused = []
        all_gates = []
        all_presence = []

        for inputs in inputs_list:
            modality_presence: Dict[str, bool] = {}
            modality_tensors: Dict[str, torch.Tensor] = {}

            for mod in MODALITIES:
                mod_input = inputs.get(mod)
                cols = self.modality_feature_cols[mod]
                is_present = (
                    mod_input is not None
                    and isinstance(mod_input, dict)
                    and len(mod_input) > 0
                    and any(v is not None for v in mod_input.values())
                )
                modality_presence[mod] = is_present

                if is_present:
                    row_dict = {}
                    for col in cols:
                        val = mod_input.get(col, np.nan)
                        try:
                            row_dict[col] = float(val) if val is not None else np.nan
                        except (ValueError, TypeError):
                            row_dict[col] = np.nan
                    df_mod = pd.DataFrame([row_dict])[cols]
                    X_imp = self.modality_imputers[mod].transform(df_mod.values)
                    X_sc = self.modality_scalers[mod].transform(X_imp)
                    modality_tensors[mod] = torch.tensor(X_sc, dtype=torch.float32)
                else:
                    dim = len(cols)
                    modality_tensors[mod] = torch.zeros((1, dim), dtype=torch.float32)

            age_val = float(inputs.get("age", 65.0))
            sex_raw = inputs.get("sex", "female")
            if isinstance(sex_raw, str):
                sex_val = 1.0 if sex_raw.lower() in ["m", "male", "1"] else 0.0
            else:
                sex_val = float(sex_raw) if sex_raw is not None else 0.0

            demo_row = np.array([[age_val, sex_val, 1.0]], dtype=float)
            demo_scaled = self.demo_scaler.transform(self.demo_imp.transform(demo_row))
            t_demo = torch.tensor(demo_scaled, dtype=torch.float32)

            pres_row = np.array(
                [[float(modality_presence[m]) for m in MODALITIES]], dtype=float
            )
            t_pres = torch.tensor(pres_row, dtype=torch.float32)

            with torch.no_grad():
                fused_repr, gate_tensor = self.fusion_net.extract_fused_representation(
                    modality_tensors=modality_tensors,
                    presence_flags=t_pres,
                    demo_tensor=t_demo,
                )

            all_fused.append(fused_repr.numpy()[0])
            all_gates.append(
                {m: float(gate_tensor.numpy()[0][i]) for i, m in enumerate(MODALITIES)}
            )
            all_presence.append(modality_presence)

        fused_matrix = np.stack(all_fused, axis=0)
        return fused_matrix, all_gates, all_presence

    # ------------------------------------------------------------------
    # SHAP explainer initialisation / lazy loading
    # ------------------------------------------------------------------

    def _get_shap_explainer(
        self,
        background_data: Optional[np.ndarray] = None,
    ) -> shap.Explainer:
        """
        Initialise (or return cached) SHAP explainer.

        Args:
            background_data: Optional background dataset for KernelExplainer.
                             Ignored for TreeExplainer / LinearExplainer.
        """
        if self._shap_explainer is not None:
            return self._shap_explainer

        if self.explanation_method == "shap_tree":
            self._shap_explainer = shap.TreeExplainer(self.classifier)
        elif self.explanation_method == "shap_linear":
            if background_data is None:
                raise ValueError(
                    "LinearExplainer requires background_data. "
                    "Pass a sample of the fused representation matrix."
                )
            self._shap_explainer = shap.LinearExplainer(
                self.classifier, background_data
            )
        else:
            if background_data is None:
                raise ValueError(
                    "KernelExplainer requires background_data. "
                    "Pass a sample of the fused representation matrix."
                )
            self._shap_explainer = shap.KernelExplainer(
                self.classifier.predict_proba, background_data
            )
        return self._shap_explainer

    # ------------------------------------------------------------------
    # Public API: compute SHAP values
    # ------------------------------------------------------------------

    def compute_shap_values(
        self,
        fused_matrix: np.ndarray,
        background_data: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Compute SHAP values for an (N, 45) fused representation matrix.

        Args:
            fused_matrix:    Array of shape (N, 45) — fused representation samples.
            background_data: Optional background for non-tree explainers.

        Returns:
            shap_values: np.ndarray of shape (N, 45) — SHAP values for class 1
                         (elevated risk signal).

        Note:
            For TreeExplainer the output is exact. No surrogate approximation.
        """
        if fused_matrix.ndim != 2 or fused_matrix.shape[1] != FUSED_DIM:
            raise ValueError(
                f"Expected fused_matrix of shape (N, {FUSED_DIM}). "
                f"Got {fused_matrix.shape}."
            )

        explainer = self._get_shap_explainer(background_data=background_data)

        if self.explanation_method == "shap_tree":
            raw = explainer.shap_values(fused_matrix)
            # XGBoost binary: shap_values may be (N, F) or [(N,F),(N,F)]
            if isinstance(raw, list) and len(raw) == 2:
                shap_vals = raw[1]  # class 1
            elif isinstance(raw, np.ndarray) and raw.ndim == 3:
                shap_vals = raw[:, :, 1]
            else:
                shap_vals = raw
        elif self.explanation_method == "shap_linear":
            raw = explainer.shap_values(fused_matrix)
            if isinstance(raw, list) and len(raw) == 2:
                shap_vals = raw[1]
            else:
                shap_vals = raw
        else:
            raw = explainer.shap_values(fused_matrix)
            if isinstance(raw, list) and len(raw) == 2:
                shap_vals = raw[1]
            else:
                shap_vals = raw

        shap_vals = np.array(shap_vals, dtype=np.float64)

        # Validate: all values must be finite
        if not np.all(np.isfinite(shap_vals)):
            n_inf = np.sum(~np.isfinite(shap_vals))
            logger.warning(
                "%d non-finite SHAP values detected; replacing with 0.0.", n_inf
            )
            shap_vals = np.where(np.isfinite(shap_vals), shap_vals, 0.0)

        return shap_vals

    # ------------------------------------------------------------------
    # Public API: aggregate modality importance
    # ------------------------------------------------------------------

    def aggregate_modality_importance(
        self,
        shap_values: np.ndarray,
        gate_weights_list: Optional[List[Dict[str, float]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate per-feature SHAP values to modality-level importance.

        Strategy:
          1. Presence flags (indices 40–44): direct SHAP attribution.
          2. Gated representation (indices 0–31): split across modalities
             proportionally to their average gate weights from the fusion encoder.
          3. Demo covariates (indices 32–39): attributed to 'demographic_covariates'.

        Args:
            shap_values:      (N, 45) SHAP value array.
            gate_weights_list: Per-sample gate weight dicts. If None, uses
                               metadata average_gate_weights.

        Returns:
            List of dicts:
              [{"modality": str, "mean_abs_shap": float, "percent_contribution": float}, ...]
        """
        N = shap_values.shape[0]

        # Mean absolute SHAP per feature index
        mean_abs = np.mean(np.abs(shap_values), axis=0)

        # 1. Presence flag contributions (direct)
        presence_contrib: Dict[str, float] = {}
        for i, mod in enumerate(MODALITIES):
            idx = FUSED_PRESENCE_RANGE[i]
            presence_contrib[mod] = float(mean_abs[idx])

        # 2. Gated representation contribution distributed by gate weights
        total_gated_shap = float(np.sum(mean_abs[FUSED_GATED_MODALITY_RANGE]))

        if gate_weights_list is not None and len(gate_weights_list) > 0:
            avg_gate: Dict[str, float] = {}
            for m in MODALITIES:
                avg_gate[m] = float(
                    np.mean([gw.get(m, 0.0) for gw in gate_weights_list])
                )
        else:
            avg_gate = {m: self.average_gate_weights.get(m, 0.2) for m in MODALITIES}

        # Normalise gate weights to sum = 1
        total_gate = sum(avg_gate.values()) or 1.0
        norm_gate = {m: avg_gate[m] / total_gate for m in MODALITIES}

        gated_contrib: Dict[str, float] = {
            m: total_gated_shap * norm_gate[m] for m in MODALITIES
        }

        # 3. Demo covariate contribution
        demo_contrib = float(np.sum(mean_abs[FUSED_DEMO_RANGE]))

        # Combine modality-level totals
        modality_totals: Dict[str, float] = {}
        for mod in MODALITIES:
            modality_totals[mod] = gated_contrib[mod] + presence_contrib[mod]
        modality_totals["demographic_covariates"] = demo_contrib

        total_all = sum(modality_totals.values()) or 1.0

        result = []
        for group, contrib in sorted(modality_totals.items(), key=lambda x: -x[1]):
            result.append(
                {
                    "modality": group,
                    "mean_abs_shap": round(float(contrib), 6),
                    "percent_contribution": round(100.0 * contrib / total_all, 2),
                }
            )

        return result
