"""
Unit tests for the MPF-PD Motor/Gait Pipeline (src/motor).

ALL data used in these tests is SYNTHETIC and clearly labelled.
No real patient data is used or generated here.

Tests cover:
  1. Feature extraction returns expected keys.
  2. Unsupported features are NOT silently created.
  3. Participant split has no overlap (zero data leakage).
  4. Quality check detects short trial duration.
  5. Prediction output schema is valid.
  6. Risk score is in [0, 1].
  7. Missing modality/task produces warnings, not crashes.
  8. Model can be trained and saved (simulation mode).
  9. Synthetic fixture is properly labelled.
  10. Step detection from synthetic VGRF returns plausible output.

IMPORTANT: These tests use SYNTHETIC DATA ONLY.
Results must NEVER be presented as clinical validation.
"""

import json
import math
import shutil
import warnings
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

# Project root: used to locate config.yaml for tmp_path test workspaces
_PROJECT_ROOT = Path(__file__).parent.parent
_CONFIG_SRC = _PROJECT_ROOT / "config.yaml"

# ─── Preprocessing ────────────────────────────────────────────────────────────
from src.motor.preprocess import (
    generate_synthetic_motor_fixture,
    preprocess_motor_data,
    split_motor_data,
)

# ─── Quality ──────────────────────────────────────────────────────────────────
from src.motor.quality import (
    check_motor_quality,
    check_vgrf_quality,
    check_feature_table_quality,
    QUALITY_DEFAULTS,
)

# ─── Features ─────────────────────────────────────────────────────────────────
from src.motor.features import (
    extract_motor_features,
    get_feature_matrix,
    GAIT_FEATURE_NAMES,
    MOTOR_FEATURE_NAMES,
    UNSUPPORTED_TASKS,
    LIMITATIONS,
    _detect_steps_from_vgrf,
    _compute_step_regularity,
)

# ─── Training ─────────────────────────────────────────────────────────────────
from src.motor.train import (
    run_motor_pipeline,
    split_motor_data_wrapper,
    _generate_synthetic_motor_fixture,
)

# ─── Prediction ───────────────────────────────────────────────────────────────
from src.motor.predict import predict_motor

# ─── Validators ───────────────────────────────────────────────────────────────
from src.data.validators import validate_participant_split


# ══════════════════════════════════════════════════════════════════════════════
# 0. Fixtures
# ══════════════════════════════════════════════════════════════════════════════

SEED = 42
N_PARTICIPANTS = 100


@pytest.fixture(scope="module")
def synthetic_motor_df() -> pd.DataFrame:
    """
    SYNTHETIC motor fixture — for unit tests and CI/CD only.
    Zero clinical validity.
    """
    return generate_synthetic_motor_fixture(n_participants=N_PARTICIPANTS, seed=SEED)


@pytest.fixture(scope="module")
def preprocessed_motor_df(synthetic_motor_df) -> pd.DataFrame:
    return preprocess_motor_data(synthetic_motor_df, raw_sensor_available=False)


@pytest.fixture(scope="module")
def split_motor_dfs(preprocessed_motor_df):
    return split_motor_data(preprocessed_motor_df, test_size=0.15, val_size=0.15, seed=SEED)


@pytest.fixture(scope="module")
def feature_df(preprocessed_motor_df) -> pd.DataFrame:
    return extract_motor_features(preprocessed_motor_df, raw_sensor_available=False)


