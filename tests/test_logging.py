import pytest
from pathlib import Path
from src.config import load_config
from src.logging_utils import setup_logging, get_logger


def test_logging_setup():
    """Verify setup_logging configures root logger and creates log file directory."""
    config = load_config("config.yaml")
    setup_logging(config)

    logger = get_logger("test_module")
    assert logger is not None

    logger.info("Test log entry")

    log_file_str = config["logging"].get("file")
    if log_file_str:
        log_file_path = Path(log_file_str)
        assert log_file_path.exists()
