"""
Unit and Integration Tests for Retinal Analysis Pipeline (Phase 5).

Verifies:
  1. Image loader handles valid arrays, PIL images, and invalid file paths.
  2. Quality Control (QC) detects blank/black images, low contrast, and blur.
  3. Preprocessing returns standardized shapes and normalized tensors.
  4. Vessel segmentation functions (classical and U-Net) produce valid masks.
  5. Quantitative vascular biomarker extractor returns numeric outputs.
  6. CNN encoder generates fixed-length embeddings (128-D / 256-D).
  7. predict_retina() returns exact required schema and handles edge cases.
  8. End-to-end evaluation produces valid retina_results.json.

All test images are small synthetic fixtures (Category E) strictly for software testing.
"""

import json
from pathlib import Path
import numpy as np
import pytest
import torch
from PIL import Image

from src.retina.quality import check_image_quality
from src.retina.preprocess import (
    load_retinal_image,
    preprocess_retina,
    extract_green_channel,
    apply_clahe,
    DEFAULT_IMAGE_SIZE,
)
from src.retina.segmentation import (
    segment_retinal_vessels,
    segment_vessels_classical,
    UNetVesselSegmentation,
)
from src.retina.vessel_features import (
    extract_vessel_features,
    RETINA_FEATURE_NAMES,
)
from src.retina.encoder import RetinalCNNEncoder
from src.retina.predict import predict_retina
from src.retina.train import (
    create_synthetic_fundus_fixture,
    train_vessel_segmentation,
    pretrain_retinal_encoder,
    evaluate_pd_retina,
    train_retinal_pipeline,
)
from src.retina.evaluate import run_retina_evaluation


@pytest.fixture
def synthetic_fundus_image(tmp_path: Path) -> Path:
    """Generate a clean synthetic fundus image saved as a PNG file."""
    img_path = tmp_path / "test_fundus.png"
    create_synthetic_fundus_fixture(output_path=img_path, size=(256, 256))
    return img_path


@pytest.fixture
def solid_black_image(tmp_path: Path) -> Path:
    """Generate an unreadable solid black image."""
    img_path = tmp_path / "black_defect.png"
    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    Image.fromarray(arr).save(img_path)
    return img_path


@pytest.fixture
def solid_white_image(tmp_path: Path) -> Path:
    """Generate an unreadable solid white image."""
    img_path = tmp_path / "white_defect.png"
    arr = np.full((256, 256, 3), 255, dtype=np.uint8)
    Image.fromarray(arr).save(img_path)
    return img_path


# ─────────────────────────────────────────────────────────────────────────────
# 1. Image Loader Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_image_loader_invalid_path():
    """Verify image loader raises FileNotFoundError on non-existent path."""
    with pytest.raises(FileNotFoundError):
        load_retinal_image("non_existent_retina_image_99999.png")


def test_image_loader_valid_inputs(synthetic_fundus_image: Path):
    """Verify loading from Path, str, PIL Image, and numpy array."""
    # From Path
    arr1 = load_retinal_image(synthetic_fundus_image)
    assert isinstance(arr1, np.ndarray)
    assert arr1.ndim == 3
    assert arr1.shape[2] == 3
    assert arr1.dtype == np.uint8

    # From string
    arr2 = load_retinal_image(str(synthetic_fundus_image))
    assert np.array_equal(arr1, arr2)

    # From PIL Image
    pil_img = Image.open(synthetic_fundus_image)
    arr3 = load_retinal_image(pil_img)
    assert np.array_equal(arr1, arr3)

    # From Grayscale array
    gray_arr = arr1[:, :, 1]
    arr4 = load_retinal_image(gray_arr)
    assert arr4.shape == (256, 256, 3)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Quality Control (QC) Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_qc_detects_solid_black_image(solid_black_image: Path):
    """Verify QC flags solid black images as unreadable and failing."""
    qc = check_image_quality(solid_black_image)
    assert qc["passed"] is False
    assert qc["unreadable"] is True
    assert any("blank" in issue.lower() or "underexposure" in issue.lower() for issue in qc["issues"])


