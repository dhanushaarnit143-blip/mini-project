"""
Retinal Image Quality Control (QC) Module for MPF-PD (Phase 5).

Implements objective quality checks for color fundus photography and retinal scans:
  1. Image size and channel validation.
  2. Blur detection via Laplacian variance.
  3. Illumination / brightness and contrast statistics.
  4. Retinal Field of View (FOV) detection and coverage.
  5. Excessive black border detection.
  6. Artifact detection (specular reflections, overexposure, severe glare).
  7. Unreadable image flag.

QC returns:
  {
    "passed": bool,
    "issues": list[str],
    "unreadable": bool,
    "metrics": dict
  }

If an image fails QC, downstream feature extraction must NOT be forced.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

from scipy import ndimage


# ─────────────────────────────────────────────────────────────────────────────
# Quality Threshold Defaults
# ─────────────────────────────────────────────────────────────────────────────

MIN_WIDTH = 128
MIN_HEIGHT = 128
MIN_BRIGHTNESS = 15.0       # Out of 255 (underexposed)
MAX_BRIGHTNESS = 240.0      # Out of 255 (overexposed)
MIN_CONTRAST_STD = 8.0      # Standard deviation of intensities
MIN_LAPLACIAN_VAR = 20.0    # Blur threshold
MIN_FOV_COVERAGE = 0.15     # At least 15% of pixels inside illuminated retina
MAX_BORDER_RATIO = 0.92     # No more than 92% black border padding when FOV is small
MAX_SATURATED_RATIO = 0.08  # Overexposure / glare threshold in FOV


def _compute_laplacian_variance(gray: np.ndarray) -> float:
    """
    Compute variance of the Laplacian filter as a focus/blur measure.
    Higher values indicate sharper edges; lower values indicate blur.
    """
    if _HAS_CV2:
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        return float(lap.var())
    else:
        # Classical 3x3 Laplacian kernel via scipy
        kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
        lap = ndimage.convolve(gray.astype(np.float64), kernel, mode="reflect")
        return float(lap.var())


def estimate_fov_mask(
    image: np.ndarray,
    threshold: float = 18.0,
) -> Tuple[np.ndarray, float]:
    """
    Estimate the circular Retinal Field of View (FOV) mask.

    In color fundus photography, the camera aperture illuminates a circular
    or elliptical region. Background outside the aperture is near-black.

    Args:
        image: RGB uint8 array [H, W, 3] or Grayscale [H, W].
        threshold: Intensity cutoff for non-background retina.

    Returns:
        Tuple of (binary boolean mask [H, W], fov_ratio).
    """
    if image.ndim == 3:
        # Green channel has strongest signal-to-noise ratio in retina
        channel = image[:, :, 1]
    else:
        channel = image

    # Light smoothing to bridge dark vessels inside the bright fundus
    smoothed = ndimage.gaussian_filter(channel.astype(np.float32), sigma=2.0)
    fov_mask = smoothed > threshold

    # Morphological closing to fill vessels and fovea inside the disc
    structure = ndimage.generate_binary_structure(2, 1)
    fov_mask = ndimage.binary_closing(fov_mask, structure=structure, iterations=3)
    # Fill internal holes
    fov_mask = ndimage.binary_fill_holes(fov_mask)

    total_pixels = image.shape[0] * image.shape[1]
    fov_ratio = float(np.sum(fov_mask)) / float(max(total_pixels, 1))

    return fov_mask, fov_ratio


def _calculate_border_ratio(image: np.ndarray, threshold: float = 12.0) -> float:
    """
    Compute ratio of near-black pixels along outer borders.
    """
    if image.ndim == 3:
        gray = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]
    else:
        gray = image.astype(np.float32)

    h, w = gray.shape[:2]
    pad_y = max(1, int(h * 0.10))
    pad_x = max(1, int(w * 0.10))

    border_mask = np.ones((h, w), dtype=bool)
    border_mask[pad_y : h - pad_y, pad_x : w - pad_x] = False

    border_pixels = gray[border_mask]
    if len(border_pixels) == 0:
        return 0.0

    black_border_fraction = float(np.mean(border_pixels < threshold))
    return black_border_fraction


def check_image_quality(
    image: Union[np.ndarray, str, Path, Image.Image],
    min_width: int = MIN_WIDTH,
    min_height: int = MIN_HEIGHT,
    min_blur_var: float = MIN_LAPLACIAN_VAR,
) -> Dict[str, Any]:
    """
    Run comprehensive quality control checks on a retinal image.

    Args:
        image: File path, PIL Image, or numpy array [H, W, 3] or [H, W].
        min_width: Minimum acceptable image width.
        min_height: Minimum acceptable image height.
        min_blur_var: Minimum acceptable Laplacian variance (sharpness).

    Returns:
        Dict conforming to Phase 5 schema:
        {
          "passed": bool,
          "issues": list of str,
          "unreadable": bool,
          "metrics": {
              "width": int,
              "height": int,
              "channels": int,
              "mean_brightness": float,
              "contrast_std": float,
              "blur_score": float,
              "fov_ratio": float,
              "border_ratio": float,
              "saturated_ratio": float,
              "overall_quality_score": float
          }
        }
    """
    issues: List[str] = []
    unreadable = False

    # 1. Load / Convert to numpy array
    if isinstance(image, (str, Path)):
        p = Path(image)
        if not p.exists():
            return {
                "passed": False,
                "issues": [f"File does not exist: {image}"],
                "unreadable": True,
                "metrics": {},
            }
        try:
            pil_img = Image.open(p).convert("RGB")
            arr = np.array(pil_img)
        except Exception as e:
            return {
                "passed": False,
                "issues": [f"Unreadable image file: {e}"],
                "unreadable": True,
                "metrics": {},
            }
    elif isinstance(image, Image.Image):
        arr = np.array(image.convert("RGB"))
    elif isinstance(image, np.ndarray):
        arr = image.copy()
    else:
        return {
            "passed": False,
            "issues": [f"Unsupported image type: {type(image).__name__}"],
            "unreadable": True,
            "metrics": {},
        }

    # Ensure correct dtype
    if arr.dtype != np.uint8:
        if arr.max() <= 1.0:
            arr = (arr * 255.0).clip(0, 255).astype(np.uint8)
        else:
            arr = arr.clip(0, 255).astype(np.uint8)

    # 2. Dimensions and channels
    if arr.ndim == 2:
        h, w = arr.shape
        c = 1
        gray = arr
    elif arr.ndim == 3:
        h, w, c = arr.shape
        if c == 1:
            gray = arr[:, :, 0]
        elif c >= 3:
            gray = (
                0.299 * arr[:, :, 0]
                + 0.587 * arr[:, :, 1]
                + 0.114 * arr[:, :, 2]
            ).astype(np.uint8)
        else:
            gray = arr[:, :, 0]
    else:
        return {
            "passed": False,
            "issues": [f"Invalid array dimension: {arr.ndim}D"],
            "unreadable": True,
            "metrics": {},
        }

    if w < min_width or h < min_height:
        issues.append(f"Image resolution too small: {w}x{h} (minimum {min_width}x{min_height})")

    # 3. Completely blank / uniform check
    intensity_min = float(np.min(gray))
    intensity_max = float(np.max(gray))
    if intensity_min == intensity_max:
        unreadable = True
        issues.append(f"Uniform/blank image (all pixels = {intensity_min})")
        return {
            "passed": False,
            "issues": issues,
            "unreadable": True,
            "metrics": {
                "width": int(w),
                "height": int(h),
                "channels": int(c),
                "mean_brightness": intensity_min,
                "contrast_std": 0.0,
                "blur_score": 0.0,
                "fov_ratio": 0.0,
                "border_ratio": 1.0,
                "saturated_ratio": 0.0,
                "overall_quality_score": 0.0,
            },
        }

    # 4. Brightness and contrast
    mean_val = float(np.mean(gray))
    std_val = float(np.std(gray))

    if mean_val < MIN_BRIGHTNESS:
        issues.append(f"Severe underexposure: mean brightness {mean_val:.1f} < {MIN_BRIGHTNESS}")
    elif mean_val > MAX_BRIGHTNESS:
        issues.append(f"Severe overexposure: mean brightness {mean_val:.1f} > {MAX_BRIGHTNESS}")

    if std_val < MIN_CONTRAST_STD:
        issues.append(f"Extremely low contrast: intensity std {std_val:.1f} < {MIN_CONTRAST_STD}")

    # 5. Blur / Focus measurement
    blur_score = _compute_laplacian_variance(gray)
    if blur_score < min_blur_var:
        issues.append(f"Image blurred or out of focus: Laplacian variance {blur_score:.1f} < {min_blur_var}")

    # 6. Field of View (FOV) detection
    fov_mask, fov_ratio = estimate_fov_mask(arr)
    if fov_ratio < MIN_FOV_COVERAGE:
        issues.append(f"Insufficient retinal FOV coverage: {fov_ratio * 100:.1f}% < {MIN_FOV_COVERAGE * 100:.1f}%")

    # 7. Excessive black borders
    border_ratio = _calculate_border_ratio(arr)
    if border_ratio > MAX_BORDER_RATIO and fov_ratio < 0.35:
        issues.append(f"Excessive black borders: {border_ratio * 100:.1f}% > {MAX_BORDER_RATIO * 100:.1f}% (FOV ratio {fov_ratio * 100:.1f}%)")

    # 8. Artifact / Glare detection inside FOV
    if fov_ratio > 0.05:
        fov_pixels = gray[fov_mask]
        saturated_ratio = float(np.mean(fov_pixels >= 250))
    else:
        saturated_ratio = float(np.mean(gray >= 250))

    if saturated_ratio > MAX_SATURATED_RATIO:
        issues.append(f"Specular reflection/glare artifact: {saturated_ratio * 100:.1f}% saturated pixels in FOV")

    # 9. Overall Quality Score (0 to 1)
    norm_blur = min(blur_score / 150.0, 1.0)
    norm_contrast = min(std_val / 50.0, 1.0)
    norm_brightness = 1.0 - abs(mean_val - 128.0) / 128.0
    overall_quality_score = float(np.clip(
        0.4 * norm_blur + 0.3 * norm_contrast + 0.3 * norm_brightness, 0.0, 1.0
    ))

    # Mark unreadable if multiple critical failures occur
    critical_issues = [
        issue for issue in issues
        if "Severe underexposure" in issue
        or "Severe overexposure" in issue
        or "Uniform/blank" in issue
        or "Insufficient retinal FOV" in issue
    ]
    if len(critical_issues) >= 2 or mean_val < 5.0 or mean_val > 250.0:
        unreadable = True

    passed = len(issues) == 0

    return {
        "passed": passed,
        "issues": issues,
        "unreadable": unreadable,
        "metrics": {
            "width": int(w),
            "height": int(h),
            "channels": int(c),
            "mean_brightness": round(mean_val, 2),
            "contrast_std": round(std_val, 2),
            "blur_score": round(blur_score, 2),
            "fov_ratio": round(fov_ratio, 4),
            "border_ratio": round(border_ratio, 4),
            "saturated_ratio": round(saturated_ratio, 4),
            "overall_quality_score": round(overall_quality_score, 4),
        },
    }
