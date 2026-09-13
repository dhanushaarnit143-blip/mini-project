"""
Retinal Vessel Segmentation Module for MPF-PD (Phase 5).

Provides two complementary segmentation methodologies:
  1. U-Net Deep Learning Baseline (`UNetVesselSegmentation`):
     Standard encoder-decoder architecture with skip connections for supervised
     vessel segmentation when trained weights or ground-truth annotations are available.
  2. Classical Morphological Fallback (`segment_vessels_classical`):
     Deterministic multiscale morphological top-hat filtering, CLAHE enhancement,
     and adaptive thresholding.
     IMPORTANT: Explicitly labeled as a heuristic baseline, NOT a trained medical model.

Scientific Honesty Disclaimer:
  - Without labeled vessel ground-truth or pretraining weights, the classical fallback
    is employed as a deterministic engineering baseline.
  - Classical morphometry provides reproducible structural surrogates (density, branching)
    but does NOT claim clinical diagnostic accuracy.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from scipy import ndimage
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.retina.preprocess import (
    extract_green_channel,
    apply_clahe,
    estimate_fov_mask,
    resize_image,
    HIGH_RES_SEGMENTATION_SIZE,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. PyTorch U-Net Baseline Architecture
# ─────────────────────────────────────────────────────────────────────────────

class DoubleConv(nn.Module):
    """(Convolution => [BatchNorm] => ReLU) * 2"""
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.double_conv(x)


class UNetVesselSegmentation(nn.Module):
    """
    Standard 4-level U-Net architecture for retinal vessel segmentation.
    Outputs single-channel vessel probability map [B, 1, H, W] in [0, 1].
    """
    def __init__(self, in_channels: int = 1, out_channels: int = 1, features: Tuple[int, ...] = (16, 32, 64, 128)):
        super().__init__()
        self.downs = nn.ModuleList()
        self.ups = nn.ModuleList()
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

        # Encoder
        curr_in = in_channels
        for feature in features:
            self.downs.append(DoubleConv(curr_in, feature))
            curr_in = feature

        # Bottleneck
        self.bottleneck = DoubleConv(features[-1], features[-1] * 2)

        # Decoder
        for feature in reversed(features):
            self.ups.append(
                nn.ConvTranspose2d(feature * 2, feature, kernel_size=2, stride=2)
            )
            self.ups.append(DoubleConv(feature * 2, feature))

        # Final 1x1 conv
        self.final_conv = nn.Conv2d(features[0], out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skip_connections = []

        for down in self.downs:
            x = down(x)
            skip_connections.append(x)
            x = self.pool(x)

        x = self.bottleneck(x)
        skip_connections = skip_connections[::-1]

        for i in range(0, len(self.ups), 2):
            x = self.ups[i](x)
            skip = skip_connections[i // 2]

            if x.shape != skip.shape:
                x = F.interpolate(x, size=skip.shape[2:], mode="bilinear", align_corners=True)

            concat_x = torch.cat((skip, x), dim=1)
            x = self.ups[i + 1](concat_x)

        logits = self.final_conv(x)
        return torch.sigmoid(logits)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Classical Heuristic Vessel Segmentation Fallback
# ─────────────────────────────────────────────────────────────────────────────

def segment_vessels_classical(
    image: np.ndarray,
    fov_mask: Optional[np.ndarray] = None,
    clip_limit: float = 3.0,
    tophat_radius: int = 7,
    threshold_offset: float = 8.0,
    min_vessel_size: int = 15,
) -> Dict[str, Any]:
    """
    Classical vessel segmentation heuristic fallback.

    Pipeline:
      1. Green channel extraction (optical contrast).
      2. CLAHE local contrast enhancement.
      3. Inverted green channel: vessels become bright ridges on darker background.
      4. Morphological Top-Hat filtering (ball/disk structuring element)
         to extract narrow curvilinear structures (vessels) while subtracting
         non-uniform retinal background illumination.
      5. Gaussian smoothing to suppress sensor/quantum noise.
      6. Adaptive local thresholding within FOV.
      7. Morphological area opening (noise removal of tiny isolated pixel clusters).

    NOTE: This is explicitly labeled as a baseline heuristic, NOT a trained medical model.

    Args:
        image: RGB uint8 array [H, W, 3] or Grayscale [H, W].
        fov_mask: Optional binary FOV mask. If None, estimated automatically.
        clip_limit: CLAHE clip limit.
        tophat_radius: Radius in pixels of morphological structuring element.
        threshold_offset: Sensitivity threshold offset.
        min_vessel_size: Minimum connected component size in pixels.

    Returns:
        Dict:
          - "vessel_mask": Binary boolean mask [H, W].
          - "fov_mask": Binary boolean FOV mask [H, W].
          - "enhanced_image": uint8 processed vessel-enhanced map.
          - "vessel_pixel_count": int.
          - "total_fov_pixels": int.
          - "method": "classical_morphological_heuristic".
          - "is_learned_model": False.
    """
    if image.ndim == 3:
        green = extract_green_channel(image)
    else:
        green = image.copy()

    h, w = green.shape[:2]

    if fov_mask is None:
        fov_mask, _ = estimate_fov_mask(image)
    elif fov_mask.shape[:2] != (h, w):
        fov_mask = resize_image(fov_mask, target_size=(w, h), is_mask=True)

    # 1. CLAHE enhancement
    enhanced = apply_clahe(green, clip_limit=clip_limit)

    # 2. Invert green channel: blood vessels (absorb green -> dark) become bright
    inverted = 255 - enhanced

    # 3. Morphological White Top-Hat on inverted image
    # Top-hat(I) = I - Opening(I)
    # Isolates bright elements smaller than structuring element (vessels)
    y, x = np.ogrid[-tophat_radius : tophat_radius + 1, -tophat_radius : tophat_radius + 1]
    kernel = (x * x + y * y <= tophat_radius * tophat_radius).astype(np.uint8)

    opened = ndimage.grey_opening(inverted, structure=kernel)
    tophat = np.clip(inverted.astype(np.int32) - opened.astype(np.int32), 0, 255).astype(np.uint8)

    # 4. Light Gaussian smoothing
    smooth_tophat = ndimage.gaussian_filter(tophat.astype(np.float32), sigma=1.0)

    # 5. Local thresholding within FOV
    if np.any(fov_mask):
        fov_intensities = smooth_tophat[fov_mask]
        median_val = float(np.median(fov_intensities))
        std_val = float(np.std(fov_intensities))
        # Adaptive cutoff
        cutoff = max(median_val + threshold_offset, median_val + 0.5 * std_val)
        raw_mask = (smooth_tophat > cutoff) & fov_mask
    else:
        cutoff = float(np.mean(smooth_tophat) + threshold_offset)
        raw_mask = smooth_tophat > cutoff

    # 6. Morphological cleaning: remove small spurious noise clusters
    structure = ndimage.generate_binary_structure(2, 2)
    labeled, num_features = ndimage.label(raw_mask, structure=structure)
    component_sizes = ndimage.sum(raw_mask, labeled, range(num_features + 1))

    # Keep only components with area >= min_vessel_size
    area_mask = component_sizes >= min_vessel_size
    area_mask[0] = False  # background
    cleaned_vessel_mask = area_mask[labeled]

    # Ensure mask strictly respects FOV
    cleaned_vessel_mask = cleaned_vessel_mask & fov_mask

    vessel_pixels = int(np.sum(cleaned_vessel_mask))
    fov_pixels = int(np.sum(fov_mask))

    return {
        "vessel_mask": cleaned_vessel_mask,
        "fov_mask": fov_mask,
        "enhanced_image": tophat,
        "vessel_pixel_count": vessel_pixels,
        "total_fov_pixels": fov_pixels,
        "method": "classical_morphological_heuristic",
        "is_learned_model": False,
        "heuristic_notice": "Baseline heuristic vessel filter; not a clinically certified segmentation network.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Unified Segmentation Interface
# ─────────────────────────────────────────────────────────────────────────────

def segment_retinal_vessels(
    image: np.ndarray,
    method: str = "classical",
    unet_model: Optional[UNetVesselSegmentation] = None,
    weights_path: Optional[Union[str, Path]] = None,
    fov_mask: Optional[np.ndarray] = None,
    threshold: float = 0.5,
    device: str = "cpu",
) -> Dict[str, Any]:
    """
    Segment retinal microvasculature using either classical heuristics or U-Net.

    Args:
        image: RGB uint8 array [H, W, 3] or Grayscale [H, W].
        method: "classical" or "unet".
        unet_model: Optional instantiated UNetVesselSegmentation.
        weights_path: Optional path to U-Net checkpoint (.pth / .pt).
        fov_mask: Optional binary FOV mask.
        threshold: Probability threshold for U-Net binarization (default 0.5).
        device: "cpu" or "cuda".

    Returns:
        Dict conforming to Phase 5 segmentation schema.
    """
    if fov_mask is None:
        fov_mask, _ = estimate_fov_mask(image)

    if method == "unet":
        # Check if model or weights are provided
        if unet_model is None:
            unet_model = UNetVesselSegmentation(in_channels=1, out_channels=1)
            is_pretrained = False
            if weights_path and Path(weights_path).exists():
                state_dict = torch.load(weights_path, map_location=device)
                unet_model.load_state_dict(state_dict)
                is_pretrained = True
        else:
            is_pretrained = True

        unet_model.to(device)
        unet_model.eval()

        if image.ndim == 3:
            green = extract_green_channel(image)
        else:
            green = image

        h, w = green.shape[:2]
        tensor = torch.from_numpy(green).float().unsqueeze(0).unsqueeze(0) / 255.0
        tensor = tensor.to(device)

        with torch.no_grad():
            prob_map = unet_model(tensor).squeeze().cpu().numpy()

        binary_mask = (prob_map >= threshold) & fov_mask
        vessel_pixels = int(np.sum(binary_mask))
        fov_pixels = int(np.sum(fov_mask))

        return {
            "vessel_mask": binary_mask,
            "probability_map": prob_map,
            "fov_mask": fov_mask,
            "vessel_pixel_count": vessel_pixels,
            "total_fov_pixels": fov_pixels,
            "method": "unet_deep_learning",
            "is_learned_model": True,
            "is_pretrained": is_pretrained,
            "threshold": threshold,
        }

    # Default to classical morphological fallback
    return segment_vessels_classical(image, fov_mask=fov_mask)
