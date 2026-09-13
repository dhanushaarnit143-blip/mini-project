"""
Gated Multimodal Fusion Architecture for MPF-PD (Phase 6).

Implements:
1. Modality-specific Encoders for Olfactory, RBD, Voice, Motor, Retina, and Demographics.
2. Common embedding projection with LayerNorm.
3. Learnable missing-modality handling with presence flags.
4. Gated multimodal fusion (GMU / Gated Attention).
5. Masked multimodal training (random modality dropout) for missingness robustness.
6. Fixed-size fused representation output compatible with XGBoost.
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.fusion.gates import LearnableMissingToken, ModalityGate

MODALITIES = ["olfactory", "rbd", "voice", "motor", "retina"]


class ModalityEncoder(nn.Module):
    """
    Projects modality raw/standardized features to a common embedding space.
    """

    def __init__(
        self,
        input_dim: int,
        embedding_dim: int = 32,
        dropout: float = 0.1,
        seed: int = 42,
    ):
        super().__init__()
        torch.manual_seed(seed)
        self.fc1 = nn.Linear(input_dim, embedding_dim)
        self.norm = nn.LayerNorm(embedding_dim)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(embedding_dim, embedding_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.fc1(x)
        h = self.norm(h)
        h = self.act(h)
        h = self.fc2(h)
        h = self.dropout(h)
        return h


class GatedMultimodalFusion(nn.Module):
    """
    Core MPF-PD Gated Multimodal Fusion Network.

    Architecture:
      Olfactory Features -> Olfactory Encoder -> (B, D)
      RBD Features       -> RBD Encoder       -> (B, D)
      Voice Features     -> Voice Encoder     -> (B, D)
      Motor Features     -> Motor Encoder     -> (B, D)
      Retina Features    -> Retina Encoder    -> (B, D)

      Missing Token Substitution -> (B, 5, D)
      Modality Gating (Attention / GMU) -> Fused Modality Vector (B, D)
      Demographics Encoder -> (B, D_demo)
      Concatenation: [Fused Modality Vector, Demographics, Presence Flags] -> (B, D_fused)
      Classification Head -> Risk Logits -> Risk Probability [0.0, 1.0]
    """

    def __init__(
        self,
        modality_dims: Dict[str, int],
        embedding_dim: int = 32,
        demo_dim: int = 3,  # age, sex, provenance
        fusion_mechanism: str = "gated_attention",
        missing_modality_strategy: str = "learnable_token",
        mask_dropout_rate: float = 0.20,
        seed: int = 42,
    ):
        """
        Args:
            modality_dims: Dict mapping modality name to feature dimension.
            embedding_dim: Target common embedding dimension for each modality.
            demo_dim: Dimension of demographic/context features.
            fusion_mechanism: 'gated_attention' or 'gated_average'.
            missing_modality_strategy: 'learnable_token' or 'zero'.
            mask_dropout_rate: Probability of randomly masking an available modality during training.
            seed: Deterministic random seed.
        """
        super().__init__()
        self.modality_dims = modality_dims
        self.embedding_dim = embedding_dim
        self.demo_dim = demo_dim
        self.modalities = MODALITIES
        self.n_modalities = len(self.modalities)
        self.fusion_mechanism = fusion_mechanism
        self.missing_modality_strategy = missing_modality_strategy
        self.mask_dropout_rate = mask_dropout_rate
        self.seed = seed

        torch.manual_seed(seed)

        # Modality Encoders
        self.encoders = nn.ModuleDict({
            mod: ModalityEncoder(
                input_dim=modality_dims.get(mod, 1),
                embedding_dim=embedding_dim,
                dropout=0.1,
                seed=seed + i,
            )
            for i, mod in enumerate(self.modalities)
        })

        # Missing token modules (if learnable_token strategy)
        if missing_modality_strategy == "learnable_token":
            self.missing_tokens = nn.ModuleDict({
                mod: LearnableMissingToken(embedding_dim=embedding_dim, seed=seed + 10 + i)
                for i, mod in enumerate(self.modalities)
            })
        else:
            self.missing_tokens = None

        # Demographic encoder
        self.demo_encoder = nn.Sequential(
            nn.Linear(demo_dim, 8),
            nn.LayerNorm(8),
            nn.GELU(),
        )

        # Modality Gating Unit
        self.gate = ModalityGate(
            embedding_dim=embedding_dim,
            n_modalities=self.n_modalities,
            mechanism=fusion_mechanism,
            seed=seed,
        )

        # Fused output dimension:
        # Fused modality representation (embedding_dim) + Demo embedding (8) + Presence flags (n_modalities)
        self.fused_dim = embedding_dim + 8 + self.n_modalities

        # Internal classification head (can be used directly or as representation extractor for XGBoost)
        self.classifier_head = nn.Sequential(
            nn.Linear(self.fused_dim, 32),
            nn.LayerNorm(32),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(32, 1),
        )

    def extract_fused_representation(
        self,
        modality_tensors: Dict[str, torch.Tensor],
        presence_flags: torch.Tensor,
        demo_tensor: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute fused representation vector and gate weights.

        Args:
            modality_tensors: Dict of (B, Dim_m) tensors for each modality.
            presence_flags: (B, M) binary tensor of presence indicators.
            demo_tensor: (B, Demo_dim) tensor of demographic covariates.

        Returns:
            Tuple[torch.Tensor, torch.Tensor]:
                - fused_embedding: (B, fused_dim)
                - gate_weights: (B, M)
        """
        B = demo_tensor.shape[0]

        # Masked multimodal training: during training, randomly drop present modalities
        effective_presence = presence_flags.clone()
        if self.training and self.mask_dropout_rate > 0:
            # Random dropout mask: drop with prob mask_dropout_rate
            drop_mask = (torch.rand_like(effective_presence) < self.mask_dropout_rate).float()
            # Keep at least 1 modality present per sample
            candidate = effective_presence * (1.0 - drop_mask)
            has_at_least_one = (candidate.sum(dim=-1, keepdim=True) > 0).float()
            effective_presence = has_at_least_one * candidate + (1.0 - has_at_least_one) * effective_presence

        encoded_list = []
        for i, mod in enumerate(self.modalities):
            raw_x = modality_tensors[mod]
            p_mod = effective_presence[:, i:i+1]  # (B, 1)

            # Replace any NaNs in raw_x with 0 before encoder to prevent NaN propagation
            clean_x = torch.nan_to_num(raw_x, nan=0.0)
            h_mod = self.encoders[mod](clean_x)  # (B, D)

            # Apply missing modality strategy
            if self.missing_tokens is not None:
                h_mod = self.missing_tokens[mod](h_mod, p_mod)
            else:
                h_mod = h_mod * p_mod

            encoded_list.append(h_mod.unsqueeze(1))  # (B, 1, D)

        # Stack into (B, M, D)
        stacked_embeddings = torch.cat(encoded_list, dim=1)

        # Apply gating unit
        fused_modality, gate_weights = self.gate(stacked_embeddings, effective_presence)  # (B, D), (B, M)

        # Encode demographics
        clean_demo = torch.nan_to_num(demo_tensor, nan=0.0)
        h_demo = self.demo_encoder(clean_demo)  # (B, 8)

        # Concatenate: [fused_modality, h_demo, presence_flags] -> (B, fused_dim)
        fused_embedding = torch.cat([fused_modality, h_demo, effective_presence], dim=-1)

        return fused_embedding, gate_weights

    def forward(
        self,
        modality_tensors: Dict[str, torch.Tensor],
        presence_flags: torch.Tensor,
        demo_tensor: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass producing risk probability, fused representation, and gate weights.

        Returns:
            Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
                - risk_probs: (B, 1) in range [0.0, 1.0]
                - fused_embedding: (B, fused_dim)
                - gate_weights: (B, M)
        """
        fused_embedding, gate_weights = self.extract_fused_representation(
            modality_tensors=modality_tensors,
            presence_flags=presence_flags,
            demo_tensor=demo_tensor,
        )

        logits = self.classifier_head(fused_embedding)
        probs = torch.sigmoid(logits)

        return probs, fused_embedding, gate_weights
