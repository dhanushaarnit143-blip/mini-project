"""
Retinal Image Preprocessing Pipeline for MPF-PD (Phase 5).

Provides standardized image preprocessing for fundus photographs and retinal scans:
  1. Robust image loading (Path, string, PIL.Image, np.ndarray).
  2. RGB conversion and dimension standardization.
  3. Circular Field of View (FOV) segmentation and bounding-box cropping.
  4. Green channel extraction (highest hemoglobin absorption contrast for microvasculature).
  5. Contrast Limited Adaptive Histogram Equalization (CLAHE).
  6. Standardized resizing and normalization (ImageNet stats; fixed constants, no test leakage).

Zero data leakage: All normalization parameters are fixed ImageNet or mathematical constants.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from PIL import Image

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

from scipy import ndimage
import torch

from src.retina.quality import estimate_fov_mask


# Fixed ImageNet normalization constants (never fit on test or evaluation data)
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

DEFAULT_IMAGE_SIZE = (224, 224)
HIGH_RES_SEGMENTATION_SIZE = (512, 512)


def load_retinal_image(image_input: Union[str, Path, Image.Image, np.ndarray]) -> np.ndarray:
    """
    Load an image from disk or memory and convert to standard uint8 RGB numpy array.

    Args:
        image_input: File path, Path object, PIL Image, or numpy array.

    Returns:
        np.ndarray: RGB uint8 array of shape [H, W, 3].

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If image format or dimensions are invalid.
    """
    if isinstance(image_input, (str, Path)):
        p = Path(image_input)
        if not p.exists():
            raise FileNotFoundError(f"Retinal image file not found: {image_input}")
        try:
            pil_img = Image.open(p).convert("RGB")
            arr = np.array(pil_img)
        except Exception as e:
            raise ValueError(f"Failed to decode image at '{image_input}': {e}") from e
    elif isinstance(image_input, Image.Image):
        arr = np.array(image_input.convert("RGB"))
    elif isinstance(image_input, np.ndarray):
        arr = image_input.copy()
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input).__name__}")

    # Standardize dtype to uint8
    if arr.dtype != np.uint8:
        if arr.max() <= 1.0:
            arr = (arr * 255.0).clip(0, 255).astype(np.uint8)
        else:
            arr = arr.clip(0, 255).astype(np.uint8)

    # Convert grayscale or 4-channel to RGB
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    elif arr.ndim == 3:
        if arr.shape[2] == 1:
            arr = np.repeat(arr, 3, axis=-1)
        elif arr.shape[2] == 4:
            arr = arr[:, :, :3]  # Strip alpha channel
        elif arr.shape[2] != 3:
            raise ValueError(f"Unexpected number of channels: {arr.shape[2]}")
    else:
        raise ValueError(f"Invalid image array dimension: {arr.ndim}D")

    return arr


def extract_green_channel(rgb_image: np.ndarray) -> np.ndarray:
    """
    Extract green channel from RGB fundus photograph.

    Retinal blood vessels have strong optical absorption in the green spectrum
    (~540-570 nm), maximizing contrast against the orange/red retinal background.

    Args:
        rgb_image: RGB uint8 array [H, W, 3].

    Returns:
        np.ndarray: uint8 array [H, W] of green channel intensities.
    """
    if rgb_image.ndim != 3 or rgb_image.shape[2] < 2:
        raise ValueError("Expected 3-channel RGB image.")
    return rgb_image[:, :, 1].copy()


def apply_clahe(
    gray_image: np.ndarray,
    clip_limit: float = 2.5,
    tile_grid_size: Tuple[int, int] = (8, 8),
) -> np.ndarray:
    """
    Apply Contrast Limited Adaptive Histogram Equalization (CLAHE).

    Enhances local microvascular contrast without amplifying noise in homogenous regions.

    Args:
        gray_image: uint8 array [H, W].
        clip_limit: Threshold for contrast limiting.
        tile_grid_size: Grid division for local histogram equalization.

    Returns:
        np.ndarray: uint8 contrast-enhanced array [H, W].
    """
    if _HAS_CV2:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        return clahe.apply(gray_image)
    else:
        # Fallback using percentile stretching and local contrast normalization
        blurred = ndimage.gaussian_filter(gray_image.astype(np.float32), sigma=12.0)
        high_pass = gray_image.astype(np.float32) - blurred
        # Rescale high-pass to 0-255
        enhanced = 128.0 + high_pass * clip_limit
        return np.clip(enhanced, 0, 255).astype(np.uint8)


def detect_and_crop_fov(
    rgb_image: np.ndarray,
    threshold: float = 18.0,
    margin: int = 4,
) -> Tuple[np.ndarray, np.ndarray, Tuple[int, int, int, int]]:
    """
    Detect the retinal aperture FOV and crop out unnecessary black borders.

    Args:
        rgb_image: RGB uint8 array [H, W, 3].
        threshold: Intensity cutoff for non-background retina.
        margin: Padding in pixels around the detected FOV bounding box.

    Returns:
        Tuple of:
          - cropped RGB image [H_crop, W_crop, 3]
          - cropped binary FOV mask [H_crop, W_crop]
          - bounding box (ymin, ymax, xmin, xmax) in original coordinates.
    """
    h, w = rgb_image.shape[:2]
    green = rgb_image[:, :, 1]
    smoothed = ndimage.gaussian_filter(green.astype(np.float32), sigma=2.5)
    fov_mask = smoothed > threshold
    fov_mask = ndimage.binary_fill_holes(fov_mask)

    coords = np.argwhere(fov_mask)
    if coords.size == 0:
        # No FOV detected; return full image
        return rgb_image, np.ones((h, w), dtype=bool), (0, h, 0, w)

    ymin, xmin = coords.min(axis=0)
    ymax, xmax = coords.max(axis=0) + 1

    ymin = max(0, ymin - margin)
    ymax = min(h, ymax + margin)
    xmin = max(0, xmin - margin)
    xmax = min(w, xmax + margin)

    cropped_rgb = rgb_image[ymin:ymax, xmin:xmax, :].copy()
    cropped_fov = fov_mask[ymin:ymax, xmin:xmax].copy()

    return cropped_rgb, cropped_fov, (int(ymin), int(ymax), int(xmin), int(xmax))


def resize_image(
    image: np.ndarray,
    target_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    is_mask: bool = False,
) -> np.ndarray:
    """
    Resize image or mask to target (width, height).

    Args:
        image: np.ndarray [H, W, C] or [H, W].
        target_size: (width, height) tuple.
        is_mask: If True, uses nearest-neighbor interpolation to preserve discrete values.

    Returns:
        np.ndarray resized to (height, width).
    """
    target_w, target_h = target_size
    pil_mode = Image.NEAREST if is_mask else Image.BILINEAR

    if image.dtype == bool:
        pil_img = Image.fromarray((image * 255).astype(np.uint8))
        resized = pil_img.resize((target_w, target_h), pil_mode)
        return np.array(resized) > 127
    else:
        pil_img = Image.fromarray(image)
        resized = pil_img.resize((target_w, target_h), pil_mode)
        return np.array(resized)


def to_torch_tensor(
    rgb_image: np.ndarray,
    normalize: bool = True,
) -> torch.Tensor:
    """
    Convert RGB uint8 numpy array [H, W, 3] to PyTorch tensor [3, H, W]
    with fixed ImageNet normalization (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]).

    Args:
        rgb_image: RGB uint8 array [H, W, 3].
        normalize: Whether to apply ImageNet mean/std normalization.

    Returns:
        torch.Tensor of shape [3, H, W], dtype torch.float32.
    """
    # [H, W, 3] -> float32 in [0, 1]
    tensor = torch.from_numpy(rgb_image.transpose(2, 0, 1)).float() / 255.0

    if normalize:
        mean = torch.tensor(IMAGENET_MEAN, dtype=torch.float32).view(3, 1, 1)
        std = torch.tensor(IMAGENET_STD, dtype=torch.float32).view(3, 1, 1)
        tensor = (tensor - mean) / std

    return tensor


def preprocess_retina(
    image_input: Union[str, Path, Image.Image, np.ndarray],
    target_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    crop_fov: bool = True,
    enhance_green: bool = True,
    clahe_clip_limit: float = 2.5,
) -> Dict[str, Any]:
    """
    End-to-end retinal image preprocessing pipeline.

    Args:
        image_input: File path, PIL Image, or numpy array.
        target_size: (width, height) for CNN input (default 224x224).
        crop_fov: Whether to detect and tightly crop the retinal FOV.
        enhance_green: Whether to generate a CLAHE-enhanced green channel.
        clahe_clip_limit: Contrast clip limit for CLAHE.

    Returns:
        Dict containing:
          - "rgb_image": Standardized RGB uint8 array [target_h, target_w, 3]
          - "green_enhanced": CLAHE-enhanced green channel [target_h, target_w]
          - "fov_mask": Binary FOV mask [target_h, target_w]
          - "tensor": Normalized PyTorch tensor [3, target_h, target_w]
          - "original_shape": (original_h, original_w, channels)
          - "bounding_box": Bounding box used for FOV crop (ymin, ymax, xmin, xmax)
    """
    raw_rgb = load_retinal_image(image_input)
    orig_shape = raw_rgb.shape

    if crop_fov:
        cropped_rgb, cropped_fov, bbox = detect_and_crop_fov(raw_rgb)
    else:
        cropped_rgb = raw_rgb
        cropped_fov = np.ones(raw_rgb.shape[:2], dtype=bool)
        bbox = (0, raw_rgb.shape[0], 0, raw_rgb.shape[1])

    # Resize to standard model input size
    resized_rgb = resize_image(cropped_rgb, target_size=target_size, is_mask=False)
    resized_fov = resize_image(cropped_fov, target_size=target_size, is_mask=True)

    # Green channel extraction and CLAHE enhancement
    green = extract_green_channel(resized_rgb)
    if enhance_green:
        green_enhanced = apply_clahe(green, clip_limit=clahe_clip_limit)
    else:
        green_enhanced = green

    # Convert to normalized PyTorch tensor
    tensor = to_torch_tensor(resized_rgb, normalize=True)

    return {
        "rgb_image": resized_rgb,
        "green_enhanced": green_enhanced,
        "fov_mask": resized_fov,
        "tensor": tensor,
        "original_shape": orig_shape,
        "bounding_box": bbox,
    }
