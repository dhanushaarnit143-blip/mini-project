"""
Unit tests for the MPF-PD Voice Pipeline (src/voice).

All audio used in tests is SYNTHETIC and clearly labeled.
No real patient data is used or generated here.

Tests cover:
  1. Audio loader handles missing file gracefully.
  2. Quality check detects silence and too-short audio.
  3. Feature extractor returns expected keys.
  4. Prediction output has required schema.
  5. Model output is in [0, 1].
  6. Participant split has no overlap.
  7. Pipeline runs and produces artifacts (simulation mode).
  8. Predict voice with tabular features.
  9. Predict voice with missing features → warnings issued.
"""

import json
import math
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

# ─── preprocess (load + synthetic audio helpers) ──────────────────────────────
from src.voice.preprocess import (
    load_audio,
    preprocess_audio,
    generate_synthetic_audio,
    generate_silent_audio,
    TARGET_SR,
)

# ─── quality ──────────────────────────────────────────────────────────────────
from src.voice.quality import check_audio_quality, QUALITY_DEFAULTS

# ─── features ─────────────────────────────────────────────────────────────────
from src.voice.features import (
    extract_tabular_voice_features,
    extract_spectral_features,
    TABULAR_FEATURE_NAMES,
    SPECTRAL_FEATURE_NAMES,
)

# ─── train + predict ──────────────────────────────────────────────────────────
from src.voice.train import (
    run_voice_pipeline,
    split_voice_data,
    _generate_synthetic_voice_fixture,
)
from src.voice.predict import predict_voice

# ─── validators ───────────────────────────────────────────────────────────────
from src.data.validators import validate_participant_split


# ══════════════════════════════════════════════════════════════════════════════
# 1. Audio loader — missing file
# ══════════════════════════════════════════════════════════════════════════════

class TestAudioLoader:

    def test_missing_file_returns_none(self):
        """Loader must return (None, 0) for non-existent file."""
        audio, sr = load_audio("non_existent_audio_file_that_does_not_exist.wav")
        assert audio is None
        assert sr == 0

    def test_missing_file_does_not_raise(self):
        """Loader must not raise an exception for a missing file."""
        try:
            load_audio("/completely/fake/path/audio.wav")
        except Exception as exc:
            pytest.fail(f"load_audio raised unexpected exception: {exc}")

    def test_synthetic_audio_loads_correctly(self, tmp_path):
        """Synthetic WAV written to tmp_path loads correctly."""
        import soundfile as sf
        audio = generate_synthetic_audio(duration_sec=2.0, sr=TARGET_SR, seed=42)
        wav_path = tmp_path / "test_synth.wav"
        sf.write(str(wav_path), audio, TARGET_SR)

        loaded, sr = load_audio(str(wav_path), target_sr=TARGET_SR)
        assert loaded is not None
        assert sr == TARGET_SR
        assert len(loaded) > 0
        assert loaded.dtype == np.float32


# ══════════════════════════════════════════════════════════════════════════════
# 2. Quality checks
# ══════════════════════════════════════════════════════════════════════════════

