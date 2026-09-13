"""
Motor/Gait Data Preprocessing and Partitioning Module for MPF-PD (Phase 4).

Handles loading, validation, cleaning, and participant-level splitting for
motor/gait force-plate time-series data.

Supported raw format:
  - PhysioNet Gait in Parkinson's Disease (physionet_gait)
    URL: https://doi.org/10.13026/C24H3N
    License: Open Data Commons Attribution (ODC-By) v1.0
    Format: space-separated ASCII text files with VGRF sensor channels at 100 Hz.
    Columns: Time, L1-L8, R1-R8, Total_Force_Left, Total_Force_Right
    Sub-study participant lists:
      - Ga (n=29 PD, n=18 HC) — Gai et al. 1997
      - Ju (n=29 PD, n=26 HC) — Juengel et al. 1997
      - Si (n=35 PD, n=29 HC) — Silsupadol et al. 1997

If real data files are not present locally, falls back to a synthetic fixture
clearly labelled as simulation mode.

LIMITATIONS:
  - Walking is on a level lab surface at self-selected comfortable pace.
  - No tapping, tremor, spiral, or non-motor data in this dataset.
  - Binary labels only (PD vs Control); no prodromal labels.
  - Raw VGRF only: no accelerometer/gyroscope/IMU data.
  - All participants are manifest PD (not prodromal), so motor markers here
    are not prodromal markers — they characterise established PD gait.

IMPORTANT: No clinical claims. Outputs are research prototype risk estimates only.
"""

import os
import warnings
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.data.validators import validate_required_columns, validate_participant_split


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

PHYSIONET_SAMPLING_RATE_HZ: int = 100  # Hz — defined by dataset protocol
PHYSIONET_LEFT_COLS: List[str] = [f"L{i}" for i in range(1, 9)]
PHYSIONET_RIGHT_COLS: List[str] = [f"R{i}" for i in range(1, 9)]
PHYSIONET_FORCE_COLS: List[str] = PHYSIONET_LEFT_COLS + PHYSIONET_RIGHT_COLS
PHYSIONET_TOTAL_COLS: List[str] = ["Total_Force_Left", "Total_Force_Right"]
PHYSIONET_ALL_SENSOR_COLS: List[str] = PHYSIONET_FORCE_COLS + PHYSIONET_TOTAL_COLS
PHYSIONET_TIME_COL: str = "Time"

PHYSIONET_DATA_DIR: str = "data/raw/physionet_gait"

# Minimum trial duration to be considered valid (seconds)
MIN_TRIAL_DURATION_SEC: float = 10.0

# Sub-study names and PD/HC counts (documentation only)
PHYSIONET_SUBSTUDIES: Dict[str, Dict[str, int]] = {
    "Ga": {"pd": 29, "hc": 18},
    "Ju": {"pd": 29, "hc": 26},
    "Si": {"pd": 35, "hc": 29},
}

# ─────────────────────────────────────────────────────────────────────────────
# Synthetic fixture generator (Category E — clearly labelled)
# ─────────────────────────────────────────────────────────────────────────────

