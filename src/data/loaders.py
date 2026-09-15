"""
Dataset Loaders Module for MPF-PD.

Provides dataset loading utilities with strict local file verification.
Does NOT fabricate data or download restricted datasets automatically.
Raises DataNotAvailableError if local files are missing, clearly guiding the user
to credentialed download instructions.

Includes:
- Generic tabular loader with format detection (.csv, .parquet).
- Dataset-specific loaders for PPMI, UCI Voice, PhysioNet Gait.
- Dedicated loader and generator for Category E synthetic test fixtures.
- Formal placeholder signatures for raw retinal image and audio time-series pipelines.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from .registry import get_dataset_metadata, load_dataset_registry

logger = logging.getLogger("mpf.data.loaders")


class DataNotAvailableError(FileNotFoundError):
    """Exception raised when a requested dataset is not available locally."""
    pass


class InvalidMultimodalCohortError(ValueError):
    """Exception raised when an attempt is made to merge non-overlapping participant cohorts."""
    pass


def load_dataset_from_local_path(path: str) -> pd.DataFrame:
    """
    Load a tabular dataset directly from a local file path (CSV or Parquet).

    Args:
        path: Path to the target CSV or Parquet file.

    Returns:
        pd.DataFrame: Loaded DataFrame.

    Raises:
        DataNotAvailableError: If the file does not exist locally.
        ValueError: If the file format is unsupported.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise DataNotAvailableError(
            f"Dataset file not found at local path: '{path}'. "
            f"Please download the dataset manually per dataset metadata instructions."
        )

    if file_path.suffix.lower() == ".csv":
        return pd.read_csv(file_path)
    elif file_path.suffix.lower() in [".parquet", ".pq"]:
        return pd.read_parquet(file_path)
    else:
        raise ValueError(
            f"Unsupported file format '{file_path.suffix}' for path '{path}'. "
            f"Expected .csv or .parquet."
        )


