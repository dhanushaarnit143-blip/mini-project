"""
Motor/Gait Feature Extraction Module for MPF-PD (Phase 4).

Extracts gait features from:
  A) Raw VGRF time-series (PhysioNet physionet_gait format, 100 Hz)
  B) Pre-existing participant-level feature tables (derived or synthetic)

Supported feature classes (only for tasks supported by physionet_gait):

  GAIT FEATURES (from VGRF time-series, if raw sensor available):
    - gait_speed_m_per_s          : estimated gait speed (m/s)
    - cadence_steps_per_min       : steps per minute from toe-off events
    - stride_interval_mean_s      : mean stride interval (s) = 1/cadence × 2
    - stride_interval_cv_pct      : stride interval coefficient of variation (%)
    - step_regularity             : autocorrelation coefficient at step lag
    - symmetry_index_pct          : left-right stride symmetry (%)
    - accel_variance              : vertical force signal variance (proxy for acceleration)
    - stance_swing_ratio          : ratio of stance phase to swing phase duration

  NOT SUPPORTED (not available in physionet_gait):
    - Finger tapping features (no tapping data)
    - Tremor frequency features (no accelerometer/gyroscope; VGRF only)
    - Spiral drawing features (no spiral data)
    - Postural tremor features (no IMU/accelerometer)

DATASET LIMITATIONS:
  - physionet_gait uses VGRF force plates, NOT wrist accelerometers or IMU.
  - FFT tremor features are NOT computed: VGRF is a ground force signal,
    not a limb movement signal. Tremor frequency extraction from VGRF would
    be scientifically invalid for upper-limb tremor characterisation.
  - Gait speed is estimated from stride interval + stride length assumptions
    unless explicit speed measurement is available.
  - All participants are manifest PD (not prodromal). These features capture
    established PD gait, not necessarily prodromal motor changes.

IMPORTANT: No clinical claims. Features are research prototype only.
"""

import warnings
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import signal as scipy_signal


# ─────────────────────────────────────────────────────────────────────────────
# Feature name registries
# ─────────────────────────────────────────────────────────────────────────────

GAIT_FEATURE_NAMES: List[str] = [
    "gait_speed_m_per_s",
    "cadence_steps_per_min",
    "stride_interval_mean_s",
    "stride_interval_cv_pct",
    "step_regularity",
    "symmetry_index_pct",
    "accel_variance",
    "stance_swing_ratio",
]

# Features from participant-level tables (precomputed or synthetic)
TABULAR_FEATURE_NAMES: List[str] = GAIT_FEATURE_NAMES + [
    "trial_duration_s",
]

# Final feature set used for model training (participant-level, merged)
MOTOR_FEATURE_NAMES: List[str] = GAIT_FEATURE_NAMES  # trial_duration excluded from model

# Tasks not supported and why (documented explicitly per project rules)
UNSUPPORTED_TASKS: Dict[str, str] = {
    "finger_tapping": "physionet_gait does not contain finger tapping data.",
    "spiral_drawing": "physionet_gait does not contain spiral drawing data.",
    "resting_tremor": (
        "physionet_gait provides VGRF force plate signals, not limb accelerometry. "
        "Tremor frequency extraction from VGRF is scientifically invalid for "
        "upper-limb resting tremor characterisation."
    ),
    "postural_tremor": (
        "No IMU or wrist accelerometer data available in physionet_gait."
    ),
}

LIMITATIONS: List[str] = [
    "physionet_gait (Category B) is the primary motor dataset. It provides VGRF "
    "force plate data at 100 Hz from 166 participants (93 PD, 73 Control).",
    "Binary classification only (PD vs Control). No prodromal labels are available "
    "in physionet_gait. Motor features here characterise manifest PD gait changes, "
    "not necessarily prodromal motor signs.",
    "Raw VGRF signal processing (step detection, stride segmentation) is supported "
    "when the physionet_gait .txt files are present locally. If not present, derived "
    "features or synthetic fixtures are used.",
    "FFT tremor features are NOT extracted: physionet_gait provides ground force "
    "signals, not limb accelerometry. Tremor characterisation from VGRF would be "
    "scientifically invalid.",
    "Finger tapping, spiral drawing, and IMU-based tremor features are NOT "
    "implemented because physionet_gait does not support these modalities.",
    "Gait speed is estimated from stride timing and assumed stride length "
    "(0.72 m default) when direct speed measurement is not available.",
    "Two-minute walking trial under controlled lab conditions. Ecological validity "
    "to real-world gait is limited.",
    "All participants are manifest PD; this pipeline is not validated for "
    "prodromal detection. Clinical claims must not be made.",
    "No clinical claims: all risk scores are research prototype estimates only.",
]


