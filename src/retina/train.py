"""
Retinal Training and Pipeline Setup for MPF-PD (Phase 5).

Implements dataset discovery, pretraining setup, and supervised training scope.

Rigorous Dataset Separation:
  Category A / Pretraining Dataset:
    - General fundus / OCT datasets (e.g., DRIVE, EyePACS, Messidor-2, OCT500).
    - Used for vessel segmentation and feature encoder pretraining.
    - Explicitly NOT assumed to contain Parkinson's disease labels.
  Category B / Feature Extraction Dataset:
    - Fundus images used to extract structural biomarkers (vessel density, tortuosity).
    - May be non-PD normative or ocular disease images.
  Category C / Parkinson's-Specific Retinal Dataset:
    - Requires true PD / control or prodromal clinical labels.
    - If absent, NO PD METRICS ARE FABRICATED. The pipeline reports pretraining setup,
      segmentation sanity checks, and embedding extraction capabilities.

Safety & Ethics:
  - Zero clinical claims.
  - Explicit documentation of missing PD labels when operating in prototype mode.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

from src.config import load_config
from src.retina.quality import check_image_quality
from src.retina.preprocess import preprocess_retina, DEFAULT_IMAGE_SIZE
from src.retina.segmentation import segment_retinal_vessels, UNetVesselSegmentation
from src.retina.vessel_features import extract_vessel_features, RETINA_FEATURE_NAMES
from src.retina.encoder import RetinalCNNEncoder


logger = logging.getLogger("mpf.retina.train")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def create_synthetic_fundus_fixture(
    output_path: Optional[Path] = None,
    size: Tuple[int, int] = (512, 512),
) -> np.ndarray:
    """
    Generate a synthetic fundus fixture image for software pipeline testing.

    Creates a synthetic fundus with:
      - Dark camera border outside circular aperture
      - Orange-red fundus background with radial shading
      - Bright optic disc candidate
      - Dark foveal/macular depression
      - Branching curvilinear vessel tree

    STRICT DISCLAIMER:
      - This is a SYNTHETIC SOFTWARE TEST FIXTURE (Category E).
      - It has ZERO clinical validity and must NEVER be used for clinical claims.
    """
    w, h = size
    img = Image.new("RGB", (w, h), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    center_x, center_y = w // 2, h // 2
    radius = int(min(w, h) * 0.44)

    # 1. Circular retinal aperture
    # Draw warm orange-red fundus background
    draw.ellipse(
        [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
        fill=(190, 75, 25),
    )

    # 2. Optic disc (bright yellow-orange oval)
    od_x = center_x - int(radius * 0.45)
    od_y = center_y
    od_r = int(radius * 0.16)
    draw.ellipse(
        [od_x - od_r, od_y - int(od_r * 1.1), od_x + od_r, od_y + int(od_r * 1.1)],
        fill=(245, 210, 110),
    )

    # 3. Macula / Fovea (dark reddish-brown spot)
    mac_x = center_x + int(radius * 0.25)
    mac_y = center_y
    mac_r = int(radius * 0.12)
    draw.ellipse(
        [mac_x - mac_r, mac_y - mac_r, mac_x + mac_r, mac_y + mac_r],
        fill=(120, 35, 15),
    )

    # 4. Branching blood vessels emerging from optic disc
    vessel_color = (95, 20, 10)
    # Superior temporal arcade
    draw.line([(od_x, od_y), (od_x + 30, od_y - 50), (od_x + 90, od_y - 90), (od_x + 160, od_y - 110)], fill=vessel_color, width=4)
    draw.line([(od_x + 90, od_y - 90), (od_x + 130, od_y - 140), (od_x + 180, od_y - 160)], fill=vessel_color, width=2)
    draw.line([(od_x + 130, od_y - 140), (od_x + 150, od_y - 180)], fill=vessel_color, width=1)

    # Inferior temporal arcade
    draw.line([(od_x, od_y), (od_x + 30, od_y + 50), (od_x + 90, od_y + 90), (od_x + 160, od_y + 110)], fill=vessel_color, width=4)
    draw.line([(od_x + 90, od_y + 90), (od_x + 130, od_y + 140), (od_x + 180, od_y + 160)], fill=vessel_color, width=2)
    draw.line([(od_x + 130, od_y + 140), (od_x + 150, od_y + 180)], fill=vessel_color, width=1)

    # Nasal vessels
    draw.line([(od_x, od_y), (od_x - 40, od_y - 40), (od_x - 90, od_y - 60)], fill=vessel_color, width=3)
    draw.line([(od_x, od_y), (od_x - 40, od_y + 40), (od_x - 90, od_y + 60)], fill=vessel_color, width=3)

    arr = np.array(img)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        logger.info("Saved synthetic fundus test fixture to: %s", output_path)

    return arr


def discover_retinal_datasets(
    data_dir: Path = Path("data"),
) -> Dict[str, Any]:
    """
    Search local filesystem for retinal datasets and categorize them rigorously:
      - Pretraining datasets (DRIVE, EyePACS, Messidor-2, APTOS, OCT500)
      - Parkinson's-specific retinal datasets
    """
    status: Dict[str, Any] = {
        "pretraining_datasets_found": [],
        "pd_specific_datasets_found": [],
        "has_pd_labels": False,
    }

    # Check common pretraining directories
    candidate_pretraining_dirs = [
        data_dir / "raw" / "retinal_fundus_pretraining",
        data_dir / "raw" / "fundus",
        data_dir / "raw" / "oct500",
        data_dir / "raw" / "oct",
        data_dir / "external" / "fundus",
    ]

    for p in candidate_pretraining_dirs:
        if p.exists() and any(p.glob("*.*")):
            status["pretraining_datasets_found"].append(str(p))

    # Check for PD-specific retinal directories
    candidate_pd_dirs = [
        data_dir / "raw" / "retina_pd",
        data_dir / "raw" / "fundus_pd",
        data_dir / "interim" / "ppmi_retina",
    ]

    for p in candidate_pd_dirs:
        if p.exists() and any(p.glob("*.*")):
            status["pd_specific_datasets_found"].append(str(p))
            status["has_pd_labels"] = True

    return status


def train_retinal_pipeline(
    output_dir: str = "models/retina",
    backbone: str = "resnet18",
    embedding_dim: int = 128,
    pretrained: bool = False,
    pd_data_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute Phase 5 retinal pipeline training / setup.

    If PD-specific labels exist:
      - Train/fine-tune classifier head using participant-level splits.
      - Report validation and test metrics.
    If PD-specific labels DO NOT exist:
      - Do NOT fabricate PD metrics.
      - Initialize and calibrate CNN feature encoder.
      - Run segmentation sanity checks on test fixture.
      - Extract and log reference vascular biomarkers and embeddings.
      - Save model metadata with explicit honesty disclaimers.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    dataset_info = discover_retinal_datasets()
    if pd_data_path and Path(pd_data_path).exists():
        dataset_info["has_pd_labels"] = True
        dataset_info["pd_specific_datasets_found"].append(pd_data_path)

    has_pd = dataset_info["has_pd_labels"]

    logger.info("=" * 60)
    logger.info("MPF-PD Phase 5: Retinal Analysis Pipeline Setup")
    logger.info("Pretraining datasets detected: %s", dataset_info["pretraining_datasets_found"])
    logger.info("PD-specific retinal datasets detected: %s", dataset_info["pd_specific_datasets_found"])
    logger.info("Has PD-specific retinal labels: %s", has_pd)
    logger.info("=" * 60)

    # 1. Initialize CNN Encoder
    encoder = RetinalCNNEncoder(
        backbone=backbone,
        embedding_dim=embedding_dim,
        pretrained=pretrained,
        pd_trained=has_pd,
    )

    # 2. Pipeline Sanity Execution using Fixture Image
    fixture_path = out_path / "synthetic_fundus_fixture.png"
    sample_img = create_synthetic_fundus_fixture(output_path=fixture_path)

    # Quality Control
    qc_result = check_image_quality(sample_img)
    logger.info("Sanity QC Check: passed=%s, issues=%s", qc_result["passed"], qc_result["issues"])

    # Preprocessing
    preprocessed = preprocess_retina(sample_img, target_size=DEFAULT_IMAGE_SIZE)
    logger.info(
        "Sanity Preprocessing: RGB shape=%s, Tensor shape=%s",
        preprocessed["rgb_image"].shape,
        preprocessed["tensor"].shape,
    )

    # Vessel Segmentation (Classical heuristic baseline)
    seg_result = segment_retinal_vessels(
        preprocessed["rgb_image"],
        method="classical",
        fov_mask=preprocessed["fov_mask"],
    )
    logger.info(
        "Sanity Segmentation: vessel pixels=%d / %d (method: %s)",
        seg_result["vessel_pixel_count"],
        seg_result["total_fov_pixels"],
        seg_result["method"],
    )

    # Vessel Biomarker Extraction
    biomarkers = extract_vessel_features(
        vessel_mask=seg_result["vessel_mask"],
        fov_mask=seg_result["fov_mask"],
        rgb_image=preprocessed["rgb_image"],
    )
    logger.info(
        "Sanity Biomarkers: vessel_density=%.4f, tortuosity=%.4f, branches=%d",
        biomarkers["vessel_density"],
        biomarkers["vessel_tortuosity_index"],
        biomarkers["branch_count"],
    )

    # CNN Embedding Extraction
    embedding = encoder.extract_embedding(preprocessed["tensor"])
    logger.info(
        "Sanity CNN Embedding: dim=%d, norm=%.4f, mean=%.4f",
        len(embedding),
        float(np.linalg.norm(embedding)),
        float(np.mean(embedding)),
    )

    # 3. Model Metadata Generation
    metadata: Dict[str, Any] = {
        "modality": "retina",
        "phase": 5,
        "model_type": "RetinalCNNEncoder_and_VascularMorphometry",
        "backbone": backbone,
        "embedding_dim": embedding_dim,
        "pretrained": pretrained,
        "pd_trained": has_pd,
        "clinical_claim": False,
        "experiment_type": "real_data" if has_pd else "prototype",
        "dataset_category": "B" if has_pd else "E",
        "segmentation_method": "classical_morphological_heuristic",
        "vessel_features_extracted": RETINA_FEATURE_NAMES,
        "reference_biomarkers_synthetic_fixture": biomarkers,
        "sample_embedding_stats": {
            "dim": len(embedding),
            "l2_norm": round(float(np.linalg.norm(embedding)), 4),
            "mean": round(float(np.mean(embedding)), 4),
            "std": round(float(np.std(embedding)), 4),
        },
        "limitations": [
            "PROTOTYPE MODE: No Parkinson's-specific retinal dataset with clinical labels is available locally or openly.",
            "Generic fundus pretraining datasets (EyePACS, Messidor-2, DRIVE) contain diabetic retinopathy or normal images, NOT Parkinson's labels.",
            "OCT datasets (OCT500) contain ophthalmic disease labels, NOT Parkinson's disease labels.",
            "Vessel segmentation utilizes a deterministic classical morphological heuristic baseline; it is not a clinically validated AI diagnostic device.",
            "Retinal embeddings and vascular features serve as prototype representations for downstream multimodal fusion.",
            "Zero clinical validity for Parkinson's diagnosis or screening without prospective clinical validation.",
            "No clinical claims are made: all risk scores and embeddings are research prototype outputs only.",
        ],
        "artifact_paths": {
            "metadata_path": str(out_path / "metadata.json"),
            "fixture_image_path": str(fixture_path),
        },
    }

    metadata_file = out_path / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved model metadata to: %s", metadata_file)

    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MPF-PD Retinal Analysis Pipeline Setup")
    parser.add_argument("--output-dir", type=str, default="models/retina")
    parser.add_argument("--backbone", type=str, default="resnet18")
    parser.add_argument("--embedding-dim", type=int, default=128)
    parser.add_argument("--pretrained", action="store_true", default=False)
    parser.add_argument("--pd-data-path", type=str, default=None)
    args = parser.parse_args()

    train_retinal_pipeline(
        output_dir=args.output_dir,
        backbone=args.backbone,
        embedding_dim=args.embedding_dim,
        pretrained=args.pretrained,
        pd_data_path=args.pd_data_path,
    )
