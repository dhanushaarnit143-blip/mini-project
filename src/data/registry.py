"""
Dataset Registry Module for MPF-PD.

Provides metadata loading, metadata validation, lookup by dataset ID,
and category filtering across metadata YAML files in data/metadata/.
"""

import os
from pathlib import Path
from typing import Dict, List, Any
import yaml

VALID_CATEGORIES = {"A", "B", "C", "D", "E"}
VALID_STATUSES = {
    "identified",
    "accessible",
    "restricted",
    "not_suitable",
    "pretraining_only",
    "synthetic_fixture",
}

REQUIRED_METADATA_FIELDS = [
    "dataset_id",
    "name",
    "official_source",
    "access_requirements",
    "license",
    "category",
    "modalities",
    "participant_count",
    "pd_labels",
    "prodromal_labels",
    "control_labels",
    "variables",
    "file_formats",
    "missing_data",
    "limitations",
    "intended_use",
    "local_path",
    "download_instructions",
    "status",
]


def validate_dataset_metadata(metadata: Dict[str, Any]) -> bool:
    """
    Validate that a dataset metadata dictionary contains all required fields
    and that its category and status are valid according to MPF-PD rules.

    Args:
        metadata: Dictionary loaded from a metadata YAML file.

    Returns:
        bool: True if metadata is valid.

    Raises:
        ValueError: If a required field is missing or an invalid category/status is found.
    """
    if not isinstance(metadata, dict):
        raise ValueError("Dataset metadata must be a dictionary.")

    missing_fields = [
        field for field in REQUIRED_METADATA_FIELDS if field not in metadata
    ]
    if missing_fields:
        raise ValueError(
            f"Dataset metadata for '{metadata.get('dataset_id', 'unknown')}' "
            f"is missing required fields: {missing_fields}"
        )

    category = metadata.get("category")
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Invalid category '{category}' for dataset '{metadata.get('dataset_id')}'. "
            f"Must be one of {sorted(list(VALID_CATEGORIES))}."
        )

    status = metadata.get("status")
    if status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}' for dataset '{metadata.get('dataset_id')}'. "
            f"Must be one of {sorted(list(VALID_STATUSES))}."
        )

    if not isinstance(metadata.get("modalities"), list):
        raise ValueError(
            f"'modalities' must be a list in dataset metadata '{metadata.get('dataset_id')}'."
        )

    return True


def load_dataset_registry(metadata_dir: str = "data/metadata") -> Dict[str, Dict[str, Any]]:
    """
    Load all metadata YAML files from the specified metadata directory.

    Args:
        metadata_dir: Directory path containing .yaml/.yml metadata files.

    Returns:
        dict: Mapping of dataset_id -> dataset_metadata_dict.

    Raises:
        FileNotFoundError: If metadata_dir does not exist.
    """
    path = Path(metadata_dir)
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Metadata directory not found: {metadata_dir}")

    registry = {}
    for file_path in sorted(path.glob("*.yaml")) + sorted(path.glob("*.yml")):
        with open(file_path, "r", encoding="utf-8") as f:
            metadata = yaml.safe_load(f)
            if metadata and isinstance(metadata, dict):
                validate_dataset_metadata(metadata)
                dataset_id = metadata["dataset_id"]
                registry[dataset_id] = metadata

    return registry


def get_dataset_metadata(dataset_id: str, metadata_dir: str = "data/metadata") -> Dict[str, Any]:
    """
    Retrieve metadata for a single dataset by dataset_id.

    Args:
        dataset_id: Identifier of the target dataset.
        metadata_dir: Directory path containing metadata YAML files.

    Returns:
        dict: Dataset metadata dictionary.

    Raises:
        KeyError: If dataset_id is not found in the registry.
    """
    registry = load_dataset_registry(metadata_dir=metadata_dir)
    if dataset_id not in registry:
        raise KeyError(f"Dataset '{dataset_id}' not found in registry at '{metadata_dir}'.")
    return registry[dataset_id]


def list_datasets_by_category(category: str, metadata_dir: str = "data/metadata") -> List[str]:
    """
    List dataset_ids belonging to a specific category (A, B, C, D, E).

    Args:
        category: Category string ('A', 'B', 'C', 'D', 'E').
        metadata_dir: Directory path containing metadata YAML files.

    Returns:
        list: List of dataset_ids matching the category.
    """
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Invalid category '{category}'. Must be one of {sorted(list(VALID_CATEGORIES))}."
        )

    registry = load_dataset_registry(metadata_dir=metadata_dir)
    return [
        dataset_id
        for dataset_id, meta in registry.items()
        if meta.get("category") == category
    ]
