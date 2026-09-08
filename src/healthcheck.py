import sys
import os
from pathlib import Path
from typing import List, Tuple


def run_healthcheck(config_path: str = "config.yaml") -> Tuple[bool, List[str]]:
    """
    Executes environment and architecture checks for MPF-PD Phase 0.
    
    Args:
        config_path: Path to configuration YAML file.
        
    Returns:
        Tuple[bool, List[str]]: (Success boolean, list of failure messages).
    """
    failures = []

    # 1. Python version check (>= 3.10)
    if sys.version_info < (3, 10):
        failures.append(f"Python version must be >= 3.10 (Current: {sys.version.split()[0]})")

    # 2. Current working directory check
    cwd = Path.cwd()
    if not cwd.exists():
        failures.append("Current working directory does not exist.")

    # 3 & 4. config.yaml exists and loads
    config = None
    try:
        from src.config import load_config, get_path
        config = load_config(config_path)
    except Exception as e:
        failures.append(f"config.yaml load error: {e}")

    if config:
        # 5. Required directories exist and are writable
        required_paths = [
            "data_raw", "data_interim", "data_processed",
            "data_external", "data_metadata", "models",
            "evaluation", "logs"
        ]
        for path_key in required_paths:
            try:
                dir_path = get_path(config, path_key)
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                
                # Test write access
                test_file = dir_path / ".write_test"
                test_file.touch()
                test_file.unlink()
            except Exception as e:
                failures.append(f"Directory write check failed for '{path_key}': {e}")

        # 6. Core imports check
        try:
            import src.config
            import src.logging_utils
            import src.seeds
        except Exception as e:
            failures.append(f"Core module import failed: {e}")

        # 7. Logging check
        try:
            from src.logging_utils import setup_logging, get_logger
            setup_logging(config)
            logger = get_logger("healthcheck")
            logger.info("Executed healthcheck logging test.")
        except Exception as e:
            failures.append(f"Logging setup or write failed: {e}")

        # 8. Seed utilities check
        try:
            from src.seeds import set_global_seed
            seed_val = config.get("project", {}).get("seed", 42)
            set_global_seed(seed_val)
        except Exception as e:
            failures.append(f"Seed initialization failed: {e}")

    # 9. pytest availability check
    try:
        import pytest
    except ImportError:
        failures.append("pytest package is not installed or importable.")

    is_success = len(failures) == 0
    return is_success, failures


def main() -> int:
    """
    Main entry point for CLI healthcheck execution.
    """
    is_success, failures = run_healthcheck()
    if is_success:
        print("HEALTHCHECK PASS")
        return 0
    else:
        print("HEALTHCHECK FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