# ─────────────────────────────────────────────────────────────────────────────
# Step/stride detection from VGRF
# ─────────────────────────────────────────────────────────────────────────────

def _detect_steps_from_vgrf(
    force_signal: np.ndarray,
    sampling_rate_hz: int = 100,
    threshold_fraction: float = 0.10,
    min_step_duration_s: float = 0.2,
    max_step_duration_s: float = 2.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Detect footfall events (toe-off / heel-strike) from a VGRF force signal.

    Uses a threshold-crossing approach: a step is detected when the force
    signal exceeds `threshold_fraction × max_force` (heel-strike onset) and
    drops below it (toe-off).

    Args:
        force_signal: 1-D array of total vertical ground reaction force (N).
        sampling_rate_hz: Sampling rate of the signal in Hz.
        threshold_fraction: Force threshold as a fraction of max force.
        min_step_duration_s: Minimum plausible stance phase duration (s).
        max_step_duration_s: Maximum plausible stance phase duration (s).

    Returns:
        Tuple[np.ndarray, np.ndarray]:
            - stance_durations_s: Array of stance phase durations (s).
            - swing_durations_s: Array of swing phase durations (s).
    """
    if len(force_signal) < 10:
        return np.array([]), np.array([])

    force_signal = np.asarray(force_signal, dtype=float)
    max_force = np.nanmax(force_signal)
    if max_force <= 0:
        return np.array([]), np.array([])

    threshold = threshold_fraction * max_force
    min_step_samples = int(min_step_duration_s * sampling_rate_hz)
    max_step_samples = int(max_step_duration_s * sampling_rate_hz)

    # Binarize: 1 = stance (force > threshold), 0 = swing
    in_stance = (force_signal > threshold).astype(int)

    # Find transitions
    diffs = np.diff(in_stance, prepend=0)
    heel_strikes = np.where(diffs == 1)[0]   # stance onset
    toe_offs = np.where(diffs == -1)[0]       # stance offset

    # Align toe-offs to heel strikes
    stance_durations = []
    swing_durations = []

    for hs in heel_strikes:
        # Find next toe-off after this heel strike
        to_candidates = toe_offs[toe_offs > hs]
        if len(to_candidates) == 0:
            continue
        to = to_candidates[0]
        stance_dur_samples = to - hs
        if not (min_step_samples <= stance_dur_samples <= max_step_samples):
            continue
        stance_durations.append(stance_dur_samples / sampling_rate_hz)

        # Find swing: time until next heel strike
        next_hs_candidates = heel_strikes[heel_strikes > to]
        if len(next_hs_candidates) == 0:
            continue
        next_hs = next_hs_candidates[0]
        swing_dur_samples = next_hs - to
        if min_step_samples <= swing_dur_samples <= max_step_samples:
            swing_durations.append(swing_dur_samples / sampling_rate_hz)

    return np.array(stance_durations), np.array(swing_durations)


def _compute_step_regularity(force_signal: np.ndarray, sampling_rate_hz: int = 100) -> float:
    """
    Compute step regularity as the autocorrelation coefficient at the dominant
    step period lag in the total VGRF signal.

    Step regularity ~ 1.0 = highly regular; lower values indicate irregular gait.

    Args:
        force_signal: 1-D array of total vertical GRF.
        sampling_rate_hz: Sampling rate in Hz.

    Returns:
        float: Step regularity coefficient (0 to 1). Returns NaN if insufficient data.
    """
    force_signal = np.asarray(force_signal, dtype=float)
    force_signal = force_signal - np.nanmean(force_signal)  # zero-mean

    if len(force_signal) < 50:
        return float("nan")

    # Normalised autocorrelation
    n = len(force_signal)
    acf = np.correlate(force_signal, force_signal, mode="full")
    acf = acf[n - 1:]  # take positive lags only
    acf = acf / (acf[0] + 1e-12)  # normalise by zero-lag

    # Search for first peak in lag range [0.2s, 2.5s] (physiological step range)
    min_lag = int(0.2 * sampling_rate_hz)
    max_lag = min(int(2.5 * sampling_rate_hz), len(acf) - 1)

    if max_lag <= min_lag:
        return float("nan")

    search_region = acf[min_lag:max_lag]
    if len(search_region) == 0:
        return float("nan")

    peak_idx = np.argmax(search_region)
    regularity = float(search_region[peak_idx])
    return round(float(np.clip(regularity, 0.0, 1.0)), 4)


# ─────────────────────────────────────────────────────────────────────────────
# Per-participant feature extraction from raw VGRF
# ─────────────────────────────────────────────────────────────────────────────

def _extract_features_from_vgrf_trial(
    df_trial: pd.DataFrame,
    participant_id: str,
    sampling_rate_hz: int = 100,
    assumed_stride_length_m: float = 0.72,
) -> Dict[str, Any]:
    """
    Extract gait features from a single participant's raw VGRF time-series.

    Args:
        df_trial: DataFrame with VGRF time-series for one participant.
        participant_id: Participant identifier.
        sampling_rate_hz: Sampling rate in Hz.
        assumed_stride_length_m: Assumed stride length for gait speed estimation
            when direct speed is not available.

    Returns:
        Dict[str, Any]: Participant-level gait feature dictionary.
    """
    features: Dict[str, Any] = {
        "participant_id": participant_id,
    }
    for feat in GAIT_FEATURE_NAMES:
        features[feat] = float("nan")

    # Aggregate total force signal
    left_cols = [c for c in [f"L{i}" for i in range(1, 9)] if c in df_trial.columns]
    right_cols = [c for c in [f"R{i}" for i in range(1, 9)] if c in df_trial.columns]

    if "Total_Force_Left" in df_trial.columns:
        left_force = df_trial["Total_Force_Left"].fillna(0).values
    elif left_cols:
        left_force = df_trial[left_cols].fillna(0).sum(axis=1).values
    else:
        left_force = np.zeros(len(df_trial))

    if "Total_Force_Right" in df_trial.columns:
        right_force = df_trial["Total_Force_Right"].fillna(0).values
    elif right_cols:
        right_force = df_trial[right_cols].fillna(0).sum(axis=1).values
    else:
        right_force = np.zeros(len(df_trial))

    total_force = left_force + right_force

    # Trial duration
    if "Time" in df_trial.columns and len(df_trial) > 1:
        trial_duration = float(df_trial["Time"].max() - df_trial["Time"].min())
        features["trial_duration_s"] = round(trial_duration, 2)
    else:
        features["trial_duration_s"] = float("nan")
        return features  # Cannot proceed without time axis

    # Step detection on left and right foot separately
    left_stance, left_swing = _detect_steps_from_vgrf(left_force, sampling_rate_hz)
    right_stance, right_swing = _detect_steps_from_vgrf(right_force, sampling_rate_hz)

    all_stance = np.concatenate([left_stance, right_stance])
    all_swing = np.concatenate([left_swing, right_swing])

    if len(all_stance) < 2:
        # Insufficient steps detected — return NaN features (not fabricated)
        warnings.warn(
            f"Participant {participant_id}: Insufficient steps detected "
            f"(left={len(left_stance)}, right={len(right_stance)}). "
            "Features will be NaN.",
            UserWarning,
            stacklevel=2,
        )
        return features

    # Stance and swing durations
    mean_stance = float(np.mean(all_stance))
    mean_swing = float(np.mean(all_swing)) if len(all_swing) > 0 else float("nan")

    # Stance-to-swing ratio
    if mean_swing > 0:
        features["stance_swing_ratio"] = round(mean_stance / mean_swing, 4)

    # Stride interval (stride = two steps, left + right)
    # Estimate: stride interval ≈ 2 × mean step interval
    step_intervals = np.concatenate([left_stance + left_swing, right_stance + right_swing])
    if len(step_intervals) >= 2:
        stride_intervals = step_intervals * 2.0  # approximate stride
        features["stride_interval_mean_s"] = round(float(np.mean(stride_intervals)), 4)
        features["stride_interval_cv_pct"] = round(
            float(np.std(stride_intervals) / (np.mean(stride_intervals) + 1e-12) * 100), 4
        )

        # Cadence = steps per minute
        # steps ≈ total_steps × sampling_rate / (mean_step_interval × sampling_rate)
        total_steps = len(step_intervals)
        total_time_steps = trial_duration
        cadence = (total_steps / total_time_steps) * 60.0
        features["cadence_steps_per_min"] = round(float(cadence), 2)

        # Gait speed estimate (stride length × stride rate)
        stride_rate_per_s = 1.0 / (features["stride_interval_mean_s"] + 1e-12)
        features["gait_speed_m_per_s"] = round(
            float(assumed_stride_length_m * stride_rate_per_s), 4
        )

    # Step regularity from total force autocorrelation
    features["step_regularity"] = _compute_step_regularity(total_force, sampling_rate_hz)

    # Acceleration variance (proxy from force signal variance, normalised by body weight proxy)
    max_force = float(np.nanmax(total_force))
    if max_force > 0:
        features["accel_variance"] = round(
            float(np.nanvar(total_force) / (max_force ** 2 + 1e-12)), 4
        )

    # Symmetry index: % asymmetry between left and right total force means
    left_mean = float(np.nanmean(left_force))
    right_mean = float(np.nanmean(right_force))
    denom = (left_mean + right_mean) / 2.0
    if denom > 0:
        features["symmetry_index_pct"] = round(
            float(abs(left_mean - right_mean) / denom * 100.0), 4
        )

    return features


# ─────────────────────────────────────────────────────────────────────────────
# Public extraction API
# ─────────────────────────────────────────────────────────────────────────────

def extract_motor_features(
    df: pd.DataFrame,
    raw_sensor_available: bool = False,
    sampling_rate_hz: int = 100,
) -> pd.DataFrame:
    """
    Extract participant-level motor/gait features.

    Dispatches to:
      - Raw VGRF extraction (if raw_sensor_available=True): runs per-participant
        step detection and gait feature computation from time-series.
      - Pass-through (if raw_sensor_available=False): reads pre-existing feature
        columns from the DataFrame (participant-level table).

    Args:
        df: Motor DataFrame. Either raw VGRF time-series or participant-level table.
        raw_sensor_available: True if df contains raw VGRF time-series.
        sampling_rate_hz: Sampling rate used for raw signal extraction.

    Returns:
        pd.DataFrame: Participant-level DataFrame with GAIT_FEATURE_NAMES columns
                      and 'participant_id', 'diagnosis' columns.
    """
    if raw_sensor_available:
        # Extract features from raw VGRF time-series per participant
        participant_features = []
        for pid, group in df.groupby("participant_id"):
            diag = int(group["diagnosis"].iloc[0])
            feat_dict = _extract_features_from_vgrf_trial(
                group.reset_index(drop=True),
                participant_id=str(pid),
                sampling_rate_hz=sampling_rate_hz,
            )
            feat_dict["diagnosis"] = diag
            if "substudy" in group.columns:
                feat_dict["substudy"] = str(group["substudy"].iloc[0])
            participant_features.append(feat_dict)

        df_features = pd.DataFrame(participant_features)
    else:
        # Participant-level table: select only known feature columns
        available_features = [c for c in TABULAR_FEATURE_NAMES if c in df.columns]
        missing_features = [c for c in MOTOR_FEATURE_NAMES if c not in df.columns]

        if missing_features:
            warnings.warn(
                f"Motor feature columns not found in DataFrame: {missing_features}. "
                "These will be NaN in the output. "
                "Ensure the data source provides these derived features.",
                UserWarning,
                stacklevel=2,
            )

        keep_cols = ["participant_id", "diagnosis"] + available_features
        if "substudy" in df.columns:
            keep_cols.append("substudy")
        keep_cols = list(dict.fromkeys(keep_cols))  # deduplicate preserving order

        df_features = df[[c for c in keep_cols if c in df.columns]].copy()

        # Add NaN columns for any completely missing features
        for feat in MOTOR_FEATURE_NAMES:
            if feat not in df_features.columns:
                df_features[feat] = float("nan")

    return df_features


def get_feature_matrix(
    df_features: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Convert participant-level feature DataFrame to numpy arrays for training.

    Args:
        df_features: Participant-level DataFrame from extract_motor_features().

    Returns:
        Tuple[np.ndarray, np.ndarray, List[str]]:
            - X: Feature matrix of shape (n_participants, n_features).
            - y: Label array of shape (n_participants,).
            - feature_names: List of feature names used.
    """
    feature_names = [c for c in MOTOR_FEATURE_NAMES if c in df_features.columns]
    X = df_features[feature_names].values.astype(np.float64)
    y = df_features["diagnosis"].values.astype(int)
    return X, y, feature_names