class TestAudioQuality:

    def test_none_audio_fails_quality(self):
        """None audio array must fail quality check."""
        result = check_audio_quality(None, sr=TARGET_SR)
        assert result["passed"] is False
        assert len(result["issues"]) > 0

    def test_silent_audio_fails_quality(self):
        """Near-silent audio must fail quality check."""
        silent = generate_silent_audio(duration_sec=2.0, sr=TARGET_SR)
        result = check_audio_quality(silent, sr=TARGET_SR)
        # Should fail: either low RMS energy or high silence ratio
        assert result["passed"] is False
        assert len(result["issues"]) > 0

    def test_too_short_audio_fails_quality(self):
        """Audio shorter than min_duration must fail."""
        # Generate 0.1 second audio — below the 1.0 second minimum
        short_audio = generate_synthetic_audio(duration_sec=0.1, sr=TARGET_SR, seed=0)
        result = check_audio_quality(short_audio, sr=TARGET_SR)
        assert result["passed"] is False
        duration_issues = [i for i in result["issues"] if "Duration" in i or "duration" in i]
        assert len(duration_issues) > 0

    def test_valid_synthetic_audio_passes_quality(self):
        """A well-formed synthetic audio of 2+ seconds must pass all checks."""
        audio = generate_synthetic_audio(duration_sec=3.0, sr=TARGET_SR, seed=42)
        result = check_audio_quality(audio, sr=TARGET_SR)
        assert result["passed"] is True
        assert result["issues"] == []

    def test_quality_metrics_populated(self):
        """Quality result dict must include duration_sec and silence_ratio."""
        audio = generate_synthetic_audio(duration_sec=2.0, sr=TARGET_SR, seed=42)
        result = check_audio_quality(audio, sr=TARGET_SR)
        assert "duration_sec" in result["metrics"]
        assert "silence_ratio" in result["metrics"]
        assert "rms_energy" in result["metrics"]
        assert "zero_crossing_rate" in result["metrics"]

    def test_clipping_detection(self):
        """Audio with many saturated samples must trigger clipping warning/fail."""
        # Create an audio signal that is mostly saturated at 1.0
        audio = generate_synthetic_audio(duration_sec=2.0, sr=TARGET_SR, seed=42)
        # Force severe clipping: set 50% of samples to 0.99+
        audio_clipped = audio.copy()
        audio_clipped[::2] = 1.0  # Every other sample at maximum amplitude
        result = check_audio_quality(audio_clipped, sr=TARGET_SR)
        # Clipping ratio = ~50% >> max_clipping_ratio 1%
        assert result["metrics"].get("clipping_ratio", 0) > QUALITY_DEFAULTS["max_clipping_ratio"]


# ══════════════════════════════════════════════════════════════════════════════
# 3. Feature extractor — expected keys
# ══════════════════════════════════════════════════════════════════════════════

class TestFeatureExtraction:

    def test_tabular_features_expected_keys(self):
        """Tabular feature extractor must return all expected UCI column names."""
        df = _generate_synthetic_voice_fixture(n_participants=5, seed=42)
        feat = extract_tabular_voice_features(df)
        for col in TABULAR_FEATURE_NAMES:
            assert col in feat.columns, f"Missing tabular feature column: {col}"
        assert len(feat) == len(df)

    def test_tabular_features_numeric(self):
        """All extracted tabular features must be numeric."""
        df = _generate_synthetic_voice_fixture(n_participants=5, seed=42)
        feat = extract_tabular_voice_features(df)
        for col in feat.columns:
            assert pd.api.types.is_numeric_dtype(feat[col]), \
                f"Column '{col}' is not numeric."

    def test_tabular_features_missing_cols_filled_nan(self):
        """Missing UCI columns must yield NaN, not raise an error."""
        # Empty DataFrame with no UCI feature columns
        df_empty = pd.DataFrame({"participant_id": [1, 2]})
        feat = extract_tabular_voice_features(df_empty)
        assert set(feat.columns) == set(TABULAR_FEATURE_NAMES)
        # All values should be NaN since no source columns exist
        assert feat.isnull().all().all()

    def test_spectral_features_expected_keys(self):
        """Spectral feature extractor must return all expected keys."""
        audio = generate_synthetic_audio(duration_sec=2.0, sr=TARGET_SR, seed=42)
        feat = extract_spectral_features(audio, sr=TARGET_SR)
        for key in SPECTRAL_FEATURE_NAMES:
            assert key in feat, f"Missing spectral feature key: {key}"

    def test_spectral_features_finite(self):
        """All spectral features must be finite floats (no inf) for valid audio."""
        audio = generate_synthetic_audio(duration_sec=2.0, sr=TARGET_SR, seed=42)
        feat = extract_spectral_features(audio, sr=TARGET_SR)
        for key, val in feat.items():
            assert math.isfinite(val), f"Feature '{key}' is not finite: {val}"


# ══════════════════════════════════════════════════════════════════════════════
# 4 & 5. Prediction output schema + model output [0, 1]
# ══════════════════════════════════════════════════════════════════════════════