def test_qc_detects_solid_white_image(solid_white_image: Path):
    """Verify QC flags solid white images as failing."""
    qc = check_image_quality(solid_white_image)
    assert qc["passed"] is False
    assert qc["unreadable"] is True
    assert any("blank" in issue.lower() or "overexposure" in issue.lower() for issue in qc["issues"])


def test_qc_detects_small_dimensions():
    """Verify QC flags images below minimum acceptable resolution."""
    tiny_img = np.full((64, 64, 3), 128, dtype=np.uint8)
    qc = check_image_quality(tiny_img, min_width=128, min_height=128)
    assert qc["passed"] is False
    assert any("small" in issue.lower() for issue in qc["issues"])


def test_qc_synthetic_fundus_fixture(synthetic_fundus_image: Path):
    """Verify valid synthetic fundus fixture passes QC."""
    qc = check_image_quality(synthetic_fundus_image)
    assert "metrics" in qc
    assert "blur_score" in qc["metrics"]
    assert "mean_brightness" in qc["metrics"]
    assert "fov_ratio" in qc["metrics"]
    assert qc["metrics"]["fov_ratio"] > 0.15


# ─────────────────────────────────────────────────────────────────────────────
# 3. Preprocessing Pipeline Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_preprocessing_returns_expected_shapes(synthetic_fundus_image: Path):
    """Verify preprocessing standardizes shapes and channels."""
    target_size = (224, 224)
    prep = preprocess_retina(synthetic_fundus_image, target_size=target_size)

    assert "rgb_image" in prep
    assert "green_enhanced" in prep
    assert "fov_mask" in prep
    assert "tensor" in prep

    assert prep["rgb_image"].shape == (224, 224, 3)
    assert prep["green_enhanced"].shape == (224, 224)
    assert prep["fov_mask"].shape == (224, 224)
    assert prep["fov_mask"].dtype == bool
    assert prep["tensor"].shape == (3, 224, 224)
    assert isinstance(prep["tensor"], torch.Tensor)


def test_green_channel_and_clahe():
    """Verify green channel extraction and CLAHE contrast enhancement."""
    rgb = np.zeros((100, 100, 3), dtype=np.uint8)
    rgb[:, :, 1] = 120  # green channel
    green = extract_green_channel(rgb)
    assert green.shape == (100, 100)
    assert green[0, 0] == 120

    enhanced = apply_clahe(green)
    assert enhanced.shape == (100, 100)
    assert enhanced.dtype == np.uint8


# ─────────────────────────────────────────────────────────────────────────────
# 4. Vessel Segmentation Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_classical_vessel_segmentation(synthetic_fundus_image: Path):
    """Verify classical morphological vessel segmentation heuristic."""
    arr = load_retinal_image(synthetic_fundus_image)
    res = segment_vessels_classical(arr)

    assert "vessel_mask" in res
    assert "fov_mask" in res
    assert "vessel_pixel_count" in res
    assert res["vessel_mask"].shape == arr.shape[:2]
    assert res["vessel_mask"].dtype == bool
    assert res["is_learned_model"] is False
    assert res["vessel_pixel_count"] >= 0