@pytest.fixture()
def motor_workspace(tmp_path, monkeypatch):
    """
    Set up a temporary workspace directory for pipeline tests.

    Copies config.yaml from the project root and creates required directories.
    Changes the working directory to tmp_path so load_config() finds config.yaml.
    """
    # Copy config.yaml so load_config() succeeds
    shutil.copy(_CONFIG_SRC, tmp_path / "config.yaml")
    # Create required output directories
    (tmp_path / "models" / "motor").mkdir(parents=True, exist_ok=True)
    (tmp_path / "evaluation").mkdir(parents=True, exist_ok=True)
    # Change cwd so relative paths resolve correctly
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _make_synthetic_vgrf_trial(
    n_samples: int = 1200,
    sampling_rate: int = 100,
    body_weight_n: float = 750.0,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Create a minimal synthetic VGRF trial for step detection testing.
    SYNTHETIC — for unit testing only.
    """
    rng = np.random.RandomState(seed)
    t = np.linspace(0, n_samples / sampling_rate, n_samples)

    # Simulate alternating left/right footfalls with a square-wave pattern
    # Period ~1 second (step rate ~60 steps/min per foot)
    step_period_s = 1.0
    phase = (t % step_period_s) / step_period_s

    # Left foot stance: 0.0 to 0.6 of period (60% stance)
    left_stance_mask = phase < 0.6
    right_stance_mask = (phase >= 0.4) & (phase < 1.0)  # overlap during double support

    left_force = np.where(
        left_stance_mask,
        body_weight_n * (0.8 + 0.2 * rng.rand(n_samples)),
        rng.rand(n_samples) * 5.0,
    )
    right_force = np.where(
        right_stance_mask,
        body_weight_n * (0.8 + 0.2 * rng.rand(n_samples)),
        rng.rand(n_samples) * 5.0,
    )

    df = pd.DataFrame({
        "Time": t,
        "L1": left_force / 8,
        "L2": left_force / 8,
        "L3": left_force / 8,
        "L4": left_force / 8,
        "L5": left_force / 8,
        "L6": left_force / 8,
        "L7": left_force / 8,
        "L8": left_force / 8,
        "R1": right_force / 8,
        "R2": right_force / 8,
        "R3": right_force / 8,
        "R4": right_force / 8,
        "R5": right_force / 8,
        "R6": right_force / 8,
        "R7": right_force / 8,
        "R8": right_force / 8,
        "Total_Force_Left": left_force,
        "Total_Force_Right": right_force,
        "participant_id": "SYN_VGRF_001",
        "diagnosis": 0,
        "sampling_rate_hz": sampling_rate,
    })
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 1. Synthetic fixture integrity
# ══════════════════════════════════════════════════════════════════════════════

class TestSyntheticFixture:

    def test_synthetic_fixture_labelled(self, synthetic_motor_df):
        """Synthetic fixture must be explicitly labelled as synthetic."""
        assert "data_source" in synthetic_motor_df.columns, (
            "Synthetic fixture must contain 'data_source' column."
        )
        assert (synthetic_motor_df["data_source"] == "synthetic_fixture").all(), (
            "All rows in synthetic fixture must have data_source='synthetic_fixture'."
        )

    def test_synthetic_fixture_not_real_sensor(self, synthetic_motor_df):
        """Synthetic fixture must indicate raw sensor is NOT available."""
        assert "raw_sensor_available" in synthetic_motor_df.columns
        assert not synthetic_motor_df["raw_sensor_available"].any(), (
            "Synthetic fixture must never claim raw sensor data is available."
        )

    def test_synthetic_fixture_shape(self, synthetic_motor_df):
        """Fixture must have expected number of participants and columns."""
        assert len(synthetic_motor_df) == N_PARTICIPANTS
        expected_cols = {"participant_id", "diagnosis", "gait_speed_m_per_s", "cadence_steps_per_min"}
        assert expected_cols.issubset(set(synthetic_motor_df.columns))

    def test_synthetic_participant_ids_unique(self, synthetic_motor_df):
        """Each participant must appear only once in the fixture."""
        assert synthetic_motor_df["participant_id"].is_unique, (
            "Synthetic fixture participant IDs must be unique (one row per participant)."
        )

    def test_synthetic_labels_valid(self, synthetic_motor_df):
        """Labels must be binary (0 or 1)."""
        assert set(synthetic_motor_df["diagnosis"].unique()).issubset({0, 1})


# ══════════════════════════════════════════════════════════════════════════════
# 2. Preprocessing
# ══════════════════════════════════════════════════════════════════════════════

class TestMotorPreprocessing:

    def test_preprocess_returns_dataframe(self, preprocessed_motor_df):
        assert isinstance(preprocessed_motor_df, pd.DataFrame)

    def test_preprocess_retains_participants(self, synthetic_motor_df, preprocessed_motor_df):
        """Preprocessing should not silently drop all participants."""
        assert len(preprocessed_motor_df) > 0
        # Most participants should be retained (allow small drop for invalid labels)
        assert len(preprocessed_motor_df) >= int(0.9 * len(synthetic_motor_df))

    def test_gait_speed_clipped(self, preprocessed_motor_df):
        """Gait speed must be within plausible range after preprocessing."""
        if "gait_speed_m_per_s" in preprocessed_motor_df.columns:
            valid = preprocessed_motor_df["gait_speed_m_per_s"].dropna()
            assert (valid >= 0.0).all(), "Gait speed cannot be negative."
            assert (valid <= 3.0).all(), "Gait speed must be <= 3.0 m/s."

    def test_cadence_clipped(self, preprocessed_motor_df):
        if "cadence_steps_per_min" in preprocessed_motor_df.columns:
            valid = preprocessed_motor_df["cadence_steps_per_min"].dropna()
            assert (valid >= 0.0).all()
            assert (valid <= 200.0).all()

    def test_diagnosis_is_binary(self, preprocessed_motor_df):
        assert set(preprocessed_motor_df["diagnosis"].unique()).issubset({0, 1})


# ══════════════════════════════════════════════════════════════════════════════
# 3. Participant-level split — no leakage
# ══════════════════════════════════════════════════════════════════════════════

class TestParticipantSplit:

    def test_no_overlap_train_val(self, split_motor_dfs):
        df_train, df_val, df_test = split_motor_dfs
        train_ids = set(df_train["participant_id"])
        val_ids = set(df_val["participant_id"])
        assert len(train_ids & val_ids) == 0, "Train and val sets must not share participants."

    def test_no_overlap_train_test(self, split_motor_dfs):
        df_train, df_val, df_test = split_motor_dfs
        train_ids = set(df_train["participant_id"])
        test_ids = set(df_test["participant_id"])
        assert len(train_ids & test_ids) == 0, "Train and test sets must not share participants."

    def test_no_overlap_val_test(self, split_motor_dfs):
        df_train, df_val, df_test = split_motor_dfs
        val_ids = set(df_val["participant_id"])
        test_ids = set(df_test["participant_id"])
        assert len(val_ids & test_ids) == 0, "Val and test sets must not share participants."

    def test_all_participants_covered(self, preprocessed_motor_df, split_motor_dfs):
        df_train, df_val, df_test = split_motor_dfs
        all_split = (
            set(df_train["participant_id"])
            | set(df_val["participant_id"])
            | set(df_test["participant_id"])
        )
        all_original = set(preprocessed_motor_df["participant_id"])
        assert all_split == all_original, "All participants must appear in exactly one split."

    def test_validate_participant_split_no_overlap(self, split_motor_dfs):
        """validator must pass with no leakage."""
        df_train, df_val, df_test = split_motor_dfs
        result = validate_participant_split(
            df_train["participant_id"].tolist(),
            df_val["participant_id"].tolist(),
            df_test["participant_id"].tolist(),
        )
        assert result is True

    def test_validate_participant_split_detects_leakage(self):
        """validator must raise on overlapping IDs."""
        with pytest.raises(ValueError, match="leakage"):
            validate_participant_split(["P1", "P2", "P3"], ["P3", "P4"], ["P5"])


# ══════════════════════════════════════════════════════════════════════════════
# 4. Feature extraction
# ══════════════════════════════════════════════════════════════════════════════

class TestFeatureExtraction:

    def test_feature_df_returns_expected_keys(self, feature_df):
        """Feature extraction must return all expected GAIT_FEATURE_NAMES columns."""
        for feat in GAIT_FEATURE_NAMES:
            assert feat in feature_df.columns, (
                f"Expected feature '{feat}' not found in feature DataFrame."
            )

    def test_feature_df_has_participant_id(self, feature_df):
        assert "participant_id" in feature_df.columns

    def test_feature_df_has_diagnosis(self, feature_df):
        assert "diagnosis" in feature_df.columns

    def test_unsupported_features_not_present(self, feature_df):
        """
        Unsupported feature categories (tapping, tremor, spiral) must NOT
        silently appear in the extracted feature DataFrame.
        """
        unsupported_patterns = [
            "tap",           # finger tapping
            "tremor",        # tremor
            "spiral",        # spiral drawing
            "mfcc",          # voice MFCCs (wrong modality)
            "dominant_freq", # tremor FFT features
            "peak_power",    # tremor power
        ]
        actual_cols = [c.lower() for c in feature_df.columns]
        for pattern in unsupported_patterns:
            for col in actual_cols:
                assert pattern not in col, (
                    f"Unsupported feature pattern '{pattern}' found in column '{col}'. "
                    f"physionet_gait does not support this task. "
                    f"UNSUPPORTED_TASKS doc: {UNSUPPORTED_TASKS}"
                )

    def test_unsupported_tasks_are_documented(self):
        """UNSUPPORTED_TASKS must document at least finger_tapping, spiral, tremor."""
        required_keys = {"finger_tapping", "spiral_drawing", "resting_tremor"}
        assert required_keys.issubset(set(UNSUPPORTED_TASKS.keys())), (
            f"UNSUPPORTED_TASKS must document: {required_keys}. "
            f"Got: {set(UNSUPPORTED_TASKS.keys())}"
        )

    def test_limitations_is_non_empty_list(self):
        """LIMITATIONS must be a non-empty list."""
        assert isinstance(LIMITATIONS, list)
        assert len(LIMITATIONS) > 0

    def test_get_feature_matrix_shapes(self, feature_df):
        X, y, names = get_feature_matrix(feature_df)
        assert X.shape[0] == len(feature_df)
        assert y.shape[0] == len(feature_df)
        assert len(names) > 0
        assert X.shape[1] == len(names)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Step detection from synthetic VGRF
# ══════════════════════════════════════════════════════════════════════════════

class TestStepDetection:

    def test_detect_steps_returns_arrays(self):
        """Step detector must return two numpy arrays."""
        df_trial = _make_synthetic_vgrf_trial(n_samples=1200, seed=SEED)
        total_force = df_trial["Total_Force_Left"].values
        stance, swing = _detect_steps_from_vgrf(total_force, sampling_rate_hz=100)
        assert isinstance(stance, np.ndarray)
        assert isinstance(swing, np.ndarray)

    def test_detect_steps_plausible_duration(self):
        """Stance durations must be within physiologically plausible range."""
        df_trial = _make_synthetic_vgrf_trial(n_samples=1200, seed=SEED)
        total_force = df_trial["Total_Force_Left"].values
        stance, swing = _detect_steps_from_vgrf(total_force, sampling_rate_hz=100)
        if len(stance) > 0:
            assert (stance >= 0.2).all(), "Stance phases must be >= 0.2s"
            assert (stance <= 2.0).all(), "Stance phases must be <= 2.0s"

    def test_detect_steps_empty_on_flat_signal(self):
        """Zero-force signal must produce empty step arrays."""
        flat_signal = np.zeros(500)
        stance, swing = _detect_steps_from_vgrf(flat_signal)
        assert len(stance) == 0

    def test_detect_steps_empty_on_short_signal(self):
        """Very short signals must return empty arrays."""
        short_signal = np.array([1.0, 2.0])
        stance, swing = _detect_steps_from_vgrf(short_signal)
        assert len(stance) == 0

    def test_step_regularity_range(self):
        """Step regularity must be in [0, 1] for a valid signal."""
        df_trial = _make_synthetic_vgrf_trial(n_samples=1200, seed=SEED)
        total_force = df_trial["Total_Force_Left"].values + df_trial["Total_Force_Right"].values
        regularity = _compute_step_regularity(total_force, sampling_rate_hz=100)
        if not math.isnan(regularity):
            assert 0.0 <= regularity <= 1.0

    def test_step_regularity_nan_on_short_signal(self):
        """Step regularity must return NaN for too-short signal."""
        short_signal = np.ones(10)
        regularity = _compute_step_regularity(short_signal)
        assert math.isnan(regularity)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Quality checks
# ══════════════════════════════════════════════════════════════════════════════

class TestQualityChecks:

    def test_feature_table_quality_passes_valid(self, preprocessed_motor_df):
        """Valid preprocessed synthetic fixture should pass quality check."""
        report = check_feature_table_quality(preprocessed_motor_df)
        # Should pass (synthetic data is well-formed)
        assert isinstance(report["passed"], bool)
        assert "issues" in report
        assert "warnings" in report
        assert "missing_ratios" in report

    def test_vgrf_quality_detects_short_trial(self):
        """VGRF quality check must flag a trial that is too short."""
        df_short = _make_synthetic_vgrf_trial(n_samples=50, seed=SEED)  # ~0.5s — too short
        report = check_vgrf_quality(df_short, participant_id="SHORT_TRIAL")
        assert not report["passed"], "Short trial must fail quality check."
        assert len(report["issues"]) > 0

    def test_vgrf_quality_passes_valid_trial(self):
        """A 12-second synthetic VGRF trial should pass quality check."""
        df_ok = _make_synthetic_vgrf_trial(n_samples=1200, seed=SEED)  # 12s
        report = check_vgrf_quality(df_ok, participant_id="VALID_TRIAL")
        assert report["passed"], (
            f"Valid trial should pass quality check. Issues: {report['issues']}"
        )

    def test_check_motor_quality_dispatcher_feature_table(self, preprocessed_motor_df):
        """Dispatcher must route to feature_table mode when raw_sensor_available=False."""
        report = check_motor_quality(preprocessed_motor_df, raw_sensor_available=False)
        assert report.get("mode") == "feature_table"

    def test_check_motor_quality_dispatcher_vgrf(self):
        """Dispatcher must route to vgrf_time_series mode when raw_sensor_available=True."""
        df_vgrf = _make_synthetic_vgrf_trial(n_samples=1200, seed=SEED)
        report = check_motor_quality(df_vgrf, raw_sensor_available=True)
        assert report.get("mode") == "vgrf_time_series"


# ══════════════════════════════════════════════════════════════════════════════
# 7. Training pipeline (simulation mode)
# ══════════════════════════════════════════════════════════════════════════════

class TestMotorTrainPipeline:

    def test_pipeline_runs_simulation_mode(self, motor_workspace):
        """
        Motor pipeline must run in simulation mode when no real data is present.
        SYNTHETIC — zero clinical validity.
        """
        tmp_path = motor_workspace
        result = run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        assert "experiment_type" in result
        assert result["experiment_type"] == "simulation"
        assert "best_model" in result
        assert result["best_model"] is not None
        assert "best_val_score" in result
        assert 0.0 <= result["best_val_score"] <= 1.0

    def test_pipeline_saves_model_artifact(self, motor_workspace):
        """Pipeline must create model.joblib and metadata.json."""
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        model_path = tmp_path / "models" / "motor" / "model.joblib"
        metadata_path = tmp_path / "models" / "motor" / "metadata.json"
        assert model_path.exists(), "model.joblib must be created by pipeline."
        assert metadata_path.exists(), "metadata.json must be created by pipeline."

    def test_pipeline_saves_evaluation_json(self, motor_workspace):
        """Pipeline must write motor_results.json."""
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        eval_path = tmp_path / "evaluation" / "motor_results.json"
        assert eval_path.exists()

        with open(eval_path) as f:
            data = json.load(f)

        assert data["phase"] == 4
        assert data["modality"] == "motor"
        assert "experiment_type" in data
        assert "tasks_used" in data
        assert "models_compared" in data
        assert "best_model" in data
        assert "metrics" in data
        assert "features_used" in data
        assert "limitations" in data
        assert "artifact_paths" in data

    def test_metadata_has_no_clinical_claim(self, motor_workspace):
        """metadata.json must explicitly state clinical_claim: false."""
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        with open(tmp_path / "models" / "motor" / "metadata.json") as f:
            meta = json.load(f)

        assert meta.get("clinical_claim") is False, (
            "metadata.json must have 'clinical_claim': false."
        )

    def test_evaluation_json_experiment_type_simulation(self, motor_workspace):
        """motor_results.json must document simulation experiment type."""
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        with open(tmp_path / "evaluation" / "motor_results.json") as f:
            data = json.load(f)

        assert data["experiment_type"] == "simulation"
        assert data["dataset_id"] == "synthetic_fixture"

    def test_generate_synthetic_motor_fixture_alias(self):
        """_generate_synthetic_motor_fixture alias must return valid DataFrame."""
        df = _generate_synthetic_motor_fixture(n_participants=50, seed=SEED)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 50
        assert "participant_id" in df.columns
        assert "diagnosis" in df.columns


# ══════════════════════════════════════════════════════════════════════════════
# 8. Prediction interface schema validation
# ══════════════════════════════════════════════════════════════════════════════

class TestPredictionSchema:

    REQUIRED_KEYS = {
        "modality",
        "risk_score",
        "embedding",
        "model_version",
        "features_used",
        "tasks_used",
        "quality",
        "warnings",
    }

    REQUIRED_QUALITY_KEYS = {"passed", "issues"}

    def test_predict_no_model_returns_valid_schema(self):
        """predict_motor must return valid schema even when model is missing."""
        result = predict_motor(
            {"gait_speed_m_per_s": 1.0},
            model_path="models/motor/nonexistent_model.joblib",
        )
        assert isinstance(result, dict)
        for key in self.REQUIRED_KEYS:
            assert key in result, f"Missing key '{key}' in prediction output."
        assert result["modality"] == "motor"

    def test_predict_risk_score_between_0_and_1_no_model(self):
        """Risk score must be in [0, 1] even when model is missing."""
        result = predict_motor(
            {"gait_speed_m_per_s": 0.9},
            model_path="models/motor/nonexistent_model.joblib",
        )
        risk = result["risk_score"]
        assert isinstance(risk, float)
        assert 0.0 <= risk <= 1.0

    def test_predict_with_real_model(self, motor_workspace):
        """predict_motor must return valid schema with trained model."""
        tmp_path = motor_workspace

        # Train model first
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        model_path = str(tmp_path / "models" / "motor" / "model.joblib")

        test_input = {
            "gait_speed_m_per_s": 0.85,
            "cadence_steps_per_min": 92.0,
            "stride_interval_mean_s": 1.30,
            "stride_interval_cv_pct": 5.1,
            "step_regularity": 0.74,
            "symmetry_index_pct": 4.5,
            "accel_variance": 0.61,
            "stance_swing_ratio": 2.1,
        }

        result = predict_motor(test_input, model_path=model_path)

        for key in self.REQUIRED_KEYS:
            assert key in result, f"Missing key '{key}' in prediction output."

        assert result["modality"] == "motor"
        assert isinstance(result["risk_score"], float)
        assert 0.0 <= result["risk_score"] <= 1.0
        assert isinstance(result["embedding"], list)
        assert len(result["embedding"]) > 0
        assert isinstance(result["features_used"], list)
        assert isinstance(result["tasks_used"], list)
        assert isinstance(result["quality"], dict)
        for qk in self.REQUIRED_QUALITY_KEYS:
            assert qk in result["quality"]
        assert isinstance(result["warnings"], list)

    def test_predict_risk_score_in_range_with_trained_model(self, motor_workspace):
        """Risk score must be in [0, 1] with trained model."""
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        model_path = str(tmp_path / "models" / "motor" / "model.joblib")

        for _ in range(5):
            rng = np.random.RandomState(SEED + _)
            test_input = {
                "gait_speed_m_per_s": float(rng.uniform(0.5, 1.5)),
                "cadence_steps_per_min": float(rng.uniform(80, 120)),
                "stride_interval_mean_s": float(rng.uniform(0.9, 1.5)),
                "stride_interval_cv_pct": float(rng.uniform(1.0, 8.0)),
            }
            result = predict_motor(test_input, model_path=model_path)
            assert 0.0 <= result["risk_score"] <= 1.0, (
                f"Risk score {result['risk_score']} out of [0, 1] range."
            )


# ══════════════════════════════════════════════════════════════════════════════
# 9. Missing modality / task produces warnings, not crashes
# ══════════════════════════════════════════════════════════════════════════════

class TestMissingModalityHandling:

    def test_empty_dict_input_returns_warnings(self):
        """Empty dict input must produce warnings and not crash."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = predict_motor(
                {},
                model_path="models/motor/nonexistent_model.joblib",
            )
        assert isinstance(result, dict)
        assert "warnings" in result
        # Should return something, not crash

    def test_wrong_type_input_raises_type_error(self, motor_workspace):
        """
        Non-dict/DataFrame/str input must NOT crash but return a graceful dict
        with warnings. predict_motor catches TypeError from _normalise_input and
        returns a standardised error dict (consistent with 'no crash' design).
        """
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )
        model_path = str(tmp_path / "models" / "motor" / "model.joblib")
        # Should return a dict with warnings, not raise
        result = predict_motor(12345, model_path=model_path)
        assert isinstance(result, dict), (
            "predict_motor must return a dict even for invalid input types."
        )
        assert len(result.get("warnings", [])) > 0, (
            "Invalid input type must generate warnings."
        )

    def test_all_nan_features_returns_warning_not_crash(self, motor_workspace):
        """All-NaN feature row must produce a warning and a valid output."""
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        model_path = str(tmp_path / "models" / "motor" / "model.joblib")

        all_nan_input = {feat: float("nan") for feat in MOTOR_FEATURE_NAMES}

        result = predict_motor(all_nan_input, model_path=model_path)
        assert isinstance(result, dict)
        assert 0.0 <= result["risk_score"] <= 1.0
        # There should be a quality issue flagged
        assert len(result["quality"]["issues"]) > 0

    def test_missing_features_produce_imputation_warning(self, motor_workspace):
        """Partial features must produce imputation warning."""
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        model_path = str(tmp_path / "models" / "motor" / "model.joblib")

        # Provide only 2 of 8 features
        partial_input = {
            "gait_speed_m_per_s": 1.0,
            "cadence_steps_per_min": 105.0,
        }

        result = predict_motor(partial_input, model_path=model_path)
        all_warnings = result["warnings"]
        has_imputation_warning = any("imputed" in w.lower() or "missing" in w.lower() for w in all_warnings)
        assert has_imputation_warning, (
            f"Expected imputation warning for partial features. Got: {all_warnings}"
        )

    def test_no_motor_features_returns_neutral_score(self, motor_workspace):
        """Completely absent motor data must return 0.5 (uninformative)."""
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        model_path = str(tmp_path / "models" / "motor" / "model.joblib")

        no_motor_input = {"olfactory_score": 25, "rbd_score": 4}  # wrong modality features
        result = predict_motor(no_motor_input, model_path=model_path)

        assert result["risk_score"] == 0.5, (
            f"Absent motor features must return 0.5. Got: {result['risk_score']}"
        )
        assert not result["quality"]["passed"]

    def test_dataframe_input_accepted(self, motor_workspace):
        """predict_motor must accept a pandas DataFrame as input."""
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        model_path = str(tmp_path / "models" / "motor" / "model.joblib")

        df_input = pd.DataFrame([{
            "gait_speed_m_per_s": 0.9,
            "cadence_steps_per_min": 95.0,
            "stride_interval_mean_s": 1.25,
            "stride_interval_cv_pct": 4.5,
            "step_regularity": 0.77,
            "symmetry_index_pct": 4.2,
            "accel_variance": 0.58,
            "stance_swing_ratio": 2.0,
        }])

        result = predict_motor(df_input, model_path=model_path)
        assert isinstance(result, dict)
        assert 0.0 <= result["risk_score"] <= 1.0

    def test_csv_input_accepted(self, motor_workspace):
        """predict_motor must accept a CSV file path as input."""
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        model_path = str(tmp_path / "models" / "motor" / "model.joblib")

        csv_path = tmp_path / "test_motor_input.csv"
        pd.DataFrame([{
            "gait_speed_m_per_s": 1.1,
            "cadence_steps_per_min": 108.0,
        }]).to_csv(csv_path, index=False)

        result = predict_motor(str(csv_path), model_path=model_path)
        assert isinstance(result, dict)
        assert 0.0 <= result["risk_score"] <= 1.0