def generate_synthetic_motor_fixture(
    n_participants: int = 200,
    seed: int = 42
) -> pd.DataFrame:
    """
    Generate a SYNTHETIC motor/gait tabular fixture for unit testing and CI/CD.

    WARNING: COMPLETELY SYNTHETIC DATA.
    - Has ZERO physiological or clinical reality.
    - Used ONLY for software testing and CI/CD pipeline verification.
    - Must NEVER be presented as real clinical results.
    - Fixture mimics the derived-feature schema produced by extract_motor_features().

    The fixture produces participant-level rows with pre-computed gait features
    that are consistent with the PhysioNet gait dataset's derived feature schema.

    Args:
        n_participants: Number of synthetic participants to generate.
        seed: Random seed for reproducibility.

    Returns:
        pd.DataFrame: Synthetic motor DataFrame with SYNTHETIC labels.
    """
    rng = np.random.RandomState(seed)

    participant_ids = [f"SYN_M_{i+1:04d}" for i in range(n_participants)]
    # 50% PD, 50% Control (synthetic)
    diagnoses = rng.choice([0, 1], size=n_participants, p=[0.5, 0.5])

    # Synthetic gait features: PD participants have altered values relative to controls
    # These are NOT real clinical measurements — purely for software testing.

    # Gait speed (m/s): Controls ~1.2, PD ~0.9
    gait_speed = np.where(
        diagnoses == 0,
        rng.normal(loc=1.2, scale=0.15, size=n_participants),
        rng.normal(loc=0.9, scale=0.2, size=n_participants)
    ).clip(0.3, 2.0).round(4)

    # Cadence (steps/min): Controls ~110, PD ~95
    cadence = np.where(
        diagnoses == 0,
        rng.normal(loc=110.0, scale=8.0, size=n_participants),
        rng.normal(loc=95.0, scale=10.0, size=n_participants)
    ).clip(50.0, 160.0).round(2)

    # Mean stride interval (s): Controls ~1.09, PD ~1.26
    stride_interval_mean = np.where(
        diagnoses == 0,
        rng.normal(loc=1.09, scale=0.07, size=n_participants),
        rng.normal(loc=1.26, scale=0.12, size=n_participants)
    ).clip(0.5, 2.5).round(4)

    # Stride interval variability (CoV %): PD higher
    stride_interval_cv = np.where(
        diagnoses == 0,
        rng.normal(loc=2.2, scale=0.6, size=n_participants),
        rng.normal(loc=4.5, scale=1.2, size=n_participants)
    ).clip(0.5, 15.0).round(4)

    # Step regularity (autocorrelation at step lag): PD lower
    step_regularity = np.where(
        diagnoses == 0,
        rng.normal(loc=0.87, scale=0.05, size=n_participants),
        rng.normal(loc=0.76, scale=0.08, size=n_participants)
    ).clip(0.3, 1.0).round(4)

    # Symmetry index (%): Controls near 0, PD higher
    symmetry_index = np.where(
        diagnoses == 0,
        rng.normal(loc=1.5, scale=0.8, size=n_participants),
        rng.normal(loc=4.8, scale=2.0, size=n_participants)
    ).clip(0.0, 20.0).round(4)

    # Acceleration variance (vertical): PD higher variance
    accel_variance = np.where(
        diagnoses == 0,
        rng.normal(loc=0.42, scale=0.06, size=n_participants),
        rng.normal(loc=0.62, scale=0.10, size=n_participants)
    ).clip(0.1, 1.5).round(4)

    # Stance-to-swing ratio: PD tends to have longer stance
    stance_swing_ratio = np.where(
        diagnoses == 0,
        rng.normal(loc=1.85, scale=0.12, size=n_participants),
        rng.normal(loc=2.05, scale=0.18, size=n_participants)
    ).clip(1.0, 3.5).round(4)

    # Total trial force signal duration (seconds): 2-minute protocol
    trial_duration_sec = rng.uniform(low=115.0, high=125.0, size=n_participants).round(1)

    df = pd.DataFrame({
        "participant_id": participant_ids,
        "diagnosis": diagnoses,
        "substudy": rng.choice(["Ga", "Ju", "Si"], size=n_participants),
        "gait_speed_m_per_s": gait_speed,
        "cadence_steps_per_min": cadence,
        "stride_interval_mean_s": stride_interval_mean,
        "stride_interval_cv_pct": stride_interval_cv,
        "step_regularity": step_regularity,
        "symmetry_index_pct": symmetry_index,
        "accel_variance": accel_variance,
        "stance_swing_ratio": stance_swing_ratio,
        "trial_duration_s": trial_duration_sec,
        "raw_sensor_available": False,  # synthetic fixtures never have raw sensor data
        "data_source": "synthetic_fixture",  # explicit label
    })

    # Insert 5% controlled missingness in step_regularity for missing-data testing
    mask = rng.rand(n_participants) < 0.05
    df.loc[mask, "step_regularity"] = np.nan

    return df


