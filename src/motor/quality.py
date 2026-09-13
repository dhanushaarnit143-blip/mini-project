"""
Motor/Gait Quality Control Module for MPF-PD (Phase 4).

Validates motor recording quality for PhysioNet VGRF files and for
participant-level derived feature tables.

Quality checks performed:
  For raw VGRF time-series:
    - Minimum trial duration check (>= 10 seconds)
    - Channel saturation/dropout detection
    - Total force floor check (> 0 N expected during stance)
    - Sampling rate consistency check

  For participant-level feature tables:
    - Missing feature rate per column
    - Feature range plausibility checks

IMPORTANT: No clinical claims. Quality checks are engineering guardrails only.
"""

import warnings
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Quality thresholds
# ─────────────────────────────────────────────────────────────────────────────

QUALITY_DEFAULTS: Dict[str, Any] = {
    # Minimum valid trial duration (seconds)
    "min_trial_duration_sec": 10.0,
    # Maximum missing fraction per feature before flagging
    "max_missing_fraction": 0.50,
    # Minimum expected total force (Newtons) — used to detect dead sensors
    "min_expected_force_n": 1.0,
    # Expected sampling rate (Hz)
    "expected_sampling_rate_hz": 100,
    # Maximum allowed sampling rate deviation fraction
    "max_sr_deviation_fraction": 0.05,
    # Plausible gait speed range (m/s)
    "gait_speed_range": (0.05, 3.0),
    # Plausible cadence range (steps/min)
    "cadence_range": (30.0, 200.0),
    # Plausible stride interval mean range (seconds)
    "stride_interval_range": (0.3, 4.0),
    # Plausible CoV range (%)
    "cv_range": (0.0, 50.0),
}


# ─────────────────────────────────────────────────────────────────────────────
# Raw VGRF time-series quality checks
# ─────────────────────────────────────────────────────────────────────────────