def test_unet_vessel_segmentation():
    """Verify U-Net baseline architecture instantiation and forward pass."""
    unet = UNetVesselSegmentation(in_channels=1, out_channels=1, features=(8, 16, 32))
    unet.eval()

    sample_tensor = torch.rand(1, 1, 128, 128)
    with torch.no_grad():
        out = unet(sample_tensor)

    assert out.shape == (1, 1, 128, 128)
    assert (out >= 0.0).all() and (out <= 1.0).all()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Vascular Biomarker Extractor Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_vessel_feature_extractor_returns_numeric_outputs():
    """Verify vessel biomarker extractor returns all required numeric features."""
    # Create synthetic binary vessel mask
    h, w = 200, 200
    vessel_mask = np.zeros((h, w), dtype=bool)
    fov_mask = np.zeros((h, w), dtype=bool)
    # Circle FOV
    y, x = np.ogrid[:h, :w]
    fov_mask[(x - 100) ** 2 + (y - 100) ** 2 <= 80 ** 2] = True
    # Curvilinear vessel lines
    vessel_mask[100, 40:160] = True
    vessel_mask[60:140, 100] = True

    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[fov_mask] = (180, 70, 20)

    features = extract_vessel_features(vessel_mask, fov_mask=fov_mask, rgb_image=rgb)

    for name in RETINA_FEATURE_NAMES:
        assert name in features, f"Missing feature: {name}"

    assert isinstance(features["vessel_density"], float)
    assert 0.0 <= features["vessel_density"] <= 1.0
    assert isinstance(features["mean_vessel_diameter_px"], float)
    assert features["mean_vessel_diameter_px"] >= 0.0
    assert isinstance(features["vessel_tortuosity_index"], float)
    assert features["vessel_tortuosity_index"] >= 1.0
    assert isinstance(features["branch_count"], int)
    assert features["branch_count"] >= 1  # Cross has at least 1 branch point


