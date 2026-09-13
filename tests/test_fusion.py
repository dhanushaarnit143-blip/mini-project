"""
Unit and Integration Tests for Phase 6 Multimodal Prodromal Fusion (MPF-PD).

Tests verify:
1. Fusion dataset builder detects missing modalities and generates presence flags.
2. Participant-level splitting is strictly disjoint (no train/val/test participant overlap).
3. Gated fusion forward pass produces fixed-size representation and gate weights.
4. Inference works with all modalities present.
5. Inference works with one modality missing.
6. Inference works with multiple modalities missing.
7. Inference handles all-modalities-missing gracefully without crashing.
8. Output risk score is strictly bounded in [0.0, 1.0].
9. Metadata JSON and evaluation JSON conform to required schema and contain no clinical claims.
"""

import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import torch

from src.fusion.dataset import (
    build_multimodal_dataset,
    generate_synthetic_multimodal_fixture,
    split_multimodal_dataset,
    check_true_multimodal_data_availability,
    MODALITIES,
)
from src.fusion.gates import LearnableMissingToken, ModalityGate
from src.fusion.gated_fusion import GatedMultimodalFusion
from src.fusion.predict import predict_fusion
from src.fusion.evaluate import compute_binary_metrics, compare_auc_significance


class TestMultimodalDataset:
    """Verify dataset generation, presence flags, and participant splitting."""

    def test_true_multimodal_availability_check(self):
        is_real, reason = check_true_multimodal_data_availability()
        assert is_real is False, "True same-participant multimodal data should not be claimed as real."
        assert "PROTOTYPE SIMULATION" in reason or "disparate" in reason

    def test_fixture_generation_presence_flags(self):
        df = generate_synthetic_multimodal_fixture(n_participants=50, seed=42)
        assert len(df) == 50
        for mod in MODALITIES:
            flag_col = f"{mod}_present"
            assert flag_col in df.columns
            # Presence flags must be strictly binary
            assert set(df[flag_col].unique()).issubset({0, 1})

    def test_missing_modality_induces_nan(self):
        df = generate_synthetic_multimodal_fixture(n_participants=100, seed=42)
        # For rows where olfactory_present == 0, total_score must be NaN
        missing_olf = df[df["olfactory_present"] == 0]
        if len(missing_olf) > 0:
            assert missing_olf["total_score"].isna().all()

    def test_participant_level_split_disjoint(self):
        df = generate_synthetic_multimodal_fixture(n_participants=100, seed=42)
        df_train, df_val, df_test = split_multimodal_dataset(df, seed=42)

        p_train = set(df_train["participant_id"])
        p_val = set(df_val["participant_id"])
        p_test = set(df_test["participant_id"])

        # Strict disjointness
        assert len(p_train.intersection(p_val)) == 0, "Leakage between train and val!"
        assert len(p_train.intersection(p_test)) == 0, "Leakage between train and test!"
        assert len(p_val.intersection(p_test)) == 0, "Leakage between val and test!"
        assert len(p_train) + len(p_val) + len(p_test) == len(df["participant_id"].unique())


class TestGatingArchitecture:
    """Verify neural gating and missing token components."""

    def test_learnable_missing_token_forward(self):
        token_mod = LearnableMissingToken(embedding_dim=16, seed=42)
        emb = torch.randn(2, 16)
        pres = torch.tensor([[1.0], [0.0]])  # Sample 0 present, Sample 1 absent

        out = token_mod(emb, pres)
        assert out.shape == (2, 16)
        # Sample 0 should match original emb
        assert torch.allclose(out[0], emb[0], atol=1e-5)
        # Sample 1 should match missing token parameter
        assert torch.allclose(out[1], token_mod.missing_token.squeeze(0), atol=1e-5)

    def test_modality_gate_attention(self):
        gate = ModalityGate(embedding_dim=16, n_modalities=5, mechanism="gated_attention", seed=42)
        emb = torch.randn(2, 5, 16)
        pres = torch.tensor([[1.0, 1.0, 1.0, 1.0, 1.0], [1.0, 0.0, 1.0, 0.0, 0.0]])

        fused, weights = gate(emb, pres)
        assert fused.shape == (2, 16)
        assert weights.shape == (2, 5)

        # Weights must sum to 1.0 along modality dimension
        assert torch.allclose(weights.sum(dim=-1), torch.ones(2), atol=1e-4)

        # For sample 1, masked modalities (idx 1, 3, 4) should receive zero or near-zero attention
        assert weights[1, 1].item() < 1e-4
        assert weights[1, 3].item() < 1e-4
        assert weights[1, 4].item() < 1e-4

    def test_gated_multimodal_fusion_fixed_size(self):
        mod_dims = {"olfactory": 5, "rbd": 16, "voice": 16, "motor": 8, "retina": 28}
        fusion_net = GatedMultimodalFusion(modality_dims=mod_dims, embedding_dim=32, demo_dim=3, seed=42)

        B = 4
        inputs = {m: torch.randn(B, mod_dims[m]) for m in MODALITIES}
        pres = torch.ones(B, 5)
        demo = torch.randn(B, 3)

        probs, fused_emb, gate_w = fusion_net(inputs, pres, demo)

        assert probs.shape == (B, 1)
        assert (probs >= 0.0).all() and (probs <= 1.0).all()
        # Fused embedding dimension = 32 (modality) + 8 (demo) + 5 (presence) = 45
        assert fused_emb.shape == (B, 45)
        assert gate_w.shape == (B, 5)