def check_vgrf_quality(
    df_trial: pd.DataFrame,
    participant_id: str,
    thresholds: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Quality check for a single-participant raw VGRF time-series DataFrame.

    Args:
        df_trial: Time-series DataFrame for one participant with VGRF sensor columns.
        participant_id: Participant identifier for logging.
        thresholds: Optional override dict for quality thresholds.

    Returns:
        Dict[str, Any]: Quality report with 'passed' bool, 'issues', and 'warnings'.
    """
    cfg = {**QUALITY_DEFAULTS, **(thresholds or {})}
    issues: List[str] = []
    quality_warnings: List[str] = []

    # 1. Trial duration check
    if "Time" in df_trial.columns and len(df_trial) > 1:
        duration_sec = float(
            df_trial["Time"].max() - df_trial["Time"].min()
        )
        if duration_sec < cfg["min_trial_duration_sec"]:
            issues.append(
                f"Trial duration too short: {duration_sec:.2f}s < "
                f"{cfg['min_trial_duration_sec']}s minimum."
            )
    else:
        quality_warnings.append("Cannot compute trial duration: 'Time' column missing or single-row.")

    # 2. Total force floor check (detect all-zero sensor frames)
    total_force_cols = [c for c in ["Total_Force_Left", "Total_Force_Right"] if c in df_trial.columns]
    if total_force_cols:
        for col in total_force_cols:
            median_force = df_trial[col].median()
            if median_force < cfg["min_expected_force_n"]:
                issues.append(
                    f"Suspicious low median force in {col}: {median_force:.2f} N. "
                    "Possible dead sensor or standing-only data."
                )
    else:
        quality_warnings.append(
            "Total force columns (Total_Force_Left, Total_Force_Right) not found. "
            "Cannot perform force floor check."
        )

    # 3. Channel completeness — check for completely missing sensor channels
    vgrf_cols = [f"L{i}" for i in range(1, 9)] + [f"R{i}" for i in range(1, 9)]
    present_vgrf = [c for c in vgrf_cols if c in df_trial.columns]
    if present_vgrf:
        for col in present_vgrf:
            null_frac = float(df_trial[col].isnull().mean())
            if null_frac > cfg["max_missing_fraction"]:
                issues.append(
                    f"Sensor channel '{col}' has {null_frac:.1%} missing values "
                    f"(threshold: {cfg['max_missing_fraction']:.0%})."
                )
    else:
        quality_warnings.append("No VGRF sensor channels (L1-L8, R1-R8) found in trial data.")

    # 4. Sample count consistency check (expected: ~100 Hz × duration)
    if "Time" in df_trial.columns and len(df_trial) > 1:
        duration_sec = float(df_trial["Time"].max() - df_trial["Time"].min())
        expected_samples = int(duration_sec * cfg["expected_sampling_rate_hz"])
        actual_samples = len(df_trial)
        deviation = abs(actual_samples - expected_samples) / max(expected_samples, 1)
        if deviation > cfg["max_sr_deviation_fraction"]:
            quality_warnings.append(
                f"Sample count deviation: expected ~{expected_samples}, "
                f"got {actual_samples} (deviation {deviation:.1%}). "
                "Possible resampling or dropped frames."
            )

    passed = len(issues) == 0
    return {
        "participant_id": participant_id,
        "passed": passed,
        "issues": issues,
        "warnings": quality_warnings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Participant-level feature table quality checks
# ─────────────────────────────────────────────────────────────────────────────

def check_feature_table_quality(
    df: pd.DataFrame,
    thresholds: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Quality check for a participant-level gait feature table.

    Args:
        df: DataFrame with one row per participant and gait feature columns.
        thresholds: Optional override dict for quality thresholds.

    Returns:
        Dict[str, Any]: Quality report with 'passed' bool, 'issues', 'warnings',
                        and 'missing_ratios'.
    """
    cfg = {**QUALITY_DEFAULTS, **(thresholds or {})}
    issues: List[str] = []
    quality_warnings: List[str] = []

    # Missing value check per feature column
    feature_cols = [
        c for c in df.columns
        if c not in ("participant_id", "diagnosis", "substudy", "data_source",
                     "raw_sensor_available", "source_file", "sampling_rate_hz",
                     "trial_duration_s")
    ]

    missing_ratios: Dict[str, float] = {}
    for col in feature_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            ratio = float(df[col].isnull().mean())
            missing_ratios[col] = round(ratio, 4)
            if ratio > cfg["max_missing_fraction"]:
                issues.append(
                    f"Feature '{col}' missing fraction {ratio:.1%} > "
                    f"threshold {cfg['max_missing_fraction']:.0%}."
                )

    # Plausibility range checks
    range_checks = {
        "gait_speed_m_per_s": cfg["gait_speed_range"],
        "cadence_steps_per_min": cfg["cadence_range"],
        "stride_interval_mean_s": cfg["stride_interval_range"],
        "stride_interval_cv_pct": cfg["cv_range"],
    }

    for col, (lo, hi) in range_checks.items():
        if col in df.columns:
            out_of_range = df[col].dropna()
            out_of_range = out_of_range[(out_of_range < lo) | (out_of_range > hi)]
            if len(out_of_range) > 0:
                quality_warnings.append(
                    f"Feature '{col}': {len(out_of_range)} values out of "
                    f"expected range [{lo}, {hi}]."
                )

    passed = len(issues) == 0
    return {
        "passed": passed,
        "issues": issues,
        "warnings": quality_warnings,
        "missing_ratios": missing_ratios,
        "n_participants_checked": len(df),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Unified public API
# ─────────────────────────────────────────────────────────────────────────────

def check_motor_quality(
    df: pd.DataFrame,
    raw_sensor_available: bool = False,
    participant_id_col: str = "participant_id",
    thresholds: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Unified motor quality check dispatcher.

    Routes to VGRF time-series check or feature-table check depending on
    whether raw sensor data is available.

    Args:
        df: Motor DataFrame (raw VGRF or participant-level features).
        raw_sensor_available: True if df contains raw VGRF time-series.
        participant_id_col: Column name for participant IDs.
        thresholds: Optional quality threshold overrides.

    Returns:
        Dict[str, Any]: Quality report with 'passed', 'issues', 'warnings'.
    """
    if raw_sensor_available:
        # Run per-participant VGRF quality checks
        participant_reports = []
        any_failed = False

        for pid, group in df.groupby(participant_id_col):
            report = check_vgrf_quality(group, str(pid), thresholds)
            participant_reports.append(report)
            if not report["passed"]:
                any_failed = True

        n_failed = sum(1 for r in participant_reports if not r["passed"])
        return {
            "passed": not any_failed,
            "n_participants": len(participant_reports),
            "n_failed": n_failed,
            "participant_reports": participant_reports,
            "mode": "vgrf_time_series",
        }
    else:
        report = check_feature_table_quality(df, thresholds)
        report["mode"] = "feature_table"
        return report
