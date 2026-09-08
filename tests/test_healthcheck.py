import pytest
from src.healthcheck import run_healthcheck


def test_healthcheck_runs():
    """Verify that run_healthcheck executes and returns a boolean status and a list of failure descriptions."""
    is_success, failures = run_healthcheck("config.yaml")
    assert isinstance(is_success, bool)
    assert isinstance(failures, list)
    assert is_success is True
    assert len(failures) == 0