def load_tabular_dataset(dataset_id: str, config: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Load a tabular dataset by dataset_id using registry metadata.

    Args:
        dataset_id: Identifier of the target dataset.
        config: Optional configuration dictionary (e.g., specifying metadata_dir or custom path).

    Returns:
        pd.DataFrame: Loaded tabular data.

    Raises:
        DataNotAvailableError: If the dataset files are missing locally.
    """
    metadata_dir = config.get("metadata_dir", "data/metadata") if config else "data/metadata"
    metadata = get_dataset_metadata(dataset_id, metadata_dir=metadata_dir)

    local_path = metadata.get("local_path", "")
    target_path = Path(local_path)

    # Check if target_path points to a specific file
    if target_path.is_file():
        return load_dataset_from_local_path(str(target_path))

    # Check if target_path is a directory containing tabular files
    if target_path.is_dir():
        parquet_files = list(target_path.glob("*.parquet")) + list(target_path.glob("*.pq"))
        if parquet_files:
            return pd.read_parquet(parquet_files[0])
        csv_files = list(target_path.glob("*.csv"))
        if csv_files:
            return pd.read_csv(csv_files[0])

    # If dataset is Category E synthetic fixture, allow programmatic fallback
    if metadata.get("category") == "E" or dataset_id == "synthetic_fixture":
        return load_synthetic_fixture(str(target_path))

    # Real dataset files are missing locally
    download_instr = metadata.get("download_instructions", "Refer to data/DATASETS.md.")
    raise DataNotAvailableError(
        f"Dataset '{dataset_id}' is not available at local path '{local_path}'. "
        f"Status: {metadata.get('status')}.\n"
        f"Download Instructions: {download_instr}"
    )


def list_available_local_datasets(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    List dataset_ids that exist and are available on the local filesystem.

    Args:
        config: Optional configuration dictionary.

    Returns:
        list: Dataset IDs currently accessible locally.
    """
    metadata_dir = config.get("metadata_dir", "data/metadata") if config else "data/metadata"
    registry = load_dataset_registry(metadata_dir=metadata_dir)
    available = []

    for dataset_id, meta in registry.items():
        local_path = Path(meta.get("local_path", ""))
        if local_path.is_file():
            available.append(dataset_id)
        elif local_path.is_dir() and (list(local_path.glob("*.csv")) or list(local_path.glob("*.parquet"))):
            available.append(dataset_id)

    return available


def load_synthetic_fixture(
    filepath: Optional[str] = None,
    n_participants: int = 100,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Load or generate an aligned synthetic test fixture for software verification (Category E).

    CRITICAL NOTE:
    This fixture contains entirely artificial mathematical data.
    It carries ZERO clinical validity and must NEVER be used to make diagnostic claims.

    Args:
        filepath: Optional path to save/load the CSV fixture.
        n_participants: Number of mock participants to generate if file absent.
        seed: Random seed for deterministic generation.

    Returns:
        pd.DataFrame: Aligned synthetic multi-biomarker DataFrame.
    """
    target_path = Path(filepath) if filepath else Path("tests/fixtures/synthetic_fixture.csv")
    if target_path.is_file():
        return pd.read_csv(target_path)

    # Generate synthetic fixture deterministically
    rng = np.random.RandomState(seed)
    participant_ids = [f"P{i+1:04d}" for i in range(n_participants)]
    diagnoses = rng.choice([0, 1, 2], size=n_participants, p=[0.35, 0.30, 0.35])

    # Modality 1: Olfactory (UPSIT: Controls ~34, Prodromal ~26, PD ~18)
    upsit = np.where(
        diagnoses == 0,
        rng.normal(34.0, 3.0, size=n_participants),
        np.where(diagnoses == 1, rng.normal(26.0, 4.0, size=n_participants), rng.normal(18.0, 4.5, size=n_participants))
    )
    upsit = np.clip(np.round(upsit), 5, 40).astype(float)

    # Modality 2: RBD Sleep (RBDSQ score 0-13: Controls low, Prodromal/PD high)
    rbd = np.where(
        diagnoses == 0,
        rng.binomial(13, 0.15, size=n_participants),
        np.where(diagnoses == 1, rng.binomial(13, 0.60, size=n_participants), rng.binomial(13, 0.70, size=n_participants))
    ).astype(float)

    # Modality 3: Motor / Gait (UPDRS Motor score 0-60)
    updrs_motor = np.where(
        diagnoses == 0,
        rng.normal(4.0, 2.0, size=n_participants),
        np.where(diagnoses == 1, rng.normal(14.0, 5.0, size=n_participants), rng.normal(28.0, 8.0, size=n_participants))
    )
    updrs_motor = np.clip(np.round(updrs_motor), 0, 60).astype(float)

    # Modality 4: Voice / Speech Dysphonia (Pitch SD in Hz)
    voice_pitch_sd = np.where(
        diagnoses == 0,
        rng.normal(12.0, 2.0, size=n_participants),
        rng.normal(6.5, 2.5, size=n_participants)
    )
    voice_pitch_sd = np.clip(np.round(voice_pitch_sd, 2), 1.0, 25.0)

    # Modality 5: Retinal RNFL Thickness in micrometers (Controls ~98, PD ~78)
    rnfl = np.where(
        diagnoses == 0,
        rng.normal(98.0, 7.0, size=n_participants),
        rng.normal(80.0, 9.0, size=n_participants)
    )
    rnfl = np.clip(np.round(rnfl, 1), 50.0, 130.0)

    df = pd.DataFrame({
        "participant_id": participant_ids,
        "upsit_score": upsit,
        "rbd_score": rbd,
        "updrs_motor": updrs_motor,
        "voice_pitch_sd": voice_pitch_sd,
        "retinal_rnfl_thickness": rnfl,
        "diagnosis": diagnoses,
    })

    # Controlled 10% missingness in non-critical columns for missingness testing
    mask_voice = rng.rand(n_participants) < 0.10
    df.loc[mask_voice, "voice_pitch_sd"] = np.nan
    mask_rnfl = rng.rand(n_participants) < 0.10
    df.loc[mask_rnfl, "retinal_rnfl_thickness"] = np.nan

    # Save to disk if directory can be created
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(target_path, index=False)
        logger.info(f"Generated synthetic fixture at {target_path}")
    except Exception as e:
        logger.warning(f"Could not persist synthetic fixture to {target_path}: {e}")

    return df


def load_uci_voice(path: Optional[str] = None) -> pd.DataFrame:
    """
    Load the UCI Parkinson's Telemonitoring Dataset (Category B).

    Args:
        path: Optional override path. Defaults to 'data/raw/uci_voice/parkinsons_telemonitoring.data'.

    Returns:
        pd.DataFrame: Loaded tabular voice dataset.

    Raises:
        DataNotAvailableError: If raw dataset is not downloaded.
    """
    default_path = Path(path) if path else Path("data/raw/uci_voice/parkinsons_telemonitoring.data")
    if not default_path.exists():
        # Also check for .csv extension
        csv_path = default_path.with_suffix(".csv")
        if csv_path.exists():
            return pd.read_csv(csv_path)
        raise DataNotAvailableError(
            f"UCI Voice dataset not found at '{default_path}'. "
            "Please download from: https://archive.ics.uci.edu/dataset/189/parkinsons+telemonitoring "
            "and place in data/raw/uci_voice/."
        )
    return pd.read_csv(default_path)


def load_physionet_gait(path: Optional[str] = None) -> pd.DataFrame:
    """
    Load PhysioNet Gait in Parkinson's Disease summary or time-series (Category B).

    Args:
        path: Optional directory or file path. Defaults to 'data/raw/physionet_gait/'.

    Returns:
        pd.DataFrame: Gait force or demographic dataset.

    Raises:
        DataNotAvailableError: If raw dataset is not downloaded.
    """
    target_dir = Path(path) if path else Path("data/raw/physionet_gait/")
    if not target_dir.exists():
        raise DataNotAvailableError(
            f"PhysioNet Gait dataset directory not found at '{target_dir}'. "
            "Please download from: https://physionet.org/content/gaitpdb/1.0.0/ "
            "and place in data/raw/physionet_gait/."
        )
    csv_files = list(target_dir.glob("*.csv")) + list(target_dir.glob("*.txt"))
    if not csv_files:
        raise DataNotAvailableError(
            f"No Gait data files found in '{target_dir}'. Download from PhysioNet."
        )
    return pd.read_csv(csv_files[0])


def load_ppmi_tabular(modality: str = "all", path: Optional[str] = None) -> pd.DataFrame:
    """
    Load PPMI tabular clinical / biomarker tables (Category A).

    Args:
        modality: Target modality table ('olfactory', 'rbd', 'motor', 'all').
        path: Optional directory path. Defaults to 'data/raw/ppmi/'.

    Returns:
        pd.DataFrame: PPMI tabular data.

    Raises:
        DataNotAvailableError: If PPMI files are not present locally.
    """
    target_dir = Path(path) if path else Path("data/raw/ppmi/")
    if not target_dir.exists():
        raise DataNotAvailableError(
            f"PPMI clinical data not found at '{target_dir}'. "
            "PPMI requires approved Data Use Agreement (DUA). "
            "Apply at: https://www.ppmi-info.org/access-data-specimens/download-data."
        )
    csv_files = list(target_dir.glob("*.csv"))
    if not csv_files:
        raise DataNotAvailableError(
            f"No PPMI CSV files located in '{target_dir}'. "
            "Download clinical tables via LONI Image Data Archive."
        )
    return pd.read_csv(csv_files[0])


def load_retinal_image_dataset(
    dataset_id: str,
    config: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Placeholder signature for loading retinal image datasets (Category C fundus/OCT images).

    Args:
        dataset_id: Retinal dataset ID (e.g., 'retinal_fundus_pretraining', 'oct500').
        config: Configuration dictionary specifying image transformations, sizing, and batching.

    Returns:
        PyTorch Dataset or DataLoader object (Phase 2/3).

    Raises:
        DataNotAvailableError: If local retinal image files do not exist.
        NotImplementedError: Placeholder signature for future phase image loading pipeline.
    """
    metadata_dir = config.get("metadata_dir", "data/metadata") if config else "data/metadata"
    metadata = get_dataset_metadata(dataset_id, metadata_dir=metadata_dir)
    local_path = Path(metadata.get("local_path", ""))

    if not local_path.exists():
        raise DataNotAvailableError(
            f"Retinal image dataset '{dataset_id}' not found locally at '{local_path}'."
        )

    raise NotImplementedError(
        "Retinal image loading pipeline (PyTorch Dataset/DataLoader) will be implemented in Phase 2/3."
    )


def load_audio_speech_dataset(
    dataset_id: str,
    config: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Placeholder signature for loading audio speech datasets (Category B voice recordings).

    Args:
        dataset_id: Voice dataset ID (e.g., 'uci_voice', 'mpower').
        config: Configuration dictionary specifying sampling rate, window size, and feature parameters.

    Returns:
        PyTorch Audio Dataset or audio waveform dictionary (Phase 2/3).

    Raises:
        DataNotAvailableError: If local audio files do not exist.
        NotImplementedError: Placeholder signature for future phase audio processing pipeline.
    """
    metadata_dir = config.get("metadata_dir", "data/metadata") if config else "data/metadata"
    metadata = get_dataset_metadata(dataset_id, metadata_dir=metadata_dir)
    local_path = Path(metadata.get("local_path", ""))

    if not local_path.exists():
        raise DataNotAvailableError(
            f"Audio speech dataset '{dataset_id}' not found locally at '{local_path}'."
        )

    raise NotImplementedError(
        "Audio speech loading pipeline (torchaudio / librosa waveform extraction) will be implemented in Phase 2/3."
    )
