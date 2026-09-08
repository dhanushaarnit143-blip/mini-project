import pytest
from pathlib import Path
from src.config import load_config, validate_config, get_path


def test_load_config():
    """Verify that config.yaml loads correctly and contains required top-level keys."""
    config = load_config("config.yaml")
    assert isinstance(config, dict)
    assert "project" in config
    assert "paths" in config
    assert "logging" in config
    assert "claims" in config
    assert "phase_status" in config


def test_validate_config():
    """Verify validate_config behavior with valid and invalid dict inputs."""
    config = load_config("config.yaml")
    assert validate_config(config) is True

    with pytest.raises(ValueError):
        validate_config({})


def test_get_path():
    """Verify get_path returns pathlib.Path objects for configured path keys."""
    config = load_config("config.yaml")
    data_raw_path = get_path(config, "data_raw")
    assert isinstance(data_raw_path, Path)
    assert str(data_raw_path).replace("\\", "/") == "data/raw"


def test_missing_config():
    """Verify FileNotFoundError when loading a non-existent config file."""
    with pytest.raises(FileNotFoundError):
        load_config("non_existent_config.yaml")
