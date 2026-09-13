"""
Gating and Missing Modality Mechanisms for MPF-PD (Phase 6).

Implements:
1. Learnable Modality Gates (Gated Multimodal Unit / Gated Attention).
2. Missing Modality Handling with learnable missing tokens or zero imputation.
3. Modality presence masking to prevent missing modalities from corrupting representations.
4. Deterministic initialization for reproducible research engineering.
"""

from typing import Dict, Tuple, Optional
import torch
import torch.nn as nn
import torch.nn.functional as F


class LearnableMissingToken(nn.Module):
    """
    Maintains a learnable embedding token for a missing modality.
    When modality presence is 0, the learnable missing token is emitted instead.
    """

    def __init__(self, embedding_dim: int, seed: int = 42):
        super().__init__()
        torch.manual_seed(seed)
        # Deterministic parameter initialization
        self.missing_token = nn.Parameter(torch.zeros(1, embedding_dim))
        nn.init.normal_(self.missing_token, mean=0.0, std=0.02)

    def forward(self, embedding: torch.Tensor, presence: torch.Tensor) -> torch.Tensor:
        """
        Args:
            embedding: (B, D) tensor of projected modality embeddings.
            presence: (B, 1) binary tensor (1=present, 0=absent).

        Returns:
            (B, D) tensor with missing token substituted where presence == 0.
        """
        # presence broadcast: (B, 1) -> (B, D)
        token_expanded = self.missing_token.expand_as(embedding)
        return presence * embedding + (1.0 - presence) * token_expanded


class ModalityGate(nn.Module):
    """
    Computes learnable gate weights across modalities using a Gated Multimodal Unit (GMU)
    or masked softmax attention over available modalities.
    """

    def __init__(
        self,
        embedding_dim: int,
        n_modalities: int = 5,
        mechanism: str = "gated_attention",
        seed: int = 42,
    ):
        super().__init__()
        self.embedding_dim = embedding_dim
        self.n_modalities = n_modalities
        self.mechanism = mechanism

        torch.manual_seed(seed)
        if mechanism == "gated_attention":
            # Cross-modality query vector
            self.query = nn.Parameter(torch.randn(1, 1, embedding_dim) * 0.02)
            self.key_proj = nn.Linear(embedding_dim, embedding_dim)
            self.scale = 1.0 / (embedding_dim ** 0.5)
        else:  # "gated_average"
            # Linear score per modality
            self.score_fc = nn.Linear(embedding_dim + 1, 1)

    def forward(
        self,
        modality_embeddings: torch.Tensor,
        presence_flags: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            modality_embeddings: (B, M, D) tensor containing all M modality embeddings.
            presence_flags: (B, M) binary tensor where 1=modality present, 0=missing.

        Returns:
            Tuple[torch.Tensor, torch.Tensor]:
                - fused_repr: (B, D) pooled representation
                - gate_weights: (B, M) normalized weights assigned to each modality
        """
        B, M, D = modality_embeddings.shape

        if self.mechanism == "gated_attention":
            # Q: (B, 1, D), K: (B, M, D)
            Q = self.query.expand(B, -1, -1)
            K = self.key_proj(modality_embeddings)
            
            # Attention scores: (B, 1, M)
            scores = torch.bmm(Q, K.transpose(1, 2)) * self.scale
            scores = scores.squeeze(1)  # (B, M)

            # Mask missing modalities: give large negative score where presence == 0
            # To handle edge case where all modalities are absent (should not happen), add eps
            mask = (presence_flags <= 0.0)
            large_neg = -1e9
            scores_masked = scores.masked_fill(mask, large_neg)

            # Softmax across modalities
            weights = F.softmax(scores_masked, dim=-1)  # (B, M)

            # Fallback if a row had all masked out (weights would be NaN)
            nan_mask = torch.isnan(weights)
            if nan_mask.any():
                # Uniform fallback across present or 1/M
                weights = torch.where(nan_mask, torch.ones_like(weights) / M, weights)

            # Weighted sum: (B, 1, M) @ (B, M, D) -> (B, 1, D) -> (B, D)
            fused_repr = torch.bmm(weights.unsqueeze(1), modality_embeddings).squeeze(1)

        else:  # "gated_average"
            # Combine embedding with presence flag
            inputs = torch.cat([modality_embeddings, presence_flags.unsqueeze(-1)], dim=-1)
            raw_scores = self.score_fc(inputs).squeeze(-1)  # (B, M)
            
            mask = (presence_flags <= 0.0)
            scores_masked = raw_scores.masked_fill(mask, -1e9)
            weights = F.softmax(scores_masked, dim=-1)

            nan_mask = torch.isnan(weights)
            if nan_mask.any():
                weights = torch.where(nan_mask, torch.ones_like(weights) / M, weights)

            fused_repr = torch.bmm(weights.unsqueeze(1), modality_embeddings).squeeze(1)

        return fused_repr, weights