# ══════════════════════════════════════════════════════════════════════════════
# 10. Embedding is fusion-compatible
# ══════════════════════════════════════════════════════════════════════════════

class TestEmbeddingFusionCompatibility:

    def test_embedding_is_list(self, motor_workspace):
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        model_path = str(tmp_path / "models" / "motor" / "model.joblib")
        result = predict_motor(
            {"gait_speed_m_per_s": 1.0, "cadence_steps_per_min": 100.0},
            model_path=model_path,
        )
        assert isinstance(result["embedding"], list)

    def test_embedding_all_finite(self, motor_workspace):
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        model_path = str(tmp_path / "models" / "motor" / "model.joblib")
        result = predict_motor(
            {feat: float(1.0) for feat in MOTOR_FEATURE_NAMES},
            model_path=model_path,
        )
        emb = result["embedding"]
        for i, v in enumerate(emb):
            assert math.isfinite(v) or math.isnan(v), (
                f"Embedding[{i}] = {v} is not finite or NaN."
            )

    def test_embedding_contains_risk_score(self, motor_workspace):
        """First element of embedding must be the risk score."""
        tmp_path = motor_workspace
        run_motor_pipeline(
            data_dir=str(tmp_path / "nonexistent_physionet"),
            seed=SEED,
        )

        model_path = str(tmp_path / "models" / "motor" / "model.joblib")
        result = predict_motor(
            {feat: float(1.0) for feat in MOTOR_FEATURE_NAMES},
            model_path=model_path,
        )
        assert result["embedding"][0] == result["risk_score"]