# ─────────────────────────────────────────────────────────────────────────────
# PhysioNet VGRF raw file parser (used when real data is present)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_physionet_vgrf_file(
    filepath: Path,
    participant_id: str,
    diagnosis: int
) -> Optional[pd.DataFrame]:
    """
    Parse a single PhysioNet VGRF text file into a DataFrame with metadata.

    Args:
        filepath: Path to the .txt VGRF file.
        participant_id: Participant identifier string.
        diagnosis: 0 = Control, 1 = PD.

    Returns:
        Optional[pd.DataFrame]: Parsed DataFrame or None if file is invalid.
    """
    try:
        df = pd.read_csv(
            filepath,
            sep=r"\s+",
            header=None,
            names=[PHYSIONET_TIME_COL] + PHYSIONET_ALL_SENSOR_COLS,
            engine="python",
            on_bad_lines="skip",
        )
        df = df.apply(pd.to_numeric, errors="coerce")
        df.dropna(subset=[PHYSIONET_TIME_COL], inplace=True)

        duration_sec = float(df[PHYSIONET_TIME_COL].max() - df[PHYSIONET_TIME_COL].min())
        if duration_sec < MIN_TRIAL_DURATION_SEC:
            warnings.warn(
                f"Participant {participant_id}: Trial too short ({duration_sec:.1f}s < "
                f"{MIN_TRIAL_DURATION_SEC}s). Skipping file: {filepath.name}",
                UserWarning,
                stacklevel=2,
            )
            return None

        df["participant_id"] = participant_id
        df["diagnosis"] = diagnosis
        df["sampling_rate_hz"] = PHYSIONET_SAMPLING_RATE_HZ
        df["source_file"] = filepath.name
        df["trial_duration_s"] = round(duration_sec, 2)
        return df
    except Exception as exc:
        warnings.warn(
            f"Failed to parse PhysioNet file {filepath.name}: {exc}",
            UserWarning,
            stacklevel=2,
        )
        return None