class TestVoicePrediction:

    @pytest.fixture(autouse=True)
    def train_pipeline(self):
        """Ensure a model artifact exists before prediction tests run."""
        run_voice_pipeline(data_path="non_existent_path.csv", seed=42)

    def test_predict_required_schema_tabular(self):
        """Prediction output must have all required schema keys."""
        features = {name: 0.1 for name in TABULAR_FEATURE_NAMES}
        result = predict_voice(tabular_features=features)

        required_keys = [
            "modality", "risk_score", "embedding",
            "model_version", "features_used", "quality", "warnings"
        ]
        for key in required_keys:
            assert key in result, f"Prediction output missing required key: '{key}'"

    def test_predict_modality_is_voice(self):
        """Prediction modality must always be 'voice'."""
        features = {name: 0.1 for name in TABULAR_FEATURE_NAMES}
        result = predict_voice(tabular_features=features)
        assert result["modality"] == "voice"

    def test_predict_risk_score_in_range(self):
        """Risk score must be in [0.0, 1.0]."""
        features = {name: 0.1 for name in TABULAR_FEATURE_NAMES}
        result = predict_voice(tabular_features=features)
        assert result["risk_score"] is not None
        assert 0.0 <= result["risk_score"] <= 1.0

    def test_predict_embedding_is_list(self):
        """Embedding must be a list of floats."""
        features = {name: 0.1 for name in TABULAR_FEATURE_NAMES}
        result = predict_voice(tabular_features=features)
        assert isinstance(result["embedding"], list)
        assert len(result["embedding"]) > 0
        for val in result["embedding"]:
            assert isinstance(val, float)

    def test_predict_missing_features_issues_warnings(self):
        """Missing features must issue warnings (not silently return wrong score)."""
        # Provide only a subset of features
        partial_features = {"jitter_pct": 0.01, "hnr": 25.0}
        result = predict_voice(tabular_features=partial_features)
        # Must still return a score (imputed)
        assert result["risk_score"] is not None
        assert 0.0 <= result["risk_score"] <= 1.0
        # Must warn about missing features
        assert len(result["warnings"]) > 0

    def test_predict_no_input_raises(self):
        """predict_voice() with no arguments must raise RuntimeError."""
        with pytest.raises(RuntimeError):
            predict_voice()

    def test_predict_missing_model_raises(self):
        """predict_voice() with a non-existent model path must raise FileNotFoundError."""
        features = {name: 0.1 for name in TABULAR_FEATURE_NAMES}
        with pytest.raises(FileNotFoundError):
            predict_voice(tabular_features=features, model_path="/fake/model.joblib")

    def test_predict_audio_missing_file(self):
        """predict_voice with a missing audio file: quality check must fail gracefully."""
        result = predict_voice(audio_file="non_existent_recording.wav")
        assert result["quality"]["passed"] is False
        assert result["risk_score"] is None

    def test_predict_simulation_warning_present(self):
        """Simulation mode prediction must include warning about synthetic data."""
        features = {name: 0.1 for name in TABULAR_FEATURE_NAMES}
        result = predict_voice(tabular_features=features)
        all_warnings = " ".join(result["warnings"]).lower()
        # Either simulation warning OR research prototype warning must be present
        assert "synthetic" in all_warnings or "research prototype" in all_warnings or "investigational" in all_warnings


# ══════════════════════════════════════════════════════════════════════════════
# 6. Participant split — no overlap
# ══════════════════════════════════════════════════════════════════════════════