def test_vessel_feature_extractor_empty_mask():
    """Verify feature extractor handles empty mask without crashing."""
    empty_mask = np.zeros((100, 100), dtype=bool)
    features = extract_vessel_features(empty_mask)

    assert features["vessel_density"] == 0.0
    assert features["branch_count"] == 0
    assert features["mean_vessel_diameter_px"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 6. CNN Feature Encoder Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_cnn_encoder_fixed_embedding():
    """Verify CNN encoder generates fixed-length embeddings with expected dimensions."""
    for dim in [64, 128]:
        encoder = RetinalCNNEncoder(backbone="resnet18", embedding_dim=dim, pretrained=False)
        tensor = torch.randn(1, 3, 224, 224)
        emb = encoder.extract_embedding(tensor)

        assert isinstance(emb, np.ndarray)
        assert emb.shape == (dim,)
        assert np.isfinite(emb).all()

    # Verify metadata contains honesty checks
    meta = encoder.get_metadata()
    assert meta["clinical_claim"] is False
    assert meta["pd_trained"] is False
    assert "limitations" in meta


# ─────────────────────────────────────────────────────────────────────────────
# 7. predict_retina API Interface Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_predict_retina_valid_fixture(synthetic_fundus_image: Path):
    """Verify predict_retina returns exact Phase 5 required schema on valid fixture."""
    res = predict_retina(str(synthetic_fundus_image), embedding_dim=128)

    assert res["modality"] == "retina"
    assert isinstance(res["embedding"], list)
    assert len(res["embedding"]) == 128
    assert "quality" in res
    assert "passed" in res["quality"]
    assert "issues" in res["quality"]
    assert "vessel_features" in res
    assert "model_version" in res
    assert res["pd_trained"] is False
    assert isinstance(res["warnings"], list)
    assert any("Research prototype" in w for w in res["warnings"])


def test_predict_retina_non_existent_file():
    """Verify predict_retina handles non-existent file gracefully without crashing."""
    res = predict_retina("invalid_path_to_fundus_9999.png", embedding_dim=128)

    assert res["modality"] == "retina"
    assert res["quality"]["passed"] is False
    assert res["vessel_features"] == {}
    assert len(res["embedding"]) == 128
    assert any("not found" in issue.lower() for issue in res["quality"]["issues"])


def test_predict_retina_qc_failure_aborts_extraction(solid_black_image: Path):
    """Verify predict_retina does NOT force feature extraction on QC failure."""
    res = predict_retina(str(solid_black_image), embedding_dim=128, allow_qc_bypass=False)

    assert res["quality"]["passed"] is False
    assert res["vessel_features"] == {}  # Not forced!
    assert any("aborted due to qc failure" in w.lower() for w in res["warnings"])


# ─────────────────────────────────────────────────────────────────────────────
# 8. Evaluation Artifact Generation Test
# ─────────────────────────────────────────────────────────────────────────────

def test_evaluation_artifact_generation(tmp_path: Path):
    """Verify run_retina_evaluation generates valid Phase 5 JSON report."""
    results_path = tmp_path / "retina_results.json"
    results = run_retina_evaluation(output_path=str(results_path))

    assert results_path.exists()
    assert results["phase"] == 5
    assert results["modality"] == "retina"
    assert results["dataset_type"] in ["pretraining", "feature_extraction", "pd_specific", "simulation"]
    assert results["experiment_type"] in ["real_data", "prototype"]
    assert "regimes" in results
    assert "retinal_pretraining" in results["regimes"]
    assert "vessel_segmentation_training" in results["regimes"]
    assert "pd_specific_evaluation" in results["regimes"]
    assert "image_quality" in results
    assert "segmentation" in results
    assert "vessel_features" in results
    assert "encoder" in results
    assert "metrics" in results
    assert "limitations" in results
    assert len(results["limitations"]) > 0
    assert "artifact_paths" in results


# ─────────────────────────────────────────────────────────────────────────────
# 9. Separated Regimes & Scientific Integrity Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_vessel_segmentation_training_routine(tmp_path: Path):
    """Verify train_vessel_segmentation executes and produces weights without claiming PD diagnosis."""
    weights_path = tmp_path / "test_unet_weights.pth"
    res = train_vessel_segmentation(
        output_weights_path=str(weights_path),
        epochs=1,
    )

    assert weights_path.exists()
    assert res["task"] == "vessel_segmentation_training"
    assert res["is_pd_model"] is False
    assert "NOT a PD diagnosis model" in res["disclaimer"]


def test_retinal_pretraining_routine_and_integrity(tmp_path: Path):
    """Verify pretrain_retinal_encoder saves weights and enforces non-PD disclaimer for DR data."""
    weights_path = tmp_path / "test_encoder_pretrained.pt"
    res = pretrain_retinal_encoder(
        output_weights_path=str(weights_path),
        epochs=1,
        is_diabetic_retinopathy_data=True,
    )

    assert weights_path.exists()
    assert res["task"] == "retinal_encoder_pretraining"
    assert res["pd_trained"] is False
    assert res["clinical_claim"] is False
    assert "Diabetic retinopathy data is NOT Parkinson's data" in res["scientific_integrity_rule"]


def test_pd_specific_evaluation_refuses_fabrication_when_absent(tmp_path: Path):
    """Verify evaluate_pd_retina does NOT fabricate metrics when authentic PD cohort is unavailable."""
    report_path = tmp_path / "pd_eval_absent.json"
    res = evaluate_pd_retina(pd_data_path=None, test_cohort=None, output_path=report_path)

    assert report_path.exists()
    assert res["pd_cohort_available"] is False
    assert res["evaluation_status"] == "no_authentic_pd_cohort_available"
    assert res["metrics"]["pd_roc_auc"] is None
    assert res["metrics"]["pd_sensitivity"] is None
    assert "Diabetic retinopathy data is NOT Parkinson's data" in res["scientific_integrity_statement"]


def test_pd_specific_evaluation_with_cohort(tmp_path: Path):
    """Verify evaluate_pd_retina evaluates properly when a true cohort is provided."""
    report_path = tmp_path / "pd_eval_cohort.json"
    # Provide synthetic mock cohort
    cohort = [
        {"subject_id": "SUBJ_001", "label": 1},
        {"subject_id": "SUBJ_002", "label": 0},
        {"subject_id": "SUBJ_003", "label": 1},
        {"subject_id": "SUBJ_004", "label": 0},
    ]
    res = evaluate_pd_retina(test_cohort=cohort, output_path=report_path)

    assert report_path.exists()
    assert res["pd_cohort_available"] is True
    assert res["evaluation_status"] == "cohort_evaluated"
    assert res["sample_size"] == 4
    assert res["participant_isolation"] is True
    assert res["metrics"]["pd_roc_auc"] is not None