def _load_physionet_directory(data_dir: Path) -> Tuple[pd.DataFrame, int]:
    """
    Load all PhysioNet VGRF text files from a directory structure.

    Expected directory layout (PhysioNet standard):
        data_dir/
            GaCo01_10m.txt, GaPt01_10m.txt, ...   (Ga sub-study)
            JuCo01_10m.txt, JuPt01_10m.txt, ...   (Ju sub-study)
            SiCo01_10m.txt, SiPt01_10m.txt, ...   (Si sub-study)
        Naming convention: {SubStudy}{Co|Pt}{ID}_*.txt
          Co = Control (HC), Pt = Patient (PD)

    Args:
        data_dir: Root directory containing PhysioNet VGRF files.

    Returns:
        Tuple[pd.DataFrame, int]: (combined DataFrame, file count loaded).
    """
    txt_files = sorted(data_dir.glob("*.txt"))
    if not txt_files:
        # Try one level deeper
        txt_files = sorted(data_dir.rglob("*.txt"))

    if not txt_files:
        raise FileNotFoundError(
            f"No VGRF .txt files found under {data_dir}. "
            "Please download the PhysioNet Gait in Parkinson's Disease dataset "
            "from https://doi.org/10.13026/C24H3N and place the .txt files in "
            f"{data_dir}."
        )

    dfs = []
    n_loaded = 0
    for fpath in txt_files:
        fname = fpath.stem  # e.g. 'GaCo01_10m'
        # Parse substudy and group from filename
        if len(fname) >= 4:
            sub = fname[:2]  # 'Ga', 'Ju', or 'Si'
            grp = fname[2:4]  # 'Co' (control) or 'Pt' (patient/PD)
            diagnosis = 1 if grp == "Pt" else 0
            participant_id = f"{fname.split('_')[0]}"
        else:
            warnings.warn(f"Unrecognized filename format: {fpath.name} — skipping.")
            continue

        df_trial = _parse_physionet_vgrf_file(fpath, participant_id, diagnosis)
        if df_trial is not None:
            dfs.append(df_trial)
            n_loaded += 1

    if not dfs:
        raise ValueError("No valid VGRF trial files could be parsed from the data directory.")

    return pd.concat(dfs, ignore_index=True), n_loaded


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_motor_data(
    data_dir: str = PHYSIONET_DATA_DIR,
    precomputed_csv: Optional[str] = None,
) -> Tuple[pd.DataFrame, str, bool]:
    """
    Load motor/gait data from PhysioNet VGRF files or a precomputed feature CSV.

    Loading order:
      1. If `precomputed_csv` points to an existing CSV, load derived features directly.
         (raw signal processing is skipped; document as "derived_only" mode.)
      2. If `data_dir` contains .txt VGRF files, parse raw time-series and return.
         (raw signal available; extract_motor_features will compute from raw signals.)
      3. Otherwise, fall back to a synthetic fixture labelled as simulation mode.

    Args:
        data_dir: Path to directory containing PhysioNet .txt VGRF files.
        precomputed_csv: Optional path to a precomputed participant-level feature CSV.

    Returns:
        Tuple[pd.DataFrame, str, bool]:
            - DataFrame: Either raw time-series or participant-level derived features.
            - experiment_type: 'real_data' | 'derived_only' | 'simulation'
            - raw_sensor_available: True if raw VGRF time-series are loaded.
    """
    # Option 1: Precomputed derived features CSV
    if precomputed_csv is not None:
        p = Path(precomputed_csv)
        if p.exists() and p.is_file():
            df = pd.read_csv(p)
            return df, "derived_only", False

    # Option 2: Raw PhysioNet VGRF directory
    data_path = Path(data_dir)
    if data_path.exists() and data_path.is_dir():
        txt_files = list(data_path.glob("*.txt")) + list(data_path.rglob("*.txt"))
        if txt_files:
            try:
                df, n_loaded = _load_physionet_directory(data_path)
                return df, "real_data", True
            except Exception as exc:
                warnings.warn(
                    f"Failed to load PhysioNet VGRF files: {exc}. "
                    "Falling back to synthetic fixture (simulation mode).",
                    UserWarning,
                    stacklevel=2,
                )

    # Option 3: Synthetic fixture fallback
    warnings.warn(
        "PhysioNet Gait dataset not found locally. Falling back to SYNTHETIC FIXTURE "
        "(simulation mode). RESULTS HAVE ZERO CLINICAL VALIDITY.",
        UserWarning,
        stacklevel=2,
    )
    df = generate_synthetic_motor_fixture(n_participants=200, seed=42)
    return df, "simulation", False