class TestInferencePipeline:
    """Verify predict_fusion with various missing modality permutations."""

    @pytest.fixture(autouse=True)
    def ensure_trained_model(self):
        from src.fusion.train import run_fusion_pipeline
        model_path = Path("models/fusion/classifier.joblib")
        if not model_path.exists():
            run_fusion_pipeline()

    def test_predict_all_modalities_present(self):
        inputs = {
            "olfactory": {"total_score": 32.0, "response_time_mean": 3.1},
            "rbd": {"rbdsq_total": 2.0, "above_cutoff_flag": 0.0},
            "voice": {"jitter_pct": 0.003, "shimmer": 0.02, "hnr": 24.0},
            "motor": {"gait_speed_m_per_s": 1.3, "cadence_steps_per_min": 112.0},
            "retina": {"vessel_density": 0.08, "mean_vessel_diameter_px": 3.4},
            "age": 62,
            "sex": "female",
        }
        res = predict_fusion(inputs)

        assert "risk_score" in res
        assert 0.0 <= res["risk_score"] <= 1.0
        assert len(res["fused_embedding"]) == 45
        assert all(res["modality_presence"].values())
        assert len(res["gate_weights"]) == 5
        assert res["experiment_type"] == "prototype_simulation"

    def test_predict_one_modality_missing(self):
        # Missing retina
        inputs = {
            "olfactory": {"total_score": 22.0},
            "rbd": {"rbdsq_total": 8.0},
            "voice": {"jitter_pct": 0.008},
            "motor": {"gait_speed_m_per_s": 0.9},
            "retina": None,
            "age": 71,
            "sex": "male",
        }
        res = predict_fusion(inputs)

        assert 0.0 <= res["risk_score"] <= 1.0
        assert res["modality_presence"]["retina"] is False
        assert res["modality_presence"]["olfactory"] is True
        assert any("retina" in w.lower() for w in res["warnings"])

    def test_predict_multiple_modalities_missing(self):
        # Only olfactory and RBD present (typical initial clinic visit)
        inputs = {
            "olfactory": {"total_score": 20.0},
            "rbd": {"rbdsq_total": 9.0},
            "age": 68,
            "sex": "male",
        }
        res = predict_fusion(inputs)

        assert 0.0 <= res["risk_score"] <= 1.0
        assert res["modality_presence"]["olfactory"] is True
        assert res["modality_presence"]["rbd"] is True
        assert res["modality_presence"]["voice"] is False
        assert res["modality_presence"]["motor"] is False
        assert res["modality_presence"]["retina"] is False

    def test_predict_all_modalities_missing(self):
        # Uninformative input
        inputs = {
            "age": 65,
            "sex": "female",
        }
        res = predict_fusion(inputs)

        assert res["risk_score"] == 0.5
        assert all(not p for p in res["modality_presence"].values())
        assert any("ALL modalities are missing" in w for w in res["warnings"])


class TestScientificHonestyAndArtifacts:
    """Verify strictly non-clinical metadata and evaluation outputs."""

    def test_evaluation_json_schema_and_honesty(self):
        eval_path = Path("evaluation/fusion_results.json")
        assert eval_path.exists(), "evaluation/fusion_results.json must exist."

        with open(eval_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["phase"] == 6
        assert data["clinical_claim"] is False
        assert data["experiment_type"] == "prototype_simulation"
        assert data["same_participant_multimodal"] is False
        assert "models_compared" in data
        assert "metrics" in data

        expected_models = [
            "olfactory_only",
            "rbd_only",
            "voice_only",
            "motor_only",
            "retina_only",
            "concatenation",
            "weighted_average",
            "gated_fusion",
        ]
        for m in expected_models:
            assert m in data["models_compared"]
            assert m in data["metrics"]

    def test_model_metadata_honesty(self):
        meta_path = Path("models/fusion/metadata.json")
        assert meta_path.exists(), "models/fusion/metadata.json must exist."

        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["clinical_claim"] is False
        assert data["experiment_type"] == "prototype_simulation"
        assert len(data["limitations"]) > 0
        assert data["model_type"] == "gated_multimodal_fusion"
