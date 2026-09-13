"""
Retinal Deep Learning Feature Encoder for MPF-PD (Phase 5).

Implements convolutional neural network feature extraction for color fundus images:
  - Standard backbones: ResNet-18, ResNet-50, EfficientNet-B0.
  - Removes final classification head.
  - Projects representations into a standardized fixed-length embedding vector (e.g. 128-D).
  - Explicitly documents whether weights are general-purpose ImageNet/retinal pretraining
    versus Parkinson's-specific fine-tuning.

Scientific Honesty & Safety:
  - By default, `pd_trained = False`.
  - Without Parkinson's-specific retinal labels, embeddings represent general-purpose
    retinal morphometry/texture representations, NOT a PD risk score.
  - Outputs are research prototype representations for downstream multimodal fusion.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
import torchvision.models as models

from src.retina.preprocess import preprocess_retina, DEFAULT_IMAGE_SIZE


class RetinalCNNEncoder(nn.Module):
    """
    Retinal CNN Encoder generating fixed-length embedding vectors.

    Args:
        backbone: Architecture name ('resnet18', 'resnet50', 'efficientnet_b0').
        embedding_dim: Dimensionality of final retinal embedding (default: 128).
        pretrained: Whether to load standard ImageNet weights for feature extraction.
        pd_trained: Whether this encoder has undergone supervised PD-specific training.
        device: Target execution device ('cpu' or 'cuda').
    """

    def __init__(
        self,
        backbone: str = "resnet18",
        embedding_dim: int = 128,
        pretrained: bool = False,
        pd_trained: bool = False,
        device: str = "cpu",
    ):
        super().__init__()
        self.backbone_name = backbone.lower()
        self.embedding_dim = embedding_dim
        self.pretrained = pretrained
        self.pd_trained = pd_trained
        self.device = device

        self.backbone, in_features = self._build_backbone(self.backbone_name, pretrained)

        # Standardized projection head: Linear -> LayerNorm
        self.projection_head = nn.Sequential(
            nn.Linear(in_features, embedding_dim),
            nn.LayerNorm(embedding_dim),
        )

        self.to(self.device)
        self.eval()

    def _build_backbone(self, name: str, pretrained: bool) -> Tuple[nn.Module, int]:
        """
        Build backbone and extract penultimate feature dimension.
        Safely handles offline environments by falling back to uninitialized weights if needed.
        """
        try:
            if name == "resnet18":
                weights = models.ResNet18_Weights.DEFAULT if pretrained else None
                model = models.resnet18(weights=weights)
                in_features = model.fc.in_features
                model.fc = nn.Identity()
                return model, in_features

            elif name == "resnet50":
                weights = models.ResNet50_Weights.DEFAULT if pretrained else None
                model = models.resnet50(weights=weights)
                in_features = model.fc.in_features
                model.fc = nn.Identity()
                return model, in_features

            elif name == "efficientnet_b0":
                weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
                model = models.efficientnet_b0(weights=weights)
                in_features = model.classifier[1].in_features
                model.classifier = nn.Identity()
                return model, in_features

            else:
                raise ValueError(
                    f"Unsupported backbone: '{name}'. Choose from 'resnet18', 'resnet50', 'efficientnet_b0'."
                )

        except Exception as e:
            # If download fails (e.g. offline environment), fallback to non-pretrained
            if pretrained:
                return self._build_backbone(name, pretrained=False)
            raise e

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass producing normalized fixed-length retinal embeddings.

        Args:
            x: Input tensor [B, 3, H, W] normalized with ImageNet statistics.

        Returns:
            torch.Tensor of shape [B, embedding_dim].
        """
        features = self.backbone(x)
        embeddings = self.projection_head(features)
        return embeddings

    def extract_embedding(
        self,
        image_input: Union[str, Path, np.ndarray, torch.Tensor],
    ) -> np.ndarray:
        """
        Extract a 1D fixed-length retinal embedding vector from an image or tensor.

        Args:
            image_input: Path to image file, numpy array [H, W, 3], or torch tensor [3, H, W].

        Returns:
            np.ndarray of shape (embedding_dim,), dtype float32.
        """
        self.eval()

        if isinstance(image_input, torch.Tensor):
            if image_input.ndim == 3:
                tensor = image_input.unsqueeze(0)
            else:
                tensor = image_input
        else:
            preprocessed = preprocess_retina(image_input, target_size=DEFAULT_IMAGE_SIZE)
            tensor = preprocessed["tensor"].unsqueeze(0)

        tensor = tensor.to(self.device)

        with torch.no_grad():
            emb = self.forward(tensor)

        return emb.squeeze(0).cpu().numpy().astype(np.float32)

    def get_metadata(self) -> Dict[str, Any]:
        """Return standardized encoder metadata."""
        return {
            "model_type": "RetinalCNNEncoder",
            "backbone": self.backbone_name,
            "embedding_dim": self.embedding_dim,
            "pretrained": self.pretrained,
            "pd_trained": self.pd_trained,
            "clinical_claim": False,
            "experiment_type": "prototype" if not self.pd_trained else "real_data",
            "status": "prototype_representation" if not self.pd_trained else "pd_fine_tuned",
            "limitations": [
                "Retinal encoder extracts generic structural/texture representations.",
                "No clinical claim: encoder output is not a diagnosis or screening for Parkinson's disease.",
                "Zero clinical validity until prospective multimodal validation is conducted.",
            ],
        }
