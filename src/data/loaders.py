"""
Dataset Loaders Module for MPF-PD.

Provides dataset loading utilities with strict local file verification.
Does NOT download datasets automatically; raises DataNotAvailableError if local files
are missing. Includes placeholders for future audio and retinal image loading.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd

from .registry import get_dataset_metadata, load_dataset_registry


class DataNotAvailableError(FileNotFoundError):
    """Exception raised when a requested dataset is not available locally."""
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

    # Check if target_path points to a specific file or directory
    if target_path.is_file():
        return load_dataset_from_local_path(str(target_path))

    if target_path.is_dir():
        # Look for CSV or Parquet files within the directory
        csv_files = list(target_path.glob("*.csv"))
        parquet_files = list(target_path.glob("*.parquet")) + list(target_path.glob("*.pq"))

        if parquet_files:
            return pd.read_parquet(parquet_files[0])
        elif csv_files:
            return pd.read_csv(csv_files[0])

    # If file/directory is not found or empty
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


def load_retinal_image_dataset(
    dataset_id: str,
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Placeholder signature for loading retinal image datasets (Category C fundus/OCT images).

    Args:
        dataset_id: Retinal dataset ID (e.g., 'retinal_fundus_pretraining', 'oct500').
        config: Configuration dictionary specifying image transformations, image sizing, and batching.

    Returns:
        PyTorch Dataset or DataLoader object (to be implemented in future phases).

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
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Placeholder signature for loading audio speech datasets (Category B voice recordings).

    Args:
        dataset_id: Voice dataset ID (e.g., 'uci_voice', 'mpower').
        config: Configuration dictionary specifying sampling rate, window size, and feature extraction parameters.

    Returns:
        PyTorch Audio Dataset or audio waveform dictionary (to be implemented in future phases).

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
