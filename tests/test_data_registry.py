"""
Unit tests for src/data/registry.py
"""

import pytest
from src.data.registry import (
    load_dataset_registry,
    get_dataset_metadata,
    list_datasets_by_category,
    validate_dataset_metadata,
    REQUIRED_METADATA_FIELDS,
)


def test_load_dataset_registry():
    """Verify that all YAML metadata files load successfully from data/metadata."""
    registry = load_dataset_registry("data/metadata")
    assert isinstance(registry, dict)
    assert len(registry) >= 8

    # Verify expected candidate datasets exist in registry
    expected_ids = {
        "ppmi",
        "predict_pd",
        "uci_voice",
        "physionet_gait",
        "mpower",
        "retinal_fundus_pretraining",
        "oct500",
        "synthetic_fixture",
    }
    for dataset_id in expected_ids:
        assert dataset_id in registry, f"Dataset '{dataset_id}' missing from registry."


def test_metadata_required_fields():
    """Verify that every dataset metadata file contains all required fields."""
    registry = load_dataset_registry("data/metadata")
    for dataset_id, metadata in registry.items():
        for field in REQUIRED_METADATA_FIELDS:
            assert field in metadata, f"Field '{field}' missing in metadata for '{dataset_id}'."


def test_metadata_categories_validity():
    """Verify that every dataset in registry has a valid category (A, B, C, D, E)."""
    registry = load_dataset_registry("data/metadata")
    valid_categories = {"A", "B", "C", "D", "E"}
    for dataset_id, metadata in registry.items():
        category = metadata.get("category")
        assert category in valid_categories, f"Invalid category '{category}' for '{dataset_id}'."


def test_get_dataset_metadata():
    """Verify get_dataset_metadata returns correct metadata for 'ppmi' and raises KeyError for unknown ID."""
    ppmi_meta = get_dataset_metadata("ppmi", metadata_dir="data/metadata")
    assert ppmi_meta["dataset_id"] == "ppmi"
    assert ppmi_meta["category"] == "A"

    with pytest.raises(KeyError):
        get_dataset_metadata("non_existent_dataset", metadata_dir="data/metadata")


def test_list_datasets_by_category():
    """Verify list_datasets_by_category correctly lists category A, B, C datasets."""
    cat_a = list_datasets_by_category("A", metadata_dir="data/metadata")
    assert "ppmi" in cat_a

    cat_b = list_datasets_by_category("B", metadata_dir="data/metadata")
    assert "uci_voice" in cat_b
    assert "physionet_gait" in cat_b

    cat_c = list_datasets_by_category("C", metadata_dir="data/metadata")
    assert "retinal_fundus_pretraining" in cat_c
    assert "oct500" in cat_c

    with pytest.raises(ValueError):
        list_datasets_by_category("Z", metadata_dir="data/metadata")


def test_validate_dataset_metadata_errors():
    """Verify validate_dataset_metadata raises ValueError on invalid fields, category, or status."""
    invalid_meta = {
        "dataset_id": "bad_dataset",
        "name": "Bad Dataset",
        "category": "INVALID_CAT",  # invalid category
    }
    with pytest.raises(ValueError):
        validate_dataset_metadata(invalid_meta)
