from pathlib import Path
from typing import Dict, Any
import yaml

REQUIRED_KEYS = [
    ("project", "name"),
    ("project", "version"),
    ("project", "seed"),
    ("project", "environment"),
    ("paths", "data_raw"),
    ("paths", "data_interim"),
    ("paths", "data_processed"),
    ("paths", "data_external"),
    ("paths", "data_metadata"),
    ("paths", "models"),
    ("paths", "evaluation"),
    ("paths", "logs"),
    ("logging", "level"),
    ("logging", "file"),
    ("logging", "console"),
    ("claims", "clinical_diagnosis"),
    ("claims", "research_prototype"),
    ("claims", "novelty_statement"),
    ("phase_status", "phase0"),
]


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Loads and validates configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file.
        
    Returns:
        dict: Validated configuration dictionary.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
        
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    if not isinstance(config, dict):
        raise ValueError(f"Invalid configuration format in '{config_path}'. Expected a dictionary.")
        
    validate_config(config)
    return config


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validates that all required sections and keys exist in the configuration.
    
    Args:
        config: Configuration dictionary.
        
    Returns:
        bool: True if valid.
        
    Raises:
        ValueError: If required keys are missing or invalid.
    """
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a dictionary.")
        
    missing_keys = []
    for section, key in REQUIRED_KEYS:
        if section not in config or not isinstance(config[section], dict) or key not in config[section]:
            missing_keys.append(f"{section}.{key}")
            
    if missing_keys:
        raise ValueError(f"Missing required configuration keys: {', '.join(missing_keys)}")
        
    return True


def get_path(config: Dict[str, Any], key: str) -> Path:
    """
    Retrieves a path from the configuration dictionary as a pathlib.Path object.
    
    Args:
        config: Configuration dictionary.
        key: Path key name (e.g. 'data_raw', 'models', 'logs').
        
    Returns:
        Path: Path object for the specified key.
    """
    if "paths" not in config or key not in config["paths"]:
        raise KeyError(f"Path key '{key}' not found in configuration paths.")
    return Path(config["paths"][key])
