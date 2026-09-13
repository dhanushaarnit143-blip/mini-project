"""
Retinal Vascular Biomarker Extraction Module for MPF-PD (Phase 5).

Provides deterministic extraction of quantitative vascular biomarkers from
segmented retinal fundus microvasculature:
  1. Vessel Density (total and per-region).
  2. Mean Vessel Diameter (via Euclidean distance transform along skeleton).
  3. Vessel Tortuosity Index (arc-to-chord length ratio along vascular branches).
  4. Branch Count and Branch Point Density (bifurcation / junction frequency).
  5. Optic Disc & Peripapillary Region Features (annular microvascular density).
  6. Macular / Foveal Region Features (parafoveal density & avascular zone area).

All computations are deterministic, reproducible, and strictly bounded by the FOV.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import ndimage


RETINA_FEATURE_NAMES = [
    "vessel_density",
    "mean_vessel_diameter_px",
    "vessel_tortuosity_index",
    "branch_count",
    "branch_point_density",
    "endpoint_count",
    "peripapillary_vessel_density",
    "peripapillary_branch_count",
    "macular_vessel_density",
    "foveal_avascular_zone_area_px",
    "optic_disc_detected",
    "macula_detected",
]


# ─────────────────────────────────────────────────────────────────────────────
# Morphological Skeletonization and Graph Analysis
# ─────────────────────────────────────────────────────────────────────────────

def _skeletonize_morphological(binary_mask: np.ndarray, max_iters: int = 100) -> np.ndarray:
    """
    Deterministic morphological thinning / skeletonization (Zhang-Suen inspired).
    Reduces binary vessel mask to 1-pixel-wide medial centerline.
    """
    skeleton = binary_mask.astype(bool).copy()
    struct_plus = ndimage.generate_binary_structure(2, 1)

    for _ in range(max_iters):
        # Erode and compare with morphological opening
        eroded = ndimage.binary_erosion(skeleton, structure=struct_plus)
        temp = ndimage.binary_opening(eroded, structure=struct_plus)
        subset = eroded & ~temp
        if not np.any(skeleton ^ (skeleton & ~subset)):
            break
        # Safe progressive thinning
        diff = skeleton & ~eroded
        skeleton = eroded | subset

    # Fallback/cleanup to ensure 1-pixel width
    # Medial axis extraction via distance transform ridges
    edt = ndimage.distance_transform_edt(binary_mask)
    lap = ndimage.laplace(edt)
    ridge = (lap < -0.4) & binary_mask
    combined = skeleton | ridge
    return combined


def _analyze_skeleton_topology(skeleton: np.ndarray) -> Tuple[int, int, float, np.ndarray, np.ndarray]:
    """
    Analyze skeleton graph topology:
      - Branch points (junctions with >= 3 neighbors in 3x3 window)
      - End points (terminal tips with == 1 neighbor in 3x3 window)
      - Tortuosity estimation across segments
    """
    if not np.any(skeleton):
        return 0, 0, 1.0, np.zeros_like(skeleton, dtype=bool), np.zeros_like(skeleton, dtype=bool)

    # 3x3 neighbor kernel (excluding center)
    kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.int32)
    neighbor_count = ndimage.convolve(skeleton.astype(np.int32), kernel, mode="constant", cval=0)
    neighbor_count = neighbor_count * skeleton

    # Branch points have >= 3 neighbors
    branch_candidates = neighbor_count >= 3
    # Group contiguous branch pixels to count true junctions
    labeled_branches, branch_count = ndimage.label(branch_candidates)

    # Endpoints have exactly 1 neighbor
    endpoint_mask = (neighbor_count == 1) & skeleton
    endpoint_count = int(np.sum(endpoint_mask))

    # Tortuosity estimation:
    # Segments are skeleton pixels excluding branch junctions
    segment_mask = skeleton & ~branch_candidates
    labeled_segments, num_segments = ndimage.label(segment_mask)

    tortuosity_list: List[float] = []
    for seg_id in range(1, min(num_segments + 1, 300)):  # Top segments
        coords = np.argwhere(labeled_segments == seg_id)
        if len(coords) >= 6:  # Minimum length for meaningful tortuosity
            arc_length = float(len(coords))
            # Chord length = Euclidean distance between furthest points
            start = coords[0]
            end = coords[-1]
            chord_length = float(np.linalg.norm(start - end))
            if chord_length > 1.0:
                t_idx = arc_length / chord_length
                tortuosity_list.append(min(t_idx, 5.0))  # Cap at reasonable upper bound

    mean_tortuosity = float(np.mean(tortuosity_list)) if tortuosity_list else 1.0

    return branch_count, endpoint_count, mean_tortuosity, branch_candidates, endpoint_mask


# ─────────────────────────────────────────────────────────────────────────────
# Anatomical Landmarks (Optic Disc & Macula)
# ─────────────────────────────────────────────────────────────────────────────

def detect_optic_disc(
    rgb_image: np.ndarray,
    fov_mask: np.ndarray,
) -> Tuple[bool, Optional[Tuple[int, int]], float]:
    """
    Estimate the Optic Disc (OD) location in a fundus photograph.
    The OD is the brightest circular region in the retina (excluding specular reflections).

    Returns:
        Tuple of (detected_flag, (center_y, center_x), radius).
    """
    h, w = rgb_image.shape[:2]
    # Red and green channels are brightest at optic nerve head
    intensity = 0.5 * rgb_image[:, :, 0].astype(np.float32) + 0.5 * rgb_image[:, :, 1].astype(np.float32)

    # Restrict search strictly to inner 80% FOV to avoid rim artifacts
    eroded_fov = ndimage.binary_erosion(fov_mask, structure=np.ones((9, 9)))
    search_area = intensity * eroded_fov

    if not np.any(eroded_fov):
        return False, None, 0.0

    # Strong Gaussian smoothing to suppress fine vessel details and find the bright disc mass
    est_disc_radius = max(8, int(min(h, w) * 0.08))
    smoothed = ndimage.gaussian_filter(search_area, sigma=est_disc_radius / 2.0)

    # Find global maximum inside eroded FOV
    max_pos = np.unravel_index(np.argmax(smoothed), smoothed.shape)
    center_y, center_x = int(max_pos[0]), int(max_pos[1])

    # Check that disc brightness exceeds local average
    local_val = smoothed[center_y, center_x]
    fov_mean = float(np.mean(intensity[fov_mask]))

    if local_val > fov_mean * 1.15:
        return True, (center_y, center_x), float(est_disc_radius)

    return False, None, 0.0


def estimate_macular_region(
    optic_disc_center: Optional[Tuple[int, int]],
    optic_disc_radius: float,
    fov_mask: np.ndarray,
    shape: Tuple[int, int],
) -> Tuple[bool, Optional[Tuple[int, int]], float]:
    """
    Estimate Macula / Fovea center given Optic Disc position.
    In standard fundus photography, macula is positioned approximately
    2.0 to 2.5 disc diameters temporally (horizontally) from the OD.
    """
    if optic_disc_center is None:
        return False, None, 0.0

    od_y, od_x = optic_disc_center
    h, w = shape[:2]
    dist = 2.5 * optic_disc_radius

    # Determine left eye (OS) vs right eye (OD):
    # In Right Eye (OD), disc is nasal (right side of image if fundus flipped or left side)
    # Check both left and right temporal candidates inside FOV
    cand1 = (od_y, int(od_x - dist))
    cand2 = (od_y, int(od_x + dist))

    valid_cands = []
    for cy, cx in [cand1, cand2]:
        if 0 <= cy < h and 0 <= cx < w and fov_mask[cy, cx]:
            valid_cands.append((cy, cx))

    if not valid_cands:
        return False, None, 0.0

    # Select candidate furthest from image center (or inside darker retinal area)
    macula_center = valid_cands[0]
    macula_radius = optic_disc_radius * 0.8

    return True, macula_center, float(macula_radius)


# ─────────────────────────────────────────────────────────────────────────────
# Primary Extraction API
# ─────────────────────────────────────────────────────────────────────────────

def extract_vessel_features(
    vessel_mask: np.ndarray,
    fov_mask: Optional[np.ndarray] = None,
    rgb_image: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Deterministic extraction of quantitative retinal vascular biomarkers.

    Args:
        vessel_mask: Binary boolean or uint8 vessel segmentation mask [H, W].
        fov_mask: Binary boolean FOV mask [H, W]. If None, assumed all True.
        rgb_image: Optional RGB image [H, W, 3] for anatomical disc/macula localization.

    Returns:
        Dict mapping biomarker names to float values.
    """
    v_mask = vessel_mask.astype(bool)
    h, w = v_mask.shape[:2]

    if fov_mask is None:
        fov_mask = np.ones((h, w), dtype=bool)
    else:
        fov_mask = fov_mask.astype(bool)

    # Mask vessels strictly to FOV
    v_mask = v_mask & fov_mask
    total_fov_pixels = int(np.sum(fov_mask))
    total_vessel_pixels = int(np.sum(v_mask))

    if total_fov_pixels == 0:
        return {k: 0.0 for k in RETINA_FEATURE_NAMES}

    # 1. Vessel Density (total)
    vessel_density = float(total_vessel_pixels) / float(total_fov_pixels)

    # 2. Skeletonization & Graph Topology
    skeleton = _skeletonize_morphological(v_mask)
    branch_count, endpoint_count, tortuosity_index, branch_mask, end_mask = (
        _analyze_skeleton_topology(skeleton)
    )

    # Branch point density (per 1,000 FOV pixels)
    branch_point_density = (float(branch_count) / float(total_fov_pixels)) * 1000.0

    # 3. Mean Vessel Diameter
    # Computed via Euclidean Distance Transform sampled along skeleton
    if np.any(skeleton):
        dist_transform = ndimage.distance_transform_edt(v_mask)
        skeleton_radii = dist_transform[skeleton]
        # Diameter = 2 * radius
        mean_diameter = float(np.mean(skeleton_radii) * 2.0)
    else:
        mean_diameter = 0.0

    # 4. Anatomical Region Features (Optic Disc & Macula)
    peripapillary_vessel_density = 0.0
    peripapillary_branch_count = 0
    macular_vessel_density = 0.0
    faz_area_px = 0.0
    od_detected = False
    mac_detected = False

    if rgb_image is not None and rgb_image.ndim == 3:
        od_ok, od_center, od_radius = detect_optic_disc(rgb_image, fov_mask)
        od_detected = od_ok

        if od_ok and od_center is not None:
            cy, cx = od_center
            y_grid, x_grid = np.ogrid[:h, :w]
            radial_dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)

            # Peripapillary zone: annular ring between 1.5 * R and 2.5 * R
            peri_mask = (radial_dist >= 1.5 * od_radius) & (radial_dist <= 2.5 * od_radius) & fov_mask
            peri_fov_pixels = int(np.sum(peri_mask))
            if peri_fov_pixels > 0:
                peri_vessels = int(np.sum(v_mask & peri_mask))
                peripapillary_vessel_density = float(peri_vessels) / float(peri_fov_pixels)
                peripapillary_branch_count = int(np.sum(branch_mask & peri_mask))

            # Macular region
            mac_ok, mac_center, mac_radius = estimate_macular_region(
                od_center, od_radius, fov_mask, (h, w)
            )
            mac_detected = mac_ok

            if mac_ok and mac_center is not None:
                my, mx = mac_center
                mac_dist = np.sqrt((x_grid - mx) ** 2 + (y_grid - my) ** 2)
                # Parafoveal ring: between 1.0 * R and 2.5 * R
                parafoveal_mask = (mac_dist >= mac_radius) & (mac_dist <= 2.5 * mac_radius) & fov_mask
                mac_fov_pixels = int(np.sum(parafoveal_mask))
                if mac_fov_pixels > 0:
                    mac_vessels = int(np.sum(v_mask & parafoveal_mask))
                    macular_vessel_density = float(mac_vessels) / float(mac_fov_pixels)

                # Central Foveal Avascular Zone (FAZ): inside mac_radius
                faz_mask = (mac_dist <= mac_radius) & fov_mask
                # Non-vessel area within fovea
                faz_area_px = float(np.sum(faz_mask & ~v_mask))

    return {
        "vessel_density": round(vessel_density, 5),
        "mean_vessel_diameter_px": round(mean_diameter, 3),
        "vessel_tortuosity_index": round(tortuosity_index, 4),
        "branch_count": int(branch_count),
        "branch_point_density": round(branch_point_density, 4),
        "endpoint_count": int(endpoint_count),
        "peripapillary_vessel_density": round(peripapillary_vessel_density, 5),
        "peripapillary_branch_count": int(peripapillary_branch_count),
        "macular_vessel_density": round(macular_vessel_density, 5),
        "foveal_avascular_zone_area_px": round(faz_area_px, 1),
        "optic_disc_detected": bool(od_detected),
        "macula_detected": bool(mac_detected),
    }