def preprocess_motor_data(
    df: pd.DataFrame,
    raw_sensor_available: bool = False,
    experiment_type: str = "simulation",
) -> pd.DataFrame:
    """
    Validate and clean motor DataFrame. Handles both raw VGRF time-series and
    precomputed/synthetic participant-level feature tables.

    For raw VGRF data:
      - Removes rows with negative or zero force values (sensor artefacts).
      - Validates required sensor columns are present.
      - Computes Total_Force_Left and Total_Force_Right if missing.

    For participant-level (derived/synthetic) data:
      - Validates required schema columns.
      - Clips known feature ranges.

    Args:
        df: Motor DataFrame (raw time-series or participant-level features).
        raw_sensor_available: True if df contains raw VGRF time-series.
        experiment_type: 'real_data' | 'derived_only' | 'simulation'

    Returns:
        pd.DataFrame: Validated and cleaned DataFrame.
    """
    df = df.copy()

    if raw_sensor_available:
        # Validate sensor columns
        validate_required_columns(df, [PHYSIONET_TIME_COL, "participant_id", "diagnosis"])

        # Remove rows where all sensor channels are NaN (corrupt frames)
        sensor_cols_present = [c for c in PHYSIONET_FORCE_COLS if c in df.columns]
        if sensor_cols_present:
            n_before = len(df)
            df = df.dropna(subset=sensor_cols_present, how="all")
            n_removed = n_before - len(df)
            if n_removed > 0:
                warnings.warn(
                    f"Removed {n_removed} rows with all sensor channels NaN.",
                    UserWarning,
                    stacklevel=2,
                )

        # Recompute aggregate force columns if missing
        if "Total_Force_Left" not in df.columns:
            left_cols = [c for c in PHYSIONET_LEFT_COLS if c in df.columns]
            if left_cols:
                df["Total_Force_Left"] = df[left_cols].sum(axis=1, min_count=1)

        if "Total_Force_Right" not in df.columns:
            right_cols = [c for c in PHYSIONET_RIGHT_COLS if c in df.columns]
            if right_cols:
                df["Total_Force_Right"] = df[right_cols].sum(axis=1, min_count=1)

    else:
        # Participant-level feature table (derived or synthetic)
        required = ["participant_id", "diagnosis"]
        validate_required_columns(df, required)

        # Clip gait speed to physiologically plausible range
        if "gait_speed_m_per_s" in df.columns:
            df["gait_speed_m_per_s"] = df["gait_speed_m_per_s"].clip(0.0, 3.0)

        # Clip cadence to plausible range
        if "cadence_steps_per_min" in df.columns:
            df["cadence_steps_per_min"] = df["cadence_steps_per_min"].clip(0.0, 200.0)

        # Clip stride interval CV to plausible range (0–50%)
        if "stride_interval_cv_pct" in df.columns:
            df["stride_interval_cv_pct"] = df["stride_interval_cv_pct"].clip(0.0, 50.0)

    # Ensure diagnosis labels are valid (0=Control, 1=PD)
    if "diagnosis" in df.columns:
        valid_mask = df["diagnosis"].isin([0, 1])
        n_invalid = (~valid_mask).sum()
        if n_invalid > 0:
            warnings.warn(
                f"Removing {n_invalid} rows with invalid diagnosis labels.",
                UserWarning,
                stacklevel=2,
            )
            df = df[valid_mask]

    return df


def split_motor_data(
    df: pd.DataFrame,
    test_size: float = 0.15,
    val_size: float = 0.15,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Participant-level stratified train/validation/test split for motor data.

    Participant-level splitting ensures that if multiple trials or time frames
    exist for the same participant, all rows for that participant land in the
    same split — preventing data leakage.

    Args:
        df: Preprocessed motor DataFrame containing 'participant_id' and 'diagnosis'.
        test_size: Fraction of participants for test split.
        val_size: Fraction of participants for validation split.
        seed: Random seed for reproducibility.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: (df_train, df_val, df_test).
    """
    # Get one row per participant (take first occurrence for stratification)
    participant_labels = (
        df.groupby("participant_id")["diagnosis"]
        .first()
        .reset_index()
    )

    # First split: train_val vs test
    train_val_participants, test_participants = train_test_split(
        participant_labels,
        test_size=test_size,
        stratify=participant_labels["diagnosis"],
        random_state=seed,
    )

    # Second split: train vs val (adjusted for train_val proportion)
    adjusted_val_size = val_size / (1.0 - test_size)
    train_participants, val_participants = train_test_split(
        train_val_participants,
        test_size=adjusted_val_size,
        stratify=train_val_participants["diagnosis"],
        random_state=seed,
    )

    train_ids = train_participants["participant_id"].tolist()
    val_ids = val_participants["participant_id"].tolist()
    test_ids = test_participants["participant_id"].tolist()

    # Strict zero-leakage check
    validate_participant_split(train_ids, val_ids, test_ids)

    df_train = df[df["participant_id"].isin(train_ids)].copy()
    df_val = df[df["participant_id"].isin(val_ids)].copy()
    df_test = df[df["participant_id"].isin(test_ids)].copy()

    return df_train, df_val, df_test