class TestParticipantSplit:

    def test_split_no_participant_overlap(self):
        """Train, val, and test splits must have zero participant ID overlap."""
        df = _generate_synthetic_voice_fixture(n_participants=60, seed=42)
        df_with_label = df.copy()
        df_with_label["diagnosis"] = df["_synthetic_label"].astype(int)

        df_train, df_val, df_test = split_voice_data(
            df_with_label, test_size=0.2, val_size=0.2, seed=42
        )

        train_ids = set(df_train["participant_id"].unique())
        val_ids = set(df_val["participant_id"].unique())
        test_ids = set(df_test["participant_id"].unique())

        assert train_ids.isdisjoint(val_ids), "Train and val share participants!"
        assert train_ids.isdisjoint(test_ids), "Train and test share participants!"
        assert val_ids.isdisjoint(test_ids), "Val and test share participants!"

    def test_split_all_participants_assigned(self):
        """Every participant must appear in exactly one split."""
        df = _generate_synthetic_voice_fixture(n_participants=60, seed=42)
        df["diagnosis"] = df["_synthetic_label"].astype(int)

        df_train, df_val, df_test = split_voice_data(
            df, test_size=0.15, val_size=0.15, seed=42
        )

        all_pids = set(df["participant_id"].unique())
        assigned_pids = (
            set(df_train["participant_id"].unique())
            | set(df_val["participant_id"].unique())
            | set(df_test["participant_id"].unique())
        )
        assert all_pids == assigned_pids, "Some participants are missing from splits!"

    def test_validate_participant_split_function(self):
        """The shared validate_participant_split utility must pass for disjoint sets."""
        train_ids = ["P001", "P002", "P003"]
        val_ids = ["P004", "P005"]
        test_ids = ["P006", "P007"]
        assert validate_participant_split(train_ids, val_ids, test_ids) is True

    def test_validate_participant_split_raises_on_overlap(self):
        """validate_participant_split must raise ValueError on overlapping IDs."""
        with pytest.raises((ValueError, AssertionError)):
            validate_participant_split(["P001", "P002"], ["P002", "P003"], ["P004"])


# ══════════════════════════════════════════════════════════════════════════════
# 7. Full pipeline — simulation mode artifacts
# ══════════════════════════════════════════════════════════════════════════════

class TestVoicePipelineArtifacts:

    def test_pipeline_runs_in_simulation_mode(self):
        """Pipeline must complete without error in simulation mode."""
        result = run_voice_pipeline(data_path="non_existent_path.csv", seed=42)
        assert result["experiment_type"] == "simulation"
        assert result["best_model"] in [
            "logistic_regression", "svm", "random_forest", "xgboost"
        ]
        assert 0.0 <= result["best_val_score"] <= 1.0

    def test_pipeline_creates_model_artifact(self):
        """Pipeline must save model.joblib artifact."""
        run_voice_pipeline(data_path="non_existent_path.csv", seed=42)
        assert Path("models/voice/model.joblib").exists()

    def test_pipeline_creates_metadata(self):
        """Pipeline must save metadata.json with required keys."""
        run_voice_pipeline(data_path="non_existent_path.csv", seed=42)
        meta_path = Path("models/voice/metadata.json")
        assert meta_path.exists()
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        required_keys = [
            "modality", "model_type", "dataset_id", "dataset_category",
            "features_used", "target_label", "training_participants",
            "validation_participants", "test_participants",
            "metrics", "seed", "timestamp", "limitations", "clinical_claim",
        ]
        for key in required_keys:
            assert key in meta, f"Metadata missing key: '{key}'"

        assert meta["modality"] == "voice"
        assert meta["clinical_claim"] is False

    def test_pipeline_creates_evaluation_json(self):
        """Pipeline must save evaluation/voice_results.json."""
        run_voice_pipeline(data_path="non_existent_path.csv", seed=42)
        eval_path = Path("evaluation/voice_results.json")
        assert eval_path.exists()

        with open(eval_path, "r", encoding="utf-8") as f:
            ev = json.load(f)

        assert ev["phase"] == 3
        assert ev["modality"] == "voice"
        assert ev["experiment_type"] == "simulation"
        assert "best_model" in ev
        assert "metrics" in ev
        assert "features_used" in ev
        assert "quality_checks" in ev
        assert "limitations" in ev
        assert "artifact_paths" in ev

    def test_metadata_no_clinical_claim(self):
        """Metadata must explicitly assert clinical_claim=False."""
        run_voice_pipeline(data_path="non_existent_path.csv", seed=42)
        with open("models/voice/metadata.json", "r", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["clinical_claim"] is False

    def test_simulation_mode_limitations_documented(self):
        """Simulation mode must document limitations including synthetic data warning."""
        run_voice_pipeline(data_path="non_existent_path.csv", seed=42)
        with open("models/voice/metadata.json", "r", encoding="utf-8") as f:
            meta = json.load(f)
        limitations_text = " ".join(meta["limitations"]).lower()
        assert "synthetic" in limitations_text or "simulation" in limitations_text
